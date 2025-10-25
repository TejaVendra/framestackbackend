from rest_framework import generics
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from threading import Thread
import logging

logger = logging.getLogger(__name__)

# Reusable async email function
def send_email_async(subject, plain_message, from_email, recipient_list, html_message=None):
    """Send email asynchronously (supports HTML)."""
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


class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def perform_create(self, serializer):
        # Save the user message
        user_message = serializer.save()

        subject = '✅ Your Message Has Been Received'
        plain_message = (
            f'Hello {user_message.name},\n\n'
            f'Thank you for contacting us. We have received your message:\n\n'
            f'"{user_message.message}"\n\n'
            f'— The FrameStack Team'
        )
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4F46E5;">Message Received ✅</h2>
                <p>Hi <strong>{user_message.name}</strong>,</p>
                <p>Thank you for contacting us. We have received your message:</p>
                <blockquote style="background:#f8f9fa; padding:10px; border-radius:5px;">"{user_message.message}"</blockquote>
                <p>Our team will get back to you as soon as possible.</p>
                <p>— The FrameStack Team</p>
            </body>
        </html>
        """

        # Send email asynchronously
        send_email_async(
            subject=subject,
            plain_message=plain_message,
            from_email='noreply@framestack.com',
            recipient_list=[user_message.email],
            html_message=html_message
        )
