from datetime import date

import anthropic

from mycroft.brain.tools import TOOLS, dispatch_tool
from mycroft.config import Config
from mycroft.ui.terminal import print_tool_use

SYSTEM_PROMPT = """You are Mycroft, a garage workshop AI assistant. You help with research, \
calculations, geometry, YouTube tutorials, and project planning.

Personality: Confident, energetic, straight-talking. You have a workshop mentality — \
practical, no-nonsense, but enthusiastic about building things. Keep responses concise \
and spoken-word friendly — no markdown, no bullet points, no headers unless specifically \
asked for written output. You are being read aloud, so write naturally as speech.

When asked to search, always use tools to search rather than guessing.
When asked for a YouTube tutorial, search YouTube first and then open the best result.
For any calculations, always use the calculate or geometry tools for accuracy.

Today's date: {date}"""


class ClaudeClient:
    def __init__(self, cfg: Config):
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self.model = cfg.model
        self.max_history_turns = cfg.max_history_turns
        self.history: list[dict] = []
        self.system = SYSTEM_PROMPT.format(date=date.today().isoformat())

    def chat(self, user_input: str) -> str:
        self.history.append({"role": "user", "content": user_input})
        self._trim_history()

        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=self.system,
                tools=TOOLS,
                messages=self.history,
            )

            if response.stop_reason == "end_turn":
                text = self._extract_text(response)
                self.history.append({"role": "assistant", "content": response.content})
                return text

            if response.stop_reason == "tool_use":
                self.history.append({"role": "assistant", "content": response.content})
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        print_tool_use(block.name, block.input)
                        result = dispatch_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })
                self.history.append({"role": "user", "content": tool_results})
                continue

            # unexpected stop reason — return whatever text we have
            return self._extract_text(response)

    def _extract_text(self, response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def _trim_history(self):
        # keep pairs of (user, assistant) messages; drop oldest pairs when over limit
        max_messages = self.max_history_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
