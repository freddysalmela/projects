import os
import tempfile

import pygame

_mixer_ready = False
_VOICE_ID = "pNInz6obpgDQGcFmaJgB"   # Adam — deep, clear, works great in Swedish
_MODEL    = "eleven_multilingual_v2"   # full Swedish support


def _init_mixer():
    global _mixer_ready
    if not _mixer_ready:
        pygame.mixer.init()
        _mixer_ready = True


def speak(text: str, api_key: str = "") -> None:
    key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    if not key:
        _speak_edge(text)
        return

    from elevenlabs.client import ElevenLabs
    _init_mixer()

    client = ElevenLabs(api_key=key)
    audio_bytes = b"".join(
        client.text_to_speech.convert(
            voice_id=_VOICE_ID,
            text=text,
            model_id=_MODEL,
            output_format="mp3_44100_128",
        )
    )

    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        with open(tmp, "wb") as f:
            f.write(audio_bytes)
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def _speak_edge(text: str) -> None:
    """Fallback TTS when no ElevenLabs key is set."""
    import asyncio
    import edge_tts
    _init_mixer()

    async def _run():
        tmp = tempfile.mktemp(suffix=".mp3")
        try:
            await edge_tts.Communicate(text, "sv-SE-SofieNeural").save(tmp)
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(50)
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass

    asyncio.run(_run())
