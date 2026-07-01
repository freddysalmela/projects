import struct
import threading
import pyaudio

_session_active = threading.Event()


def set_session_active(active: bool):
    if active:
        _session_active.set()
    else:
        _session_active.clear()


def start(access_key: str, keyword_path: str, on_detected) -> threading.Thread:
    """Start a background thread that fires on_detected() when the wake word is heard."""
    import pvporcupine

    porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[keyword_path])
    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length,
    )

    def _loop():
        try:
            while True:
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                if _session_active.is_set():
                    continue  # already in a session, ignore
                pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                if porcupine.process(pcm) >= 0:
                    on_detected()
        finally:
            stream.close()
            pa.terminate()
            porcupine.delete()

    t = threading.Thread(target=_loop, daemon=True, name="wake-word")
    t.start()
    return t
