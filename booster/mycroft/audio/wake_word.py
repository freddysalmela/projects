import threading
import time
from typing import Callable

import speech_recognition as sr

from mycroft.ui.terminal import print_status, print_error


class WakeWordDetector:
    def __init__(self, on_wake: Callable, trigger: str = "mycroft"):
        self.on_wake = on_wake
        self.trigger = trigger.lower()
        self._running = False
        self._listen_thread: threading.Thread | None = None
        self._enter_thread: threading.Thread | None = None
        self._in_session = False
        self._recognizer = sr.Recognizer()
        self._recognizer.pause_threshold = 0.6
        self._recognizer.energy_threshold = 300

    def start(self):
        self._running = True

        # Always run Enter key as fallback alongside voice detection
        self._enter_thread = threading.Thread(target=self._enter_loop, daemon=True)
        self._enter_thread.start()

        self._listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listen_thread.start()

    def stop(self):
        self._running = False

    def _listen_loop(self):
        print_status('Say "Hey Mycroft" to activate — or just press Enter.')
        while self._running:
            if self._in_session:
                time.sleep(0.1)
                continue
            try:
                with sr.Microphone() as source:
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=3, phrase_time_limit=4
                        )
                    except sr.WaitTimeoutError:
                        continue

                try:
                    text = self._recognizer.recognize_google(audio).lower()
                    print_status(f'Heard: "{text}"')
                    if self.trigger in text:
                        self._trigger_wake()
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print_error(f"Speech recognition unavailable: {e} — use Enter key instead.")
                    time.sleep(5)

            except OSError as e:
                print_error(f"Microphone error: {e}")
                time.sleep(2)
            except Exception as e:
                print_error(f"Wake word error: {e}")
                time.sleep(1)

    def _enter_loop(self):
        while self._running:
            try:
                input()
                if self._running and not self._in_session:
                    self._trigger_wake()
            except EOFError:
                time.sleep(0.1)

    def _trigger_wake(self):
        self._in_session = True
        try:
            self.on_wake()
        finally:
            self._in_session = False
