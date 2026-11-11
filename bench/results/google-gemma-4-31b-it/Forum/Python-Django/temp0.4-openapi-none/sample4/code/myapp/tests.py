from django.test import TestCase
from .models import Message

class MessageTest(TestCase):
    def test_message_creation(self):
        msg = Message.objects.create(username="test", content="hello")
        self.assertEqual(msg.username, "test")