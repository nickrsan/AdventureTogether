"""
Unit tests for core application configuration and health checks.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


class HealthCheckAPITests(TestCase):
    """
    Validates that the API health check endpoint accurately reports system health.
    """

    def setUp(self):
        self.client = APIClient()

    def test_health_check_endpoint_returns_200_and_healthy_status(self):
        """
        Ensures GET /api/health/ returns 200 OK with expected JSON payload structure.
        """
        url = reverse('api-health-check')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertEqual(response.data.get('service'), 'AdventureTogether Backend API')
        self.assertTrue(response.data.get('database_connected'))
        self.assertIn('database_engine', response.data)
        self.assertEqual(response.data.get('version'), '1.0.0')
