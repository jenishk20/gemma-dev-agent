from django.db import models
from django.contrib.auth.models import User
import uuid

class Invitation(models.Model):
    invite_id = models.CharField(max_length=255, unique=True, default=uuid.uuid4)
    email = models.EmailField(unique=True)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite for {self.email}"