import re
import sys
import time
import queue
import random
import threading
import webbrowser
from datetime import datetime

from mycroft import state
from mycroft.audio.recorder import record
from mycroft.audio.stt import transcribe
from mycroft.audio.tts import speak
from mycroft.config import get_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error
from mycroft.ui import server as ui

_MUTE = {"mute", "stop", "stop talking", "be quiet", "quiet", "silence", "shut up"}
_DISMISS = {
    "thanks", "thank you", "that's all", "that's all for now",
    "thanks that's all", "thanks that's all for now",
    "go to sleep", "stop listening", "stand by",
}
_SHUTDOWN = {"goodbye gaia", "shut down", "goodbye", "exit"}
_ACKS = ["Sure.", "Got it.", "Mm.", "Alright.", "On it."]

_LEADING = re.compile(r"^(?:(?:hey|ok|okay)\s+)?(?:gaia|jarvis)\s+|^(?:please|ok|okay)\s+")
_TRAILING = re.compile(r"\s+(?:please|gaia|now)$")


def normalise(text: str) -> str:
    """Reduce a transcript to its bare words, so 'Okay, mute please.' matches 'mute'."""
    text = re.sub(r"[^\w\s']", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    previous = None
    while text != previous:
        previous = text
        text = _TRAILING.sub("", _LEADING.sub("", text))
    return text


def main():
    cfg = get_config()

    if not cfg.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY is missing from the .env file.")
        sys.exit(1)
    if not cfg.openai_api_key:
        print_error("OPENAI_API_KEY is missing from the .env file.")
        sys.exit(1)

    claude = ClaudeClient(cfg)
    tts_key = cfg.elevenlabs_api_key

    print_banner()
    print_status(f"Model: {cfg.model}")

    # Start the HUD server and open the browser
    ui.start(host=cfg.ui_host, port=cfg.ui_port)
    if cfg.ui_open_browser:
        webbrowser.open(f"http://localhost:{cfg.ui_port}")
    ui.set_state("idle", status="REDO")

    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
    speak(f"{greeting}, sir. Gaia online and ready. How are you today?", tts_key)

    from mycroft.capabilities.briefing import morning_briefing
    briefing = morning_briefing()
    if briefing:
        speak(briefing, tts_key)

    # Wake word — tries to start openwakeword; falls back to spacebar on error
    ww = None
    try:
        from mycroft.capabilities import wake_word as ww
        ww.start(cfg.wake_word_model, ui.trigger, threshold=cfg.wake_word_threshold)
        wake_label = cfg.wake_word_model.replace("_", " ").upper()
        print_status(f"Wake word active — say '{wake_label}' to start.")
        idle_label = f"SAY {wake_label}..."
    except Exception as e:
        ww = None
        print_status(f"Wake word unavailable ({e}), using spacebar.")
        idle_label = "PRESS SPACE TO START"

    def respond(text: str) -> None:
        """Send the request to Claude and speak the answer as it streams in."""
        tts_q: queue.Queue = queue.Queue()

        def tts_worker():
            while True:
                chunk = tts_q.get()
                if chunk is None:
                    return
                # Say everything that is already waiting in one go: fewer requests, and the
                # voice flows across sentences instead of pausing between them.
                parts, finished = [chunk], False
                while True:
                    try:
                        more = tts_q.get_nowait()
                    except queue.Empty:
                        break
                    if more is None:
                        finished = True
                        break
                    parts.append(more)
                try:
                    speak(" ".join(parts), tts_key)
                except Exception as e:
                    print_error(f"Speech failed: {e}")
                if finished:
                    return

        ui.set_state("thinking", status="THINKING...", heard=text)
        state.speaking.set()   # from here on the wake word interrupts her
        worker = threading.Thread(target=tts_worker, daemon=True)
        worker.start()
        # A short acknowledgment covers the wait. It goes through the queue so the request
        # to Claude starts right away instead of after the acknowledgment has been spoken.
        tts_q.put(random.choice(_ACKS))

        sentences: list[str] = []
        stream = claude.chat_stream(text)
        try:
            for sentence in stream:
                if state.stop_event.is_set():
                    break
                if not sentences:
                    ui.set_state("speaking", status="SPEAKING", heard=text)
                sentences.append(sentence)
                print(sentence, end=" ", flush=True)
                tts_q.put(sentence)
        except Exception as e:
            print()
            print_error(str(e))
            if not state.stop_event.is_set():
                tts_q.put("Sorry, I ran into a problem with that." if not sentences
                          else "Sorry, I lost the thread there.")
        finally:
            stream.close()   # stores what was said so far, also when she was interrupted
            tts_q.put(None)
            worker.join()
            state.speaking.clear()

        print()
        if sentences:
            full = " ".join(sentences)
            ui.set_state("speaking", status="SPEAKING", heard=text, text=full)
            print_mycroft(full)

    def run_once() -> bool:
        """Run one listen→respond cycle.
        Returns True  → keep session alive (listen again).
        Returns False → end session, go idle.
        """
        state.stop_event.clear()
        state.barge_in.clear()

        ui.set_state("recording", status="LISTENING...")
        wav = record()
        if wav is None:
            # Stopped from the HUD, or nobody said anything: back to standby without a word.
            return False

        ui.set_state("thinking", status="TRANSCRIBING...")
        text = transcribe(wav)
        if state.stop_event.is_set():
            return False
        if not text:
            return True

        print_user(text)
        command = normalise(text)

        if command in _SHUTDOWN:
            speak("Shutting down. Take care!", tts_key)
            sys.exit(0)

        if command in _MUTE:
            return False  # silent — no verbal response

        if command in _DISMISS:
            speak("Alright, I'll stand by.", tts_key)
            return False

        respond(text)

        if state.barge_in.is_set():
            return True   # interrupted by voice: stop talking and hear what they want
        return not state.stop_event.is_set()

    while True:
        try:
            ui.set_state("idle", status=idle_label)
            ui.wait_for_trigger()
        except KeyboardInterrupt:
            print_status("Goodbye!")
            sys.exit(0)

        # A stop left over from the last session must not silence this one.
        state.stop_event.clear()
        state.barge_in.clear()
        if ww:
            ww.set_session_active(True)

        try:
            speak("I'm listening.", tts_key)
            while run_once():
                time.sleep(0.2)
        except KeyboardInterrupt:
            print_status("Goodbye!")
            sys.exit(0)
        except Exception as e:
            print_error(str(e))
            ui.set_state("idle", status="ERROR — TRY AGAIN")
            time.sleep(2)
        finally:
            if ww:
                ww.set_session_active(False)
            ui.clear_triggers()   # wake words heard during the session must not restart it


if __name__ == "__main__":
    main()
