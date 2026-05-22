import sys
import threading
import webbrowser
from pathlib import Path
from datetime import date

from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit

from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error

app = Flask(__name__, static_folder=str(Path(__file__).parent / "ui" / "static"))
socketio = SocketIO(app, cors_allowed_origins="*")

_claude = None


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@socketio.on("command")
def handle_command(data):
    text = data.get("text", "").strip()
    if not text:
        return

    print_user(text)

    shutdown_phrases = ("goodbye mycroft", "shut down", "power off")
    if text.lower() in shutdown_phrases:
        emit("response", {"text": "Shutting down. See you later."})
        socketio.stop()
        return

    print_status("Thinking...")
    try:
        response = _claude.chat(text)
        print_mycroft(response)
        emit("response", {"text": response})
    except Exception as e:
        print_error(str(e))
        emit("error", {"message": str(e)})


def _open_browser():
    import time
    time.sleep(1.5)
    brave_paths = [
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        str(Path.home() / r"AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ]
    url = "http://localhost:5050"
    for p in brave_paths:
        if Path(p).exists():
            import subprocess
            subprocess.Popen([p, url])
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
    print_status("Starting Mycroft on http://localhost:5050")
    print_status("Opening Brave — say 'Hey Mycroft' to activate.")

    threading.Thread(target=_open_browser, daemon=True).start()
    socketio.run(app, host="127.0.0.1", port=5050, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
