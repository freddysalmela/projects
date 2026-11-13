import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent
_CONFIG_FILE = _ROOT / "config.yaml"

# Load .env from the project folder, so it works whatever directory Gaia is started from.
load_dotenv(_ROOT / ".env")
load_dotenv()


def _load_yaml() -> dict:
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@dataclass
class Config:
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""

    model: str = "claude-sonnet-5"
    max_history_turns: int = 20
    wake_word_model: str = "hey_jarvis"
    wake_word_threshold: float = 0.3

    input_device: str = ""
    output_device: str = ""
    silence_threshold: int = 200
    silence_secs: float = 2.8
    max_record_secs: float = 30
    session_timeout_secs: float = 20
    stt_model: str = "whisper-1"
    barge_in: bool = False
    barge_in_threshold: int = 600

    ui_host: str = "127.0.0.1"
    ui_port: int = 5050
    ui_open_browser: bool = True

    search_max_results: int = 5


def _section(raw: dict, *names: str) -> dict:
    """First section that exists. Older config files used 'booster' or 'mycroft'."""
    for name in names:
        value = raw.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def load_config() -> Config:
    raw = _load_yaml()
    gaia = _section(raw, "gaia", "booster", "mycroft")
    audio = _section(raw, "audio")
    ui = _section(raw, "ui")
    search = _section(raw, "search")
    d = Config()

    return Config(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        elevenlabs_api_key=os.environ.get("ELEVENLABS_API_KEY", ""),
        model=os.environ.get("MYCROFT_MODEL") or _text(gaia.get("model")) or d.model,
        max_history_turns=int(gaia.get("max_history_turns", d.max_history_turns)),
        wake_word_model=_text(gaia.get("wake_word_model")) or d.wake_word_model,
        wake_word_threshold=float(gaia.get("wake_word_threshold", d.wake_word_threshold)),
        input_device=_text(audio.get("input_device")),
        output_device=_text(audio.get("output_device")),
        silence_threshold=int(audio.get("silence_threshold", d.silence_threshold)),
        silence_secs=float(audio.get("silence_secs", d.silence_secs)),
        max_record_secs=float(audio.get("max_record_secs", d.max_record_secs)),
        session_timeout_secs=float(audio.get("session_timeout_secs", d.session_timeout_secs)),
        stt_model=_text(audio.get("stt_model")) or d.stt_model,
        barge_in=bool(audio.get("barge_in", d.barge_in)),
        barge_in_threshold=int(audio.get("barge_in_threshold", d.barge_in_threshold)),
        ui_host=_text(ui.get("host")) or d.ui_host,
        ui_port=int(ui.get("port", d.ui_port)),
        ui_open_browser=bool(ui.get("open_browser", d.ui_open_browser)),
        search_max_results=int(search.get("max_results", d.search_max_results)),
    )


_cached: Config | None = None


def get_config() -> Config:
    """Config loaded once and shared by every module."""
    global _cached
    if _cached is None:
        _cached = load_config()
    return _cached
