# Gaia — Garage AI Assistant

A voice assistant for the workshop PC. Say **"Hey Jarvis"**, ask, and she answers out loud.

## What she can do

- **Web search** — "look up torque specs for a 351 Windsor"
- **YouTube** — "find me a video on TIG welding aluminium" (opens the best match)
- **Maths and geometry** — "what's the volume of a cylinder 40 across and 120 long?"
- **Notes** — "remember the engine bay is 820 millimetres wide", "what was the engine bay width?"
- **The screen** — "what am I looking at?", "read what I copied"
- **The computer** — "open Spotify", "pause the music", "click Search in Brave"
- **Morning briefing** — weather, top headline and your latest note at startup

## Talking to her

| Say | What happens |
|---|---|
| "Hey Jarvis" | She starts listening. Also interrupts her while she is talking. |
| a question | She answers and keeps listening for a follow-up. |
| "mute", "stop", "quiet" | She goes silent and back to standby, without replying. |
| "thanks", "that's all" | "Alright, I'll stand by." |
| "goodbye", "shut down" | Gaia exits. |
| nothing for 20 seconds | Back to standby. |

Spacebar in the HUD starts a session, Escape stops her.

## Install (Windows)

1. Install [Python 3.11 or 3.12](https://www.python.org/downloads/) with **Add Python to PATH** ticked.
2. Run `install.bat`. It creates `venv`, installs everything and opens `.env`.
3. Put your keys in `.env` (see `.env.example`). Anthropic and OpenAI are required; a Cartesia or
   ElevenLabs key gives a better voice.
4. Run `mycroft.bat`.

After a `git pull`, update the packages with:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Start with Windows:** right-click `setup_autostart.ps1` → *Run with PowerShell*, once.

## Settings

Everything is in `config.yaml`:

| Setting | Default | Meaning |
|---|---|---|
| `gaia.model` | `claude-sonnet-5` | Claude model. A faster model answers sooner, a larger one reasons better. |
| `gaia.wake_word_threshold` | `0.3` | Lower triggers more easily. |
| `audio.input_device` / `output_device` | blank | Part of a device name; blank uses the Windows default. |
| `audio.silence_secs` | `2.8` | Pause that ends a command. Lower means faster replies, but she may cut you off. |
| `audio.session_timeout_secs` | `20` | Silence before she returns to standby. `0` keeps listening forever. |
| `audio.barge_in` | `false` | `true` makes any loud sound stop her talking. |
| `ui.host` | `127.0.0.1` | Set to `0.0.0.0` to open the HUD from a tablet or phone on the same network. |

List microphones and speakers with:

```powershell
venv\Scripts\python.exe -m mycroft.audio.devices
```

## If something is off

- **Music sounds dull or like a phone call while Gaia runs.** A Bluetooth headset or speaker that is
  also the microphone switches to its low-quality call mode whenever the microphone is open. Use a
  separate microphone (USB or built-in) and set it as `audio.input_device`.
- **She doesn't hear the wake word.** Lower `gaia.wake_word_threshold`, and check the microphone with
  the command above.
- **She cuts you off, or waits too long.** Adjust `audio.silence_secs`.
- **The window closes at startup.** Start `gaia_autostart.bat` by hand; it stays open and shows the error.

## Layout

```
mycroft/main.py            the listen → think → speak loop
mycroft/brain/             Claude client and tool definitions
mycroft/audio/             recording, speech-to-text, text-to-speech
mycroft/capabilities/      search, calculator, screen, computer control, wake word, briefing
mycroft/ui/                the browser HUD
pi_gateway/                Raspberry Pi at the garage door: wake phrase → lights + Wake-on-LAN
```
