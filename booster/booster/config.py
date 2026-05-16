import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).parent.parent
_CONFIG_FILE = _ROOT / "config.yaml"


def _load_yaml() -> dict:
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


@dataclass
class Config:
    anthropic_api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    model: str = "claude-sonnet-4-6"
    max_history_turns: int = 20

    stt_backend: str = "google"
    tts_backend: str = "gtts"
    whisper_model: str = "tiny"
    wake_mode: str = "wake_word"
    speech_timeout: int = 5
    pause_threshold: float = 0.8

    search_max_results: int = 5

    save_plans: bool = True
    plans_directory: str = "~/booster_plans"


def load_config() -> Config:
    raw = _load_yaml()
    booster = raw.get("booster", {})
    audio = raw.get("audio", {})
    search = raw.get("search", {})
    planner = raw.get("planner", {})

    cfg = Config(
        model=os.environ.get("BOOSTER_MODEL", booster.get("model", "claude-sonnet-4-6")),
        max_history_turns=int(booster.get("max_history_turns", 20)),
        stt_backend=os.environ.get("BOOSTER_STT", audio.get("stt_backend", "google")),
        tts_backend=os.environ.get("BOOSTER_TTS", audio.get("tts_backend", "gtts")),
        whisper_model=audio.get("whisper_model", "tiny"),
        wake_mode=os.environ.get("BOOSTER_WAKE_MODE", audio.get("wake_mode", "wake_word")),
        speech_timeout=int(audio.get("speech_timeout", 5)),
        pause_threshold=float(audio.get("pause_threshold", 0.8)),
        search_max_results=int(search.get("max_results", 5)),
        save_plans=bool(planner.get("save_plans", True)),
        plans_directory=planner.get("plans_directory", "~/booster_plans"),
    )
    return cfg
