from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

@receiver(post_save, sender=Message)
def notify_user(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        room_name = f"chat_{min(instance.sender.id, instance.receiver.id)}_{max(instance.sender.id, instance.receiver.id)}"
        async_to_sync(channel_layer.group_send)(
            room_name,
            {
                "type": "chat_message",
                "message": instance.content,
                "sender_id": instance.sender.id
            }
        )
