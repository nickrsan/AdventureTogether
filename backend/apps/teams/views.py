"""
Views and API ViewSets for Team management and joining.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Team, TeamMembership
from .serializers import TeamSerializer, TeamMembershipSerializer, JoinTeamRequestSerializer


class TeamViewSet(viewsets.ModelViewSet):
    """
    API endpoint for creating teams, viewing team rosters, and joining groups via join code.
    """
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        return queryset

    @action(detail=False, methods=['post'], serializer_class=JoinTeamRequestSerializer)
    def join(self, request):
        """
        Allows a participant to join a team using a unique join code.
        """
        serializer = JoinTeamRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        join_code = serializer.validated_data['join_code'].strip().upper()
        user_identifier = serializer.validated_data['user_identifier'].strip()
        display_name = serializer.validated_data.get('display_name', 'Anonymous Mapper').strip()

        try:
            team = Team.objects.get(join_code__iexact=join_code)
        except Team.DoesNotExist:
            return Response(
                {'error': f'Team with join code "{join_code}" does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        membership, created = TeamMembership.objects.update_or_create(
            team=team,
            user_identifier=user_identifier,
            defaults={'display_name': display_name}
        )

        return Response({
            'message': f'Successfully joined team {team.name}!',
            'team': TeamSerializer(team).data,
            'membership': TeamMembershipSerializer(membership).data
        }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
