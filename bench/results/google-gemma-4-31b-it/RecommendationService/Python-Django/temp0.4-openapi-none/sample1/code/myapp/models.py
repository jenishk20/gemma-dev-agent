from django.db import models

class Product(models.Model):
    product_name = models.CharField(max_length=255)

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    product = models.ForeignKey(Product, related_name='tags', on_delete=models.CASCADE)

    def __str__(self):
        return self.name