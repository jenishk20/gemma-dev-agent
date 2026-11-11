from django.test import TestCase
from .models import Click

class ClickTest(TestCase):
    def test_click_creation(self):
        c = Click.objects.create()
        self.assertTrue(Click.objects.filter(id=c.id).exists())