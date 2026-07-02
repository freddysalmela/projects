"""
Computer control — two layers:
1. Windows UI Automation via pywinauto (primary): click by element name/title, no screenshot needed
2. pyautogui (fallback): coordinate-based clicks for apps without accessibility trees (games, Electron, etc.)
"""


# ── pyautogui helpers (coordinate-based fallback) ─────────────────────────────

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
        _pg().write(text, interval=0.05)
        return f"Typed: {text!r}"
    except Exception as e:
        return f"keyboard_type failed: {e}"


def key_press(key: str) -> str:
    """Press a key or hotkey combo, e.g. 'enter', 'escape', 'ctrl+v', 'win'."""
    try:
        pg = _pg()
        keys = [k.strip() for k in key.split("+")]
        if len(keys) == 1:
            pg.press(keys[0])
        else:
            pg.hotkey(*keys)
        return f"Pressed: {key}"
    except Exception as e:
        return f"key_press failed: {e}"


def scroll(direction: str, amount: int = 3) -> str:
    try:
        clicks = amount if direction.lower() == "up" else -amount
        _pg().scroll(clicks)
        return f"Scrolled {direction} by {amount}."
    except Exception as e:
        return f"scroll failed: {e}"


# ── Windows UI Automation via pywinauto (faster — no screenshot needed) ───────

def find_and_click(window_title: str, control_name: str) -> str:
    """Find a UI element by window title + control name and click it without a screenshot.
    Works for standard Windows apps, browsers, Spotify, File Explorer, etc.
    Falls back gracefully if the window or control isn't found."""
    try:
        from pywinauto import Application, Desktop
        from pywinauto.findwindows import ElementNotFoundError

        # Find the window (partial title match)
        desktop = Desktop(backend="uia")
        win = desktop.window(title_re=f".*{window_title}.*")
        win.set_focus()

        ctrl = win.child_window(title_re=f".*{control_name}.*", control_type="Button")
        ctrl.click_input()
        return f"Clicked '{control_name}' in '{window_title}'."
    except Exception as e:
        return f"find_and_click failed (try mouse_click with coordinates instead): {e}"


def focus_window(title: str) -> str:
    """Bring a window to the foreground by its title."""
    try:
        from pywinauto import Desktop
        win = Desktop(backend="uia").window(title_re=f".*{title}.*")
        win.set_focus()
        return f"Focused window matching '{title}'."
    except Exception as e:
        return f"focus_window failed: {e}"


def list_windows() -> str:
    """List all currently open window titles — useful before using focus_window or find_and_click."""
    try:
        from pywinauto import Desktop
        titles = [w.window_text() for w in Desktop(backend="uia").windows() if w.window_text().strip()]
        return "Open windows:\n" + "\n".join(f"  - {t}" for t in titles)
    except Exception as e:
        return f"list_windows failed: {e}"
