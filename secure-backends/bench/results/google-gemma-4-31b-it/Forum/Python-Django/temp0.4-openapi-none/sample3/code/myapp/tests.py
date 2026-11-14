from django.test import TestCase
from .models import Message

class MessageModelTest(TestCase):
    def test_message_creation(self):
        Message.objects.create(username="testuser", content="test content")
        self.assertEqual(Message.objects.count(), 1)