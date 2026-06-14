import sys
import tempfile
import os
import time
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
_SILENCE_THRESHOLD = 400
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
            language="sv",
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

    speak("Gaia online. Redo att hjälpa.", tts_key)

    from mycroft import state

    def run_once() -> bool:
        """Run one listen→respond cycle. Returns True if should auto-listen again."""
        state.stop_event.clear()

        ui.set_state("recording", status="LYSSNAR...")
        wav = record()
        if wav is None or state.stop_event.is_set():
            print_status("Hörde ingenting.")
            return False

        ui.set_state("thinking", status="TRANSKRIBERAR...")
        text = transcribe(wav, cfg.openai_api_key)
        if not text or state.stop_event.is_set():
            print_status("Hörde ingenting.")
            return False

        print_user(text)
        ui.set_state("thinking", status="TÄNKER...", heard=text)

        if text.lower().strip() in ("hej då gaia", "stäng av", "avsluta"):
            speak("Stänger av. Ha det bra!", tts_key)
            sys.exit(0)

        full_sentences = []
        for sentence in claude.chat_stream(text):
            if state.stop_event.is_set():
                break
            full_sentences.append(sentence)
            print(sentence, end=" ", flush=True)

        if state.stop_event.is_set():
            print()
            return False

        full_response = " ".join(full_sentences)
        print()

        ui.set_state("speaking", status="TALAR", heard=text, text=full_response)
        print_mycroft(full_response)
        speak(full_response, tts_key)

        if state.stop_event.is_set():
            return False
        return True

    while True:
        try:
            ui.set_state("idle", status="REDO")
            ui.wait_for_trigger()
        except KeyboardInterrupt:
            print_status("Avslutar. Hej då!")
            sys.exit(0)

        while True:
            try:
                should_continue = run_once()
            except KeyboardInterrupt:
                print_status("Avslutar. Hej då!")
                sys.exit(0)
            except Exception as e:
                print_error(str(e))
                ui.set_state("idle", status="FEL — FÖRSÖK IGEN")
                break

            if state.stop_event.is_set():
                ui.set_state("idle", status="AVBRUTEN")
                break
            if should_continue:
                time.sleep(0.7)
            else:
                break


if __name__ == "__main__":
    main()
