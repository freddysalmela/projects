import subprocess
import webbrowser
from pathlib import Path

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
        # Always open the top result automatically
        if results and results[0]["url"]:
            open_url(results[0]["url"])
        return results
    except Exception as e:
        return [{"title": "YouTube search error", "url": "", "channel": "", "duration": "", "error": str(e)}]


_BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    str(Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
]


def _find_brave() -> str | None:
    for p in _BRAVE_PATHS:
        if Path(p).exists():
            return p
    return None


def open_url(url: str) -> str:
    brave = _find_brave()
    if brave:
        subprocess.Popen([brave, url])
    else:
        webbrowser.open(url)
    return f"Opened {url} in browser."
