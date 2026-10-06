"""
Wikimedia Commons Image & Category Harvester.
"""

import requests
from typing import List, Dict, Any

WIKIMEDIA_COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DEFAULT_USER_AGENT = "AdventureTogether-Harvester/1.0 (https://adventuretogether.org; contact@adventuretogether.org)"


def parse_wikimedia_search_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses MediaWiki search JSON response into structured photo submission records.
    """
    results = []
    query = data.get('query', {})
    search_results = query.get('search', [])

    for item in search_results:
        page_id = str(item.get('pageid'))
        title = item.get('title', '')
        snippet = item.get('snippet', '')
        timestamp = item.get('timestamp', '')

        # Clean title for URL
        clean_title = title.replace(' ', '_')
        external_url = f"https://commons.wikimedia.org/wiki/{clean_title}"

        results.append({
            'external_id': page_id,
            'platform': 'commons',
            'author_username': 'Wikimedia Uploader',
            'external_url': external_url,
            'title': title,
            'snippet': snippet,
            'created_at': timestamp,
            'diff_payload': {
                'media_type': 'image',
                'title': title,
                'snippet': snippet,
                'pageid': page_id
            }
        })

    return results


def fetch_wikimedia_commons_uploads(hashtag: str, user_agent: str = DEFAULT_USER_AGENT) -> List[Dict[str, Any]]:
    """
    Searches Wikimedia Commons for files with the designated hashtag.
    """
    normalized_tag = hashtag.lstrip('#')
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': f"#{normalized_tag} file:",
        'srnamespace': '6',  # Namespace 6 = File
        'srlimit': '50',
        'format': 'json'
    }
    headers = {'User-Agent': user_agent}

    try:
        response = requests.get(WIKIMEDIA_COMMONS_API, params=params, headers=headers, timeout=15)
        if response.status_code == 200:
            return parse_wikimedia_search_response(response.json())
    except Exception:
        pass
    return []
