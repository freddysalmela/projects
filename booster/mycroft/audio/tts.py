import asyncio
import os
import tempfile

import pygame

_mixer_ready = False


def _init_mixer():
    global _mixer_ready
    if not _mixer_ready:
        pygame.mixer.init()
        _mixer_ready = True


async def _speak_async(text: str, voice: str = "sv-SE-SofieNeural") -> None:
    import edge_tts
    _init_mixer()
    communicate = edge_tts.Communicate(text, voice)
    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        await communicate.save(tmp)
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass


def speak(text: str) -> None:
    asyncio.run(_speak_async(text))
