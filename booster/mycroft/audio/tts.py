import os
import tempfile
import threading

_mixer_ready = False


def _init_mixer():
    global _mixer_ready
    if not _mixer_ready:
        import pygame
        pygame.mixer.init()
        _mixer_ready = True


def speak(text: str, openai_api_key: str):
    """Generate TTS with OpenAI and play it directly — no browser involved."""
    import openai
    import pygame

    _init_mixer()

    client = openai.OpenAI(api_key=openai_api_key)
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",
        input=text,
        speed=1.0,
    )

    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        tmp_path = tmp
        with open(tmp_path, "wb") as f:
            f.write(response.content)

        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
