import re
import tempfile
import os

from mycroft.config import Config


def _strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'^\s*[-*]\s+', '', text, flags=re.MULTILINE)
    return text.strip()


class Speaker:
    def __init__(self, cfg: Config):
        self.backend = cfg.tts_backend
        # Always init pyttsx3 so the fallback is always available
        self._init_pyttsx3()
        if self.backend == "gtts":
            try:
                import pygame
                pygame.mixer.init()
                self._pygame = pygame
            except Exception:
                self.backend = "pyttsx3"

    def _init_pyttsx3(self):
        import pyttsx3
        self._engine = pyttsx3.init()
        self._engine.setProperty("rate", 175)

    def speak(self, text: str):
        clean = _strip_markdown(text)
        if not clean:
            return
        if self.backend == "gtts":
            self._speak_gtts(clean)
        else:
            self._speak_pyttsx3(clean)

    def _speak_gtts(self, text: str):
        from gtts import gTTS
        tmp = tempfile.mktemp(suffix=".mp3")
        try:
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(tmp)
            self._pygame.mixer.music.load(tmp)
            self._pygame.mixer.music.play()
            while self._pygame.mixer.music.get_busy():
                self._pygame.time.wait(100)
        except Exception:
            self._speak_pyttsx3(text)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _speak_pyttsx3(self, text: str):
        self._engine.say(text)
        self._engine.runAndWait()
