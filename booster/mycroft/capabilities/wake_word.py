import threading
import time

import numpy as np
import pyaudio

from mycroft import state
from mycroft.audio.devices import open_input

_session_active = threading.Event()
_CHUNK = 1280   # 80ms at 16kHz — openwakeword's preferred frame size
_RATE  = 16000
_THRESHOLD = 0.3
_COOLDOWN_SECS = 1.5   # one spoken wake phrase scores high for several frames in a row
_INTERRUPT_GRACE_SECS = 3.0   # the phrase that opened a session must not also interrupt it
_INTERRUPT_MIN_SCORE = 0.5    # interrupting her needs a clearer match than waking her
_session_started = 0.0


def set_session_active(active: bool):
    global _session_started
    if active:
        _session_started = time.monotonic()
        _session_active.set()
    else:
        _session_active.clear()


def start(model_name: str, on_detected, threshold: float = _THRESHOLD) -> threading.Thread:
    """Download the model if needed, then listen in the background.

    Outside a session the wake word calls on_detected(). While Gaia is answering it interrupts
    her instead, so she stops talking and listens. Raises if the model or microphone is missing.
    """
    import openwakeword
    from openwakeword.model import Model

    try:
        openwakeword.utils.download_models()
    except Exception as e:
        # No network yet. If the model files are already on disk, loading still works below.
        print(f"[wake] could not check for model downloads: {e}", flush=True)
    oww = Model(wakeword_models=[model_name], inference_framework="onnx")

    pa = pyaudio.PyAudio()
    try:
        stream = open_input(pa, _RATE, _CHUNK)
    except Exception:
        pa.terminate()
        raise

    def _loop():
        nonlocal stream
        last_trigger = 0.0
        while True:
            try:
                data = stream.read(_CHUNK, exception_on_overflow=False)
            except Exception as e:
                # Microphone unplugged or the driver reset: keep trying rather than going deaf.
                print(f"[wake] microphone error ({e}), reconnecting...", flush=True)
                try:
                    stream.close()
                except Exception:
                    pass
                while True:
                    time.sleep(3)
                    try:
                        stream = open_input(pa, _RATE, _CHUNK)
                        break
                    except Exception:
                        continue
                continue

            # Every frame goes through the model, in a session or not: it keeps a running
            # window of audio and misses the phrase if frames are skipped.
            prediction = oww.predict(np.frombuffer(data, dtype=np.int16))
            score = max(prediction.values(), default=0.0)
            if score < threshold or time.monotonic() - last_trigger < _COOLDOWN_SECS:
                continue

            if not _session_active.is_set():
                print(f"[wake] score={score:.2f} — triggered", flush=True)
                last_trigger = time.monotonic()
                oww.reset()
                on_detected()
            elif (state.speaking.is_set()
                  and score >= max(threshold, _INTERRUPT_MIN_SCORE)
                  and time.monotonic() - _session_started > _INTERRUPT_GRACE_SECS):
                print(f"[wake] score={score:.2f} — interrupting", flush=True)
                last_trigger = time.monotonic()
                oww.reset()
                state.interrupt_by_voice()

    t = threading.Thread(target=_loop, daemon=True, name="wake-word")
    t.start()
    return t
