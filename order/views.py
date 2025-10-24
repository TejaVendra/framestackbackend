from django.shortcuts import render
from .serilizers import OrderSerializer
# Create your views here.

import logging
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .utils import reset_expired_plans

logger = logging.getLogger(__name__)

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
        reset_expired_plans(user)
        user.credit += int(credits)
        user.plan = plan
        user.save()

        Order.objects.create(
            user=user,
            plan=plan,
            credits=credits,
            status="completed"
        )

        # ✅ Send email notification to the user
        self._send_purchase_email(user, plan, credits)

        return Response({
            "message": "Payment successful!",
            "plan": user.plan,
            "credits": user.credit
        })

    def _send_purchase_email(self, user, plan, added_credits):
        """
        Send a confirmation email to the user after successful plan purchase.
        """
        if not user.email:
            logger.warning(f"Cannot send email: User {user.name} has no email address.")
            return

        # Email subject
        subject = f"Welcome to {plan} - Payment Confirmed!"

        # Email message (HTML format for better UX)
        message_html = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #4F46E5; text-align: center;">Welcome to FrameStack! 🎉</h2>
                <p>Hi {user.name or user.name or 'User '},</p>
                <p>Thank you for purchasing the <strong>{plan}</strong> plan! Your payment has been processed successfully.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Plan Details:</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Plan:</strong> {plan}</li>
                        <li><strong>Credits Added:</strong> {added_credits}</li>
                        <li><strong>Total Credits:</strong> {user.credit}</li>
                    </ul>
                </div>
                
                <p>With this plan, you can now build amazing websites without coding. Start creating your first project in the dashboard!</p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/dashboard" style="background: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Go to Dashboard</a>
                </div>
                
                <p>If you have any questions, our support team is here to help. Reply to this email or contact us at support@framestack.com.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="text-align: center; color: #666; font-size: 12px;">
                    Best regards,<br>
                    The FrameStack Team<br>
                    <a href="http://localhost:3000">framestack.com</a>
                </p>
            </body>
        </html>
        """

        # Plain text fallback (for email clients that don't support HTML)
        message_plain = f"""
        Welcome to FrameStack!

        Hi {user.name or user.name or 'User '},

        Thank you for purchasing the {plan} plan! Your payment has been processed successfully.

        Plan Details:
        - Plan: {plan}
        - Credits Added: {added_credits}
        - Total Credits: {user.credit}

        With this plan, you can now build amazing websites without coding. Start creating your first project in the dashboard!

        If you have any questions, our support team is here to help. Reply to this email or contact us at support@framestack.com.

        Best regards,
        The FrameStack Team
        framestack.com
        """

        try:
            send_mail(
                subject=subject,
                message=message_plain,  # Plain text required
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=message_html,  # Optional HTML version
                fail_silently=False,  # Set to True in production to avoid crashing on email failure
            )
            logger.info(f"Purchase email sent successfully to {user.email} for plan {plan}.")
        except Exception as e:
            logger.error(f"Failed to send purchase email to {user.email}: {str(e)}")
            # Don't raise here—payment is still successful



# views.py
class UserOrdersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user).order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
