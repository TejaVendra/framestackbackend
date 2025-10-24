from django.contrib import admin
from .models import ContactMessage

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at")  # columns to show
    search_fields = ("name", "email", "message")     # allow search
    list_filter = ("created_at",)                    # filter by date
    ordering = ("-created_at",)                      # latest messages first
