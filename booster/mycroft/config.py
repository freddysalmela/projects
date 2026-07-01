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
    anthropic_api_key: str  = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    openai_api_key: str     = field(default_factory=lambda: os.environ.get("OPENAI_API_KEY", ""))
    elevenlabs_api_key: str = field(default_factory=lambda: os.environ.get("ELEVENLABS_API_KEY", ""))
    wake_word_model: str    = "hey_jarvis"
    model: str = "claude-sonnet-4-6"
    max_history_turns: int = 20
    search_max_results: int = 5


def load_config() -> Config:
    raw = _load_yaml()
    booster = raw.get("mycroft", {})
    search = raw.get("search", {})

    cfg = Config(
        model=os.environ.get("MYCROFT_MODEL", booster.get("model", "claude-sonnet-4-6")),
        max_history_turns=int(booster.get("max_history_turns", 20)),
        search_max_results=int(search.get("max_results", 5)),
        wake_word_model=booster.get("wake_word_model", "hey_jarvis"),
    )
    return cfg
