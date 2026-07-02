import base64
import io


def take_screenshot() -> dict:
    """Capture the screen and return a base64-encoded PNG for Claude vision."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        actual_w, actual_h = img.size
        img.thumbnail((1280, 720))
        preview_w, preview_h = img.size
        scale_x = round(actual_w / preview_w, 2)
        scale_y = round(actual_h / preview_h, 2)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        text = (
            f"Screenshot: {preview_w}x{preview_h} preview "
            f"(actual screen: {actual_w}x{actual_h}, scale {scale_x}x). "
            f"To click at preview position (px, py), use mouse_click(round(px*{scale_x}), round(py*{scale_y}))."
        )
        return {"image": b64, "text": text, "media_type": "image/jpeg"}
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
