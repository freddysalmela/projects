import base64
import io


def take_screenshot() -> dict:
    """Capture the screen and return a base64-encoded PNG for Claude vision."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.thumbnail((1600, 900))  # cap size to keep token cost reasonable
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        w, h = img.size
        return {"image": b64, "text": f"Screenshot captured ({w}x{h} px)."}
    except Exception as e:
        return {"image": None, "text": f"Screenshot failed: {e}"}


def read_clipboard() -> str:
    """Return whatever text is currently in the clipboard."""
    try:
        import pyperclip
        text = pyperclip.paste()
        return text.strip() if text and text.strip() else "(Clipboard is empty)"
    except Exception as e:
        return f"Could not read clipboard: {e}"
