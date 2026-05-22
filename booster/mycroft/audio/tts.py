import base64


def speak_to_base64(text: str, openai_api_key: str) -> str | None:
    """Generate speech with OpenAI TTS. Returns base64-encoded MP3."""
    try:
        import openai
        client = openai.OpenAI(api_key=openai_api_key)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",   # deep, clear voice — works well in Swedish
            input=text,
            speed=1.0,
        )
        return base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        print(f"TTS error: {e}")
        return None
