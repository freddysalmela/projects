import sys
import tempfile
import os
import time
import queue
import threading
import webbrowser
from datetime import date

import pyaudio
import wave
import math
import struct

from mycroft.audio.tts import speak
from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error
from mycroft.ui import server as ui

_RATE      = 16000
_CHUNK     = 1024
_CHANNELS  = 1
_FORMAT    = pyaudio.paInt16
_SILENCE_THRESHOLD = 200
_SILENCE_SECS      = 2.8
_MAX_SECS          = 30


def record() -> str | None:
    pa     = pyaudio.PyAudio()
    stream = pa.open(format=_FORMAT, channels=_CHANNELS, rate=_RATE,
                     input=True, frames_per_buffer=_CHUNK)
    frames         = []
    silent_chunks  = 0
    max_silent     = int(_RATE / _CHUNK * _SILENCE_SECS)
    max_chunks     = int(_RATE / _CHUNK * _MAX_SECS)
    lead_in        = int(_RATE / _CHUNK * 0.3)
    speech_started = False

    print_status("Lyssnar... (tala nu)")
    try:
        stream.start_stream()
        while len(frames) < max_chunks:
            data = stream.read(_CHUNK, exception_on_overflow=False)
            frames.append(data)
            count  = len(data) // 2
            shorts = struct.unpack(f"{count}h", data)
            rms    = math.sqrt(sum(s * s for s in shorts) / count) if count else 0

            if rms > _SILENCE_THRESHOLD:
                speech_started = True
                silent_chunks  = 0
            elif speech_started and len(frames) > lead_in:
                silent_chunks += 1
                if silent_chunks >= max_silent:
                    break
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    # Reject recordings that never had real speech
    all_shorts = struct.unpack(f"{len(b''.join(frames)) // 2}h", b"".join(frames))
    peak_rms = math.sqrt(sum(s * s for s in all_shorts) / len(all_shorts)) if all_shorts else 0
    print_status(f"Peak RMS: {round(peak_rms)} (threshold: {_SILENCE_THRESHOLD})")
    if peak_rms < _SILENCE_THRESHOLD or not speech_started:
        return None

    tmp = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(pyaudio.get_sample_size(_FORMAT))
        wf.setframerate(_RATE)
        wf.writeframes(b"".join(frames))
    return tmp


def transcribe(wav_path: str, openai_key: str) -> str:
    import openai
    client = openai.OpenAI(api_key=openai_key)
    with open(wav_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="en",
        )
    os.remove(wav_path)
    return result.text.strip()


