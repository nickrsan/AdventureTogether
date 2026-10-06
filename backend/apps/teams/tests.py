"""
Unit and Integration Tests for Team Formation, Join Codes, and Rosters.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.gis.geos import Polygon
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.events.models import Event
from .models import Team, TeamMembership


class TeamManagementAPITests(TestCase):
    """
    Validates team creation, join code mechanics, and participant enrollment.
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
            title="Hayes Valley Hunt",
            description="Explore Hayes Valley with your team.",
            hashtag="HayesHunt",
            bounding_polygon=self.sf_polygon,
            start_time=now,
            end_time=now + timedelta(hours=3),
        )
        self.team = Team.objects.create(
            event=self.event,
            name="Urban Explorers",
            join_code="EXPLORE1"
        )

    def test_create_team_generates_join_code(self):
        """Creating a team automatically assigns a unique join code."""
        url = reverse('teams:team-list')
        data = {
            'event': self.event.id,
            'name': 'Street Cartographers'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(len(response.data.get('join_code')) >= 6)

    def test_join_team_success(self):
        """Participant successfully joins team using join code."""
        url = reverse('teams:team-join')
        data = {
            'join_code': 'EXPLORE1',
            'user_identifier': 'user-device-uuid-1234',
            'display_name': 'Alice the Mapper'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('Successfully joined team', response.data['message'])

        # Verify membership in database
        membership = TeamMembership.objects.get(user_identifier='user-device-uuid-1234')
        self.assertEqual(membership.team, self.team)
        self.assertEqual(membership.display_name, 'Alice the Mapper')

    def test_join_team_invalid_code(self):
        """Joining with invalid code returns 404."""
        url = reverse('teams:team-join')
        data = {
            'join_code': 'NONEXISTENT',
            'user_identifier': 'user-device-uuid-999',
            'display_name': 'Bob'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
