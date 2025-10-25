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
import razorpay, hmac, hashlib

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

User = get_user_model()
token_generator = PasswordResetTokenGenerator()

# -------------------------------------------------------
# ✅ Utility: Send email asynchronously in a background thread
# -------------------------------------------------------
def send_email_async(subject, message, from_email, recipient_list, html_message=None):
    """Send plain-text or HTML email asynchronously using a background thread."""
    def _send():
        try:
            if html_message:
                msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=False)
            else:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception as e:
            print(f"❌ Email failed: {e}")
    Thread(target=_send).start()


# -------------------------------------------------------
# 1️⃣ Register (Signup)
# -------------------------------------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()

        subject = '🎉 Welcome to FrameStack!'
        message = (
            f'Hello {user.name},\n\n'
            f'Thank you for creating an account with FrameStack.\n'
            f'We’re excited to have you onboard!'
        )
        from_email = None  # Uses DEFAULT_FROM_EMAIL
        recipient_list = [user.email]

        Thread(target=send_email_async, args=(subject, message, from_email, recipient_list)).start()

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response({"message": "Account created successfully"}, status=status.HTTP_201_CREATED)


# -------------------------------------------------------
# 2️⃣ Login
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
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


# -------------------------------------------------------
# 3️⃣ Profile
# -------------------------------------------------------
class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user


# -------------------------------------------------------
# 4️⃣ Change Password
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

        if not user.check_password(serializer.validated_data['old_password']):
            return Response({"old_password": "Wrong password."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        subject = '✅ Your Password Has Been Changed'
        message = (
            f'Hello {user.name},\n\n'
            f'Your password for your FrameStack account has been changed successfully.\n\n'
            f'If this wasn’t you, please reset your password immediately or contact our support team.\n\n'
            f'— The FrameStack Security Team 🔒'
        )

        Thread(target=send_email_async, args=(subject, message, 'noreply@framestack.com', [user.email])).start()

        return Response(
            {"detail": "Password updated successfully and confirmation email sent."},
            status=status.HTTP_200_OK
        )


# -------------------------------------------------------
# 5️⃣ Forgot Password - Send Reset Link (Async)
# -------------------------------------------------------
class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don’t reveal if email exists (security best practice)
            return Response({'detail': 'If your email exists, you will receive a reset link.'}, status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        reset_link = f"https://framestack.onrender.com/reset-password/{uid}/{token}/"  # ✅ Change this to your frontend URL

        subject = '🔒 Reset Your Password'
        message = (
            f'Hello {user.name},\n\n'
            f'We received a request to reset your FrameStack account password.\n'
            f'Click the link below to set a new password:\n\n{reset_link}\n\n'
            f'If you didn’t request this, please ignore this email.\n\n'
            f'— The FrameStack Team'
        )
        html_message = f"""
        <html>
        <body style="font-family: Arial; line-height: 1.6;">
            <h2>🔒 Reset Your Password</h2>
            <p>Hello {user.name},</p>
            <p>We received a request to reset your FrameStack account password.</p>
            <p>
                <a href="{reset_link}" style="background-color:#007bff; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">
                    Reset Password
                </a>
            </p>
            <p>If you didn’t request this, please ignore this email.</p>
            <p>— The FrameStack Team</p>
        </body>
        </html>
        """

        Thread(target=send_email_async, args=(subject, message, 'noreply@framestack.com', [email], html_message)).start()

        return Response({'detail': 'If your email exists, you will receive a reset link.'}, status=status.HTTP_200_OK)


# -------------------------------------------------------
# 6️⃣ Reset Password
# -------------------------------------------------------
class ResetPasswordView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer

    def put(self, request, uidb64, token):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'detail': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not token_generator.check_token(user, token):
            return Response({'detail': 'Token is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['password'])
        user.save()
        return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)


# -------------------------------------------------------
# 7️⃣ Payment Integration (Razorpay)
# -------------------------------------------------------
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = int(request.data.get("amount")) * 100  # in paise
        currency = "INR"
        order = client.order.create({"amount": amount, "currency": currency, "payment_capture": 1})
        return Response(order)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get("payment_id")
        order_id = request.data.get("order_id")
        signature = request.data.get("signature")
        plan = request.data.get("plan")
        credits = int(request.data.get("credits"))

        if not payment_id or not order_id or not signature:
            return Response({"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify Razorpay signature
        secret = settings.RAZORPAY_KEY_SECRET
        msg = f"{order_id}|{payment_id}"
        generated_signature = hmac.new(
            bytes(secret, "utf-8"),
            bytes(msg, "utf-8"),
            hashlib.sha256
        ).hexdigest()

        if generated_signature != signature:
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)

        # Update user plan & credits
        user = request.user
        user.plan = plan
        user.credit += credits
        user.save()

        return Response({
            "message": "Payment verified successfully",
            "plan": user.plan,
            "credits": user.credit
        })
