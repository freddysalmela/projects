import pyautogui

pyautogui.PAUSE = 0.1  # small delay between actions for stability


def mouse_click(x: int, y: int, button: str = "left") -> str:
    try:
        pyautogui.click(x=x, y=y, button=button)
        return f"Clicked {button} at ({x}, {y})."
    except Exception as e:
        return f"mouse_click failed: {e}"


def double_click(x: int, y: int) -> str:
    try:
        pyautogui.doubleClick(x=x, y=y)
        return f"Double-clicked at ({x}, {y})."
    except Exception as e:
        return f"double_click failed: {e}"


def keyboard_type(text: str) -> str:
    try:
        pyautogui.write(text, interval=0.05)
        return f"Typed: {text!r}"
    except Exception as e:
        return f"keyboard_type failed: {e}"


def key_press(key: str) -> str:
    """Press a key or hotkey combo, e.g. 'enter', 'escape', 'ctrl+v', 'win'."""
    try:
        keys = [k.strip() for k in key.split("+")]
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return f"Pressed: {key}"
    except Exception as e:
        return f"key_press failed: {e}"


def scroll(direction: str, amount: int = 3) -> str:
    try:
        clicks = amount if direction.lower() == "up" else -amount
        pyautogui.scroll(clicks)
        return f"Scrolled {direction} by {amount}."
    except Exception as e:
        return f"scroll failed: {e}"
