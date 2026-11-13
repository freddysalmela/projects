"""Shared state flags accessible across all modules without circular imports."""
import threading

# Set to cut off whatever Gaia is doing right now (speech, the current answer).
stop_event = threading.Event()

# Set together with stop_event when the user interrupted her by voice: she stops
# talking but keeps listening, instead of going back to standby.
barge_in = threading.Event()

# Set while audio is playing, so the wake word can be used to interrupt her.
speaking = threading.Event()


def interrupt_by_voice() -> None:
    barge_in.set()
    stop_event.set()
