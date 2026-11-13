"""Text to speech. Tries Cartesia, then ElevenLabs, then edge-tts, using whichever keys are set."""
import os
import re
import time
import tempfile
import threading

from mycroft import state
from mycroft.config import get_config

_CARTESIA_URL = "https://api.cartesia.ai/tts/bytes"
_CARTESIA_RATE = 44100
_WRITE_BYTES = 4096      # ~46 ms of 16-bit mono at 44.1 kHz; how often a stop request is checked

_BARGE_IN_WARMUP = 0.5   # seconds spent measuring how loud Gaia's own voice is at the microphone
_BARGE_IN_CHUNKS = 4     # loud chunks in a row (~0.25 s) that count as the user talking

_session = None          # reused HTTP connection, saves a TLS handshake on every sentence


def _clean(text: str) -> str:
    """Remove markdown that would otherwise be read out as 'asterisk asterisk'."""
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'^\s*#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    return text.strip()


def speak(text: str, api_key: str = "") -> None:
    """Say `text` and return when it has finished playing or was interrupted."""
    text = _clean(text)
    if not text or state.stop_event.is_set():
        return

    cartesia_key = os.environ.get("CARTESIA_API_KEY", "")
    elevenlabs_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    providers = []
    if cartesia_key:
        providers.append(("cartesia", lambda played: _speak_cartesia(text, cartesia_key, played)))
    if elevenlabs_key:
        providers.append(("elevenlabs", lambda played: _speak_elevenlabs(text, elevenlabs_key, played)))
    providers.append(("edge-tts", lambda played: _speak_edge(text, played)))

    already_speaking = state.speaking.is_set()
    state.speaking.set()
    done = threading.Event()
    if get_config().barge_in:
        threading.Thread(target=_barge_in_listener, args=(done,), daemon=True).start()
    try:
        for name, provider in providers:
            played = threading.Event()   # set once any sound has come out
            try:
                provider(played)
                return
            except Exception as e:
                print(f"[tts] {name} failed: {e}", flush=True)
                if played.is_set() or state.stop_event.is_set():
                    return   # half a sentence was heard; don't start it again in another voice
    finally:
        done.set()
        if not already_speaking:
            state.speaking.clear()


# ── playback ──────────────────────────────────────────────────────────────────

def _output_device():
    return get_config().output_device or None


def _play_pcm(chunks, samplerate: int, played: threading.Event) -> None:
    """Play 16-bit mono PCM as it arrives, so speech starts before the download has finished."""
    import sounddevice as sd

    with sd.RawOutputStream(samplerate=samplerate, channels=1, dtype="int16",
                            device=_output_device()) as out:
        leftover = b""
        for chunk in chunks:
            data = leftover + chunk
            usable = len(data) - (len(data) % 2)   # a sample is two bytes; keep any odd byte for later
            leftover = data[usable:]
            for i in range(0, usable, _WRITE_BYTES):
                if state.stop_event.is_set():
                    out.abort()
                    return
                out.write(data[i:i + _WRITE_BYTES])
                played.set()
        # Leaving the `with` block plays out what is still buffered.


def _play_file(path: str, played: threading.Event) -> None:
    import sounddevice as sd
    import soundfile as sf

    data, samplerate = sf.read(path, dtype="float32")
    sd.play(data, samplerate, device=_output_device())
    played.set()
    while sd.get_stream().active:
        if state.stop_event.is_set():
            sd.stop()
            return
        time.sleep(0.03)


def _play_mp3_bytes(audio: bytes, played: threading.Event) -> None:
    fd, tmp = tempfile.mkstemp(suffix=".mp3")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio)
        _play_file(tmp, played)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ── providers ─────────────────────────────────────────────────────────────────

def _speak_cartesia(text: str, api_key: str, played: threading.Event) -> None:
    global _session
    import requests

    if _session is None:
        _session = requests.Session()
    response = _session.post(
        _CARTESIA_URL,
        headers={"X-API-Key": api_key, "Cartesia-Version": "2024-11-13"},
        json={
            "model_id": os.environ.get("CARTESIA_MODEL", "sonic-turbo"),
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": os.environ.get("CARTESIA_VOICE_ID", "bf0a246a-8642-498a-9950-80c35e9276b5"),
            },
            "language": "en",
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": _CARTESIA_RATE,
            },
        },
        stream=True,
        timeout=(5, 30),
    )
    try:
        if response.status_code >= 400:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
        _play_pcm(response.iter_content(chunk_size=_WRITE_BYTES), _CARTESIA_RATE, played)
    finally:
        response.close()


def _speak_elevenlabs(text: str, api_key: str, played: threading.Event) -> None:
    from elevenlabs.client import ElevenLabs

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
    client = ElevenLabs(api_key=api_key)
    audio = b"".join(
        client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
    )
    _play_mp3_bytes(audio, played)


def _speak_edge(text: str, played: threading.Event) -> None:
    import asyncio
    import edge_tts

    fd, tmp = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        asyncio.run(edge_tts.Communicate(text, "en-GB-SoniaNeural").save(tmp))
        _play_file(tmp, played)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


# ── optional: stop talking when the user starts ───────────────────────────────

def _barge_in_listener(done: threading.Event) -> None:
    """Watch the microphone while Gaia talks and interrupt her when the user speaks over her.

    Her own voice reaches the microphone too, so the first half second measures that level and
    the user has to be clearly louder than it. Off by default (audio.barge_in in config.yaml):
    in a workshop, tools and music set it off. The wake word interrupts her either way.
    """
    import pyaudio
    import numpy as np
    from mycroft.audio.devices import open_input

    rate, chunk = 16000, 1024
    floor = get_config().barge_in_threshold
    pa = pyaudio.PyAudio()
    stream = None
    try:
        stream = open_input(pa, rate, chunk)
        started = time.monotonic()
        own_voice = 0.0
        loud_run = 0
        while not done.is_set() and not state.stop_event.is_set():
            samples = np.frombuffer(stream.read(chunk, exception_on_overflow=False), dtype=np.int16)
            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2))) if samples.size else 0.0
            if time.monotonic() - started < _BARGE_IN_WARMUP:
                own_voice = max(own_voice, rms)
                continue
            loud_run = loud_run + 1 if rms > max(floor, own_voice * 2.5) else 0
            if loud_run >= _BARGE_IN_CHUNKS:
                state.interrupt_by_voice()
                return
    except Exception as e:
        print(f"[tts] barge-in listener stopped: {e}", flush=True)
    finally:
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        pa.terminate()
