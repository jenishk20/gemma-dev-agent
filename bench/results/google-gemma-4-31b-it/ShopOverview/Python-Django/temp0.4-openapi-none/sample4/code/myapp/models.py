from django.db import models
from django.contrib.auth.models import User

class Ware(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.FloatField()
    merchant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wares')

    def __str__(self):
        return self.name