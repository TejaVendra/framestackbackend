from rest_framework import serializers
from .models import WebsiteRequest


# For users to create and edit their own requests (excluding admin-only fields)
class WebsiteRequestSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = WebsiteRequest
        fields = "__all__"
        read_only_fields = [
            "user", "created_at", "status", "sample_url",
            "original_url", "user_email", "user_username"
        ]

    def validate_website_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Website name cannot be empty.")
        return value

    def validate_description(self, value):
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        return value

# For admins (can edit everything)
class AdminWebsiteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebsiteRequest
        fields = "__all__"


# Read-only serializer for showing detailed info
class WebsiteRequestDetailSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    template_file = serializers.ImageField(use_url=True)
    
    class Meta:
        model = WebsiteRequest
        fields = "__all__"
        read_only_fields = [
            "user",
            "website_name",
            "description",
            "template_file",
            "timeline",
            "features",
            "created_at",
            "status",
            "sample_url",
            "original_url"
        ]

# List serializer for showing brief info
class WebsiteRequestListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    template_file = serializers.ImageField(use_url=True)

    class Meta:
        model = WebsiteRequest
        fields = ['id', 'website_name', 'status', 'created_at', 'updated_at', 'user_email', 'user_username','template_file']
