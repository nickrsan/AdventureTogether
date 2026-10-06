"""
Wikidata Entity Edit & Revision Harvester.
"""

import requests
from typing import List, Dict, Any

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
DEFAULT_USER_AGENT = "AdventureTogether-Harvester/1.0 (https://adventuretogether.org; contact@adventuretogether.org)"


def parse_wikidata_search_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses MediaWiki search JSON response into structured Wikidata entity submission records.
    """
    results = []
    query = data.get('query', {})
    search_results = query.get('search', [])

    for item in search_results:
        page_id = str(item.get('pageid'))
        title = item.get('title', '')
        snippet = item.get('snippet', '')
        timestamp = item.get('timestamp', '')

        external_url = f"https://www.wikidata.org/wiki/{title}"

        results.append({
            'external_id': page_id,
            'platform': 'wikidata',
            'author_username': 'Wikidata Contributor',
            'external_url': external_url,
            'title': title,
            'snippet': snippet,
            'created_at': timestamp,
            'diff_payload': {
                'entity_id': title,
                'snippet': snippet,
                'pageid': page_id
            }
        })

    return results


def fetch_wikidata_revisions(hashtag: str, user_agent: str = DEFAULT_USER_AGENT) -> List[Dict[str, Any]]:
    """
    Searches Wikidata for entity edits matching the event hashtag.
    """
    normalized_tag = hashtag.lstrip('#')
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': f"#{normalized_tag}",
        'srnamespace': '0',  # Main item namespace
        'srlimit': '50',
        'format': 'json'
    }
    headers = {'User-Agent': user_agent}

    try:
        response = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return parse_wikidata_search_response(response.json())
    except Exception:
        pass
    return []
