import base64
import os
import tempfile


def speak_to_base64(text: str, lang: str = "sv") -> str | None:
    """Generate speech with gTTS, return base64-encoded MP3. Returns None on failure."""
    try:
        from gtts import gTTS
        tmp = tempfile.mktemp(suffix=".mp3")
        gTTS(text=text, lang=lang, slow=False).save(tmp)
        with open(tmp, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tmp)
        return data
    except Exception:
        return None
