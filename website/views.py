from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .models import WebsiteRequest
from django.core.mail import send_mail
from django.conf import settings
import json
from .serializers import (
    WebsiteRequestSerializer, 
    AdminWebsiteRequestSerializer,
    WebsiteRequestDetailSerializer,
    WebsiteRequestListSerializer
)
from django.shortcuts import get_object_or_404


# ✅ 1. Create website request
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

        serializer.save(user=user)


# ✅ 2. List all requests
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


# ✅ 3. Retrieve a single request (details view)
class WebsiteRequestDetailView(generics.RetrieveAPIView):
    serializer_class = WebsiteRequestDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return WebsiteRequest.objects.all()
        return WebsiteRequest.objects.filter(user=user)


# ✅ 4. User updates their own request (but not admin fields)
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
            
            subject='✅ Website request updated successfully ',
            message=(
                        f'Hello {self.request.user.name},\n\n'
                        f'your website request has been updated sucessfully.\n\n'
                        f'— The FrameStack Security Team 🔒'
                    )   
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email='noreply@framestack.com',
                    recipient_list=[self.request.user.email],
                    fail_silently=False
                )
            except Exception as e:
                print(f'Email send failed: {e}')
            return Response({
                "message": "Website request updated successfully",
                "data": serializer.data
            },status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ✅ 5. Admin updates everything
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
            subject='✅ Website request status updated or added URL ',
            message=(
                        f'Hello {self.request.user.name},\n\n'
                        f'your website request status has been updated or admin added URL.\n\n'
                        f'— The FrameStack Security Team 🔒'
                    )   
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email='noreply@framestack.com',
                    recipient_list=[self.request.user.email],
                    fail_silently=False
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Email send failed :  {e}")
                print(f'Email send failed: {e}')
            return Response({
                "message": "Website request updated successfully by admin",
                "data": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
