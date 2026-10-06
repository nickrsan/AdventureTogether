"""
Location and Ephemeral Geolocation Models.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from apps.events.models import Event


class LocationPing(models.Model):
    """
    Records an ephemeral geolocation ping from a participant.
    Only transmitted when the client application is active in the foreground.
    """
    VISIBILITY_CHOICES = [
        ('nobody', 'Nobody'),
        ('team', 'Team Only'),
        ('quest', 'Whole Quest'),
    ]

    user_identifier = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique device identifier or username for the participant."
    )
    display_name = models.CharField(
        max_length=255,
        default='Anonymous Mapper',
        help_text="Participant display name visible on the map."
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='location_pings',
        help_text="The participant's team (if joined)."
    )
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='location_pings',
        help_text="The active event."
    )
    coordinates = gis_models.PointField(
        srid=4326,
        help_text="WGS 84 GPS coordinates (longitude, latitude)."
    )
    visibility = models.CharField(
        max_length=16,
        choices=VISIBILITY_CHOICES,
        default='team',
        help_text="Privacy visibility scope selected by the user."
    )
    is_foreground = models.BooleanField(
        default=True,
        help_text="True if the browser tab/app was active in the foreground at capture time."
    )
    recorded_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp of the most recent coordinate update."
    )

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Location Ping'
        verbose_name_plural = 'Location Pings'

    def __str__(self):
        return f"{self.display_name} ({self.visibility}) at {self.recorded_at}"
