from django.db import models
import uuid

class Cart(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = uuid.uuid4()
        super().save(*args, **kwargs)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item_id = models.IntegerField()
    count = models.IntegerField()

    class Meta:
        unique_together = ('cart', 'item_id')