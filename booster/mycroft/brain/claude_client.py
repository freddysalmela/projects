import re
from datetime import date
from typing import Generator

import anthropic

from mycroft.brain.tools import TOOLS, dispatch_tool
from mycroft.config import Config
from mycroft.ui.terminal import print_tool_use

SYSTEM_PROMPT = """Du är Gaia, en AI-assistent i ett garageverkstad. Du hjälper till med research, \
beräkningar, geometri, YouTube-tutorials och projektplanering.

Personlighet: Lugn, intelligent och precis. Du är som en kunnig kollega som alltid har svaret — \
varm men effektiv, entusiastisk inför teknik och byggprojekt.

Svarsformat — VIKTIGT: Du läses upp högt via röst. Inga markdown, punktlistor eller rubriker. \
Skriv naturligt som tal. För enkla frågor: svara i 1-2 meningar. \
För tekniska frågor eller förklaringar: 3-4 meningar max om inte användaren ber om mer. \
Dela aldrig upp i numrerade steg om det inte uttryckligen efterfrågas — berätta det istället.

Svara alltid på svenska om inte användaren skriver på engelska.
När du ombeds söka, använd alltid sökverktygen istället för att gissa.
När du ombeds hitta en YouTube-tutorial, sök först och öppna sedan bästa resultatet.
Använd alltid calculate- eller geometry-verktygen för beräkningar.

Dagens datum: {date}"""

_SENTENCE_END = re.compile(r'(?<=[.!?])\s+')


class ClaudeClient:
    def __init__(self, cfg: Config):
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        self.model = cfg.model
        self.max_history_turns = cfg.max_history_turns
        self.history: list[dict] = []
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
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
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

        # Append completed response to history
        full_text = " ".join(full_content)
        self.history.append({"role": "assistant", "content": full_text})

    def _trim_history(self):
        max_messages = self.max_history_turns * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]
