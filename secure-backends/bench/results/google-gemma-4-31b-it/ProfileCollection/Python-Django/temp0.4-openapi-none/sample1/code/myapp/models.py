from django.db import models

class Profile(models.Model):
    username = models.CharField(max_length=255, unique=True, primary_key=True)
    profile_page_html = models.TextField()
    profile_photo = models.ImageField(upload_to='profiles/')