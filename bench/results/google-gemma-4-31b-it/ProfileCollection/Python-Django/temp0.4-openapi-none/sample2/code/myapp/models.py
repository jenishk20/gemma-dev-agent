from django.db import models

class Profile(models.Model):
    username = models.CharField(max_length=150, unique=True, primary_key=True)
    profile_page = models.TextField()
    profile_photo = models.BinaryField()

    def __str__(self):
        return self.username