import sys
import threading

from mycroft.config import load_config
from mycroft.brain.claude_client import ClaudeClient
from mycroft.audio.speaker import Speaker
from mycroft.audio.listener import Listener
from mycroft.audio.wake_word import WakeWordDetector
from mycroft.ui.terminal import print_banner, print_user, print_mycroft, print_status, print_error

_lock = threading.Lock()


def main():
    cfg = load_config()

    if not cfg.anthropic_api_key:
        print_error("ANTHROPIC_API_KEY is not set. Please set it in your .env file or environment.")
        sys.exit(1)

    print_banner()

    claude = ClaudeClient(cfg)
    speaker = Speaker(cfg)
    listener = Listener(cfg)

    listener.calibrate()
    speaker.speak("Mycroft online. Ready to work.")

    def handle_session():
        if not _lock.acquire(blocking=False):
            return  # already in a session
        try:
            speaker.speak("Yeah?")
            user_input = listener.listen_once()

            if not user_input:
                print_status("Didn't catch that.")
                return

            print_user(user_input)

            if user_input.lower().strip() in ("goodbye mycroft", "shut down", "exit", "quit", "power off"):
                speaker.speak("Shutting down. Stay safe out there.")
                wake_detector.stop()
                sys.exit(0)

            print_status("Thinking...")
            response = claude.chat(user_input)
            print_mycroft(response)
            speaker.speak(response)
        except Exception as e:
            print_error(str(e))
        finally:
            _lock.release()

    wake_detector = WakeWordDetector(on_wake=handle_session, trigger="mycroft")
    wake_detector.start()

    try:
        wake_detector._thread.join()
    except KeyboardInterrupt:
        print_status("\nShutting down Mycroft. See you later.")
        wake_detector.stop()


if __name__ == "__main__":
    main()
