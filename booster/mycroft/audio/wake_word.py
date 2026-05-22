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
        self._recognizer = sr.Recognizer()
        self._recognizer.pause_threshold = 0.6
        self._recognizer.energy_threshold = 300
        self._stop_bg = None
        self._listen_thread = threading.Thread(target=self._keep_alive, daemon=True)

    def start(self):
        self._running = True
        print_status('Say "Hey Mycroft" to activate — or just press Enter.')
        self._start_bg()
        # Enter key always works as fallback
        threading.Thread(target=self._enter_loop, daemon=True).start()
        self._listen_thread.start()

    def stop(self):
        self._running = False
        if self._stop_bg:
            self._stop_bg(wait_for_stop=False)

    def _start_bg(self):
        try:
            mic = sr.Microphone()
            self._stop_bg = self._recognizer.listen_in_background(
                mic, self._on_audio, phrase_time_limit=3
            )
        except OSError as e:
            print_error(f"Microphone error: {e} — use Enter key to activate.")

    def _on_audio(self, recognizer, audio):
        if not self._running:
            return
        try:
            text = recognizer.recognize_google(audio).lower()
            print_status(f'Heard: "{text}"')
            if self.trigger in text:
                self._trigger_wake()
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print_error(f"Speech recognition error: {e}")

    def _trigger_wake(self):
        # Stop background listening so it doesn't steal mic from the command listener
        if self._stop_bg:
            self._stop_bg(wait_for_stop=True)
            self._stop_bg = None
        try:
            self.on_wake()
        finally:
            # Restart background listening after session is done
            if self._running:
                self._start_bg()

    def _enter_loop(self):
        while self._running:
            try:
                input()
                if self._running:
                    self._trigger_wake()
            except EOFError:
                time.sleep(0.1)

    def _keep_alive(self):
        # Keeps the main thread alive
        while self._running:
            time.sleep(0.5)
