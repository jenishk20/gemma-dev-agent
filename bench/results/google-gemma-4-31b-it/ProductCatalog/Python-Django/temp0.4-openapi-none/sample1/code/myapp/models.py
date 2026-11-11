from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255, unique=True)
    # properties stores all additional unstructured fields
    properties = models.JSONField(default=dict)

    def __str__(self):
        return self.name