"""
Submission and Multi-Platform Ingestion Models.
"""

from django.db import models
from apps.events.models import Event
from apps.quests.models import Quest


class Submission(models.Model):
    """
    Represents an open data contribution harvested from OpenStreetMap,
    Wikimedia Commons, or Wikidata matching the event hashtag.
    """
    PLATFORMS = [
        ('osm', 'OpenStreetMap'),
        ('commons', 'Wikimedia Commons'),
        ('wikidata', 'Wikidata'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='submissions',
        help_text="The event this submission belongs to."
    )
    quest = models.ForeignKey(
        Quest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Matched quest (if criteria tags match)."
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submissions',
        help_text="Team credited with the submission (if author is a member)."
    )
    platform = models.CharField(
        max_length=16,
        choices=PLATFORMS,
        help_text="Source platform of the contribution."
    )
    external_id = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Changeset ID, Page ID, or Revision ID on the target platform."
    )
    author_username = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Username of the contributor on the external platform."
    )
    external_url = models.URLField(
        help_text="Direct link to the external changeset, photo, or item."
    )
    diff_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured diff showing added/modified tags, images, or statements."
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether a host has reviewed and verified this submission."
    )
    verified_by_username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Host username who confirmed verification."
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when verification was granted."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the submission was harvested."
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ('platform', 'external_id')
        verbose_name = 'Open Data Submission'
        verbose_name_plural = 'Open Data Submissions'

    def __str__(self):
        return f"[{self.get_platform_display()}] {self.external_id} by {self.author_username} ({'Verified' if self.is_verified else 'Pending'})"
