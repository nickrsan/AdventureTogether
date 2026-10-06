"""
Serializers for Team and Membership models.
"""

from rest_framework import serializers
from .models import Team, TeamMembership


class TeamMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for team participant memberships.
    """
    class Meta:
        model = TeamMembership
        fields = ['id', 'user_identifier', 'display_name', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class TeamSerializer(serializers.ModelSerializer):
    """
    Serializer for Teams with embedded member count and roster.
    """
    memberships = TeamMembershipSerializer(many=True, read_only=True)
    member_count = serializers.IntegerField(source='memberships.count', read_only=True)

    class Meta:
        model = Team
        fields = [
            'id',
            'event',
            'name',
            'join_code',
            'score',
            'member_count',
            'memberships',
            'created_at',
        ]
        read_only_fields = ['id', 'join_code', 'score', 'created_at']


class JoinTeamRequestSerializer(serializers.Serializer):
    """
    Input serializer for joining a team via join code.
    """
    join_code = serializers.CharField(max_length=32, required=True)
    user_identifier = serializers.CharField(max_length=255, required=True)
    display_name = serializers.CharField(max_length=255, required=False, default='Anonymous Mapper')
