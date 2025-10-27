from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from threading import Thread
import razorpay
import hmac
import hashlib
import logging

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
    UpdatePlanSerializer,
    PlanPurchaseSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
)
from utils.brevo_email import send_email_async_api
# Initialize logger


# Get User model and token generator
User = get_user_model()
token_generator = PasswordResetTokenGenerator()

# -------------------------------------------------------
# ✅ Utility: Send email asynchronously with proper error handling
# -------------------------------------------------------
import logging
import locale
import sys

# Configure logger with UTF-8 encoding
logger = logging.getLogger(__name__)

# -------------------------------------------------------
# ✅ Utility: Send email asynchronously with proper error handling
# -------------------------------------------------------
send_email_async = send_email_async_api  
# -------------------------------------------------------
# 1️⃣ Register (Signup) View
# -------------------------------------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()

        # Prepare welcome email
        subject = '🎉 Welcome to FrameStack!'
        
        # Plain text version
        message = (
            f'Hello {user.name},\n\n'
            f'Thank you for creating an account with FrameStack.\n'
            f'We\'re excited to have you onboard!\n\n'
            f'Here\'s what you can do next:\n'
            f'• Complete your profile\n'
            f'• Explore our features\n'
            f'• Choose a plan that suits your needs\n\n'
            f'If you have any questions, feel free to reach out to our support team.\n\n'
            f'Best regards,\n'
            f'The FrameStack Team'
        )
        
        # HTML version
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Welcome to FrameStack!</h1>
                </div>
                <div class="content">
                    <h2>Hello {user.name}!</h2>
                    <p>Thank you for creating an account with FrameStack. We're thrilled to have you as part of our community!</p>
                    
                    <h3>Here's what you can do next:</h3>
                    <ul>
                        <li>✨ Complete your profile</li>
                        <li>🚀 Explore our features</li>
                        <li>💎 Choose a plan that suits your needs</li>
                    </ul>
                    
                    <center>
                        <a href="https://framestack.onrender.com/dashboard" class="button">Go to Dashboard</a>
                    </center>
                    
                    <p style="margin-top: 30px;">If you have any questions, our support team is here to help!</p>
                </div>
                <div class="footer">
                    <p>© 2024 FrameStack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send welcome email asynchronously
        send_email_async(subject, message, [user.email], html_message)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response(
            {"message": "Account created successfully! Check your email for confirmation."},
            status=status.HTTP_201_CREATED
        )


