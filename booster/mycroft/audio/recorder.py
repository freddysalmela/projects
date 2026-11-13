import io
import wave
from collections import deque

import numpy as np
import pyaudio

from mycroft import state
from mycroft.audio.devices import open_input
from mycroft.config import get_config

_RATE = 16000
_CHUNK = 1024
_PRE_ROLL_SECS = 0.5    # audio kept from just before speech starts, so the first word is whole
_TAIL_SECS = 0.3        # silence kept after the last word
_START_CHUNKS = 2       # loud chunks in a row that count as speech (ignores clicks and bangs)


def _rms(data: bytes) -> float:
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float64)
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def record() -> bytes | None:
    """Wait for speech, record until the speaker pauses, and return it as WAV bytes.

    Returns None when nobody spoke before the session timeout, or when a stop was requested.
    Only the speech itself is returned: leading and trailing silence are cut, which keeps the
    upload small and stops the speech recogniser inventing words out of background noise.
    """
    cfg = get_config()
    per_sec = _RATE / _CHUNK
    threshold = cfg.silence_threshold
    max_silent = int(per_sec * cfg.silence_secs)
    max_chunks = int(per_sec * cfg.max_record_secs)
    wait_chunks = int(per_sec * cfg.session_timeout_secs)   # 0 = wait forever
    tail_chunks = int(per_sec * _TAIL_SECS)

    pre_roll: deque = deque(maxlen=max(1, int(per_sec * _PRE_ROLL_SECS)))
    frames: list[bytes] = []
    started = False
    loud_run = 0
    silent = 0
    waited = 0

    pa = pyaudio.PyAudio()
    stream = None
    try:
        stream = open_input(pa, _RATE, _CHUNK)
        while True:
            if state.stop_event.is_set():
                return None
            data = stream.read(_CHUNK, exception_on_overflow=False)
            loud = _rms(data) > threshold

            if not started:
                pre_roll.append(data)
                loud_run = loud_run + 1 if loud else 0
                if loud_run >= _START_CHUNKS:
                    started = True
                    frames = list(pre_roll)
                else:
                    waited += 1
                    if wait_chunks and waited >= wait_chunks:
                        return None
                continue

            frames.append(data)
            silent = 0 if loud else silent + 1
            if silent >= max_silent or len(frames) >= max_chunks:
                break
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pa.terminate()

    if silent > tail_chunks:
        frames = frames[:len(frames) - (silent - tail_chunks)]

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_RATE)
        wf.writeframes(b"".join(frames))
    return buf.getvalue()
