import threading
import queue
import time
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO

_static = str(Path(__file__).parent / "static")
_app = Flask(__name__, static_folder=_static)
_sio = SocketIO(_app, cors_allowed_origins="*", async_mode="threading")
_trigger_queue: queue.Queue = queue.Queue()

# ── Price + sparkline cache ────────────────────────────────────────────────────
_price_cache: dict = {}
_price_ts: float = 0
_PRICE_TTL = 60


def _fetch_crypto() -> dict:
    url = "https://api.coingecko.com/api/v3/coins/markets"
    r = requests.get(url, params={
        "vs_currency": "usd",
        "ids": "bitcoin,ethereum",
        "sparkline": "true",
        "price_change_percentage": "24h",
    }, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    result = {}
    for coin in r.json():
        sym = "BTC-USD" if coin["id"] == "bitcoin" else "ETH-USD"
        raw = coin.get("sparkline_in_7d", {}).get("price", [])
        step = max(1, len(raw) // 40)
        result[sym] = {
            "price":      round(coin["current_price"], 2),
            "change_pct": round(coin.get("price_change_percentage_24h") or 0, 2),
            "sparkline":  raw[::step][-40:],
        }
    return result


def _fetch_yahoo(symbol: str) -> dict:
    r = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"interval": "1d", "range": "1mo"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    res  = r.json()["chart"]["result"][0]
    meta = res["meta"]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    price  = meta.get("regularMarketPrice", 0)
    prev   = meta.get("previousClose") or meta.get("chartPreviousClose") or price
    chg    = (price - prev) / prev * 100 if prev else 0
    return {
        "price":      round(price, 2),
        "change_pct": round(chg, 2),
        "sparkline":  closes[-40:],
    }


def _fetch_prices() -> dict:
    global _price_cache, _price_ts
    if time.time() - _price_ts < _PRICE_TTL and _price_cache:
        return _price_cache
    data: dict = {}
    try:
        data.update(_fetch_crypto())
    except Exception:
        pass
    for sym in ["SPY", "GC=F"]:
        try:
            data[sym] = _fetch_yahoo(sym)
        except Exception:
            pass
    if data:
        _price_cache = data
        _price_ts = time.time()
    return _price_cache


# ── News cache ─────────────────────────────────────────────────────────────────
_news_cache: list = []
_news_ts: float = 0
_NEWS_TTL = 300


def _fetch_news() -> list:
    global _news_cache, _news_ts
    if time.time() - _news_ts < _NEWS_TTL and _news_cache:
        return _news_cache
    try:
        r = requests.get(
            "https://feeds.bbci.co.uk/news/world/rss.xml",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        root = ET.fromstring(r.content)
        _news_cache = [
            item.findtext("title", "").strip()
            for item in root.findall(".//item")[:8]
            if item.findtext("title", "").strip()
        ]
        _news_ts = time.time()
    except Exception:
        pass
    return _news_cache


# ── Weather cache (Vaasa / Ostrobothnia) ──────────────────────────────────────
_weather_cache: dict = {}
_weather_ts: float = 0
_WEATHER_TTL = 600  # 10 minutes

_WMO_DESC = {
    0:"Klart", 1:"Mestadels klart", 2:"Delvis molnigt", 3:"Mulet",
    45:"Dimma", 48:"Rimfrost",
    51:"Duggregn", 53:"Duggregn", 55:"Tätt duggregn",
    61:"Lätt regn", 63:"Regn", 65:"Kraftigt regn",
    71:"Lätt snöfall", 73:"Snöfall", 75:"Kraftigt snöfall", 77:"Snöhagel",
    80:"Regnskurar", 81:"Regnskurar", 82:"Kraftiga skurar",
    85:"Snöskurar", 86:"Kraftiga snöskurar",
    95:"Åska", 96:"Åska med hagel", 99:"Kraftig åska",
}
_WMO_ICON = {
    0:"☀", 1:"🌤", 2:"⛅", 3:"☁",
    45:"🌫", 48:"🌫",
    51:"🌦", 53:"🌦", 55:"🌦",
    61:"🌧", 63:"🌧", 65:"🌧",
    71:"❄", 73:"❄", 75:"❄", 77:"❄",
    80:"🌦", 81:"🌦", 82:"🌦",
    85:"❄", 86:"❄",
    95:"⛈", 96:"⛈", 99:"⛈",
}
_DAYS_SV = ["Mån","Tis","Ons","Tor","Fre","Lör","Sön"]


def _fetch_weather() -> dict:
    global _weather_cache, _weather_ts
    if time.time() - _weather_ts < _WEATHER_TTL and _weather_cache:
        return _weather_cache
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 63.0951, "longitude": 21.6165,
                "current": "temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m",
                "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                "timezone": "Europe/Helsinki",
                "forecast_days": 4,
                "wind_speed_unit": "ms",
            },
            timeout=8,
        )
        d = r.json()
        cur = d["current"]
        day = d["daily"]
        wc  = cur.get("weather_code", 0)
        forecast = []
        for i in range(4):
            dt = datetime.date.fromisoformat(day["time"][i])
            label = ["Idag", "Imorgon"][i] if i < 2 else _DAYS_SV[dt.weekday()]
            forecast.append({
                "day":  label,
                "max":  round(day["temperature_2m_max"][i]),
                "min":  round(day["temperature_2m_min"][i]),
                "icon": _WMO_ICON.get(day["weather_code"][i], "?"),
                "desc": _WMO_DESC.get(day["weather_code"][i], ""),
            })
        _weather_cache = {
            "temp":     round(cur["temperature_2m"]),
            "desc":     _WMO_DESC.get(wc, "Okänt"),
            "icon":     _WMO_ICON.get(wc, "?"),
            "wind":     round(cur.get("wind_speed_10m", 0)),
            "humidity": round(cur.get("relative_humidity_2m", 0)),
            "forecast": forecast,
        }
        _weather_ts = time.time()
    except Exception:
        pass
    return _weather_cache


# ── Routes ─────────────────────────────────────────────────────────────────────
@_app.route("/")
def index():
    return send_from_directory(_static, "index.html")

@_app.route("/api/prices")
def api_prices():
    return jsonify(_fetch_prices())

@_app.route("/api/news")
def api_news():
    return jsonify({"headlines": _fetch_news()})

@_app.route("/api/weather")
def api_weather():
    return jsonify(_fetch_weather())


# ── SocketIO ───────────────────────────────────────────────────────────────────
@_sio.on("trigger")
def on_trigger():
    _trigger_queue.put(True)


@_sio.on("stop")
def on_stop():
    from mycroft import state
    state.stop_event.set()


def set_state(state: str, **kwargs):
    _sio.emit("state", {"state": state, **kwargs})


def wait_for_trigger():
    _trigger_queue.get()


def start(port: int = 5050):
    t = threading.Thread(
        target=lambda: _sio.run(_app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True),
        daemon=True,
    )
    t.start()