# -------------------------------------------------------
# 2️⃣ Login View
# -------------------------------------------------------
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = authenticate(email=email, password=password)
        
        if user:
            refresh = RefreshToken.for_user(user)
            
            # Optional: Send login notification email
            if settings.SEND_LOGIN_NOTIFICATIONS:
                subject = '🔐 New Login to Your Account'
                message = (
                    f'Hello {user.name},\n\n'
                    f'A new login to your account was detected.\n'
                    f'If this wasn\'t you, please change your password immediately.\n\n'
                    f'— The FrameStack Security Team'
                )
                send_email_async(subject, message, [user.email])
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'plan': user.plan,
                    'credit': user.credit
                }
            })
        
        return Response(
            {'detail': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


# -------------------------------------------------------
# 3️⃣ Profile View
# -------------------------------------------------------
class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


# -------------------------------------------------------
# 4️⃣ Change Password View
# -------------------------------------------------------
class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self, queryset=None):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": "Wrong password."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Send confirmation email
        subject = '✅ Your Password Has Been Changed'
        
        message = (
            f'Hello {user.name},\n\n'
            f'Your password for your FrameStack account has been changed successfully.\n\n'
            f'When: {user.updated_at.strftime("%B %d, %Y at %I:%M %p")}\n\n'
            f'If this wasn\'t you, please:\n'
            f'1. Reset your password immediately\n'
            f'2. Contact our support team\n'
            f'3. Review your account activity\n\n'
            f'Stay secure,\n'
            f'The FrameStack Security Team 🔒'
        )
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .alert {{ background: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .success {{ background: #d4edda; border: 1px solid #28a745; padding: 15px; border-radius: 5px; }}
                .button {{ display: inline-block; padding: 10px 20px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">
                    <h2>✅ Password Changed Successfully</h2>
                </div>
                
                <p>Hello {user.name},</p>
                <p>Your password has been changed successfully.</p>
                
                <div class="alert">
                    <strong>⚠️ Security Alert</strong><br>
                    If you didn't make this change, your account may be compromised.
                    <br><br>
                    <a href="https://framestack.onrender.com/forgot-password" class="button">Reset Password Now</a>
                </div>
                
                <p>For your security, please:</p>
                <ul>
                    <li>Never share your password with anyone</li>
                    <li>Use a unique password for FrameStack</li>
                    <li>Enable two-factor authentication if available</li>
                </ul>
                
                <p>Best regards,<br>The FrameStack Security Team 🔒</p>
            </div>
        </body>
        </html>
        """
        
        send_email_async(subject, message, [user.email], html_message)

        return Response(
            {"detail": "Password updated successfully. Confirmation email sent."},
            status=status.HTTP_200_OK
        )


# -------------------------------------------------------
# 5️⃣ Forgot Password View - Send Reset Link
# -------------------------------------------------------
class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            
            # Build reset link
            frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else 'https://framestack.onrender.com'
            reset_link = f"{frontend_url}/reset-password/{uid}/{token}/"
            
            # Prepare email
            subject = '🔒 Reset Your Password - FrameStack'
            
            message = (
                f'Hello {user.name},\n\n'
                f'We received a request to reset your FrameStack account password.\n\n'
                f'Click the link below to set a new password:\n'
                f'{reset_link}\n\n'
                f'This link will expire in 24 hours.\n\n'
                f'If you didn\'t request this, please ignore this email.\n'
                f'Your password won\'t change until you create a new one.\n\n'
                f'— The FrameStack Team'
            )
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; background: #f9f9f9; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px; }}
                    .content {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .button {{ display: inline-block; padding: 15px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; border-radius: 5px; font-weight: bold; margin: 20px 0; }}
                    .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
                    .warning {{ background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🔒 Password Reset Request</h1>
                    </div>
                    
                    <div class="content">
                        <h2>Hello {user.name}!</h2>
                        
                        <p>We received a request to reset the password for your FrameStack account.</p>
                        
                        <center>
                            <a href="{reset_link}" class="button">Reset My Password</a>
                        </center>
                        
                        <p><strong>Or copy and paste this link:</strong><br>
                        <code style="background: #f4f4f4; padding: 10px; display: block; margin: 10px 0; word-break: break-all;">
                            {reset_link}
                        </code></p>
                        
                        <div class="warning">
                            <strong>⏰ This link expires in 24 hours</strong><br>
                            For security reasons, this password reset link will expire in 24 hours.
                        </div>
                        
                        <p><strong>Didn't request this?</strong><br>
                        If you didn't request a password reset, you can safely ignore this email. 
                        Your password won't be changed.</p>
                        
                        <p>For additional help, contact our support team.</p>
                    </div>
                    
                    <div class="footer">
                        <p>© 2024 FrameStack. All rights reserved.<br>
                        This is an automated message, please do not reply.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email asynchronously
            send_email_async(subject, message, [email], html_message)
            
            logger.info(f"Password reset email sent to {email}")
            
        except User.DoesNotExist:
            # Don't reveal if email exists (security best practice)
            logger.warning(f"Password reset attempted for non-existent email: {email}")
        
        # Always return the same response for security
        return Response(
            {'detail': 'If an account exists with this email, you will receive a password reset link.'},
            status=status.HTTP_200_OK
        )


# -------------------------------------------------------
# 6️⃣ Reset Password View - Confirm Reset
# -------------------------------------------------------
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def put(self, request, uidb64, token):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Decode user ID
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {'detail': 'Invalid reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is valid
        if not token_generator.check_token(user, token):
            return Response(
                {'detail': 'Reset link is invalid or has expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.validated_data['password'])
        user.save()
        
        # Send confirmation email
        subject = '✅ Password Reset Successful'
        
        message = (
            f'Hello {user.name},\n\n'
            f'Your password has been reset successfully.\n'
            f'You can now log in with your new password.\n\n'
            f'If you didn\'t make this change, please contact support immediately.\n\n'
            f'— The FrameStack Team'
        )
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .success {{ background: #d4edda; border: 1px solid #28a745; padding: 20px; border-radius: 5px; text-align: center; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">
                    <h2>✅ Password Reset Successful!</h2>
                </div>
                
                <p>Hello {user.name},</p>
                <p>Your password has been successfully reset. You can now log in with your new password.</p>
                
                <center>
                    <a href="https://framestack.onrender.com/login" class="button">Login Now</a>
                </center>
                
                <p style="margin-top: 30px;">If you didn't make this change, please contact our support team immediately.</p>
                
                <p>Best regards,<br>The FrameStack Team</p>
            </div>
        </body>
        </html>
        """
        
        send_email_async(subject, message, [user.email], html_message)
        
        return Response(
            {'detail': 'Password has been reset successfully.'},
            status=status.HTTP_200_OK
        )


# -------------------------------------------------------
# 7️⃣ Update Plan View
# -------------------------------------------------------
class UpdatePlanView(generics.UpdateAPIView):
    serializer_class = UpdatePlanSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        old_plan = user.plan
        
        response = super().update(request, *args, **kwargs)
        
        # Send plan update notification
        if old_plan != user.plan:
            subject = f'📊 Plan Updated to {user.plan}'
            
            message = (
                f'Hello {user.name},\n\n'
                f'Your FrameStack plan has been updated.\n\n'
                f'Previous Plan: {old_plan}\n'
                f'New Plan: {user.plan}\n'
                f'Current Credits: {user.credit}\n\n'
                f'Thank you for your continued support!\n\n'
                f'— The FrameStack Team'
            )
            
            send_email_async(subject, message, [user.email])
        
        return response


# -------------------------------------------------------
# 8️⃣ Payment Integration (Razorpay)
# -------------------------------------------------------
# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            amount = int(request.data.get("amount")) * 100  # Convert to paise
            currency = request.data.get("currency", "INR")
            
            # Create Razorpay order
            order_data = {
                "amount": amount,
                "currency": currency,
                "payment_capture": 1,
                "notes": {
                    "user_id": str(request.user.id),
                    "email": request.user.email
                }
            }
            
            order = client.order.create(order_data)
            
            return Response(order, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {str(e)}")
            return Response(
                {"error": "Failed to create order"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        order_id = request.data.get("order_id")
        signature = request.data.get("signature")
        plan = request.data.get("plan")
        credits = int(request.data.get("credits", 0))

        # Validate required fields
        if not all([payment_id, order_id, signature]):
            return Response(
                {"error": "Missing payment information"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify Razorpay signature
        secret = settings.RAZORPAY_KEY_SECRET
        msg = f"{order_id}|{payment_id}"
        
        generated_signature = hmac.new(
            bytes(secret, "utf-8"),
            bytes(msg, "utf-8"),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != signature:
            logger.error(f"Payment verification failed for user {request.user.email}")
            return Response(
                {"error": "Payment verification failed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update user plan & credits
        user = request.user
        old_plan = user.plan
        old_credits = user.credit
        
        user.plan = plan
        user.credit += credits
        user.save()

        # Send payment confirmation email
        subject = '💳 Payment Successful - FrameStack'
        
        message = (
            f'Hello {user.name},\n\n'
            f'Your payment has been processed successfully!\n\n'
            f'Transaction Details:\n'
            f'• Payment ID: {payment_id}\n'
            f'• Plan: {plan}\n'
            f'• Credits Added: {credits}\n'
            f'• Total Credits: {user.credit}\n\n'
            f'Thank you for your purchase!\n\n'
            f'— The FrameStack Team'
        )
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .success {{ background: #d4edda; border: 1px solid #28a745; padding: 20px; border-radius: 5px; }}
                .receipt {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .receipt-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #dee2e6; }}
                .total {{ font-size: 18px; font-weight: bold; color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">
                    <h2>💳 Payment Successful!</h2>
                </div>
                
                <p>Hello {user.name},</p>
                <p>Thank you for your purchase! Your payment has been processed successfully.</p>
                
                <div class="receipt">
                    <h3>Transaction Receipt</h3>
                    <div class="receipt-row">
                        <span>Payment ID:</span>
                        <span>{payment_id}</span>
                    </div>
                    <div class="receipt-row">
                        <span>Plan:</span>
                        <span>{plan}</span>
                    </div>
                    <div class="receipt-row">
                        <span>Credits Added:</span>
                        <span>{credits}</span>
                    </div>
                    <div class="receipt-row total">
                        <span>Total Credits:</span>
                        <span>{user.credit}</span>
                    </div>
                </div>
                
                <p>You can now use your credits to access premium features.</p>
                
                <p>Best regards,<br>The FrameStack Team</p>
            </div>
        </body>
        </html>
        """
        
        send_email_async(subject, message, [user.email], html_message)
        
        logger.info(f"Payment verified for user {user.email}: {plan} plan, {credits} credits")

        return Response({
            "message": "Payment verified successfully",
            "plan": user.plan,
            "credits": user.credit,
            "payment_id": payment_id
        })


# -------------------------------------------------------
# 9️⃣ Plan Purchase View (Alternative)
# -------------------------------------------------------
class PlanPurchaseView(generics.CreateAPIView):
    serializer_class = PlanPurchaseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        purchase = serializer.save(user=self.request.user)
        
        # Send purchase confirmation
        subject = f'🎯 {purchase.plan} Plan Activated'
        message = f'Your {purchase.plan} plan is now active with {purchase.credits} credits.'
        
        send_email_async(subject, message, [self.request.user.email])
        
        return purchase