import threading
import numpy as np
import pyaudio

_session_active = threading.Event()
_CHUNK = 1280   # 80ms at 16kHz — openwakeword's preferred frame size
_RATE  = 16000
_THRESHOLD = 0.5


def set_session_active(active: bool):
    if active:
        _session_active.set()
    else:
        _session_active.clear()


def start(model_name: str, on_detected, threshold: float = _THRESHOLD) -> threading.Thread:
    """Download model if needed, then listen in the background.
    Calls on_detected() whenever the wake word is heard outside an active session."""
    import openwakeword
    from openwakeword.model import Model

    openwakeword.utils.download_models()
    oww = Model(wakeword_models=[model_name], inference_framework="onnx")

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=_RATE,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=_CHUNK,
    )

    def _loop():
        try:
            while True:
                audio = np.frombuffer(
                    stream.read(_CHUNK, exception_on_overflow=False),
                    dtype=np.int16,
                )
                if _session_active.is_set():
                    continue
                prediction = oww.predict(audio)
                if any(score >= threshold for score in prediction.values()):
                    oww.reset()
                    on_detected()
        finally:
            stream.close()
            pa.terminate()

    t = threading.Thread(target=_loop, daemon=True, name="wake-word")
    t.start()
    return t
