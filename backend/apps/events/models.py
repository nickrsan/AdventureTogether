"""
Event Models for AdventureTogether.

Manages scavenger hunt events, spatial bounding perimeters, and active time windows.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.text import slugify


class Event(models.Model):
    """
    Represents a localized scavenger hunt event.
    Restricts participant quests and submission harvesting to a designated bounding perimeter.
    """
    title = models.CharField(
        max_length=255,
        help_text="Human-readable title of the scavenger hunt event."
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier for the event."
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed overview and rules for participants."
    )
    hashtag = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Designated event hashtag (without leading #) to identify edits across OSM and Wikimedia."
    )
    bounding_polygon = gis_models.PolygonField(
        srid=4326,
        help_text="Geographic perimeter defining the hunt boundary (EPSG:4326 WGS 84)."
    )
    start_time = models.DateTimeField(
        help_text="Timestamp when the hunt begins."
    )
    end_time = models.DateTimeField(
        help_text="Timestamp when the hunt concludes."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Flag indicating whether the event is actively accepting location pings and submissions."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the event was created."
    )

    class Meta:
        ordering = ['-start_time', 'title']
        verbose_name = 'Scavenger Hunt Event'
        verbose_name_plural = 'Scavenger Hunt Events'

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided, and strip '#' from hashtag."""
        if not self.slug and self.title:
            self.slug = slugify(self.title)
        if self.hashtag:
            self.hashtag = self.hashtag.lstrip('#').strip()
        super().save(*args, **kwargs)

    def is_within_bounds(self, geometry) -> bool:
        """
        Evaluates whether a given geometry (Point, Polygon, or GeometryCollection)
        is contained within or intersects the event bounding polygon.
        """
        if not geometry or not self.bounding_polygon:
            return False
        return self.bounding_polygon.intersects(geometry) or self.bounding_polygon.contains(geometry)

    def __str__(self):
        return f"{self.title} (#{self.hashtag})"
