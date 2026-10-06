"""
OpenStreetMap Changeset Harvester & XML Diff Parser.
"""

import xml.etree.ElementTree as ET
import requests
from typing import List, Dict, Any, Optional

OSM_API_BASE = "https://api.openstreetmap.org/api/0.6"
DEFAULT_USER_AGENT = "AdventureTogether-Harvester/1.0 (https://adventuretogether.org; contact@adventuretogether.org)"


def parse_osm_changeset_xml(xml_content: str, hashtag: str) -> List[Dict[str, Any]]:
    """
    Parses OpenStreetMap changeset XML and filters changesets matching the hashtag.
    """
    results = []
    normalized_tag = hashtag.lstrip('#').lower()

    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return results

    for cs in root.findall('changeset'):
        cs_id = cs.attrib.get('id')
        user = cs.attrib.get('user', 'Anonymous OSM Contributor')
        created_at = cs.attrib.get('created_at', '')

        # Extract tags
        tags = {}
        for tag in cs.findall('tag'):
            k = tag.attrib.get('k')
            v = tag.attrib.get('v')
            if k and v:
                tags[k] = v

        comment = tags.get('comment', '')
        hashtags_in_comment = tags.get('hashtags', '')

        # Match hashtag in comment, hashtags key, or created_by
        combined_text = f"{comment} {hashtags_in_comment}".lower()
        if f"#{normalized_tag}" in combined_text or normalized_tag in combined_text:
            results.append({
                'external_id': str(cs_id),
                'platform': 'osm',
                'author_username': user,
                'external_url': f"https://www.openstreetmap.org/changeset/{cs_id}",
                'comment': comment,
                'tags': tags,
                'created_at': created_at
            })

    return results


def parse_osm_change_diff(xml_content: str) -> Dict[str, Any]:
    """
    Parses an osmChange XML payload (e.g. from changeset download)
    and extracts modified element tags and coordinates.
    """
    diff_payload: Dict[str, Any] = {
        'actions': [],
        'elements_summary': {'created': 0, 'modified': 0, 'deleted': 0},
        'modified_tags_list': []
    }

    try:
        root = ET.fromstring(xml_content)
    except Exception:
        return diff_payload

    for action_elem in root:
        action_name = action_elem.tag  # 'create', 'modify', 'delete'
        if action_name not in ['create', 'modify', 'delete']:
            continue

        for elem in action_elem:
            elem_type = elem.tag  # 'node', 'way', 'relation'
            elem_id = elem.attrib.get('id')
            lat = elem.attrib.get('lat')
            lon = elem.attrib.get('lon')

            elem_tags = {}
            for t in elem.findall('tag'):
                k = t.attrib.get('k')
                v = t.attrib.get('v')
                if k and v:
                    elem_tags[k] = v

            action_data = {
                'action': action_name,
                'element_type': elem_type,
                'id': elem_id,
                'lat': float(lat) if lat else None,
                'lon': float(lon) if lon else None,
                'tags': elem_tags
            }

            diff_payload['actions'].append(action_data)
            action_key = 'created' if action_name == 'create' else ('modified' if action_name == 'modify' else 'deleted')
            if action_key in diff_payload['elements_summary']:
                diff_payload['elements_summary'][action_key] += 1

            if elem_tags:
                diff_payload['modified_tags_list'].append(elem_tags)

    return diff_payload


def fetch_osm_changesets(bbox_str: str, hashtag: str, user_agent: str = DEFAULT_USER_AGENT) -> List[Dict[str, Any]]:
    """
    Queries the OSM Changeset API for changesets intersecting the bounding box.
    bbox_str format: 'min_lon,min_lat,max_lon,max_lat'
    """
    url = f"{OSM_API_BASE}/changesets"
    params = {'bbox': bbox_str}
    headers = {'User-Agent': user_agent, 'Accept': 'application/xml'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return parse_osm_changeset_xml(response.text, hashtag)
    except Exception:
        pass
    return []


def fetch_osm_changeset_diff(changeset_id: str, user_agent: str = DEFAULT_USER_AGENT) -> Dict[str, Any]:
    """
    Downloads and parses the osmChange XML diff for a specific changeset.
    """
    url = f"{OSM_API_BASE}/changeset/{changeset_id}/download"
    headers = {'User-Agent': user_agent, 'Accept': 'application/xml'}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return parse_osm_change_diff(response.text)
    except Exception:
        pass
    return {'actions': [], 'elements_summary': {'created': 0, 'modified': 0, 'deleted': 0}, 'modified_tags_list': []}
