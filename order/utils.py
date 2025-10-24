# utils.py
from django.utils import timezone
from .models import Order

def reset_expired_plans(user):
    """
    Check if the user's current plan has expired.
    If expired, reset their credits and plan to 'Free Plan'.
    """
    latest_order = Order.objects.filter(user=user).order_by("-created_at").first()
    if not latest_order:
        return

    if latest_order.expires_at and timezone.now() > latest_order.expires_at:
        # Plan expired → reset user
        user.credit = 0
        user.plan = "Free Plan"
        user.save()

        # Update order status and credits
        latest_order.status = "expired"
        latest_order.credits = 0  # ✅ set expired order credits to zero
        latest_order.save()
