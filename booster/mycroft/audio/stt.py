"""Speech to text through the OpenAI transcription API."""
from mycroft.config import get_config

_client = None


def transcribe(wav: bytes) -> str:
    global _client
    cfg = get_config()
    if _client is None:
        import openai
        _client = openai.OpenAI(api_key=cfg.openai_api_key)
    result = _client.audio.transcriptions.create(
        model=cfg.stt_model,
        file=("speech.wav", wav, "audio/wav"),
        language="en",
    )
    return result.text.strip()
