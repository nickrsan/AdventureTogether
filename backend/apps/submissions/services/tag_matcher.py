"""
Tag Comparison & Quest Criteria Matching Engine.
"""

from typing import Optional, List, Dict, Any
from apps.events.models import Event
from apps.quests.models import Quest
from apps.teams.models import TeamMembership, Team


def match_submission_to_quest(event: Event, platform: str, diff_payload: Dict[str, Any]) -> Optional[Quest]:
    """
    Evaluates a submission's diff against the event's active quests and returns the matching Quest (if any).
    """
    active_quests = Quest.objects.filter(event=event, is_active=True)

    if platform == 'osm':
        osm_quests = active_quests.filter(criteria_type='osm_tags')
        modified_tags_list = diff_payload.get('modified_tags_list', [])

        for quest in osm_quests:
            for tags in modified_tags_list:
                if quest.matches_osm_tags(tags):
                    return quest

    elif platform == 'commons':
        commons_quests = active_quests.filter(criteria_type='wikimedia_commons')
        if commons_quests.exists():
            return commons_quests.first()

    elif platform == 'wikidata':
        wikidata_quests = active_quests.filter(criteria_type='wikidata_entry')
        if wikidata_quests.exists():
            return wikidata_quests.first()

    return None


def match_author_to_team(event: Event, author_username: str) -> Optional[Team]:
    """
    Looks up whether the author has joined a team in this event.
    """
    if not author_username:
        return None

    membership = TeamMembership.objects.filter(
        team__event=event,
        user_identifier__iexact=author_username
    ).select_related('team').first()

    if not membership:
        membership = TeamMembership.objects.filter(
            team__event=event,
            display_name__iexact=author_username
        ).select_related('team').first()

    return membership.team if membership else None
