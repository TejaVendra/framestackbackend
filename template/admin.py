from django.contrib import admin
from .models import Template
from django.utils.html import format_html

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'preview_image', 'url', 'created_at')
    readonly_fields = ('preview_image',)

    def preview_image(self, obj):
        if obj.template_file:
            return format_html(
                '<img src="{}" style="width: 150px; height: auto;" />', 
                obj.template_file.url
            )
        return "-"
    preview_image.short_description = "Preview"
