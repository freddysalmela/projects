import threading
import time
from typing import Callable

from booster.ui.terminal import print_status, print_error

# Chunk size for audio streaming (30ms at 16kHz)
_CHUNK = 1280
_RATE = 16000
_CHANNELS = 1
_FORMAT = None  # set at runtime


class WakeWordDetector:
    """
    Listens continuously for a wake word using openwakeword.
    Falls back to a push-to-talk mode (Enter key) if openwakeword is unavailable.
    """

    def __init__(self, on_wake: Callable, model_name: str = "hey_mycroft"):
        self.on_wake = on_wake
        self.model_name = model_name
        self._running = False
        self._thread: threading.Thread | None = None
        self._use_oww = self._try_import_oww()

    def _try_import_oww(self) -> bool:
        try:
            import openwakeword  # noqa: F401
            return True
        except ImportError:
            return False

    def start(self):
        self._running = True
        if self._use_oww:
            self._thread = threading.Thread(target=self._oww_loop, daemon=True)
        else:
            print_status("openwakeword not available — using push-to-talk mode (press Enter to speak).")
            self._thread = threading.Thread(target=self._push_to_talk_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _oww_loop(self):
        import pyaudio
        import openwakeword
        from openwakeword.model import Model

        openwakeword.utils.download_models()
        oww_model = Model(wakeword_models=[self.model_name], inference_framework="onnx")

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=_RATE,
            channels=_CHANNELS,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=_CHUNK,
        )

        print_status(f"Listening for wake word ({self.model_name})...")

        try:
            while self._running:
                audio = stream.read(_CHUNK, exception_on_overflow=False)
                prediction = oww_model.predict(audio)
                for name, score in prediction.items():
                    if score > 0.5:
                        oww_model.reset()
                        self.on_wake()
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

    def _push_to_talk_loop(self):
        while self._running:
            try:
                input()  # blocks until Enter is pressed
                if self._running:
                    self.on_wake()
            except EOFError:
                time.sleep(0.1)
