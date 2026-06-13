import threading
import queue
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO

_static = str(Path(__file__).parent / "static")
_app = Flask(__name__, static_folder=_static)
_sio = SocketIO(_app, cors_allowed_origins="*", async_mode="threading")
_trigger_queue: queue.Queue = queue.Queue()

# ── Price cache ────────────────────────────────────────────────────────────────
_price_cache: dict = {}
_price_ts: float = 0
_PRICE_TTL = 60  # seconds

def _fetch_prices() -> dict:
    global _price_cache, _price_ts
    if time.time() - _price_ts < _PRICE_TTL and _price_cache:
        return _price_cache
    try:
        symbols = "BTC-USD,ETH-USD,SPY,GC=F"
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        items = r.json()["quoteResponse"]["result"]
        _price_cache = {
            item["symbol"]: {
                "price": round(item.get("regularMarketPrice", 0), 2),
                "change_pct": round(item.get("regularMarketChangePercent", 0), 2),
            }
            for item in items
        }
        _price_ts = time.time()
    except Exception:
        pass
    return _price_cache

# ── News cache ─────────────────────────────────────────────────────────────────
_news_cache: list = []
_news_ts: float = 0
_NEWS_TTL = 300  # 5 minutes

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
            for item in root.findall(".//item")[:7]
            if item.findtext("title", "").strip()
        ]
        _news_ts = time.time()
    except Exception:
        pass
    return _news_cache


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


# ── SocketIO ───────────────────────────────────────────────────────────────────
@_sio.on("trigger")
def on_trigger():
    _trigger_queue.put(True)


def set_state(state: str, **kwargs):
    """Push a state update to all connected browsers."""
    _sio.emit("state", {"state": state, **kwargs})


def wait_for_trigger():
    """Block until the browser emits a 'trigger' event."""
    _trigger_queue.get()


def start(port: int = 5050):
    """Start the Flask-SocketIO server in a daemon thread."""
    t = threading.Thread(
        target=lambda: _sio.run(_app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True),
        daemon=True,
    )
    t.start()
