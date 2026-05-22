import threading
import time
from typing import Callable

from mycroft.audio.stt import load_model, stream_for_trigger
from mycroft.ui.terminal import print_status, print_error


class WakeWordDetector:
    def __init__(self, on_wake: Callable, trigger: str = "mycroft"):
        self.on_wake = on_wake
        self.trigger = trigger.lower()
        self._running = False
        self._stop_event = threading.Event()
        self._in_session = False
        self._model = None
        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)

    def start(self):
        self._running = True
        print_status('Say "Hey Mycroft" to activate — or just press Enter.')
        threading.Thread(target=self._enter_loop, daemon=True).start()
        self._listen_thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()

    def _listen_loop(self):
        try:
            self._model = load_model()
        except Exception as e:
            print_error(f"Could not load speech model: {e}")
            return

        while self._running:
            if self._in_session:
                time.sleep(0.1)
                continue
            self._stop_event.clear()
            try:
                stream_for_trigger(
                    model=self._model,
                    trigger=self.trigger,
                    on_heard=lambda t: print_status(f'Heard: "{t}"'),
                    on_trigger=self._trigger_wake,
                    stop_event=self._stop_event,
                )
            except Exception as e:
                if self._running:
                    print_error(f"Wake word error: {e}")
                    time.sleep(1)

    def _trigger_wake(self):
        if self._in_session:
            return
        self._in_session = True
        self._stop_event.set()  # stop the audio stream
        time.sleep(0.1)         # let stream fully release mic
        try:
            self.on_wake()
        finally:
            self._in_session = False

    def _enter_loop(self):
        while self._running:
            try:
                input()
                if self._running and not self._in_session:
                    self._trigger_wake()
            except EOFError:
                time.sleep(0.1)
