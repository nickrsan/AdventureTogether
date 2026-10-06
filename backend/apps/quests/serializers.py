"""
Serializers for Quest models and spatial validation.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Quest


class QuestSerializer(serializers.ModelSerializer):
    """
    Standard serializer for Quests with spatial containment validation.
    """
    class Meta:
        model = Quest
        fields = [
            'id',
            'event',
            'title',
            'description',
            'target_geometry',
            'criteria_type',
            'validation_rules',
            'points_reward',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        """
        Validates that quest target geometry resides within or intersects the event bounding perimeter.
        """
        event = attrs.get('event') or (self.instance.event if self.instance else None)
        target_geometry = attrs.get('target_geometry', getattr(self.instance, 'target_geometry', None))

        if event and target_geometry:
            if not event.is_within_bounds(target_geometry):
                raise serializers.ValidationError({
                    'target_geometry': 'Quest target geometry must reside within or intersect the event bounding perimeter.'
                })
        return attrs


class QuestGeoSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON Feature serializer for Quests.
    """
    class Meta:
        model = Quest
        geo_field = 'target_geometry'
        fields = [
            'id',
            'event',
            'title',
            'description',
            'criteria_type',
            'validation_rules',
            'points_reward',
            'is_active',
            'created_at',
        ]
