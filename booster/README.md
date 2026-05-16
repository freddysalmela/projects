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
- Windows, Linux (Ubuntu/Debian), or macOS
- Microphone + speakers
- `ANTHROPIC_API_KEY` environment variable

---

## Install — Windows

### 1. Install Python 3.11+

Download from [python.org](https://www.python.org/downloads/). Check **"Add Python to PATH"** during install.

### 2. Install PyAudio (Windows needs this done separately)

PyAudio requires PortAudio. The easiest way on Windows:

```powershell
pip install pipwin
pipwin install pyaudio
```

If `pipwin` fails, download the matching `.whl` from
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
then install it with `pip install <filename>.whl`.

### 3. Set up the project

```powershell
cd booster
python -m venv venv
venv\Scripts\activate
pip install -e .
```

### 4. Set your API key

Copy the example env file and fill it in:

```powershell
copy .env.example .env
notepad .env
```

Add your key:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Or set it for the current session only:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

### 5. Run Booster

```powershell
venv\Scripts\activate
booster
# or:
python -m booster.main
```

---

## Install — Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y portaudio19-dev python3-dev espeak-ng

cd booster
python3 -m venv venv
source venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY

booster
```

---

## Install — macOS

```bash
brew install portaudio

cd booster
python3 -m venv venv
source venv/bin/activate
pip install -e .

cp .env.example .env
# Edit .env and fill in ANTHROPIC_API_KEY

booster
```

---

## Usage

| Mode | Default | How to activate |
|---|---|---|
| Wake word | `hey_mycroft` model | Say "Hey Mycroft" (or train a custom "Hey Booster" model) |
| Push-to-talk | Fallback | Press **Enter** then speak |

Say **"Goodbye Booster"** or press **Ctrl+C** to quit.

---

## Configuration

Edit `config.yaml` to change defaults.

| Key | Default | Options |
|---|---|---|
| `audio.tts_backend` | `gtts` | `gtts`, `pyttsx3` |
| `audio.stt_backend` | `google` | `google` |
| `audio.wake_mode` | `wake_word` | `wake_word`, `push_to_talk` |
| `booster.model` | `claude-sonnet-4-6` | any Anthropic model |

On Windows, `pyttsx3` uses the built-in Windows SAPI5 voices — no extra install needed.
`gtts` (Google TTS) is the default and sounds more natural but requires internet.

---

## Custom wake word

To use "Hey Booster" as the wake word, train a custom model with [OpenWakeWord](https://github.com/dscripka/openWakeWord).
Until then, "Hey Mycroft" is the closest available built-in trigger phrase.

---

## Offline mode

If internet is unavailable, set `audio.tts_backend: pyttsx3` in `config.yaml` for offline speech synthesis.
STT requires internet (Google Speech Recognition). For offline STT, install `openai-whisper` and set `audio.stt_backend: whisper`.
