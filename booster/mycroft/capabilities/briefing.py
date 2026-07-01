import xml.etree.ElementTree as ET
from pathlib import Path

import requests

_WMO_DESC = {
    0: "clear skies", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "showers", 82: "heavy showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "heavy thunderstorm",
}


def morning_briefing() -> str:
    parts = []

    # Weather — Vaasa
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 63.0951, "longitude": 21.6165,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "Europe/Helsinki",
            },
            timeout=6,
        )
        cur = r.json()["current"]
        temp = round(cur["temperature_2m"])
        wind = round(cur.get("wind_speed_10m", 0))
        desc = _WMO_DESC.get(cur.get("weather_code", 0), "")
        parts.append(f"Weather in Vaasa: {temp} degrees, {desc}, wind at {wind} metres per second.")
    except Exception:
        pass

    # Top news headline — BBC World
    try:
        r = requests.get(
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=6,
        )
        root = ET.fromstring(r.content)
        headline = root.findtext(".//item/title", "").strip()
        if headline:
            parts.append(f"Top news: {headline}.")
    except Exception:
        pass

    # Remind about most-recently-saved note
    try:
        notes = sorted(
            (Path.home() / "gaia_notes").glob("*.md"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if notes:
            name = notes[0].stem.replace("_", " ")
            parts.append(f"You have a saved note on {name}.")
    except Exception:
        pass

    return " ".join(parts)
