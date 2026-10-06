"""
Serializers for Ingested Submissions and Host Verification.
"""

from rest_framework import serializers
from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    """
    Serializer for Submission objects with embedded quest and team details.
    """
    quest_title = serializers.CharField(source='quest.title', read_only=True, allow_null=True)
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id',
            'event',
            'quest',
            'quest_title',
            'team',
            'team_name',
            'platform',
            'platform_display',
            'external_id',
            'author_username',
            'external_url',
            'diff_payload',
            'is_verified',
            'verified_by_username',
            'verified_at',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class VerifySubmissionInputSerializer(serializers.Serializer):
    """
    Input serializer for verifying or un-verifying a staged submission.
    """
    is_verified = serializers.BooleanField(default=True)
    verified_by_username = serializers.CharField(max_length=255, default='Host')
