"""
Computer control — two layers:
1. Windows UI Automation via pywinauto (primary): click by element name/title, no screenshot needed
2. pyautogui (fallback): coordinate-based clicks for apps without accessibility trees (games, some web content)
"""
import os
import time


# ── pyautogui helpers (keyboard, mouse, coordinates) ──────────────────────────

def _pg():
    import pyautogui
    pyautogui.PAUSE = 0.1
    return pyautogui


def mouse_click(x: int, y: int, button: str = "left") -> str:
    try:
        _pg().click(x=x, y=y, button=button)
        return f"Clicked {button} at ({x}, {y})."
    except Exception as e:
        return f"mouse_click failed: {e}"


def double_click(x: int, y: int) -> str:
    try:
        _pg().doubleClick(x=x, y=y)
        return f"Double-clicked at ({x}, {y})."
    except Exception as e:
        return f"double_click failed: {e}"


def keyboard_type(text: str) -> str:
    try:
        pg = _pg()
        if text.isascii():
            pg.write(text, interval=0.02)
        else:
            # pyautogui cannot type å, ä, ö and other non-ASCII characters; paste them instead.
            import pyperclip
            previous = pyperclip.paste()
            pyperclip.copy(text)
            pg.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyperclip.copy(previous)
        return f"Typed: {text!r}"
    except Exception as e:
        return f"keyboard_type failed: {e}"


_KEY_ALIASES = {
    "control": "ctrl", "windows": "win", "escape": "esc", "return": "enter", "del": "delete",
    "play": "playpause", "pause": "playpause", "play/pause": "playpause",
    "next": "nexttrack", "previous": "prevtrack", "prev": "prevtrack", "mute": "volumemute",
}


def key_press(key: str) -> str:
    """Press a key or hotkey combo, e.g. 'enter', 'escape', 'ctrl+v', 'win', 'playpause'."""
    try:
        pg = _pg()
        keys = [k.strip().lower() for k in key.split("+") if k.strip()]
        keys = [_KEY_ALIASES.get(k, k) for k in keys]
        # pyautogui silently ignores names it does not know, which would look like success.
        unknown = [k for k in keys if k not in pg.KEYBOARD_KEYS]
        if not keys or unknown:
            return f"key_press failed: unknown key name(s) {unknown or key!r}."
        if len(keys) == 1:
            pg.press(keys[0])
        else:
            pg.hotkey(*keys)
        return f"Pressed: {'+'.join(keys)}"
    except Exception as e:
        return f"key_press failed: {e}"


def scroll(direction: str, amount: int = 3) -> str:
    try:
        # pyautogui passes the number straight to Windows, where one wheel notch is 120.
        clicks = (amount if direction.lower() == "up" else -amount) * 120
        _pg().scroll(clicks)
        return f"Scrolled {direction} by {amount}."
    except Exception as e:
        return f"scroll failed: {e}"


# ── Starting programs ─────────────────────────────────────────────────────────

_APP_TARGETS = {
    "spotify": "spotify:",
    "settings": "ms-settings:",
    "calculator": "calc.exe",
    "notepad": "notepad.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
}


def open_app(name: str) -> str:
    """Start a program by name: directly when its launcher is known, otherwise through Start."""
    wanted = name.strip().lower()
    target = _APP_TARGETS.get(wanted)
    if target and hasattr(os, "startfile"):
        try:
            os.startfile(target)
            return f"Started {name}."
        except OSError:
            pass   # not installed that way; try the Start menu
    try:
        pg = _pg()
        pg.press("win")
        time.sleep(0.7)
        keyboard_type(name)
        time.sleep(1.0)
        pg.press("enter")
        return f"Searched the Start menu for '{name}' and opened the top result. Use list_windows to confirm it started."
    except Exception as e:
        return f"open_app failed: {e}"


# ── Windows UI Automation via pywinauto (faster — no screenshot needed) ───────

# Kinds of control worth clicking, most likely first.
_CLICKABLE = ["Button", "MenuItem", "TabItem", "ListItem", "Hyperlink", "CheckBox", "RadioButton", "TreeItem", "Text"]


def _windows():
    from pywinauto import Desktop
    return [w for w in Desktop(backend="uia").windows() if w.window_text().strip()]


def _best_match(candidates, text_of, wanted: str):
    """Exact name first, then a name that starts with it, then one that contains it."""
    wanted = wanted.strip().lower()
    named = [(text_of(c).strip().lower(), c) for c in candidates]
    for test in (lambda t: t == wanted, lambda t: t.startswith(wanted), lambda t: wanted in t):
        hits = [c for t, c in named if t and test(t)]
        if hits:
            return hits[0]
    return None


def _find_window(title: str):
    return _best_match(_windows(), lambda w: w.window_text(), title)


def find_and_click(window_title: str, control_name: str) -> str:
    """Find a UI element by window title + control name and click it without a screenshot.
    Works for standard Windows apps, browsers, Spotify, File Explorer, etc."""
    try:
        win = _find_window(window_title)
        if win is None:
            return f"No open window matches '{window_title}'. {list_windows()}"
        win.set_focus()

        for control_type in _CLICKABLE:
            ctrl = _best_match(win.descendants(control_type=control_type),
                               lambda c: c.window_text(), control_name)
            if ctrl is not None:
                ctrl.click_input()
                return f"Clicked {control_type.lower()} '{ctrl.window_text()}' in '{win.window_text()}'."
        return (f"Nothing named '{control_name}' found in '{win.window_text()}'. "
                f"Take a screenshot and use mouse_click with coordinates instead.")
    except Exception as e:
        return f"find_and_click failed (try mouse_click with coordinates instead): {e}"


def focus_window(title: str) -> str:
    """Bring a window to the foreground by its title."""
    try:
        win = _find_window(title)
        if win is None:
            return f"No open window matches '{title}'. {list_windows()}"
        win.set_focus()
        return f"Focused '{win.window_text()}'."
    except Exception as e:
        return f"focus_window failed: {e}"


def list_windows() -> str:
    """List all currently open window titles — useful before using focus_window or find_and_click."""
    try:
        titles = [w.window_text() for w in _windows()]
        return "Open windows:\n" + "\n".join(f"  - {t}" for t in titles)
    except Exception as e:
        return f"list_windows failed: {e}"
