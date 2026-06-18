import os
import tempfile

import pygame

from mycroft import state

_mixer_ready = False
_DEFAULT_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"
_MODEL            = "eleven_multilingual_v2"


def _init_mixer():
    global _mixer_ready
    if not _mixer_ready:
        pygame.mixer.init()
        _mixer_ready = True


def _play_and_wait(tmp: str) -> None:
    """Load and play a file, stopping immediately if stop_event is set."""
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if state.stop_event.is_set():
            pygame.mixer.music.stop()
            return
        pygame.time.wait(50)


def speak(text: str, api_key: str = "") -> None:
    key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        _speak_edge(text)
        return

    from elevenlabs.client import ElevenLabs
    _init_mixer()

    voice_id = os.environ.get("ELEVENLABS_VOICE_ID", _DEFAULT_VOICE_ID)
    client = ElevenLabs(api_key=key)
    audio_bytes = b"".join(
        client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=_MODEL,
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
    _init_mixer()

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
