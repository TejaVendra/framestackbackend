from rest_framework import generics
from django.core.mail import send_mail
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from django.conf import settings
class ContactMessageCreateView(generics.CreateAPIView):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer

    def perform_create(self, serializer):
        # Save the user message
        user_message = serializer.save()

        # Send email to the user
        send_mail(
            subject='✅ Your Message Has Been Received',
            message=(
                f'Hello {user_message.name},\n\n'
                f'Thank you for contacting us. We have received your message:\n\n'
                f'"{user_message.message}"\n\n'
                f'— The FrameStack Team'
            ),
            from_email='noreply@framestack.com',
            recipient_list=[user_message.email],
            fail_silently=False,
        )
