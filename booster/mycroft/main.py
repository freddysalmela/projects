import os
import subprocess
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error

_STATIC = str(Path(__file__).parent / "ui" / "static")

app      = Flask(__name__, static_folder=_STATIC)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

_claude        = None
_openai_key    = None

_BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    str(Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
]


@app.route("/")
def index():
    return send_from_directory(_STATIC, "index.html")


@app.route("/transcribe", methods=["POST"])
def transcribe():
    """Receive audio blob from browser, transcribe with OpenAI Whisper API."""
    import openai

    audio_file = request.files.get("audio")
    if not audio_file:
        return jsonify({"error": "No audio received"}), 400

    suffix = ".webm"
    tmp = tempfile.mktemp(suffix=suffix)
    try:
        audio_file.save(tmp)
        client = openai.OpenAI(api_key=_openai_key)
        with open(tmp, "rb") as f:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="sv",
            )
        text = result.text.strip()
        print_user(text)
        return jsonify({"text": text})
    except Exception as e:
        print_error(f"Transcription error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


@socketio.on("command")
def handle_command(data):
    text = data.get("text", "").strip()
    if not text:
        return

    if text.lower() in ("hej då mycroft", "stäng av", "goodbye mycroft", "shut down"):
        emit("response", {"text": "Stänger av. Ha det bra!", "audio": None})
        return

    print_status("Thinking...")
    try:
        from mycroft.audio.tts import speak_to_base64
        response = _claude.chat(text)
        print_mycroft(response)
        audio = speak_to_base64(response, openai_api_key=_openai_key)
        emit("response", {"text": response, "audio": audio})
    except Exception as e:
        print_error(str(e))
        emit("error", {"message": str(e)})


def _open_brave():
    import time
    time.sleep(1.5)
    url = "http://localhost:5050"
    for p in _BRAVE_PATHS:
        if Path(p).exists():
            subprocess.Popen([p, "--new-tab", url])
            return
    webbrowser.open(url)


def main():
    cfg = load_config()

    if not cfg.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY saknas. Lägg till den i .env-filen.")
        sys.exit(1)

    if not cfg.openai_api_key:
        print_error("OPENAI_API_KEY saknas. Lägg till den i .env-filen.")
        sys.exit(1)

    global _claude, _openai_key
    _claude     = ClaudeClient(cfg)
    _openai_key = cfg.openai_api_key

    print_banner()
    print_status("Server på http://localhost:5050")
    print_status("Öppnar Brave...")

    threading.Thread(target=_open_brave, daemon=True).start()

    socketio.run(
        app,
        host="127.0.0.1",
        port=5050,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
