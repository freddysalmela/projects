import os
import math
import struct
import time
import tempfile
import threading

from mycroft import state

# RMS level above which we treat incoming audio as intentional speech (barge-in).
# Higher than the recording threshold so speaker bleed doesn't trigger it.
_BARGE_IN_THRESHOLD = 600
_BARGE_IN_CONFIRM_CHUNKS = 3   # must exceed threshold this many times in a row


def _barge_in_listener() -> None:
    """Monitor the mic during TTS. If the user speaks, stop playback immediately."""
    import pyaudio
    _RATE, _CHUNK = 16000, 1024
    pa = pyaudio.PyAudio()
    try:
        stream = pa.open(format=pyaudio.paInt16, channels=1, rate=_RATE,
                         input=True, frames_per_buffer=_CHUNK)
        consecutive = 0
        # Brief warm-up delay so the start of Gaia's own voice doesn't trigger it
        time.sleep(0.4)
        while not state.stop_event.is_set():
            data = stream.read(_CHUNK, exception_on_overflow=False)
            shorts = struct.unpack(f"{len(data) // 2}h", data)
            rms = math.sqrt(sum(s * s for s in shorts) / len(shorts)) if shorts else 0
            if rms > _BARGE_IN_THRESHOLD:
                consecutive += 1
                if consecutive >= _BARGE_IN_CONFIRM_CHUNKS:
                    state.stop_event.set()
                    break
            else:
                consecutive = 0
        stream.stop_stream()
        stream.close()
    except Exception:
        pass
    finally:
        pa.terminate()


def _play_and_wait(tmp: str) -> None:
    """Play audio; start a barge-in listener so the user can interrupt instantly."""
    import sounddevice as sd
    import soundfile as sf

    data, samplerate = sf.read(tmp, dtype="float32")

    barge_in = threading.Thread(target=_barge_in_listener, daemon=True)
    barge_in.start()

    sd.play(data, samplerate)
    while sd.get_stream().active:
        if state.stop_event.is_set():
            sd.stop()
            return
        time.sleep(0.05)


def speak(text: str, api_key: str = "") -> None:
    # Priority: Cartesia (40ms) → ElevenLabs → edge-tts (free)
    cartesia_key = os.environ.get("CARTESIA_API_KEY", "")
    elevenlabs_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")

    if cartesia_key:
        _speak_cartesia(text, cartesia_key)
    elif elevenlabs_key:
        _speak_elevenlabs(text, elevenlabs_key)
    else:
        _speak_edge(text)


def _speak_cartesia(text: str, api_key: str) -> None:
    from cartesia import Cartesia

    client = Cartesia(api_key=api_key)
    voice_id = os.environ.get("CARTESIA_VOICE_ID", "bf0a246a-8642-498a-9950-80c35e9276b5")

    audio_data = b""
    for chunk in client.tts.sse(
        model_id="sonic-turbo",
        transcript=text,
        voice={"mode": "id", "id": voice_id},
        language="en",
        output_format={"container": "mp3", "bit_rate": 128000, "sample_rate": 44100},
    ):
        audio_data += chunk.get("audio", b"")

    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        with open(tmp, "wb") as f:
            f.write(audio_data)
        _play_and_wait(tmp)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def _speak_elevenlabs(text: str, api_key: str) -> None:
    from elevenlabs.client import ElevenLabs

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
    client = ElevenLabs(api_key=api_key)
    audio_bytes = b"".join(
        client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
    )

    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        with open(tmp, "wb") as f:
            f.write(audio_bytes)
        _play_and_wait(tmp)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def _speak_edge(text: str) -> None:
    import asyncio
    import edge_tts

    async def _run():
        tmp = tempfile.mktemp(suffix=".mp3")
        try:
            await edge_tts.Communicate(text, "en-GB-SoniaNeural").save(tmp)
            _play_and_wait(tmp)
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    asyncio.run(_run())
