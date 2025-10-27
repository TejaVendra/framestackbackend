import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = None
        self.user = self.scope["user"]
        self.chat_user_id = self.scope['url_route']['kwargs'].get('user_id')

        if self.chat_user_id is None or self.user.is_anonymous:
            await self.close()
            return

        self.chat_user_id = int(self.chat_user_id)
        self.room_name = f"chat_{min(self.user.id, self.chat_user_id)}_{max(self.user.id, self.chat_user_id)}"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.room_name:
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('content', '')

        if message.strip() == '':
            return

        # Save to DB
        timestamp = await self.save_message(self.user.id, self.chat_user_id, message)

        # Broadcast to group (including sender)
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat_message",
                "content": message,
                "sender_id": self.user.id,
                "receiver_id": self.chat_user_id,
                "timestamp": timestamp
            }
        )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "content": event["content"],
            "sender_id": event["sender_id"],
            "receiver_id": event["receiver_id"],
            "timestamp": event["timestamp"]
        }))

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, content):
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)
        msg = Message.objects.create(sender=sender, receiver=receiver, content=content)
        return msg.timestamp.isoformat()

