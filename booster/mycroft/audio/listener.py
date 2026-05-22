from mycroft.audio.stt import load_model, transcribe_once
from mycroft.config import Config
from mycroft.ui.terminal import print_status, print_error


class Listener:
    def __init__(self, cfg: Config):
        self.timeout = cfg.speech_timeout
        self._model = None

    def calibrate(self):
        print_status("Loading speech recognition model (downloading if first run)...")
        self._model = load_model()
        print_status("Ready.")

    def listen_once(self) -> str | None:
        print_status("Listening...")
        try:
            return transcribe_once(self._model, timeout_seconds=self.timeout)
        except Exception as e:
            print_error(f"Listen error: {e}")
            return None
