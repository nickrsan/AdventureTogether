"""
Unit and Integration Tests for Quests, Criteria Rules, and Geometry Containment.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.gis.geos import Polygon, Point
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.events.models import Event
from .models import Quest


class QuestValidationAndAPITests(TestCase):
    """
    Validates Quest criteria matching algorithms, geometry validation against event bounds, and REST endpoints.
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
            title="Downtown Mapping Challenge",
            hashtag="DowntownMap",
            bounding_polygon=self.sf_polygon,
            start_time=now,
            end_time=now + timedelta(hours=5),
        )
        self.quest = Quest.objects.create(
            event=self.event,
            title="Add Restaurant Opening Hours",
            description="Add opening_hours tag to 5 restaurants.",
            criteria_type="osm_tags",
            validation_rules={
                "required_tags": {
                    "amenity": "restaurant",
                    "opening_hours": "*"
                },
                "target_count": 5
            },
            points_reward=20
        )

    def test_osm_tag_matching_positive(self):
        """Element matching required tags succeeds."""
        tags = {
            "amenity": "restaurant",
            "name": "Super Duper Burgers",
            "opening_hours": "Mo-Su 11:00-22:00"
        }
        self.assertTrue(self.quest.matches_osm_tags(tags))

    def test_osm_tag_matching_missing_key(self):
        """Element missing opening_hours fails."""
        tags = {
            "amenity": "restaurant",
            "name": "Super Duper Burgers"
        }
        self.assertFalse(self.quest.matches_osm_tags(tags))

    def test_osm_tag_matching_wrong_amenity(self):
        """Element with non-matching amenity fails."""
        tags = {
            "amenity": "cafe",
            "opening_hours": "Mo-Su 08:00-18:00"
        }
        self.assertFalse(self.quest.matches_osm_tags(tags))

    def test_create_quest_within_event_bounds_succeeds(self):
        """Creating quest with target geometry inside bounding polygon succeeds."""
        inside_point = Point(-122.41, 37.77)
        url = reverse('quests:quest-list')
        data = {
            'event': self.event.id,
            'title': 'Map Dolores Park Benches',
            'description': 'Map benches in the park.',
            'criteria_type': 'osm_tags',
            'target_geometry': inside_point.ewkt,
            'validation_rules': {'required_tags': {'amenity': 'bench'}},
            'points_reward': 15
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_quest_outside_event_bounds_rejected(self):
        """Creating quest with target geometry outside bounding polygon returns 400 Bad Request."""
        outside_point = Point(-122.60, 37.90)  # Outside SF polygon
        url = reverse('quests:quest-list')
        data = {
            'event': self.event.id,
            'title': 'Out of Bounds Quest',
            'description': 'This should fail validation.',
            'criteria_type': 'osm_tags',
            'target_geometry': outside_point.ewkt,
            'validation_rules': {'required_tags': {'amenity': 'bench'}}
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_geometry', response.data)
