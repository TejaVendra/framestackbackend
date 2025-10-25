from django.shortcuts import render
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .utils import reset_expired_plans
from .serilizers import OrderSerializer
import logging
from threading import Thread

logger = logging.getLogger(__name__)


# ✅ Reusable async email sender
def send_email_async(subject, plain_message, from_email, recipient_list, html_message=None):
    """
    Sends an email asynchronously (HTML + plain fallback).
    """
    def _send():
        try:
            if html_message:
                msg = EmailMultiAlternatives(subject, plain_message, from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=False)
            else:
                send_mail(subject, plain_message, from_email, recipient_list, fail_silently=False)
            logger.info(f"✅ Async email sent to {recipient_list}")
        except Exception as e:
            logger.error(f"❌ Failed to send async email to {recipient_list}: {e}")

    Thread(target=_send).start()


# 💳 1️⃣ Dummy Payment View (Simulates successful payment)
class DummyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan")
        credits = request.data.get("credits", 0)

        if not plan:
            return Response(
                {"error": "Plan is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # Reset expired plans before updating
        reset_expired_plans(user)

        # Update user plan and credits
        user.credit += int(credits)
        user.plan = plan
        user.save()

        # Save order
        Order.objects.create(
            user=user,
            plan=plan,
            credits=credits,
            status="completed"
        )

        # ✅ Send async confirmation email
        self._send_purchase_email_async(user, plan, credits)

        return Response({
            "message": "Payment successful!",
            "plan": user.plan,
            "credits": user.credit
        }, status=status.HTTP_200_OK)

    def _send_purchase_email_async(self, user, plan, added_credits):
        """
        Send purchase confirmation email asynchronously.
        """
        if not user.email:
            logger.warning(f"⚠️ Cannot send email: User {user.name} has no email address.")
            return

        subject = f"🎉 Welcome to {plan} Plan - Payment Confirmed!"

        # Plain text message
        message_plain = f"""
        Hi {user.name or 'User'},

        Thank you for purchasing the {plan} plan! Your payment has been processed successfully.

        Plan Details:
        - Plan: {plan}
        - Credits Added: {added_credits}
        - Total Credits: {user.credit}

        You can now start creating websites using your credits.

        — The FrameStack Team
        """

        # HTML message
        message_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4F46E5;">Welcome to FrameStack! 🎉</h2>
                <p>Hi <strong>{user.name or 'User'}</strong>,</p>
                <p>Thank you for purchasing the <strong>{plan}</strong> plan! Your payment was processed successfully.</p>

                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                    <h3>Plan Details:</h3>
                    <ul>
                        <li><strong>Plan:</strong> {plan}</li>
                        <li><strong>Credits Added:</strong> {added_credits}</li>
                        <li><strong>Total Credits:</strong> {user.credit}</li>
                    </ul>
                </div>

                <p>Start building amazing websites now from your dashboard!</p>

                <p>
                    <a href="http://localhost:3000/dashboard" 
                    style="background: #4F46E5; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">
                    Go to Dashboard</a>
                </p>

                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #666;">The FrameStack Team<br>
                <a href="http://localhost:3000" style="color: #4F46E5;">framestack.com</a></p>
            </body>
        </html>
        """

        # Call async email function
        send_email_async(
            subject=subject,
            plain_message=message_plain,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=message_html
        )


# 📦 2️⃣ Fetch all orders for the logged-in user
class UserOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user).order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
