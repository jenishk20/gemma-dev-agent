from django.test import TestCase
from .models import Message

class MessageModelTest(TestCase):
    def test_message_creation(self):
        msg = Message.objects.create(username="testuser", content="test content")
        self.assertEqual(msg.username, "testuser")