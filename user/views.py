from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import RegisterSerializer, LoginSerializer, ProfileSerializer, ChangePasswordSerializer ,  UpdatePlanSerializer ,PlanPurchaseSerializer
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from django.core.mail import send_mail


import razorpay
from django.conf import settings
import hmac, hashlib
User = get_user_model()

# Sign Up
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        # Save the new user
        user = serializer.save()

        # Send welcome email
        send_mail(
            subject='🎉 Welcome to FrameStack!',
            message=f'Hello {user.name},\n\nThank you for creating an account with FrameStack.\nWe are excited to have you onboard!',
            from_email=None,  # uses DEFAULT_FROM_EMAIL in settings.py
            recipient_list=[user.email],
            fail_silently=False,
        )
    
    def create(self, request, *args, **kwargs):
        """Override to return a custom message in the API response"""
        super().create(request, *args, **kwargs)
        return Response({"message": "Account created successfully"}, status=status.HTTP_201_CREATED)

# Login
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

# Profile view
class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user

# Change password
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
        send_mail(
                    subject='✅ Your Password Has Been Changed',
                    message=(
                        f'Hello {user.name},\n\n'
                        f'Your password for your FrameStack account has been changed successfully.\n\n'
                        f'If this wasn’t you, please reset your password immediately or contact our support team.\n\n'
                        f'— The FrameStack Security Team 🔒'
                    ),
                    from_email='noreply@framestack.com',
                    recipient_list=[user.email],
                    fail_silently=False,
                )

        return Response({"detail": "Password updated successfully and confirmation email sent."})


# views.py
from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer

User = get_user_model()
token_generator = PasswordResetTokenGenerator()

# 1️⃣ Forgot Password - send reset link
class ForgotPasswordView(generics.GenericAPIView):
    serializer_class = ForgotPasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'If your email exists, you will receive a reset link.'}, status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        reset_link = f"http://localhost:5173/reset-password/{uid}/{token}/"  # React frontend URL
        send_mail(
            '🔒 Reset Your Password',
            f'Click the link to reset your password: {reset_link}',
            'noreply@framestack.com',
            [email],
            fail_silently=False,
        )
        return Response({'detail': 'Check your email for reset link.'}, status=status.HTTP_200_OK)


# 2️⃣ Reset Password - set new password
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


#payment 

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
