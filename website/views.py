# views.py - Website Request Views with Brevo API Email
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
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

# Import Brevo API email sender
from utils.brevo_email import send_email_async_api

logger = logging.getLogger(__name__)

# -------------------------------------------------------
# ✅ Use Brevo API for email sending (works on Render!)
# -------------------------------------------------------
send_email_async = send_email_async_api  # Use Brevo API instead of SMTP


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

        # Send confirmation email via Brevo API
        subject = 'Website Request Created Successfully'
        
        message = (
            f'Hello {user.name},\n\n'
            f'Your website request (ID: {request_obj.id}) has been created successfully.\n'
            f'Our team will start processing it soon.\n\n'
            f'Request Details:\n'
            f'• Website Name: {request_obj.website_name}\n'
            f'• Status: {request_obj.status}\n\n'
            f'You can track the progress in your dashboard.\n\n'
            f'Best regards,\n'
            f'The FrameStack Team'
        )
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Website Request Created</h1>
                </div>
                <div class="content">
                    <h2>Hello {user.name}!</h2>
                    <p>Your website request has been created successfully and our team will start processing it soon.</p>
                    
                    <div class="details">
                        <h3>Request Details:</h3>
                        <div class="detail-row">
                            <span><strong>Request ID:</strong></span>
                            <span>{request_obj.id}</span>
                        </div>
                        <div class="detail-row">
                            <span><strong>Website Name:</strong></span>
                            <span>{request_obj.website_name}</span>
                        </div>
                    
                        <div class="detail-row">
                            <span><strong>Status:</strong></span>
                            <span style="color: #28a745;">{request_obj.status}</span>
                        </div>
                    </div>
                    
                    <center>
                        <a href="{settings.FRONTEND_URL}/dashboard" class="button">View in Dashboard</a>
                    </center>
                    
                    <p style="margin-top: 30px;">We'll notify you once there's an update on your request.</p>
                </div>
                <div class="footer">
                    <p>© 2024 FrameStack. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email asynchronously using Brevo API
        send_email_async(subject, message, [user.email], html_message)
        
        logger.info(f"Website request {request_obj.id} created by user {user.email}")


# -------------------------------------------------------
# ✅ 2. List all requests
# -------------------------------------------------------
class WebsiteRequestListView(generics.ListAPIView):
    serializer_class = WebsiteRequestListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Admin sees all requests
            queryset = WebsiteRequest.objects.all()
            logger.info(f"Admin {user.email} viewing all website requests")
        else:
            # Normal user sees only their own
            queryset = WebsiteRequest.objects.filter(user=user)
            logger.info(f"User {user.email} viewing their website requests")
        
        # Optional: Add filtering by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')


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
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        logger.info(f"User {request.user.email} viewing website request {instance.id}")
        return Response(serializer.data)


