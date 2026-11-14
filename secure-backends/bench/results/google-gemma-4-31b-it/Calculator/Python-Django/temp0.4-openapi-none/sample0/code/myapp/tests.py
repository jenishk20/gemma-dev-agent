from django.test import TestCase
from django.urls import reverse

class CalculatorTests(TestCase):
    def test_calculate_success(self):
        response = self.client.post('/calculator', data='{"expression": "1 + 2*3"}', content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['result'], '7')

    def test_calculate_invalid(self):
        response = self.client.post('/calculator', data='{"expression": "invalid"}', content_type='application/json')
        self.assertEqual(response.status_code, 400)