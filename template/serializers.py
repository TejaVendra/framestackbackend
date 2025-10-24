from rest_framework import serializers
from .models import Template

class TemplateSerializer(serializers.ModelSerializer):
    template_file = serializers.ImageField(use_url=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'category', 'template_file', 'url', 'created_at']
