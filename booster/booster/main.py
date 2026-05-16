import sys
import threading

from booster.config import load_config
from booster.brain.claude_client import ClaudeClient
from booster.audio.speaker import Speaker
from booster.audio.listener import Listener
from booster.audio.wake_word import WakeWordDetector
from booster.ui.terminal import print_banner, print_user, print_booster, print_status, print_error

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
    speaker.speak("Booster online. Ready to work.")

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

            if user_input.lower().strip() in ("goodbye booster", "shut down", "exit", "quit", "power off"):
                speaker.speak("Shutting down. Stay safe out there.")
                wake_detector.stop()
                sys.exit(0)

            print_status("Thinking...")
            response = claude.chat(user_input)
            print_booster(response)
            speaker.speak(response)
        except Exception as e:
            print_error(str(e))
        finally:
            _lock.release()

    wake_mode = cfg.wake_mode
    model_name = "hey_mycroft"  # closest available; swap for custom "hey_booster" model when trained

    wake_detector = WakeWordDetector(on_wake=handle_session, model_name=model_name)
    wake_detector.start()

    if wake_mode == "wake_word":
        try:
            import openwakeword  # noqa: F401
            print_status("Say 'Hey Booster' to activate. Ctrl+C to quit.")
        except ImportError:
            print_status("Press Enter to speak. Ctrl+C to quit.")
    else:
        print_status("Press Enter to speak. Ctrl+C to quit.")

    try:
        wake_detector._thread.join()
    except KeyboardInterrupt:
        print_status("\nShutting down Booster. See you later.")
        wake_detector.stop()


if __name__ == "__main__":
    main()
