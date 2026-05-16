# Booster — Garage AI Assistant

Your voice-activated workshop buddy. Say "Hey Booster" and ask anything.

## What it can do

- **Web search** — "Booster, look up torque specs for a 351 Windsor"
- **YouTube** — "Find me a video on TIG welding aluminium" (opens browser + summarises)
- **Math & geometry** — "What's the area of a 7-inch circle?"
- **Calculations** — "If I need 3 litres of 30% epoxy, how much hardener is that?"
- **Project planning** — "Help me plan building a tool wall"

## Requirements

- Python 3.11+
- Linux (Ubuntu/Debian) or macOS
- Microphone + speakers
- `ANTHROPIC_API_KEY` environment variable

## Install

### 1. System dependencies (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev espeak-ng
```

### 2. Python setup

```bash
cd booster
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 3. API key

Booster uses the Anthropic API. Set your key:

```bash
cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY
```

Or export it directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
source venv/bin/activate
booster
# or:
python3 -m booster.main
```

## Usage

| Mode | Default | How to activate |
|---|---|---|
| Wake word | `hey_mycroft` model | Say "Hey Mycroft" (or train a custom "Hey Booster" model) |
| Push-to-talk | Fallback | Press **Enter** then speak |

Say **"Goodbye Booster"** or press **Ctrl+C** to quit.

## Configuration

Edit `config.yaml` to change defaults (TTS backend, model, search results, etc.).

| Key | Default | Options |
|---|---|---|
| `audio.tts_backend` | `gtts` | `gtts`, `pyttsx3` |
| `audio.stt_backend` | `google` | `google` |
| `audio.wake_mode` | `wake_word` | `wake_word`, `push_to_talk` |
| `booster.model` | `claude-sonnet-4-6` | any Anthropic model |

## Custom wake word

To use "Hey Booster" as the wake word, train a custom model with [OpenWakeWord](https://github.com/dscripka/openWakeWord).
Until then, "Hey Mycroft" is the closest available built-in trigger phrase.

## Offline mode

If internet is unavailable, set `audio.tts_backend: pyttsx3` in `config.yaml` for offline speech synthesis.
STT requires internet (Google Speech Recognition). For offline STT, install `openai-whisper` and set `audio.stt_backend: whisper`.
