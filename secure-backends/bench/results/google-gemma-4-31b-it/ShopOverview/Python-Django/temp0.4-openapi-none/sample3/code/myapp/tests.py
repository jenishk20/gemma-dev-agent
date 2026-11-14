from django.test import TestCase
from .models import Merchant, Ware

class WarehouseTest(TestCase):
    def test_models(self):
        m = Merchant.objects.create(email="test@test.com", name="Test", password="123")
        w = Ware.objects.create(merchant=m, name="Item", description="Desc", price=10.0)
        self.assertEqual(str(w), "Item")