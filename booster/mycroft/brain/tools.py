import re
from pathlib import Path
from datetime import datetime

from mycroft.capabilities.search import web_search, youtube_search, open_url
from mycroft.capabilities.calculator import evaluate_expression, geometry, GEOMETRY_FORMULAS
from mycroft.capabilities.system import take_screenshot, read_clipboard
from mycroft.capabilities.computer import mouse_click, double_click, keyboard_type, key_press, scroll, find_and_click, focus_window, list_windows

_NOTES_DIR = Path.home() / "gaia_notes"


def _ensure_notes_dir():
    _NOTES_DIR.mkdir(parents=True, exist_ok=True)


def _safe_filename(title: str) -> str:
    return re.sub(r'[^\w\-_åäöÅÄÖ ]', '', title).strip().replace(' ', '_')[:80]


def save_note(title: str, content: str) -> str:
    _ensure_notes_dir()
    fname = _safe_filename(title) or "note"
    path = _NOTES_DIR / f"{fname}.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = f"# {title}\n_Sparat: {timestamp}_\n\n{content}\n"
    path.write_text(text, encoding="utf-8")
    return f"Anteckning sparad: {path}"


def recall_notes(query: str) -> str:
    _ensure_notes_dir()
    files = list(_NOTES_DIR.glob("*.md"))
    if not files:
        return "Inga anteckningar sparade ännu."
    q = query.lower()
    hits = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
            if q in text.lower():
                hits.append(f"--- {f.stem} ---\n{text.strip()}")
        except Exception:
            pass
    if not hits:
        all_notes = "\n\n".join(
            f"--- {f.stem} ---\n{f.read_text(encoding='utf-8').strip()}"
            for f in files[:10]
        )
        return f"Inga träffar för '{query}'. Alla anteckningar:\n\n{all_notes}"
    return "\n\n".join(hits[:5])


TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Use this for general knowledge, how-to questions, technical specs, or anything that benefits from current information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_search",
        "description": "Search YouTube for video tutorials or demonstrations and automatically opens the top result in the browser. Use this when the user asks to find or watch a video — no need to call open_url afterwards.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "YouTube search query"},
                "max_results": {"type": "integer", "description": "Number of results to return (default 5)", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "open_url",
        "description": "Open a URL in the user's default web browser. Use after youtube_search to open the best video result, or to open any webpage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to open"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression. Supports arithmetic, algebra, square roots, pi, powers, etc. Always use this for calculations rather than doing math in your head.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Math expression to evaluate, e.g. 'pi * 4**2' or 'sqrt(144)' or '(3/8) * 16'"},
            },
            "required": ["expression"],
        },
    },
    {
        "name": "geometry",
        "description": f"Calculate common geometry formulas used in workshop and construction. Available formulas: {', '.join(GEOMETRY_FORMULAS)}",
        "input_schema": {
            "type": "object",
            "properties": {
                "formula": {
                    "type": "string",
                    "description": "The formula name",
                    "enum": GEOMETRY_FORMULAS,
                },
                "dimensions": {
                    "type": "object",
                    "description": "Dimension values as key-value pairs. For circle: {r: value}. For rectangle: {w: value, h: value}. For cylinder: {r: value, h: value}. For triangle: {b: value, h: value}. For Pythagorean: {a: value, b: value} or {c: value, b: value}.",
                },
            },
            "required": ["formula", "dimensions"],
        },
    },
    {
        "name": "save_note",
        "description": "Save a note, measurement, part number, task, or any information to persistent memory. Use when the user asks to remember something, or when useful info should be stored for later sessions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short descriptive title for the note, e.g. 'Motorrumsmått' or 'Inköpslista'"},
                "content": {"type": "string", "description": "The content to save"},
            },
            "required": ["title", "content"],
        },
    },
    {
        "name": "recall_notes",
        "description": "Search saved notes and memory for information from previous sessions. Use when the user asks you to recall, look up, or check something previously stored.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in saved notes"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Take a screenshot of the user's screen and analyse it. Use when the user asks what is on screen, wants help with something they are looking at, or says 'look at this' / 'what do you see'.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "read_clipboard",
        "description": "Read the text currently in the clipboard. Use when the user says 'what's in my clipboard', 'I copied something', or pastes a reference to something they copied.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "mouse_click",
        "description": "Click the mouse at specific screen coordinates. Always take a screenshot first to see the screen and calculate the correct coordinates using the scale factor provided.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in actual screen pixels"},
                "y": {"type": "integer", "description": "Y coordinate in actual screen pixels"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button (default: left)"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "double_click",
        "description": "Double-click at screen coordinates. Use to open files, apps, or select a word.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in actual screen pixels"},
                "y": {"type": "integer", "description": "Y coordinate in actual screen pixels"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "keyboard_type",
        "description": "Type a string of text using the keyboard. Click the target input field first, then use this tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "key_press",
        "description": "Press a key or keyboard shortcut. Examples: 'enter', 'escape', 'tab', 'space', 'ctrl+v', 'ctrl+c', 'ctrl+a', 'win', 'alt+f4', 'ctrl+shift+t'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name or hotkey combo using + separator, e.g. 'enter' or 'ctrl+v'"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel up or down at the current cursor position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction"},
                "amount": {"type": "integer", "description": "Number of scroll clicks (default 3)"},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "list_windows",
        "description": "List all open window titles on the screen. Use this first when you need to interact with a specific app — it tells you the exact window title to use with focus_window or find_and_click.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "focus_window",
        "description": "Bring an app window to the foreground by its title. Use before interacting with it. Faster than taking a screenshot to find it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Partial window title, e.g. 'Spotify', 'Chrome', 'Notepad'"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "find_and_click",
        "description": "Click a button or UI element in an app by name — no screenshot or coordinates needed. Works for most standard Windows apps, browsers, Spotify, File Explorer. Use this before falling back to mouse_click with coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "window_title": {"type": "string", "description": "Partial title of the app window, e.g. 'Spotify'"},
                "control_name": {"type": "string", "description": "Name of the button or control to click, e.g. 'Play', 'Search', 'Close'"},
            },
            "required": ["window_title", "control_name"],
        },
    },
]


