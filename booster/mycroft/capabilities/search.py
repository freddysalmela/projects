import json
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

import requests
from ddgs import DDGS

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


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
        print(f"[search] ERROR: {e}", flush=True)
        return [{"title": "Search error", "url": "", "snippet": str(e)}]


# ── YouTube ───────────────────────────────────────────────────────────────────

def _video_renderers(node):
    """Every 'videoRenderer' object anywhere inside YouTube's page data, in page order."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "videoRenderer" and isinstance(value, dict):
                yield value
            else:
                yield from _video_renderers(value)
    elif isinstance(node, list):
        for item in node:
            yield from _video_renderers(item)


def _first_text(node) -> str:
    if not isinstance(node, dict):
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    runs = node.get("runs") or []
    return "".join(r.get("text", "") for r in runs)


def parse_youtube_results(html: str, max_results: int = 5) -> list[dict[str, str]]:
    """Pull the video list out of a YouTube search results page."""
    marker = "ytInitialData"
    start = html.find(marker)
    if start < 0:
        return []
    brace = html.find("{", start)
    if brace < 0:
        return []
    data, _ = json.JSONDecoder().raw_decode(html[brace:])

    results = []
    for video in _video_renderers(data):
        video_id = video.get("videoId")
        if not video_id:
            continue
        results.append({
            "title": _first_text(video.get("title")),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "channel": _first_text(video.get("ownerText")),
            "duration": _first_text(video.get("lengthText")),
        })
        if len(results) >= max_results:
            break
    return results


def _youtube_direct(query: str, max_results: int) -> list[dict[str, str]]:
    r = requests.get(
        "https://www.youtube.com/results",
        params={"search_query": query, "hl": "en"},
        headers=_BROWSER_HEADERS,
        cookies={"SOCS": "CAI"},   # skips the EU cookie-consent page
        timeout=10,
    )
    r.raise_for_status()
    return parse_youtube_results(r.text, max_results)


def _youtube_via_duckduckgo(query: str, max_results: int) -> list[dict[str, str]]:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.videos(query, max_results=max_results * 3):
            url = r.get("content", "")
            if "youtube.com/watch" not in url:
                continue
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "channel": r.get("uploader", "") or r.get("publisher", ""),
                "duration": r.get("duration", ""),
            })
            if len(results) >= max_results:
                break
    return results


def youtube_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Find videos and open the best match. If no video list can be fetched, the YouTube
    results page is opened instead, so the user always ends up looking at something."""
    results: list[dict[str, str]] = []
    for name, source in (("youtube", _youtube_direct), ("duckduckgo", _youtube_via_duckduckgo)):
        try:
            results = source(query, max_results)
        except Exception as e:
            print(f"[youtube] {name} lookup failed: {e}", flush=True)
            results = []
        if results:
            break

    if results:
        open_url(results[0]["url"])
        return results

    page = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    open_url(page)
    return [{
        "title": f"Could not read the video list, so the YouTube results page for '{query}' was opened instead.",
        "url": page, "channel": "", "duration": "",
    }]


# ── Browser ───────────────────────────────────────────────────────────────────

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
    if not url.lower().startswith(("http://", "https://")):
        return f"Refused to open '{url}': only http and https links can be opened."
    brave = _find_brave()
    if brave:
        subprocess.Popen([brave, url])
    else:
        webbrowser.open(url)
    return f"Opened {url} in browser."
