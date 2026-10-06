"""
Views and API Endpoints for Ephemeral Foreground Location Ingestion and Privacy Filtering.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import LocationPing
from .serializers import (
    LocationPingIngestSerializer,
    LocationPingSerializer,
    LocationPingGeoSerializer
)
from apps.teams.models import TeamMembership


def cleanup_expired_pings(decay_minutes: int = 20) -> int:
    """
    Deletes location pings older than the decay retention window (default: 20 minutes).
    Returns count of deleted records.
    """
    cutoff = timezone.now() - timedelta(minutes=decay_minutes)
    deleted_count, _ = LocationPing.objects.filter(recorded_at__lt=cutoff).delete()
    return deleted_count


@api_view(['POST'])
@permission_classes([AllowAny])
def ping_location(request):
    """
    Ingests a foreground location ping from a participant.
    """
    serializer = LocationPingIngestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    ping = serializer.save()

    return Response(
        LocationPingSerializer(ping).data,
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_locations(request):
    """
    Returns active participant locations within the 20-minute decay window,
    filtered by the privacy visibility matrix.
    """
    event_id = request.query_params.get('event')
    user_identifier = request.query_params.get('user_identifier', '').strip()
    as_geojson = request.query_params.get('format') == 'geojson'

    if not event_id:
        return Response(
            {'error': 'Parameter "event" is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 20-minute decay cutoff
    decay_cutoff = timezone.now() - timedelta(minutes=20)

    # Base query: matching event and active within 20 minutes
    base_qs = LocationPing.objects.filter(
        event_id=event_id,
        recorded_at__gte=decay_cutoff
    ).select_related('team')

    # Determine requesting user's team
    user_team = None
    if user_identifier:
        membership = TeamMembership.objects.filter(
            team__event_id=event_id,
            user_identifier=user_identifier
        ).select_related('team').first()
        if membership:
            user_team = membership.team

    # Build privacy visibility filter:
    # 1. Own ping (user_identifier == request user)
    # 2. Whole quest visible pings (visibility == 'quest')
    # 3. Teammate pings (team == user_team AND visibility == 'team'), if user is on a team
    privacy_filter = Q(user_identifier=user_identifier) | Q(visibility='quest')

    if user_team:
        privacy_filter |= Q(team=user_team, visibility='team')

    active_pings = base_qs.filter(privacy_filter).order_by('-recorded_at')

    if as_geojson:
        serializer = LocationPingGeoSerializer(active_pings, many=True)
    else:
        serializer = LocationPingSerializer(active_pings, many=True)

    return Response(serializer.data)
