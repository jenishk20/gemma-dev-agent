from django.db import models
import uuid

class Cart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return str(self.id)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item_id = models.IntegerField()
    count = models.IntegerField()

    class Meta:
        unique_together = ('cart', 'item_id')