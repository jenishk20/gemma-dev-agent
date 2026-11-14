from django.test import TestCase
from .models import Click

class ClickTest(TestCase):
    def test_model(self):
        c = Click.objects.create()
        self.assertEqual(str(c.id), str(c.id))