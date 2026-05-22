"""Offline speech recognition using Vosk."""
import json
import os
import urllib.request
import zipfile
import tempfile
from pathlib import Path

import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)  # silence vosk logs

_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
_MODEL_DIR = Path.home() / ".mycroft" / "vosk-model"
_RATE = 16000
_CHUNK = 4000


def _ensure_model():
    if _MODEL_DIR.exists():
        return
    print("  Downloading speech recognition model (~40MB, one time only)...")
    _MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    zip_path = str(_MODEL_DIR.parent / "model.zip")
    urllib.request.urlretrieve(_MODEL_URL, zip_path)
    with zipfile.ZipFile(zip_path, "r") as z:
        extracted = z.namelist()[0].split("/")[0]
        z.extractall(str(_MODEL_DIR.parent))
    os.rename(str(_MODEL_DIR.parent / extracted), str(_MODEL_DIR))
    os.remove(zip_path)
    print("  Model ready.")


def load_model() -> Model:
    _ensure_model()
    return Model(str(_MODEL_DIR))


def transcribe_once(model: Model, timeout_seconds: int = 8) -> str | None:
    """Record until silence or timeout, return transcribed text."""
    rec = KaldiRecognizer(model, _RATE)
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=_RATE,
                     input=True, frames_per_buffer=_CHUNK)
    result = None
    chunks_since_speech = 0
    max_silent_chunks = int(_RATE / _CHUNK * 1.5)  # ~1.5s silence = done
    max_chunks = int(_RATE / _CHUNK * timeout_seconds)
    total = 0

    try:
        stream.start_stream()
        while total < max_chunks:
            data = stream.read(_CHUNK, exception_on_overflow=False)
            total += 1
            if rec.AcceptWaveform(data):
                r = json.loads(rec.Result())
                text = r.get("text", "").strip()
                if text:
                    result = text
                    break
                chunks_since_speech += 1
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                if partial:
                    chunks_since_speech = 0
                else:
                    chunks_since_speech += 1
            if chunks_since_speech > max_silent_chunks and total > 8:
                final = json.loads(rec.FinalResult()).get("text", "").strip()
                if final:
                    result = final
                break
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    return result or None


def stream_for_trigger(model: Model, trigger: str, on_heard, on_trigger, stop_event):
    """Stream audio continuously, call on_trigger when trigger word heard."""
    rec = KaldiRecognizer(model, _RATE)
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1, rate=_RATE,
                     input=True, frames_per_buffer=_CHUNK)
    try:
        stream.start_stream()
        while not stop_event.is_set():
            data = stream.read(_CHUNK, exception_on_overflow=False)
            if rec.AcceptWaveform(data):
                text = json.loads(rec.Result()).get("text", "").strip().lower()
                if text:
                    on_heard(text)
                    if trigger in text:
                        on_trigger()
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "").strip().lower()
                if partial and trigger in partial:
                    rec.Reset()
                    on_trigger()
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
