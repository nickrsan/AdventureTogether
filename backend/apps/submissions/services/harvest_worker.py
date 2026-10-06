"""
Background Harvester Worker Orchestrator (Django-Q2).
"""

from typing import List, Dict, Any
from apps.events.models import Event
from apps.submissions.models import Submission
from .osm_harvester import fetch_osm_changesets, fetch_osm_changeset_diff
from .wikimedia_harvester import fetch_wikimedia_commons_uploads
from .wikidata_harvester import fetch_wikidata_revisions
from .tag_matcher import match_submission_to_quest, match_author_to_team


def harvest_event_submissions(event_id: int) -> Dict[str, int]:
    """
    Harvests OSM, Commons, and Wikidata contributions for a specific event.
    Returns counts of harvested and staged submissions.
    """
    stats = {'harvested': 0, 'created': 0, 'matched': 0}

    try:
        event = Event.objects.get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        return stats

    hashtag = event.hashtag

    # 1. Harvest OpenStreetMap Changesets
    min_lon, min_lat, max_lon, max_lat = event.bounding_polygon.extent
    bbox_str = f"{min_lon:.5f},{min_lat:.5f},{max_lon:.5f},{max_lat:.5f}"

    osm_items = fetch_osm_changesets(bbox_str, hashtag)
    stats['harvested'] += len(osm_items)

    for item in osm_items:
        ext_id = item['external_id']
        diff = fetch_osm_changeset_diff(ext_id)

        quest = match_submission_to_quest(event, 'osm', diff)
        team = match_author_to_team(event, item['author_username'])

        submission, created = Submission.objects.get_or_create(
            platform='osm',
            external_id=ext_id,
            defaults={
                'event': event,
                'quest': quest,
                'team': team,
                'author_username': item['author_username'],
                'external_url': item['external_url'],
                'diff_payload': diff,
            }
        )
        if created:
            stats['created'] += 1
            if quest:
                stats['matched'] += 1

    # 2. Harvest Wikimedia Commons Uploads
    commons_items = fetch_wikimedia_commons_uploads(hashtag)
    stats['harvested'] += len(commons_items)

    for item in commons_items:
        ext_id = item['external_id']
        quest = match_submission_to_quest(event, 'commons', item['diff_payload'])
        team = match_author_to_team(event, item['author_username'])

        submission, created = Submission.objects.get_or_create(
            platform='commons',
            external_id=ext_id,
            defaults={
                'event': event,
                'quest': quest,
                'team': team,
                'author_username': item['author_username'],
                'external_url': item['external_url'],
                'diff_payload': item['diff_payload'],
            }
        )
        if created:
            stats['created'] += 1
            if quest:
                stats['matched'] += 1

    # 3. Harvest Wikidata Edits
    wikidata_items = fetch_wikidata_revisions(hashtag)
    stats['harvested'] += len(wikidata_items)

    for item in wikidata_items:
        ext_id = item['external_id']
        quest = match_submission_to_quest(event, 'wikidata', item['diff_payload'])
        team = match_author_to_team(event, item['author_username'])

        submission, created = Submission.objects.get_or_create(
            platform='wikidata',
            external_id=ext_id,
            defaults={
                'event': event,
                'quest': quest,
                'team': team,
                'author_username': item['author_username'],
                'external_url': item['external_url'],
                'diff_payload': item['diff_payload'],
            }
        )
        if created:
            stats['created'] += 1
            if quest:
                stats['matched'] += 1

    return stats


def harvest_all_active_events() -> Dict[int, Dict[str, int]]:
    """
    Scheduled task entrypoint: iterates through all active events and harvests submissions.
    """
    results = {}
    active_events = Event.objects.filter(is_active=True)
    for event in active_events:
        results[event.id] = harvest_event_submissions(event.id)
    return results
