"""
Unit and Integration Tests for Ephemeral Geolocation Tracking, Privacy Matrix, and 20-Minute Decay.
"""

from datetime import datetime, timezone, timedelta
from django.contrib.gis.geos import Polygon, Point
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.events.models import Event
from apps.teams.models import Team, TeamMembership
from .models import LocationPing
from .views import cleanup_expired_pings


class LocationTrackingAndPrivacyTests(TestCase):
    """
    Validates location ingestion, visibility scope enforcement, and temporal decay behavior.
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
            title="Location Privacy Hunt",
            hashtag="LocationHunt",
            bounding_polygon=self.sf_polygon,
            start_time=now,
            end_time=now + timedelta(hours=4),
        )

        # Team 1: Alpha (Users: alpha-1, alpha-2)
        self.team_alpha = Team.objects.create(
            event=self.event,
            name="Team Alpha",
            join_code="ALPHA1"
        )
        self.member_a1 = TeamMembership.objects.create(
            team=self.team_alpha,
            user_identifier="user-alpha-1",
            display_name="Alpha 1"
        )
        self.member_a2 = TeamMembership.objects.create(
            team=self.team_alpha,
            user_identifier="user-alpha-2",
            display_name="Alpha 2"
        )

        # Team 2: Beta (User: beta-1)
        self.team_beta = Team.objects.create(
            event=self.event,
            name="Team Beta",
            join_code="BETA11"
        )
        self.member_b1 = TeamMembership.objects.create(
            team=self.team_beta,
            user_identifier="user-beta-1",
            display_name="Beta 1"
        )

    def test_ping_location_creates_and_links_team(self):
        """Posting to /api/locations/ping/ records coordinates and associates team."""
        url = reverse('locations:location-ping')
        data = {
            'event': self.event.id,
            'user_identifier': 'user-alpha-1',
            'display_name': 'Alpha 1',
            'longitude': -122.4194,
            'latitude': 37.7749,
            'visibility': 'team',
            'is_foreground': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        ping = LocationPing.objects.get(user_identifier='user-alpha-1')
        self.assertEqual(ping.team, self.team_alpha)
        self.assertEqual(ping.coordinates.x, -122.4194)
        self.assertEqual(ping.coordinates.y, 37.7749)

    def test_privacy_visibility_nobody(self):
        """Visibility 'nobody' is hidden from teammates and other teams."""
        LocationPing.objects.create(
            event=self.event,
            user_identifier="user-alpha-1",
            display_name="Alpha 1",
            team=self.team_alpha,
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="nobody"
        )

        url = reverse('locations:location-active')

        # Teammate Alpha 2 requests active locations -> should NOT see Alpha 1
        res_a2 = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-alpha-2")
        self.assertEqual(len(res_a2.data), 0)

        # Alpha 1 requests -> CAN see own ping
        res_a1 = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-alpha-1")
        self.assertEqual(len(res_a1.data), 1)

    def test_privacy_visibility_team_only(self):
        """Visibility 'team' is visible to teammates but hidden from other teams."""
        LocationPing.objects.create(
            event=self.event,
            user_identifier="user-alpha-1",
            display_name="Alpha 1",
            team=self.team_alpha,
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="team"
        )

        url = reverse('locations:location-active')

        # Teammate Alpha 2 sees Alpha 1
        res_a2 = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-alpha-2")
        self.assertEqual(len(res_a2.data), 1)
        self.assertEqual(res_a2.data[0]['user_identifier'], 'user-alpha-1')

        # Other team Beta 1 does NOT see Alpha 1
        res_b1 = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-beta-1")
        self.assertEqual(len(res_b1.data), 0)

    def test_privacy_visibility_whole_quest(self):
        """Visibility 'quest' is visible to everyone in the event."""
        LocationPing.objects.create(
            event=self.event,
            user_identifier="user-alpha-1",
            display_name="Alpha 1",
            team=self.team_alpha,
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="quest"
        )

        url = reverse('locations:location-active')

        # Other team Beta 1 can see Alpha 1
        res_b1 = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-beta-1")
        self.assertEqual(len(res_b1.data), 1)
        self.assertEqual(res_b1.data[0]['user_identifier'], 'user-alpha-1')

    def test_20_minute_decay_cutoff(self):
        """Location pings older than 20 minutes are excluded from active locations."""
        ping = LocationPing.objects.create(
            event=self.event,
            user_identifier="user-alpha-1",
            display_name="Alpha 1",
            team=self.team_alpha,
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="quest"
        )

        # Artificially set recorded_at to 25 minutes ago
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=25)
        LocationPing.objects.filter(id=ping.id).update(recorded_at=stale_time)

        url = reverse('locations:location-active')
        res = self.client.get(f"{url}?event={self.event.id}&user_identifier=user-alpha-2")
        self.assertEqual(len(res.data), 0)

    def test_cleanup_expired_pings_routine(self):
        """cleanup_expired_pings purges records older than 20 minutes and keeps fresh ones."""
        fresh_ping = LocationPing.objects.create(
            event=self.event,
            user_identifier="fresh-user",
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="quest"
        )
        stale_ping = LocationPing.objects.create(
            event=self.event,
            user_identifier="stale-user",
            coordinates=Point(-122.41, 37.77, srid=4326),
            visibility="quest"
        )

        # Set stale ping to 30 mins ago
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        LocationPing.objects.filter(id=stale_ping.id).update(recorded_at=stale_time)

        deleted = cleanup_expired_pings(decay_minutes=20)
        self.assertEqual(deleted, 1)

        # Fresh ping remains in database
        self.assertTrue(LocationPing.objects.filter(id=fresh_ping.id).exists())
        self.assertFalse(LocationPing.objects.filter(id=stale_ping.id).exists())
