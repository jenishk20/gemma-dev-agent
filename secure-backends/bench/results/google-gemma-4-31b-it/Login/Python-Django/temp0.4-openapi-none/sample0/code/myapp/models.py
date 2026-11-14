from django.db import models
from django.contrib.auth.models import AbstractUser

class UserProfile(AbstractUser):
    email = models.EmailField(unique=True)
    # We use AbstractUser to leverage Django's built-in password hashing and auth system
    # but we ensure email is the primary identifier for the API.
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']

    def __str__(self):
        return self.email