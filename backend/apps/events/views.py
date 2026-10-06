"""
Views and API ViewSets for Event management.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Event
from .serializers import EventSerializer, EventGeoSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    API endpoint for listing, creating, and retrieving scavenger hunt events.
    Supports GeoJSON output via ?format=geojson or dedicated /geojson/ action.
    """
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.request.query_params.get('format') == 'geojson':
            return EventGeoSerializer
        return EventSerializer

    @action(detail=True, methods=['get'], serializer_class=EventGeoSerializer)
    def geojson(self, request, pk=None):
        """
        Returns the event and its bounding polygon formatted as a GeoJSON Feature.
        """
        event = self.get_object()
        serializer = EventGeoSerializer(event, context={'request': request})
        return Response(serializer.data)
