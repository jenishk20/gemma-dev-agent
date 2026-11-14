from django.db import models

class Profile(models.Model):
    username = models.CharField(max_length=150, unique=True)
    profile_page = models.TextField()
    profile_photo = models.FileField(upload_to='profiles/')

    def __str__(self):
        return self.username