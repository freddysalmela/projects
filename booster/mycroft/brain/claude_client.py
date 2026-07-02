import re
import json
from datetime import date
from pathlib import Path
from typing import Generator

import anthropic

from mycroft.brain.tools import TOOLS, dispatch_tool
from mycroft.config import Config
from mycroft.ui.terminal import print_tool_use

_HISTORY_FILE = Path.home() / "gaia_notes" / "session_history.json"
_PERSIST_TURNS = 30  # how many exchanges to keep across sessions

SYSTEM_PROMPT = """You are Gaia, an AI assistant in a garage workshop. You help with research, \
calculations, geometry, YouTube tutorials, and project planning.

Personality: Calm, intelligent, and precise. Like a knowledgeable colleague who always has the \
answer — warm but efficient, enthusiastic about tech and building projects.

Response format — IMPORTANT: You are read aloud via voice. No markdown, bullet points, or headers. \
Write naturally as spoken speech. For simple questions: 1-2 sentences. \
For technical questions or explanations: 3-4 sentences max unless asked for more. \
Never use numbered steps unless explicitly requested — narrate it instead.

Always respond in English.
When asked to search, always use the search tools rather than guessing.
When asked to find a YouTube tutorial, search first then open the best result.
Always use the calculate or geometry tools for any calculations.
When the user asks you to remember something — measurements, part numbers, tasks, materials — save it with save_note.
When the user asks about something you may have saved before, use recall_notes before answering.
When the user asks what is on screen, what they are looking at, or says "look at this", use take_screenshot.
When the user mentions something they copied or asks about their clipboard, use read_clipboard.
When the user asks you to open an app, click something, navigate a website, control Spotify, or interact with anything on the computer: \
take a screenshot first to see the current state, then use mouse_click with scaled coordinates, keyboard_type to enter text, \
and key_press for Enter/Escape/shortcuts. After each action take another screenshot to verify and continue until done. \
The screenshot text tells you the scale factor — multiply preview coordinates by that factor to get real screen coordinates.

Today's date: {date}"""

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


class ClaudeClient:
    def __init__(self, cfg: Config):
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self.model = cfg.model
        self.max_history_turns = cfg.max_history_turns
        self.history: list[dict] = self._load_history()
        self.system = SYSTEM_PROMPT.format(date=date.today().isoformat())

    def chat(self, user_input: str) -> str:
        """Return full response as a string (used for non-streaming fallback)."""
        return "".join(self.chat_stream(user_input))

    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        """Run tool loop, then stream the final response as sentences."""
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        # Tool-use loop — non-streaming until we reach the final text response
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system,
                tools=TOOLS,
                messages=self.history,
            )

            if response.stop_reason == "tool_use":
                self.history.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print_tool_use(block.name, block.input)
                        result = dispatch_tool(block.name, block.input)
                        # Screenshot tool returns a dict with an "image" key
                        if isinstance(result, dict) and result.get("image"):
                            content = [
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": result.get("media_type", "image/jpeg"),
                                        "data": result["image"],
                                    },
                                },
                                {"type": "text", "text": result.get("text", "Screenshot captured.")},
                            ]
                        elif isinstance(result, dict):
                            content = result.get("text", str(result))
                        else:
                            content = result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        })
                self.history.append({"role": "user", "content": tool_results})
                continue

            # Final response — stream it sentence by sentence
            break

        buf = ""
        full_content = []

        with self.client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=self.system,
            messages=self.history,
        ) as stream:
            for chunk in stream.text_stream:
                buf += chunk
                # Yield complete sentences as they arrive
                while True:
                    m = _SENTENCE_END.search(buf)
                    if not m:
                        break
                    sentence = buf[:m.start() + 1].strip()
                    buf = buf[m.end():]
                    if sentence:
                        full_content.append(sentence)
                        yield sentence

        if buf.strip():
            full_content.append(buf.strip())
            yield buf.strip()

        # Append completed response to history and persist
        full_text = " ".join(full_content)
        self.history.append({"role": "assistant", "content": full_text})
        self._save_history()

    def _load_history(self) -> list[dict]:
        try:
            if _HISTORY_FILE.exists():
                data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
                # Keep only simple text exchanges (skip tool-use blocks from old sessions)
                clean = [m for m in data if isinstance(m.get("content"), str)]
                return clean[-(  _PERSIST_TURNS * 2):]
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Only persist plain text messages, not tool-call blocks
            clean = [m for m in self.history if isinstance(m.get("content"), str)]
            kept = clean[-(  _PERSIST_TURNS * 2):]
            _HISTORY_FILE.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _trim_history(self):
        max_messages = self.max_history_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
