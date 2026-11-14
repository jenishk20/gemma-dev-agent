from django.db import models

class Product(models.Model):
    product_name = models.CharField(max_length=255)

    def __str__(self):
        return self.product_name

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class ProductTag(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_tags')
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='tag_products')

    class Meta:
        unique_together = ('product', 'tag')