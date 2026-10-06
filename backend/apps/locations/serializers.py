"""
Serializers for Ephemeral Foreground Location Ingestion and Retrieval.
"""

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from django.contrib.gis.geos import Point
from .models import LocationPing
from apps.events.models import Event
from apps.teams.models import Team, TeamMembership


class LocationPingIngestSerializer(serializers.Serializer):
    """
    Serializer for incoming participant location pings from the mobile/web foreground client.
    """
    event = serializers.PrimaryKeyRelatedField(queryset=Event.objects.all())
    user_identifier = serializers.CharField(max_length=255, required=True)
    display_name = serializers.CharField(max_length=255, required=False, default='Anonymous Mapper')
    longitude = serializers.FloatField(required=True)
    latitude = serializers.FloatField(required=True)
    visibility = serializers.ChoiceField(choices=LocationPing.VISIBILITY_CHOICES, default='team')
    is_foreground = serializers.BooleanField(default=True)

    def create(self, validated_data):
        event = validated_data['event']
        user_identifier = validated_data['user_identifier']
        display_name = validated_data.get('display_name', 'Anonymous Mapper')
        lng = validated_data['longitude']
        lat = validated_data['latitude']
        visibility = validated_data.get('visibility', 'team')
        is_foreground = validated_data.get('is_foreground', True)

        point = Point(lng, lat, srid=4326)

        # Look up team membership if registered
        membership = TeamMembership.objects.filter(
            team__event=event,
            user_identifier=user_identifier
        ).select_related('team').first()

        team = membership.team if membership else None

        ping, _ = LocationPing.objects.update_or_create(
            event=event,
            user_identifier=user_identifier,
            defaults={
                'coordinates': point,
                'display_name': display_name,
                'team': team,
                'visibility': visibility,
                'is_foreground': is_foreground
            }
        )
        return ping


class LocationPingSerializer(serializers.ModelSerializer):
    """
    Standard representation of an active location ping with team metadata.
    """
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    longitude = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()

    class Meta:
        model = LocationPing
        fields = [
            'id',
            'event',
            'user_identifier',
            'display_name',
            'team',
            'team_name',
            'longitude',
            'latitude',
            'visibility',
            'is_foreground',
            'recorded_at',
        ]

    def get_longitude(self, obj):
        return obj.coordinates.x if obj.coordinates else None

    def get_latitude(self, obj):
        return obj.coordinates.y if obj.coordinates else None


class LocationPingGeoSerializer(GeoFeatureModelSerializer):
    """
    GeoJSON Feature serializer for rendering active participant locations on Leaflet maps.
    """
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)

    class Meta:
        model = LocationPing
        geo_field = 'coordinates'
        fields = [
            'id',
            'event',
            'user_identifier',
            'display_name',
            'team_name',
            'visibility',
            'is_foreground',
            'recorded_at',
        ]
