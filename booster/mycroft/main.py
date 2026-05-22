import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit

from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error

_STATIC = str(Path(__file__).parent / "ui" / "static")

app = Flask(__name__, static_folder=_STATIC)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

_claude: ClaudeClient | None = None

_BRAVE_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    str(Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
]


@app.route("/")
def index():
    return send_from_directory(_STATIC, "index.html")


@socketio.on("command")
def handle_command(data):
    text = data.get("text", "").strip()
    if not text:
        return

    print_user(text)

    if text.lower() in ("goodbye mycroft", "shut down", "power off"):
        emit("response", {"text": "Shutting down. See you later."})
        return

    print_status("Thinking...")
    try:
        response = _claude.chat(text)
        print_mycroft(response)
        emit("response", {"text": response})
    except Exception as e:
        print_error(str(e))
        emit("error", {"message": f"Error: {e}"})


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
        print_error("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)

    global _claude
    _claude = ClaudeClient(cfg)

    print_banner()
    print_status("Server running on http://localhost:5050")
    print_status("Opening Brave...")

    threading.Thread(target=_open_brave, daemon=True).start()

    socketio.run(
        app,
        host="127.0.0.1",
        port=5050,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
