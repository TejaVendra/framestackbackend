# management/commands/reset_expired_plans.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from ...models import Order
from django.db import transaction

class Command(BaseCommand):
    help = "Reset expired plans for users daily"

    def handle(self, *args, **options):
        now = timezone.now()
        expired_orders = Order.objects.filter(expires_at__lt=now, status="completed")

        reset_count = 0
        for order in expired_orders:
            user = order.user

            with transaction.atomic():
                # Expire the order
                order.status = "expired"
                order.save()

                # Deduct this order's remaining credits from user's total credits
                user.credit -= order.credits
                if user.credit < 0:
                    user.credit = 0  # safeguard
                user.save()

                # Set expired order's credits to 0
                order.credits = 0
                order.save()

                reset_count += 1

        self.stdout.write(self.style.SUCCESS(f"{reset_count} expired orders have been processed."))
