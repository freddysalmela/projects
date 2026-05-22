import sys
import tempfile
import os
from datetime import date

import pyaudio
import wave
import math
import struct

from mycroft.audio.tts import speak
from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error

_RATE      = 16000
_CHUNK     = 1024
_CHANNELS  = 1
_FORMAT    = pyaudio.paInt16
_SILENCE_THRESHOLD = 400
_SILENCE_SECS      = 1.5
_MAX_SECS          = 12


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
    print_status("Tryck Enter för att tala. Ctrl+C för att avsluta.")

    speak("Mycroft online. Redo att hjälpa.")

    while True:
        try:
            input()  # wait for Enter
        except KeyboardInterrupt:
            print_status("Avslutar. Hej då!")
            sys.exit(0)

        try:
            wav  = record()
            print_status("Transkriberar...")
            text = transcribe(wav, cfg.openai_api_key)

            if not text:
                print_status("Hörde ingenting.")
                continue

            print_user(text)

            if text.lower().strip() in ("hej då mycroft", "stäng av", "avsluta"):
                speak("Stänger av. Ha det bra!")
                sys.exit(0)

            print_status("Tänker...")
            full_sentences = []
            for sentence in claude.chat_stream(text):
                full_sentences.append(sentence)
                print(sentence, end=" ", flush=True)  # show text as it streams in

            full_response = " ".join(full_sentences)
            print()  # newline after streamed text
            print_mycroft(full_response)
            speak(full_response)

        except KeyboardInterrupt:
            print_status("Avslutar. Hej då!")
            sys.exit(0)
        except Exception as e:
            print_error(str(e))


if __name__ == "__main__":
    main()