def main():
    cfg = load_config()

    if not cfg.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY saknas i .env-filen.")
        sys.exit(1)
    if not cfg.openai_api_key:
        print_error("OPENAI_API_KEY saknas i .env-filen.")
        sys.exit(1)

    claude = ClaudeClient(cfg)

    print_banner()

    tts_key = cfg.elevenlabs_api_key

    # Start the HUD server and open the browser
    ui.start(port=5050)
    webbrowser.open("http://localhost:5050")
    ui.set_state("idle", status="REDO")

    from datetime import datetime
    _hour = datetime.now().hour
    _greeting = "Good morning" if _hour < 12 else "Good afternoon" if _hour < 18 else "Good evening"
    speak(f"{_greeting}, sir. Gaia online and ready. How are you today?", tts_key)

    from mycroft import state
    from mycroft.capabilities.briefing import morning_briefing

    briefing = morning_briefing()
    if briefing:
        speak(briefing, tts_key)

    # Wake word — tries to start openwakeword; falls back to spacebar on error
    _use_wake_word = False
    try:
        from mycroft.capabilities import wake_word as _ww
        _ww.start(cfg.wake_word_model, ui.trigger)
        _wake_label = cfg.wake_word_model.replace("_", " ").upper()
        print_status(f"Wake word active — say '{_wake_label}' to start.")
        _idle_label = f"SAY {_wake_label}..."
        _use_wake_word = True
    except Exception as _ww_err:
        print_status(f"Wake word unavailable ({_ww_err}), using spacebar.")
        _idle_label = "PRESS SPACE TO START"

    _MUTE = {"mute", "stop", "stop talking", "be quiet", "quiet", "silence", "shut up"}
    _DISMISS = {
        "thanks", "thank you", "that's all", "that's all for now",
        "thanks that's all", "thanks that's all for now",
        "go to sleep", "stop listening", "stand by",
    }
    _SHUTDOWN = {"goodbye gaia", "shut down", "goodbye", "exit"}

    def run_once() -> bool:
        """Run one listen→respond cycle.
        Returns True  → keep session alive (listen again).
        Returns False → end session, go idle.
        """
        state.stop_event.clear()

        ui.set_state("recording", status="LISTENING...")
        wav = record()

        if state.stop_event.is_set():
            return False

        if wav is None:
            # Silence — stay in session, just loop back quietly
            return True

        ui.set_state("thinking", status="TRANSCRIBING...")
        text = transcribe(wav, cfg.openai_api_key)
        if not text or state.stop_event.is_set():
            return True  # bad transcription — keep session alive

        print_user(text)
        normalised = text.lower().strip().rstrip(".,!")

        if normalised in _SHUTDOWN:
            speak("Shutting down. Take care!", tts_key)
            sys.exit(0)

        if normalised in _MUTE:
            state.stop_event.set()
            ui.set_state("idle", status=_idle_label)
            return False  # silent — no verbal response

        if normalised in _DISMISS:
            speak("Alright, I'll stand by.", tts_key)
            ui.set_state("idle", status="STANDING BY")
            return False  # end session

        # Short acknowledgment so there's no dead silence while Claude thinks
        import random
        ack = random.choice(["Sure.", "Got it.", "Mm.", "Alright.", "On it."])
        speak(ack, tts_key)

        ui.set_state("thinking", status="THINKING...", heard=text)

        # ── Pipeline: stream sentences → TTS queue → worker thread ─────────
        tts_q: queue.Queue = queue.Queue()

        def _tts_worker():
            while True:
                chunk = tts_q.get()
                if chunk is None:
                    break
                if not state.stop_event.is_set():
                    speak(chunk, tts_key)

        tts_thread = threading.Thread(target=_tts_worker, daemon=True)
        tts_thread.start()

        full_sentences: list[str] = []
        pending: list[str] = []
        first_chunk_sent = False

        for sentence in claude.chat_stream(text):
            if state.stop_event.is_set():
                break
            full_sentences.append(sentence)
            print(sentence, end=" ", flush=True)
            pending.append(sentence)

            threshold = 2 if not first_chunk_sent else 1
            if len(pending) >= threshold:
                tts_q.put(" ".join(pending))
                pending.clear()
                if not first_chunk_sent:
                    first_chunk_sent = True
                    ui.set_state("speaking", status="SPEAKING", heard=text)

        if pending and not state.stop_event.is_set():
            tts_q.put(" ".join(pending))

        tts_q.put(None)
        tts_thread.join()

        full_response = " ".join(full_sentences)
        print()

        ui.set_state("speaking", status="SPEAKING", heard=text, text=full_response)
        print_mycroft(full_response)

        if state.stop_event.is_set():
            return False
        return True

    while True:
        try:
            ui.set_state("idle", status=_idle_label)
            ui.wait_for_trigger()
        except KeyboardInterrupt:
            print_status("Goodbye!")
            sys.exit(0)

        if _use_wake_word:
            _ww.set_session_active(True)

        speak("I'm listening.", tts_key)

        while True:
            try:
                should_continue = run_once()
            except KeyboardInterrupt:
                print_status("Goodbye!")
                sys.exit(0)
            except Exception as e:
                print_error(str(e))
                ui.set_state("idle", status="ERROR — TRY AGAIN")
                break

            if state.stop_event.is_set():
                ui.set_state("idle", status="STOPPED")
                break
            if should_continue:
                time.sleep(0.4)
            else:
                break

        if _use_wake_word:
            _ww.set_session_active(False)


if __name__ == "__main__":
    main()
