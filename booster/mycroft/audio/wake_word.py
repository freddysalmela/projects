import threading
import time
from typing import Callable

import speech_recognition as sr

from mycroft.ui.terminal import print_status, print_error


class WakeWordDetector:
    """
    Listens continuously for the phrase "mycroft" using short Google STT bursts.
    Falls back to push-to-talk (Enter key) if the microphone is unavailable.
    """

    def __init__(self, on_wake: Callable, trigger: str = "mycroft"):
        self.on_wake = on_wake
        self.trigger = trigger.lower()
        self._running = False
        self._thread: threading.Thread | None = None
        self._recognizer = sr.Recognizer()
        self._recognizer.pause_threshold = 0.6
        self._recognizer.energy_threshold = 300

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _listen_loop(self):
        print_status(f'Say "Hey Mycroft" to activate. Ctrl+C to quit.')
        while self._running:
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
                    if self.trigger in text:
                        self.on_wake()
                except sr.UnknownValueError:
                    pass
                except sr.RequestError:
                    # network blip — wait briefly and retry
                    time.sleep(2)

            except OSError:
                print_error(
                    "Microphone unavailable. Falling back to push-to-talk — press Enter to speak."
                )
                self._push_to_talk_loop()
                return

    def _push_to_talk_loop(self):
        while self._running:
            try:
                input()
                if self._running:
                    self.on_wake()
            except EOFError:
                time.sleep(0.1)
