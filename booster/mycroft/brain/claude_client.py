import re
import json
from datetime import datetime
from pathlib import Path
from typing import Generator

import anthropic

from mycroft import state
from mycroft.brain.tools import TOOLS, dispatch_tool
from mycroft.config import Config
from mycroft.ui.terminal import print_tool_use

_HISTORY_FILE = Path.home() / "gaia_notes" / "session_history.json"
_PERSIST_TURNS = 30     # how many exchanges to keep across sessions
_MAX_TOOL_ROUNDS = 12   # safety stop for a runaway tool loop
_MAX_TOKENS = 2048

SYSTEM_PROMPT = """You are Gaia, an AI assistant in a garage workshop. You help with research, \
calculations, geometry, YouTube tutorials, project planning, and controlling the workshop computer.

Personality: Calm, intelligent, and precise. Like a knowledgeable colleague who always has the \
answer — warm but efficient, enthusiastic about tech and building projects.

Everything you write is read aloud by a speech synthesiser, so write the way you would speak. \
No markdown, bullet points, headers, emoji, or URLs. Spell out units and symbols a voice would \
stumble on. For simple questions give one or two sentences. For technical questions or explanations \
give three or four sentences unless asked for more. Narrate steps in flowing sentences rather than \
numbering them, unless numbered steps are requested.

The user's words reach you through speech recognition, so expect the occasional misheard word and \
go with the most sensible reading. Each user message starts with the local date and time in square \
brackets; use it when the time matters and never read it out.

Always respond in English.

Tools:
For anything that benefits from current information, use web_search rather than guessing.
youtube_search opens the best matching video in the browser by itself, so call it once and then \
say what you opened.
Use calculate or geometry for every calculation, however simple.
When the user asks you to remember something — measurements, part numbers, tasks, materials — \
save it with save_note. When they ask about something you may have saved before, use recall_notes first.
When the user asks what is on screen or says "look at this", use take_screenshot. When they \
mention something they copied, use read_clipboard.

Controlling the computer:
To start a program, use open_app. For music and video playback, key_press with playpause, \
nexttrack, prevtrack, volumeup, volumedown or volumemute works whatever window is in front.
To click something in an app, first try list_windows, then focus_window, then find_and_click with \
the visible name of the button or item; this needs no screenshot and works in most Windows apps. \
Fall back to take_screenshot followed by mouse_click with coordinates only when that fails. \
Use keyboard_type to enter text after clicking an input field, and key_press for Enter, Escape and shortcuts.
If a step fails, try one other way and then say plainly what did not work."""

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')
_IMAGE_PLACEHOLDER = {"type": "text", "text": "[screenshot no longer available]"}