def dispatch_tool(name: str, inputs: dict) -> str:
    if name == "web_search":
        results = web_search(inputs["query"], inputs.get("max_results", 5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n")
        return "\n".join(lines)

    if name == "youtube_search":
        results = youtube_search(inputs["query"], inputs.get("max_results", 5))
        if not results:
            return "No YouTube results found."
        lines = []
        for r in results:
            lines.append(f"Title: {r['title']}\nURL: {r['url']}\nChannel: {r['channel']}\nDuration: {r['duration']}\n")
        return "\n".join(lines)

    if name == "open_url":
        return open_url(inputs["url"])

    if name == "calculate":
        return evaluate_expression(inputs["expression"])

    if name == "geometry":
        return geometry(inputs["formula"], inputs["dimensions"])

    if name == "save_note":
        return save_note(inputs["title"], inputs["content"])

    if name == "recall_notes":
        return recall_notes(inputs["query"])

    if name == "take_screenshot":
        result = take_screenshot()
        print(f"[screenshot] {'OK' if result.get('image') else 'FAILED'}: {result.get('text', '')}", flush=True)
        return result

    if name == "read_clipboard":
        return read_clipboard()

    if name == "mouse_click":
        return mouse_click(inputs["x"], inputs["y"], inputs.get("button", "left"))

    if name == "double_click":
        return double_click(inputs["x"], inputs["y"])

    if name == "keyboard_type":
        return keyboard_type(inputs["text"])

    if name == "key_press":
        return key_press(inputs["key"])

    if name == "scroll":
        return scroll(inputs["direction"], inputs.get("amount", 3))

    if name == "list_windows":
        return list_windows()

    if name == "focus_window":
        return focus_window(inputs["title"])

    if name == "find_and_click":
        return find_and_click(inputs["window_title"], inputs["control_name"])

    return f"Unknown tool: {name}"
