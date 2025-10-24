# models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    plan = models.CharField(max_length=100)
    credits = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Automatically set expiry date to 30 days after creation if not set
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.name} - {self.plan} ({self.credits} credits)"