def _text_of(content) -> str:
    """Plain text of a message's content, whether it is a string or a list of blocks."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        btype = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        if btype == "text":
            parts.append(block["text"] if isinstance(block, dict) else block.text)
    return " ".join(p.strip() for p in parts if p and p.strip())


class ClaudeClient:
    def __init__(self, cfg: Config):
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self.model = cfg.model
        self.max_history_turns = cfg.max_history_turns
        self.history: list[dict] = self._load_history()
        # Stable across requests so the system prompt and tool list are served from the prompt cache.
        self.system = [{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}]
        # A spoken reply should start within a second, so thinking is switched off where the
        # model allows it. Models that reject that setting run with their default instead.
        self._thinking_off = True

    def chat(self, user_input: str) -> str:
        """Return the full response as one string."""
        return " ".join(self.chat_stream(user_input))

    def chat_stream(self, user_input: str) -> Generator[str, None, None]:
        """Yield the reply sentence by sentence as it is generated, running tools in between."""
        self._trim_history()
        turn_start = len(self.history)
        stamp = datetime.now().strftime("%Y-%m-%d %a %H:%M")
        self.history.append({"role": "user", "content": f"[{stamp}] {user_input}"})

        spoken: list[str] = []      # everything said this turn
        last_round: list[str] = []  # what was said after the final tool call
        completed = False
        try:
            for _ in range(_MAX_TOOL_ROUNDS):
                buf = ""
                last_round = []
                with self._open_stream() as stream:
                    for chunk in stream.text_stream:
                        buf += chunk
                        while True:
                            m = _SENTENCE_END.search(buf)
                            if not m:
                                break
                            sentence = buf[:m.start()].strip()
                            buf = buf[m.end():]
                            if sentence:
                                spoken.append(sentence)
                                last_round.append(sentence)
                                yield sentence
                    final = stream.get_final_message()

                if buf.strip():
                    spoken.append(buf.strip())
                    last_round.append(buf.strip())
                    yield buf.strip()

                if final.stop_reason == "tool_use" and not state.stop_event.is_set():
                    self.history.append({"role": "assistant", "content": final.content})
                    self.history.append({"role": "user", "content": self._run_tools(final.content)})
                    continue

                if final.stop_reason == "refusal" and not spoken:
                    last_round.append("Sorry, I can't help with that one.")
                    spoken.append(last_round[-1])
                    yield last_round[-1]
                break
            else:
                last_round = ["I had to stop there, that took more steps than I expected."]
                spoken.append(last_round[0])
                yield last_round[0]
            completed = True
        finally:
            # Runs on normal completion, on an API error, and when the caller stops listening
            # mid-answer. Either way the turn is stored as plain text, so the history never
            # holds a tool call without its result, which the API would reject from then on.
            self._close_turn(turn_start, " ".join(spoken), " ".join(last_round), keep_blocks=completed)

    # ── request ────────────────────────────────────────────────────────────────

    def _open_stream(self):
        kwargs = dict(
            model=self.model,
            max_tokens=_MAX_TOKENS,
            system=self.system,
            tools=TOOLS,
            messages=self.history,
        )
        if self._thinking_off:
            try:
                manager = self.client.messages.stream(thinking={"type": "disabled"}, **kwargs)
                return _Entered(manager)
            except anthropic.BadRequestError as e:
                if "thinking" not in str(e).lower():
                    raise
                self._thinking_off = False
        return _Entered(self.client.messages.stream(**kwargs))

    def _run_tools(self, blocks) -> list[dict]:
        results = []
        for block in blocks:
            if block.type != "tool_use":
                continue
            print_tool_use(block.name, block.input)
            is_error = False
            try:
                result = dispatch_tool(block.name, block.input)
            except Exception as e:
                result, is_error = f"{block.name} failed: {e}", True

            # The screenshot tool returns a dict with an "image" key
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
                content = str(result)

            entry = {"type": "tool_result", "tool_use_id": block.id, "content": content}
            if is_error:
                entry["is_error"] = True
            results.append(entry)
        return results

    # ── history ────────────────────────────────────────────────────────────────

    def _close_turn(self, turn_start: int, spoken: str, last_round: str, keep_blocks: bool):
        turn = self.history[turn_start:]
        user_msg = turn[0]
        if keep_blocks:
            # Keep the tool calls and results so follow-up questions can refer to them.
            # Earlier rounds already hold their own text next to their tool calls.
            self.history.append({"role": "assistant", "content": last_round or "(no reply)"})
            if self._thinking_off:
                self._drop_images(turn_start)
        else:
            del self.history[turn_start:]
            if spoken:
                self.history.append(user_msg)
                self.history.append({"role": "assistant", "content": spoken})
        self._save_history()

    def _drop_images(self, turn_start: int):
        """Screenshots are only useful in the turn they were taken; resending them costs tokens."""
        for msg in self.history[turn_start:]:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for block in msg["content"]:
                if isinstance(block, dict) and isinstance(block.get("content"), list):
                    block["content"] = [
                        _IMAGE_PLACEHOLDER if b.get("type") == "image" else b
                        for b in block["content"]
                    ]

    def _plain_history(self) -> list[dict]:
        """The conversation as plain text turns: what the user said and what Gaia said back."""
        plain: list[dict] = []
        for msg in self.history:
            text = _text_of(msg["content"])
            if not text:
                continue
            if plain and plain[-1]["role"] == msg["role"]:
                plain[-1]["content"] += " " + text
            else:
                plain.append({"role": msg["role"], "content": text})
        return plain

    def _load_history(self) -> list[dict]:
        try:
            if _HISTORY_FILE.exists():
                data = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
                clean = [
                    {"role": m["role"], "content": m["content"]}
                    for m in data
                    if m.get("role") in ("user", "assistant")
                    and isinstance(m.get("content"), str) and m["content"].strip()
                ]
                clean = clean[-(_PERSIST_TURNS * 2):]
                while clean and clean[0]["role"] != "user":
                    clean.pop(0)
                return clean
        except Exception:
            pass
        return []

    def _save_history(self):
        try:
            _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            kept = self._plain_history()[-(_PERSIST_TURNS * 2):]
            _HISTORY_FILE.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _trim_history(self):
        """Drop the oldest whole turns. A turn starts at a user message the user actually spoke,
        so a tool result is never separated from the tool call it answers."""
        starts = [
            i for i, m in enumerate(self.history)
            if m["role"] == "user" and isinstance(m["content"], str)
        ]
        keep = max(1, self.max_history_turns) - 1   # leave room for the turn about to start
        if len(starts) > keep:
            del self.history[:starts[len(starts) - keep] if keep else len(self.history)]


class _Entered:
    """Enters a stream context manager right away, so a request the API rejects fails inside
    _open_stream where it can be retried, and hands the same stream to a later `with`."""

    def __init__(self, manager):
        self._manager = manager
        self._stream = manager.__enter__()

    def __enter__(self):
        return self._stream

    def __exit__(self, *exc):
        return self._manager.__exit__(*exc)
