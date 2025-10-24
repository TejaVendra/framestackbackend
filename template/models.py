from django.db import models
from cloudinary_storage.storage import MediaCloudinaryStorage

class Template(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=100)
    template_file = models.ImageField(
        upload_to='all_templates/',
        storage=MediaCloudinaryStorage()
    )
    url = models.URLField()  # external link
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
