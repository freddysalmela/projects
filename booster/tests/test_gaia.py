"""Offline checks for Gaia: no microphone, speakers or API keys needed.
Run with: venv/Scripts/python.exe tests/test_gaia.py
"""
import sys, os, types, json, struct, math, threading, tempfile, time, queue
# Point the home folder at a temp dir (HOME on Linux/macOS, USERPROFILE on Windows) so the
# tests never touch the real ~/gaia_notes.
os.environ["HOME"] = os.environ["USERPROFILE"] = tempfile.mkdtemp()
os.environ.update(ANTHROPIC_API_KEY="k", OPENAI_API_KEY="k")
for k in ("CARTESIA_API_KEY","ELEVENLABS_API_KEY","MYCROFT_MODEL"): os.environ.pop(k, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- fake pyaudio -----------------------------------------------------------
def tone(amp, n=1024): return struct.pack(f"{n}h", *([amp, -amp] * (n // 2)))
class FakeStream:
    script = []          # list of chunks; repeats silence after
    def __init__(s): s.i = 0
    def read(s, n, exception_on_overflow=False):
        s.i += 1
        return FakeStream.script[s.i-1] if s.i <= len(FakeStream.script) else tone(10, n)
    def stop_stream(s): pass
    def close(s): pass
class FakePA:
    def open(s, **kw): return FakeStream()
    def terminate(s): pass
    def get_device_count(s): return 0
pa = types.ModuleType("pyaudio"); pa.PyAudio = FakePA; pa.paInt16 = 8
sys.modules["pyaudio"] = pa

from mycroft import state
from mycroft.config import get_config
cfg = get_config()

def test_config():
    assert cfg.model == "claude-sonnet-5", cfg.model
    assert cfg.wake_word_threshold == 0.3 and cfg.silence_secs == 2.8 and cfg.ui_host == "127.0.0.1"
    assert cfg.input_device == "" and cfg.barge_in is False

def test_calculator():
    from mycroft.capabilities.calculator import evaluate_expression as ev, geometry as g
    assert ev("pi * 4**2") == "50.2655"
    assert ev("sqrt(144)") == "12"
    assert ev("2^10") == "1024"
    assert ev("(3/8) * 16") == "6"
    assert "only numbers" in ev("__import__('os').system('echo hi')")
    assert "only numbers" in ev("x.__class__")
    assert ev("0.5 + 1.25") == "1.7500"
    a = g("cylinder_volume", {"r": 2, "h": 10}); b = g("cylinder_volume", {"h": 10, "r": 2})
    assert a == b and "125.6637" in a, (a, b)
    assert "needs exactly" in g("cylinder_volume", {"radius": 2, "h": 10})
    assert "5.0000" in g("pythagorean_c", {"a": 3, "b": 4})
    assert "4.0000" in g("pythagorean_a", {"b": 3, "c": 5})

def test_youtube_parse():
    from mycroft.capabilities.search import parse_youtube_results
    data = {"contents": {"x": [{"itemSectionRenderer": {"contents": [
        {"adSlotRenderer": {}},
        {"videoRenderer": {"videoId": "abc123", "title": {"runs": [{"text": "TIG "}, {"text": "basics"}]},
                           "ownerText": {"runs": [{"text": "Weld.com"}]}, "lengthText": {"simpleText": "12:01"}}},
        {"videoRenderer": {"videoId": "zzz", "title": {"simpleText": "Second; var x = {}"}}}]}}]}}
    html = "<script>var ytInitialData = " + json.dumps(data) + ";</script><script>var other = {};</script>"
    r = parse_youtube_results(html, 5)
    assert r[0] == {"title": "TIG basics", "url": "https://www.youtube.com/watch?v=abc123", "channel": "Weld.com", "duration": "12:01"}, r
    assert len(r) == 2 and parse_youtube_results("<html>consent</html>") == []

def test_youtube_fallback():
    from mycroft.capabilities import search
    opened = []
    real_open = search.open_url
    search.open_url = lambda u: opened.append(u)
    def boom(q, n): raise RuntimeError("blocked")
    search._youtube_direct = boom; search._youtube_via_duckduckgo = boom
    r = search.youtube_search("tig welding")
    assert opened == ["https://www.youtube.com/results?search_query=tig+welding"] and "results page" in r[0]["title"]
    search._youtube_via_duckduckgo = lambda q, n: [{"title": "t", "url": "https://www.youtube.com/watch?v=1", "channel": "", "duration": ""}]
    opened.clear(); r = search.youtube_search("x")
    assert opened == ["https://www.youtube.com/watch?v=1"]
    search.open_url = real_open

def test_normalise():
    from mycroft.main import normalise, _MUTE, _DISMISS
    for t in ["Mute.", "mute!", "Okay, mute please.", "Gaia, mute.", "Hey Gaia, be quiet", "Stop."]:
        assert normalise(t) in _MUTE, (t, normalise(t))
    assert normalise("Thanks, that's all.") in _DISMISS
    assert normalise("Mute the TV and open Spotify") not in _MUTE
    assert normalise("Please") == "please"

# ---- recorder ---------------------------------------------------------------
def test_recorder():
    from mycroft.audio import recorder
    import wave, io
    state.stop_event.clear()
    FakeStream.script = [tone(10)]*20 + [tone(3000)]*8      # 20 quiet, 8 loud, then silence
    wav = recorder.record()
    w = wave.open(io.BytesIO(wav)); frames = w.getnframes() // 1024
    # pre-roll (7 chunks incl. the 2 trigger chunks) + 6 more loud + 4 tail chunks
    assert w.getframerate() == 16000 and 14 <= frames <= 19, frames
    FakeStream.script = [tone(10)]*5 + [tone(3000)] + [tone(10)]*5    # single click: not speech
    cfg.session_timeout_secs = 2
    t = time.time(); assert recorder.record() is None; assert time.time() - t < 2
    state.stop_event.set(); assert recorder.record() is None; state.stop_event.clear()
    cfg.session_timeout_secs = 20

# ---- tts --------------------------------------------------------------------
def test_tts():
    from mycroft.audio import tts
    written = []
    class Out:
        def __init__(s, **kw): s.aborted = False
        def __enter__(s): return s
        def __exit__(s, *a): pass
        def write(s, d): assert len(d) % 2 == 0; written.append(d)
        def abort(s): written.append("ABORT")
    sd = types.ModuleType("sounddevice"); sd.RawOutputStream = Out; sys.modules["sounddevice"] = sd
    played = threading.Event()
    tts._play_pcm(iter([b"\x01", b"\x02\x03\x04", b"\x05" * 5000]), 44100, played)
    assert played.is_set() and b"".join(written) == b"\x01\x02\x03\x04" + b"\x05" * 4999 + b""[:0] or len(b"".join(written)) == 5004
    written.clear(); state.stop_event.set()
    tts._play_pcm(iter([b"\x00" * 100]), 44100, threading.Event()); assert written == ["ABORT"]
    state.stop_event.clear()

    # provider chain: cartesia fails before any sound -> falls through to edge
    calls = []
    os.environ["CARTESIA_API_KEY"] = "c"
    def bad(text, key, played): calls.append("cartesia"); raise RuntimeError("401")
    def edge(text, played): calls.append(("edge", text))
    tts._speak_cartesia, tts._speak_edge = bad, edge
    tts.speak("**Hello** `there`")
    assert calls == ["cartesia", ("edge", "Hello there")], calls
    assert not state.speaking.is_set()
    # fails after sound started -> no second voice
    calls.clear()
    def half(text, key, played): calls.append("cartesia"); played.set(); raise RuntimeError("dropped")
    tts._speak_cartesia = half; tts.speak("x"); assert calls == ["cartesia"]
    # stop requested -> nothing is said
    calls.clear(); state.stop_event.set(); tts.speak("x"); assert calls == []; state.stop_event.clear()
    os.environ.pop("CARTESIA_API_KEY")

def test_cartesia_request():
    from mycroft.audio import tts
    import importlib; importlib.reload(tts)
    seen = {}
    class Resp:
        status_code = 200; text = ""
        def iter_content(s, chunk_size): yield b"\x00\x00" * 10
        def close(s): seen["closed"] = True
    class Sess:
        def post(s, url, **kw): seen.update(url=url, **kw); return Resp()
    tts._session = Sess()
    got = []
    tts._play_pcm = lambda chunks, rate, played: got.append((b"".join(chunks), rate))
    tts._speak_cartesia("hi", "KEY", threading.Event())
    assert seen["url"].endswith("/tts/bytes") and seen["headers"]["X-API-Key"] == "KEY" and seen["stream"] is True
    assert seen["json"]["output_format"] == {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 44100}
    assert got == [(b"\x00" * 20, 44100)] and seen["closed"]
    class Bad(Resp): status_code = 401; text = "nope"
    Sess.post = lambda s, url, **kw: Bad()
    try: tts._speak_cartesia("hi", "KEY", threading.Event()); assert False
    except RuntimeError as e: assert "401" in str(e)

# ---- claude client ----------------------------------------------------------
import anthropic
from anthropic.types import TextBlock, ToolUseBlock
class Final:
    def __init__(s, content, stop_reason): s.content, s.stop_reason = content, stop_reason
class FakeStreamCM:
    def __init__(s, pieces, final, on_exit): s.text_stream, s.final, s.on_exit = iter(pieces), final, on_exit
    def __enter__(s): return s
    def __exit__(s, *a): s.on_exit(); return False
    def get_final_message(s): return s.final
class FakeMessages:
    def __init__(s, rounds, reject_thinking=False): s.rounds, s.calls, s.exits, s.reject = list(rounds), [], 0, reject_thinking
    def stream(s, **kw):
        s.calls.append({**kw, "messages": json.loads(json.dumps(kw["messages"], default=lambda o: o.model_dump()))})
        if s.reject and "thinking" in kw:
            class CM:
                def __enter__(_): 
                    import httpx
                    raise anthropic.BadRequestError("thinking: disabled is not supported", response=_resp(), body=None)
                def __exit__(_, *a): pass
            return CM()
        r = s.rounds.pop(0)
        if isinstance(r, Exception):
            class CM:
                def __enter__(_): raise r
                def __exit__(_, *a): pass
            return CM()
        pieces, final = r
        def done(): s.exits += 1
        return FakeStreamCM(pieces, final, done)
def _resp():
    try:
        import httpx2 as hx
    except ImportError:
        import httpx as hx
    return hx.Response(400, request=hx.Request("POST", "https://api.anthropic.com/v1/messages"))

def make(rounds, **kw):
    from mycroft.brain import claude_client as cc
    if cc._HISTORY_FILE.exists(): cc._HISTORY_FILE.unlink()
    c = cc.ClaudeClient(cfg); fm = FakeMessages(rounds, **kw)
    c.client = types.SimpleNamespace(messages=fm)
    return c, fm, cc

def test_claude_plain():
    c, fm, cc = make([(["Hel", "lo there. How ", "are you? I am", " fine"], Final([TextBlock(type="text", text="x")], "end_turn"))])
    out = list(c.chat_stream("hi"))
    assert out == ["Hello there.", "How are you?", "I am fine"], out
    assert len(fm.calls) == 1 and fm.calls[0]["thinking"] == {"type": "disabled"} and fm.calls[0]["tools"]
    assert fm.calls[0]["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert [m["role"] for m in c.history] == ["user", "assistant"]
    assert c.history[0]["content"].endswith("] hi") and c.history[0]["content"].startswith("[20")
    saved = json.loads(cc._HISTORY_FILE.read_text())
    assert saved[1] == {"role": "assistant", "content": "Hello there. How are you? I am fine"}

def test_claude_tools():
    from mycroft.brain import claude_client as cc
    tool = ToolUseBlock(type="tool_use", id="tu_1", name="calculate", input={"expression": "2+2"})
    shot = ToolUseBlock(type="tool_use", id="tu_2", name="take_screenshot", input={})
    boom = ToolUseBlock(type="tool_use", id="tu_3", name="read_clipboard", input={})
    c, fm, cc = make([
        (["Let me check. "], Final([TextBlock(type="text", text="Let me check. "), tool, shot, boom], "tool_use")),
        (["It is four."], Final([TextBlock(type="text", text="It is four.")], "end_turn")),
        (["Again."], Final([TextBlock(type="text", text="Again.")], "end_turn")),
    ])
    real = cc.dispatch_tool
    def fake(name, inputs):
        if name == "take_screenshot": return {"image": "QUJD", "text": "Screenshot: ok", "media_type": "image/jpeg"}
        if name == "read_clipboard": raise OSError("no clipboard")
        return real(name, inputs)
    cc.dispatch_tool = fake
    try:
        out = list(c.chat_stream("what is two plus two"))
        assert out == ["Let me check.", "It is four."], out
        roles = [m["role"] for m in c.history]
        assert roles == ["user", "assistant", "user", "assistant"], roles
        res = fm.calls[1]["messages"][2]["content"]
        assert [r["tool_use_id"] for r in res] == ["tu_1", "tu_2", "tu_3"]
        assert res[0]["content"] == "4" and res[1]["content"][0]["type"] == "image" and res[2]["is_error"] is True
        assert c.history[3]["content"] == "It is four."
        # screenshot dropped from history once the turn is over, tool call/result pairing intact
        assert c.history[2]["content"][1]["content"][0] == cc._IMAGE_PLACEHOLDER
        list(c.chat_stream("again"))
        sent = fm.calls[2]["messages"]
        assert [m["role"] for m in sent] == ["user", "assistant", "user", "assistant", "user"]
        assert "image" not in json.dumps(sent)
        saved = json.loads(cc._HISTORY_FILE.read_text())
        assert [m["role"] for m in saved] == ["user", "assistant", "user", "assistant"]
        assert saved[1]["content"] == "Let me check. It is four.", saved
    finally:
        cc.dispatch_tool = real

def test_claude_interrupt_and_error():
    tool = ToolUseBlock(type="tool_use", id="tu_1", name="calculate", input={"expression": "2+2"})
    c, fm, cc = make([
        (["One. Two. Three."], Final([], "end_turn")),
        RuntimeError("network down"),
        (["Calculating. "], Final([TextBlock(type="text", text="Calculating. "), tool], "tool_use")),
        RuntimeError("network down mid-turn"),
        (["Fine."], Final([], "end_turn")),
    ])
    g = c.chat_stream("count"); assert next(g) == "One."; g.close()       # interrupted mid-answer
    assert fm.exits == 1
    assert [(m["role"], m["content"][-6:]) for m in c.history] == [("user", " count"), ("assistant", "One.")]
    try: list(c.chat_stream("fail")); assert False
    except RuntimeError: pass
    assert len(c.history) == 2                                              # failed turn left no trace
    try: list(c.chat_stream("calc")); assert False
    except RuntimeError: pass
    assert [m["role"] for m in c.history] == ["user", "assistant", "user", "assistant"]
    assert all(isinstance(m["content"], str) for m in c.history)           # no dangling tool call
    assert list(c.chat_stream("ok")) == ["Fine."]
    assert [m["role"] for m in fm.calls[-1]["messages"]] == ["user", "assistant", "user", "assistant", "user"]

def test_claude_thinking_fallback_and_refusal():
    c, fm, cc = make([(["Hi."], Final([], "end_turn")), (["Yo."], Final([], "end_turn")), ([], Final([], "refusal"))], reject_thinking=True)
    assert list(c.chat_stream("a")) == ["Hi."]
    assert "thinking" in fm.calls[0] and "thinking" not in fm.calls[1]
    assert list(c.chat_stream("b")) == ["Yo."] and len(fm.calls) == 3 and "thinking" not in fm.calls[2]
    assert list(c.chat_stream("c")) == ["Sorry, I can't help with that one."]

def test_claude_trim_and_load():
    c, fm, cc = make([(["R."], Final([], "end_turn"))] * 30)
    c.max_history_turns = 3
    for i in range(6): list(c.chat_stream(f"q{i}"))
    msgs = fm.calls[-1]["messages"]
    assert len(msgs) == 5 and msgs[0]["role"] == "user" and msgs[0]["content"].endswith("q3"), msgs
    cc._HISTORY_FILE.write_text(json.dumps([{"role": "assistant", "content": "orphan"}, {"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]))
    assert [m["role"] for m in cc.ClaudeClient(cfg).history] == ["user", "assistant"]

def test_tools_schema():
    from mycroft.brain.tools import TOOLS, dispatch_tool
    names = [t["name"] for t in TOOLS]
    assert len(names) == len(set(names)) and "open_app" in names
    for t in TOOLS:
        assert t["input_schema"]["type"] == "object" and t["description"]
    assert dispatch_tool("nope", {}).startswith("Unknown tool")
    assert "Note saved" in dispatch_tool("save_note", {"title": "Engine bay", "content": "width 820 mm"})
    assert "820" in dispatch_tool("recall_notes", {"query": "what was the engine width"})
    assert "Nothing matches" in dispatch_tool("recall_notes", {"query": "zzzz"})
    assert "Refused" in dispatch_tool("open_url", {"url": "file:///c:/x"})

# ---- end-to-end session through main() with fakes -----------------------------
def test_main_session():
    from mycroft import main as m
    from mycroft.ui import server as ui
    said, states = [], []
    script = iter([
        ("Mute.", None),                    # session 1: silent standby
        ("What is two plus two?", None),    # session 2: answer...
        ("Tell me a long story", "barge"),  # ...interrupted by the wake word -> keeps listening
        ("Thanks.", None),                  # -> stand by
        (None, None),                       # session 3: nobody speaks -> silent standby
        ("Goodbye.", None),                 # session 4: shut down
    ])
    current = {}
    def fake_record():
        text, action = next(script); current["action"] = action; current["text"] = text
        return None if text is None else b"wav"
    class FakeClaude:
        def __init__(s, cfg): s.closed = 0
        def chat_stream(s, text):
            try:
                if current["action"] == "barge":
                    yield "Once upon a time."
                    for _ in range(200):
                        if any("Once upon" in x for x in said): break
                        time.sleep(0.01)
                    state.interrupt_by_voice()
                    yield "There was a welder."
                    yield "Never spoken."
                else:
                    yield "It is four."
            finally:
                s.closed += 1
    def fake_speak(text, key=""):
        if not state.stop_event.is_set(): said.append(text)
    m.record, m.transcribe, m.speak, m.ClaudeClient = fake_record, (lambda wav: current["text"]), fake_speak, FakeClaude
    m.webbrowser = types.SimpleNamespace(open=lambda u: None)
    triggers = iter([1, 1, 1, 1])
    ui.start = lambda **kw: None
    ui.set_state = lambda st, **kw: states.append((st, kw.get("status")))
    ui.wait_for_trigger = lambda: next(triggers)
    ww = types.ModuleType("mycroft.capabilities.wake_word"); active = []
    ww.start = lambda *a, **k: None; ww.set_session_active = active.append
    sys.modules["mycroft.capabilities.wake_word"] = ww
    import mycroft.capabilities as caps; caps.wake_word = ww
    br = types.ModuleType("mycroft.capabilities.briefing"); br.morning_briefing = lambda: ""
    sys.modules["mycroft.capabilities.briefing"] = br
    state.stop_event.set()      # a stale stop from "before" must not silence the session
    try: m.main(); assert False
    except SystemExit as e: assert e.code == 0
    said = [s for s in said if not s.startswith("Good ")]
    acks = set(m._ACKS)
    flat = [("ACK" if s in acks else s) for s in said]
    joined = " | ".join(flat)
    # ack may be merged with the first sentence by the worker; normalise that
    for a in acks: joined = joined.replace(a + " ", "ACK | ")
    exp = "I'm listening. | I'm listening. | ACK | It is four. | ACK | Once upon a time. | Alright, I'll stand by. | I'm listening. | I'm listening. | Shutting down. Take care!"
    assert joined == exp, joined
    assert active == [True, False, True, False, True, False, True, False], active
    assert not state.speaking.is_set()

if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try: fn(); print("PASS", name)
            except Exception as e:
                import traceback; fails += 1; print("FAIL", name); traceback.print_exc()
    sys.exit(1 if fails else 0)
