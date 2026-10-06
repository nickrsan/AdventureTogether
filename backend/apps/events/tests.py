"""
Unit and Integration Tests for Event Lifecycle and Spatial Boundary Validation.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.gis.geos import Polygon, Point
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from .models import Event


class EventModelSpatialTests(TestCase):
    """
    Tests spatial bounding perimeter calculations and model behaviors.
    """

    def setUp(self):
        # Bounding box roughly around central San Francisco: (lon, lat)
        self.sf_polygon = Polygon([
            (-122.43, 37.76),
            (-122.40, 37.76),
            (-122.40, 37.79),
            (-122.43, 37.79),
            (-122.43, 37.76),
        ])
        now = datetime.now(timezone.utc)
        self.event = Event.objects.create(
            title="San Francisco Landmark Hunt",
            description="Explore and map historic landmarks in San Francisco.",
            hashtag="#SFMapHunt2026",
            bounding_polygon=self.sf_polygon,
            start_time=now,
            end_time=now + timedelta(hours=6),
            is_active=True
        )

    def test_hashtag_and_slug_normalization(self):
        """Ensures leading hash symbol is stripped and slug is automatically generated."""
        self.assertEqual(self.event.hashtag, "SFMapHunt2026")
        self.assertEqual(self.event.slug, "san-francisco-landmark-hunt")

    def test_spatial_containment_positive(self):
        """Point inside the perimeter returns True."""
        inside_point = Point(-122.415, 37.775)
        self.assertTrue(self.event.is_within_bounds(inside_point))

    def test_spatial_containment_negative(self):
        """Point outside the perimeter returns False."""
        outside_point = Point(-122.50, 37.85)  # Far outside
        self.assertFalse(self.event.is_within_bounds(outside_point))


class EventAPITests(TestCase):
    """
    Integration tests for Event REST endpoints and GeoJSON serialization.
    """

    def setUp(self):
        self.client = APIClient()
        self.sf_polygon = Polygon([
            (-122.43, 37.76),
            (-122.40, 37.76),
            (-122.40, 37.79),
            (-122.43, 37.79),
            (-122.43, 37.76),
        ])
        now = datetime.now(timezone.utc)
        self.event = Event.objects.create(
            title="Mission District Hunt",
            description="Map opening hours in the Mission.",
            hashtag="MissionHunt",
            bounding_polygon=self.sf_polygon,
            start_time=now,
            end_time=now + timedelta(hours=4),
        )

    def test_list_events(self):
        """GET /api/events/ returns list of events."""
        url = reverse('events:event-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], "Mission District Hunt")

    def test_event_geojson_endpoint(self):
        """GET /api/events/<id>/geojson/ returns valid GeoJSON Feature."""
        url = reverse('events:event-geojson', kwargs={'pk': self.event.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('type'), 'Feature')
        self.assertEqual(response.data['geometry']['type'], 'Polygon')
        self.assertEqual(response.data['properties']['hashtag'], 'MissionHunt')
