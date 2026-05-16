import webbrowser
from typing import Any

from ddgs import DDGS
from youtubesearchpython import VideosSearch


def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as e:
        return [{"title": "Search error", "url": "", "snippet": str(e)}]


def youtube_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    try:
        search = VideosSearch(query, limit=max_results)
        raw = search.result().get("result", [])
        results = []
        for item in raw:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "channel": item.get("channel", {}).get("name", ""),
                "duration": item.get("duration", ""),
            })
        return results
    except Exception as e:
        return [{"title": "YouTube search error", "url": "", "channel": "", "duration": "", "error": str(e)}]


def open_url(url: str) -> str:
    webbrowser.open(url)
    return f"Opened {url} in browser."
