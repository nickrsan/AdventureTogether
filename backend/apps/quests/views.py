"""
Views and API ViewSets for Quest creation and spatial querying.
"""

from rest_framework import viewsets, permissions
from .models import Quest
from .serializers import QuestSerializer, QuestGeoSerializer


class QuestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and creating quests.
    Supports filtering by event ID and GeoJSON representation.
    """
    queryset = Quest.objects.all()
    serializer_class = QuestSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.request.query_params.get('format') == 'geojson':
            return QuestGeoSerializer
        return QuestSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset
