from django.db import models
from django.contrib.auth.models import User
import uuid

class Invitation(models.Model):
    email = models.EmailField(unique=True)
    invite_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite for {self.email}"