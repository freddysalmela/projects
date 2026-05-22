import math
import struct
import tempfile
import wave

import pyaudio

_RATE      = 16000
_CHUNK     = 1024
_FORMAT    = pyaudio.paInt16
_CHANNELS  = 1
_RMS_THRESHOLD   = 400   # below this = silence
_SILENCE_SECS    = 1.5   # stop after this many silent seconds
_MAX_SECS        = 12    # hard cutoff
_LEAD_IN_SECS    = 0.3   # record a bit before checking for silence


def record_until_silence() -> str:
    """Record from microphone until silence or max duration. Returns path to WAV file."""
    pa = pyaudio.PyAudio()
    stream = pa.open(
        format=_FORMAT, channels=_CHANNELS,
        rate=_RATE, input=True, frames_per_buffer=_CHUNK,
    )

    frames         = []
    silent_chunks  = 0
    max_silent     = int(_RATE / _CHUNK * _SILENCE_SECS)
    max_chunks     = int(_RATE / _CHUNK * _MAX_SECS)
    lead_in_chunks = int(_RATE / _CHUNK * _LEAD_IN_SECS)
    speech_started = False

    try:
        stream.start_stream()
        while len(frames) < max_chunks:
            data = stream.read(_CHUNK, exception_on_overflow=False)
            frames.append(data)

            count  = len(data) // 2
            shorts = struct.unpack(f"{count}h", data)
            rms    = math.sqrt(sum(s * s for s in shorts) / count) if count else 0

            if rms > _RMS_THRESHOLD:
                speech_started = True
                silent_chunks  = 0
            elif speech_started and len(frames) > lead_in_chunks:
                silent_chunks += 1
                if silent_chunks >= max_silent:
                    break
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    tmp = tempfile.mktemp(suffix=".wav")
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(pyaudio.PyAudio().get_sample_size(_FORMAT))
        wf.setframerate(_RATE)
        wf.writeframes(b"".join(frames))

    return tmp
