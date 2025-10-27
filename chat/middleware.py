# chat/middleware.py - UPDATED VERSION
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from jwt import decode as jwt_decode
from django.conf import settings
from django.utils.functional import SimpleLazyObject
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        # Convert to int if it's a string
        user_id = int(user_id) if isinstance(user_id, str) else user_id
        return User.objects.get(id=user_id)
    except (User.DoesNotExist, ValueError, TypeError):
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Extracts JWT token from query string and sets scope['user']
    ws://localhost:8000/ws/chat/2/?token=ACCESS_TOKEN
    """
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JWTAuthMiddlewareInstance(scope, self.inner)

class JWTAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        query_string = self.scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token")
        user = AnonymousUser()

        if token:
            token = token[0]
            try:
                payload = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")
                
                if user_id:
                    user = await get_user(user_id)
                    print(f"✅ WebSocket authenticated user: {user.id if not user.is_anonymous else 'Anonymous'}")
                else:
                    print("❌ No user_id in JWT payload")
                    
            except Exception as e:
                print(f"❌ JWT Error: {e}")

        self.scope["user"] = user
        inner = self.inner(self.scope)
        return await inner(receive, send)