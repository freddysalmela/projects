import os
from mycroft.ui.terminal import print_status

_model = None


def _get_model():
    global _model
    if _model is None:
        print_status("Loading speech model (first run only)...")
        from faster_whisper import WhisperModel
        _model = WhisperModel("small", device="cpu", compute_type="int8")
        print_status("Speech model ready.")
    return _model


def transcribe(wav_path: str) -> str:
    model = _get_model()
    segments, _ = model.transcribe(wav_path, language="sv", beam_size=5, vad_filter=True)
    text = " ".join(s.text for s in segments).strip()
    if os.path.exists(wav_path):
        os.remove(wav_path)
    return text