# -------------------------------------------------------
# ✅ 4. User updates their own request (non-admin fields only)
# -------------------------------------------------------
class WebsiteRequestUserUpdateView(generics.UpdateAPIView):
    serializer_class = WebsiteRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        # Only user's own requests
        return WebsiteRequest.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()

        # Block admin-only fields from being updated by normal users
        forbidden_fields = ["status", "sample_url", "original_url", "admin_notes"]
        for field in forbidden_fields:
            if field in data:
                logger.warning(f"User {request.user.email} attempted to update forbidden field '{field}'")
                return Response(
                    {"error": f"You cannot update the '{field}' field. Only admins can modify this."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = self.get_serializer(instance, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()

            # Send update confirmation email
            subject = 'Website Request Updated'
            
            message = (
                f'Hello {request.user.name},\n\n'
                f'Your website request (ID: {instance.id}) has been updated successfully.\n\n'
                f'Updated Information:\n'
                f'• Website Name: {instance.website_name}\n'
          
                f'If you have any questions, please contact our support team.\n\n'
                f'Best regards,\n'
                f'The FrameStack Team'
            )
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .success {{ background: #d4edda; border: 1px solid #28a745; padding: 20px; border-radius: 5px; text-align: center; }}
                    .details {{ background: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                    .button {{ display: inline-block; padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">
                        <h2>✅ Request Updated Successfully</h2>
                    </div>
                    
                    <p>Hello {request.user.name},</p>
                    <p>Your website request has been updated successfully.</p>
                    
                    <div class="details">
                        <h3>Updated Information:</h3>
                        <p><strong>Request ID:</strong> {instance.id}</p>
                        <p><strong>Website Name:</strong> {instance.website_name}</p>
                    
                        <p><strong>Status:</strong> {instance.status}</p>
                    </div>
                    
                    <center>
                        <a href="{settings.FRONTEND_URL}/requests/{instance.id}" class="button">View Request</a>
                    </center>
                    
                    <p style="margin-top: 30px;">Thank you for using FrameStack!</p>
                </div>
            </body>
            </html>
            """

            send_email_async(subject, message, [request.user.email], html_message)
            
            logger.info(f"User {request.user.email} updated website request {instance.id}")

            return Response({
                "message": "Website request updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------
# ✅ 5. Admin updates everything (including status and URLs)
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
        old_status = instance.status
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            updated_instance = serializer.save()
            
            # Check if status changed
            status_changed = old_status != updated_instance.status
            
            # Prepare notification email for the user
            if status_changed:
                subject = f'Website Request Status: {updated_instance.status}'
                
                # Customize message based on status
                status_messages = {
                    'processing': 'Our team has started working on your request.',
                    'completed': 'Great news! Your website request has been completed.',
                    'cancelled': 'Your website request has been cancelled.',
                    'on_hold': 'Your website request has been put on hold temporarily.'
                }
                
                status_message = status_messages.get(
                    updated_instance.status, 
                    f'Your request status has been updated to: {updated_instance.status}'
                )
                
                message = (
                    f'Hello {instance.user.name},\n\n'
                    f'{status_message}\n\n'
                    f'Request Details:\n'
                    f'• Request ID: {instance.id}\n'
                    f'• Website Name: {instance.website_name}\n'
                    f'• New Status: {updated_instance.status}\n'
                )
                
                # Add URLs if available
                if updated_instance.sample_url:
                    message += f'• Sample URL: {updated_instance.sample_url}\n'
                if updated_instance.original_url:
                    message += f'• Original URL: {updated_instance.original_url}\n'
                
                message += (
                    f'\nIf you have any questions, please contact our support team.\n\n'
                    f'Best regards,\n'
                    f'The FrameStack Team'
                )
                
                # HTML version with better styling
                html_message = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
                        .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: bold; margin: 10px 0; }}
                        .status-completed {{ background: #28a745; color: white; }}
                        .status-processing {{ background: #ffc107; color: #333; }}
                        .status-cancelled {{ background: #dc3545; color: white; }}
                        .status-on_hold {{ background: #6c757d; color: white; }}
                        .content {{ background: #f9f9f9; padding: 30px; border-radius: 10px; margin-top: 20px; }}
                        .details {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                        .detail-row {{ padding: 10px 0; border-bottom: 1px solid #eee; }}
                        .button {{ display: inline-block; padding: 12px 30px; background-color: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                        .url-box {{ background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 10px 0; word-break: break-all; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>Website Request Update</h1>
                            <div class="status-badge status-{updated_instance.status}">
                                {updated_instance.status.upper()}
                            </div>
                        </div>
                        
                        <div class="content">
                            <h2>Hello {instance.user.name}!</h2>
                            <p>{status_message}</p>
                            
                            <div class="details">
                                <h3>Request Details:</h3>
                                <div class="detail-row">
                                    <strong>Request ID:</strong> {instance.id}
                                </div>
                                <div class="detail-row">
                                    <strong>Website Name:</strong> {instance.website_name}
                                </div>
                           
                                <div class="detail-row">
                                    <strong>Status:</strong> <span style="color: #667eea;">{updated_instance.status}</span>
                                </div>
                """
                
                # Add URLs if available
                if updated_instance.sample_url:
                    html_message += f"""
                                <div class="detail-row">
                                    <strong>Sample URL:</strong>
                                    <div class="url-box">
                                        <a href="{updated_instance.sample_url}" style="color: #667eea;">{updated_instance.sample_url}</a>
                                    </div>
                                </div>
                    """
                
                if updated_instance.original_url:
                    html_message += f"""
                                <div class="detail-row">
                                    <strong>Original URL:</strong>
                                    <div class="url-box">
                                        <a href="{updated_instance.original_url}" style="color: #667eea;">{updated_instance.original_url}</a>
                                    </div>
                                </div>
                    """
                
                html_message += f"""
                            </div>
                            
                            <center>
                                <a href="{settings.FRONTEND_URL}/requests/{instance.id}" class="button">View Full Details</a>
                            </center>
                            
                            <p style="margin-top: 30px; color: #666;">
                                If you have any questions, please don't hesitate to contact our support team.
                            </p>
                        </div>
                    </div>
                </body>
                </html>
                """
                
                # Send notification email via Brevo API
                send_email_async(subject, message, [instance.user.email], html_message)
                
                logger.info(f"Admin {request.user.email} updated website request {instance.id} - Status changed from {old_status} to {updated_instance.status}")
            else:
                logger.info(f"Admin {request.user.email} updated website request {instance.id}")

            return Response({
                "message": "Website request updated successfully by admin",
                "status_changed": status_changed,
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -------------------------------------------------------
# ✅ 6. Delete website request (Admin only)
# -------------------------------------------------------
class WebsiteRequestDeleteView(generics.DestroyAPIView):
    queryset = WebsiteRequest.objects.all()
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_email = instance.user.email
        user_name = instance.user.name
        request_id = instance.id
        
        # Delete the request
        self.perform_destroy(instance)
        
        # Send deletion notification
        subject = 'Website Request Deleted'
        message = (
            f'Hello {user_name},\n\n'
            f'Your website request (ID: {request_id}) has been deleted by an administrator.\n\n'
            f'If you believe this was done in error, please contact our support team.\n\n'
            f'Best regards,\n'
            f'The FrameStack Team'
        )
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .alert {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="alert">
                    <h2>Website Request Deleted</h2>
                </div>
                
                <p>Hello {user_name},</p>
                <p>Your website request (ID: {request_id}) has been deleted by an administrator.</p>
                <p>If you believe this was done in error, please contact our support team immediately.</p>
                
                <p>Best regards,<br>The FrameStack Team</p>
            </div>
        </body>
        </html>
        """
        
        send_email_async(subject, message, [user_email], html_message)
        
        logger.info(f"Admin {request.user.email} deleted website request {request_id}")
        
        return Response(
            {"message": f"Website request {request_id} deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )