"""
Quest and Geospatial Challenge Models.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from apps.events.models import Event


class Quest(models.Model):
    """
    Represents a scavenger hunt challenge created by a host.
    Includes target geometries (points or zones) and open data validation criteria.
    """
    CRITERIA_TYPES = [
        ('osm_tags', 'OpenStreetMap Tag Rule'),
        ('wikimedia_commons', 'Wikimedia Commons Photo'),
        ('wikidata_entry', 'Wikidata Item Edit'),
    ]

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='quests',
        help_text="The event this quest belongs to."
    )
    title = models.CharField(
        max_length=255,
        help_text="Short title of the quest challenge."
    )
    description = models.TextField(
        help_text="Instructions for field participants."
    )
    target_geometry = gis_models.GeometryField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Specific point, polygon zone, or geometry for the quest (optional, defaults to entire event perimeter)."
    )
    criteria_type = models.CharField(
        max_length=32,
        choices=CRITERIA_TYPES,
        default='osm_tags',
        help_text="Platform and verification type for this quest."
    )
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text='JSON criteria: e.g. {"required_tags": {"amenity": "restaurant", "opening_hours": "*"}, "target_count": 5}'
    )
    points_reward = models.IntegerField(
        default=10,
        help_text="Score awarded to a team upon verified completion."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this quest is active for completion."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the quest was created."
    )

    class Meta:
        ordering = ['title']
        verbose_name = 'Scavenger Hunt Quest'
        verbose_name_plural = 'Scavenger Hunt Quests'

    def matches_osm_tags(self, tags: dict) -> bool:
        """
        Validates if an OpenStreetMap element's tags satisfy this quest's tag criteria.
        Wildcard '*' matches any non-empty value.
        """
        if self.criteria_type != 'osm_tags' or not isinstance(tags, dict):
            return False

        required_tags = self.validation_rules.get('required_tags', {})
        if not required_tags:
            return True

        for key, expected_val in required_tags.items():
            if key not in tags:
                return False
            if expected_val != '*' and str(tags[key]).lower() != str(expected_val).lower():
                return False

        return True

    def __str__(self):
        return f"{self.title} ({self.get_criteria_type_display()}) - Event: {self.event.title}"
