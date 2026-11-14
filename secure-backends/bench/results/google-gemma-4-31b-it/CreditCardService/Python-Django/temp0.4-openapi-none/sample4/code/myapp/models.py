from django.db import models

class CreditCard(models.Model):
    card_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.card_number

class Phone(models.Model):
    phone_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.phone_number

class Association(models.Model):
    card = models.ForeignKey(CreditCard, on_delete=models.CASCADE)
    phone = models.ForeignKey(Phone, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('card', 'phone')