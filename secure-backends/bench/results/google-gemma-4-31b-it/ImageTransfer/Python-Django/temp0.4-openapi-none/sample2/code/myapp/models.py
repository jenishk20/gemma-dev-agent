from django.db import models
import uuid

class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='uploads/')
    content_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return str(self.id)