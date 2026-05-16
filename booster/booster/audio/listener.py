import speech_recognition as sr

from booster.config import Config
from booster.ui.terminal import print_status, print_error


class Listener:
    def __init__(self, cfg: Config):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = cfg.pause_threshold
        self.timeout = cfg.speech_timeout
        self.backend = cfg.stt_backend

    def calibrate(self):
        print_status("Calibrating microphone for ambient noise...")
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        print_status("Microphone ready.")

    def listen_once(self) -> str | None:
        print_status("Listening...")
        try:
            with sr.Microphone() as source:
                audio = self.recognizer.listen(source, timeout=self.timeout, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            return None
        except Exception as e:
            print_error(f"Microphone error: {e}")
            return None

        try:
            if self.backend == "google":
                text = self.recognizer.recognize_google(audio)
            else:
                text = self.recognizer.recognize_google(audio)
            return text.strip()
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print_error(f"STT service error: {e}")
            return None
