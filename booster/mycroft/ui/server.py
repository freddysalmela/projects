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
    _sio.emit("state", {"state": state, **kwargs})


def wait_for_trigger():
    _trigger_queue.get()


def start(port: int = 5050):
    t = threading.Thread(
        target=lambda: _sio.run(_app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True),
        daemon=True,
    )
    t.start()
