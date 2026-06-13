import threading
import queue
from pathlib import Path
from flask import Flask, send_from_directory
from flask_socketio import SocketIO

_static = str(Path(__file__).parent / "static")
_app = Flask(__name__, static_folder=_static)
_sio = SocketIO(_app, cors_allowed_origins="*", async_mode="threading")
_trigger_queue: queue.Queue = queue.Queue()


@_app.route("/")
def index():
    return send_from_directory(_static, "index.html")


@_sio.on("trigger")
def on_trigger():
    _trigger_queue.put(True)


def set_state(state: str, **kwargs):
    """Push a state update to all connected browsers."""
    _sio.emit("state", {"state": state, **kwargs})


def wait_for_trigger():
    """Block until the browser emits a 'trigger' event (user clicked orb)."""
    _trigger_queue.get()


def start(port: int = 5050):
    """Start the Flask-SocketIO server in a daemon thread."""
    t = threading.Thread(
        target=lambda: _sio.run(_app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True),
        daemon=True,
    )
    t.start()
