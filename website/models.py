
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from cloudinary_storage.storage import MediaCloudinaryStorage
User = get_user_model()

class WebsiteRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("In Progress", "In Progress"),
        ("Completed", "Completed"),
        ("Rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="website_requests"
    )
    website_name = models.CharField(max_length=200)
    description = models.TextField()
    template_file = models.ImageField(upload_to='templates/',storage=MediaCloudinaryStorage() , blank=True,null=True)
    timeline = models.CharField(max_length=100, blank=True, null=True)
    features = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    sample_url = models.URLField(blank=True, null=True)
    original_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Website Request"
        verbose_name_plural = "Website Requests"

    def __str__(self):
        return f"{self.website_name} - {self.user.name} ({self.status})"

    @property
    def is_completed(self):
        return self.status == "Completed"