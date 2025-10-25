from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.shortcuts import get_object_or_404
from threading import Thread
import logging

from .models import WebsiteRequest
from .serializers import (
    WebsiteRequestSerializer,
    AdminWebsiteRequestSerializer,
    WebsiteRequestDetailSerializer,
    WebsiteRequestListSerializer
)

logger = logging.getLogger(__name__)


# -------------------------------------------------------
# ✅ Utility: Send email asynchronously (threaded)
# -------------------------------------------------------
def send_email_async(subject, message, from_email, recipient_list, html_message=None):
    """Send email asynchronously (with optional HTML content)."""
    def _send():
        try:
            if html_message:
                msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=False)
            else:
                send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")
            print(f"Email sending failed: {e}")
    Thread(target=_send).start()


# -------------------------------------------------------
# ✅ 1. Create website request
# -------------------------------------------------------
class WebsiteRequestCreateView(generics.CreateAPIView):
    queryset = WebsiteRequest.objects.all()
    serializer_class = WebsiteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        # Optional credit logic
        if hasattr(user, 'credit') and user.credit <= 0:
            raise PermissionDenied("You don't have enough credits. Please upgrade your plan.")

        if hasattr(user, 'credit'):
            user.credit -= 1
            user.save()

        request_obj = serializer.save(user=user)

        # Async email confirmation
        subject = '✅ Website Request Created Successfully'
        message = (
            f'Hello {user.name},\n\n'
            f'Your website request (ID: {request_obj.id}) has been created successfully.\n'
            f'Our team will start processing it soon.\n\n'
            f'— The FrameStack Team ⚙️'
        )
        html_message = f"""
        <html><body>
        <h3>✅ Website Request Created</h3>
        <p>Hello {user.name},</p>
        <p>Your website request (ID: {request_obj.id}) has been created successfully.</p>
        <p>Our team will start processing it soon.</p>
        <p>— The FrameStack Team ⚙️</p>
        </body></html>
        """
        send_email_async(subject, message, 'noreply@framestack.com', [user.email], html_message)


# -------------------------------------------------------
# ✅ 2. List all requests
# -------------------------------------------------------
class WebsiteRequestListView(generics.ListAPIView):
    serializer_class = WebsiteRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Admin sees all
            return WebsiteRequest.objects.all()
        # Normal user sees only their own
        return WebsiteRequest.objects.filter(user=user)


# -------------------------------------------------------
# ✅ 3. Retrieve a single request (details view)
# -------------------------------------------------------
class WebsiteRequestDetailView(generics.RetrieveAPIView):
    serializer_class = WebsiteRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return WebsiteRequest.objects.all()
        return WebsiteRequest.objects.filter(user=user)


# -------------------------------------------------------
# ✅ 4. User updates their own request (non-admin fields only)
# -------------------------------------------------------
class WebsiteRequestUserUpdateView(generics.UpdateAPIView):
    serializer_class = WebsiteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Only user’s own requests
        return WebsiteRequest.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()

        # 🚫 Block these fields from being updated by normal users
        forbidden = ["status", "sample_url", "original_url"]
        for field in forbidden:
            if field in data:
                return Response(
                    {"error": f"You cannot update '{field}' field."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()

            subject = '✅ Your Website Request Has Been Updated'
            message = (
                f'Hello {request.user.name},\n\n'
                f'Your website request (ID: {instance.id}) has been updated successfully.\n\n'
                f'— The FrameStack Team 🔒'
            )
            html_message = f"""
            <html><body>
            <h3>✅ Website Request Updated</h3>
            <p>Hello {request.user.name},</p>
            <p>Your website request (ID: {instance.id}) has been updated successfully.</p>
            <p>— The FrameStack Team 🔒</p>
            </body></html>
            """

            send_email_async(subject, message, 'noreply@framestack.com', [request.user.email], html_message)

            return Response({
                "message": "Website request updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------
# ✅ 5. Admin updates everything
# -------------------------------------------------------
class AdminWebsiteRequestUpdateView(generics.UpdateAPIView):
    serializer_class = AdminWebsiteRequestSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

    def get_queryset(self):
        # Admin can access all requests
        return WebsiteRequest.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()

            subject = '⚙️ Website Request Status Updated'
            message = (
                f'Hello {instance.user.name},\n\n'
                f'The status or URL for your website request (ID: {instance.id}) '
                f'has been updated by the admin.\n\n'
                f'— The FrameStack Team 🔒'
            )
            html_message = f"""
            <html><body>
            <h3>⚙️ Website Request Update</h3>
            <p>Hello {instance.user.name},</p>
            <p>The status or URL for your website request (ID: {instance.id}) has been updated by the admin.</p>
            <p>— The FrameStack Team 🔒</p>
            </body></html>
            """

            send_email_async(subject, message, 'noreply@framestack.com', [instance.user.email], html_message)

            return Response({
                "message": "Website request updated successfully by admin",
                "data": serializer.data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
