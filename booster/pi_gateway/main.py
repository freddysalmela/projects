"""
Gaia Gateway — runs on a Raspberry Pi at the garage entrance.
Listens for the wake phrase, then:
  1. Turns on configured smart lights (TP-Link Kasa)
  2. Sends a Wake-on-LAN magic packet to the main PC
"""

import asyncio
import time
import yaml
import numpy as np
import pyaudio
from pathlib import Path

_CHUNK = 1280   # 80ms at 16kHz — openwakeword's frame size
_RATE  = 16000
_COOLDOWN_SECS = 30  # ignore re-triggers for this long after activation


def _load_config() -> dict:
    path = Path(__file__).parent / "config.yaml"
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _wake_pc(mac: str):
    from wakeonlan import send_magic_packet
    send_magic_packet(mac)
    print(f"[gateway] WoL sent to {mac}", flush=True)


async def _turn_on_kasa(ips: list[str]):
    from kasa import SmartPlug, SmartBulb, Discover
    for ip in ips:
        try:
            device = await Discover.discover_single(ip)
            await device.turn_on()
            print(f"[gateway] Turned on Kasa device at {ip}", flush=True)
        except Exception as e:
            print(f"[gateway] Kasa error {ip}: {e}", flush=True)


def _toggle_gpio(pins: list[int], state: bool):
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        print(f"[gateway] GPIO pins {pins} set to {'HIGH' if state else 'LOW'}", flush=True)
    except Exception as e:
        print(f"[gateway] GPIO error: {e}", flush=True)


def _activate(cfg: dict):
    kasa = cfg.get("kasa_devices", [])
    if kasa:
        asyncio.run(_turn_on_kasa(kasa))

    gpio_pins = cfg.get("gpio_relay_pins", [])
    if gpio_pins:
        _toggle_gpio(gpio_pins, state=True)

    pc_mac = cfg.get("pc_mac", "")
    if pc_mac:
        _wake_pc(pc_mac)


def main():
    cfg = _load_config()
    wake_word   = cfg.get("wake_word", "hey_jarvis")
    threshold   = float(cfg.get("threshold", 0.4))

    import openwakeword
    from openwakeword.model import Model

    print("[gateway] Downloading/checking wake word model...", flush=True)
    openwakeword.utils.download_models()
    oww = Model(wakeword_models=[wake_word], inference_framework="tflite")

    pa = pyaudio.PyAudio()
    stream = pa.open(
        rate=_RATE, channels=1, format=pyaudio.paInt16,
        input=True, frames_per_buffer=_CHUNK,
    )

    print(f"[gateway] Listening for '{wake_word}' (threshold {threshold})...", flush=True)

    last_trigger = 0.0
    try:
        while True:
            audio = np.frombuffer(
                stream.read(_CHUNK, exception_on_overflow=False),
                dtype=np.int16,
            )
            prediction = oww.predict(audio)

            for mdl, score in prediction.items():
                if score >= threshold:
                    now = time.time()
                    if now - last_trigger < _COOLDOWN_SECS:
                        break
                    last_trigger = now
                    oww.reset()
                    print(f"[gateway] '{mdl}' detected (score={score:.2f}) — activating!", flush=True)
                    _activate(cfg)
                    break
    finally:
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    main()
