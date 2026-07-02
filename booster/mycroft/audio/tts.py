import os
import time
import tempfile

from mycroft import state


def _play_and_wait(tmp: str) -> None:
    """Play an audio file through the system default output (same device as Spotify/browser)."""
    import sounddevice as sd
    import soundfile as sf

    data, samplerate = sf.read(tmp, dtype="float32")
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
