from django.test import TestCase
from django.urls import reverse
import json

class ServiceMonitoringTests(TestCase):
    def test_heartbeat(self):
        response = self.client.post('/heartbeat', data=json.dumps({'serviceId': 'test', 'token': 'pass1'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_services(self):
        self.client.post('/heartbeat', data=json.dumps({'serviceId': 'test', 'token': 'pass1'}), content_type='application/json')
        response = self.client.post('/services', data=json.dumps({'token': 'pass1'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)