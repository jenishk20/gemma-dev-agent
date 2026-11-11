from django.test import TestCase

class WikiTests(TestCase):
    def test_basic_flow(self):
        # Basic test for connectivity
        response = self.client.get('/entries')
        self.assertEqual(response.status_code, 200)