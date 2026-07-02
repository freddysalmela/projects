# Gaia Gateway — Shopping List

Everything needed to run the Pi gateway at the garage entrance.
Search these exact product names on Amazon, Verkkokauppa, or Gigantti.

---

## Raspberry Pi

| Item | Search / Model | Est. Price |
|------|---------------|------------|
| **Raspberry Pi Zero 2 W** | "Raspberry Pi Zero 2 W" | €18–22 |

> If unavailable, the **Raspberry Pi 4 Model B 2GB** is a fine alternative (~€45) and has full-size USB ports (skip the OTG adapter then).

---

## Pi Accessories

| Item | Notes | Est. Price |
|------|-------|------------|
| **Micro SD card** | 16GB minimum, Class 10 or better — e.g. SanDisk Ultra 32GB | €8–12 |
| **Micro USB power supply** | 5V / 2.5A, official Pi foundation supply preferred | €8–12 |
| **Micro USB OTG adapter** | "Micro USB OTG hub" — needed to connect USB mic to Pi Zero | €5–8 |
| **Case for Pi Zero** | Optional but protects the board — search "Raspberry Pi Zero 2 W case" | €5–10 |

---

## Microphone

| Item | Notes | Est. Price |
|------|-------|------------|
| **Mini USB microphone** | Search "mini USB microphone Raspberry Pi" — plug-and-play, no drivers needed. The MAONO AU-UX1 or similar works well. | €8–15 |

> Avoid microphones that need dedicated software/drivers. Any USB microphone that shows up as a standard audio device on Linux will work.

---

## Smart Lights (TP-Link Kasa — recommended)

| Item | Notes | Est. Price (each) |
|------|-------|------------|
| **TP-Link Kasa Smart Plug EP25** | For switching existing garage lights on/off — just plug your light into it | €15–20 |
| **TP-Link Kasa Smart Bulb KL130** | If you want colour/dimming instead of just on/off | €18–25 |

> Buy as many as you have light circuits to control. One plug per lamp/circuit.
> You only need the Kasa app for initial setup — after that Gaia controls them locally over WiFi with no cloud required.

---

## Total Estimate

| Scenario | Cost |
|----------|------|
| Pi Zero 2 W + mic + one Kasa plug (minimal setup) | **~€55–70** |
| Pi Zero 2 W + mic + case + two Kasa plugs | **~€75–95** |
| Pi 4 2GB instead (more headroom) | **+€25** |

---

## What You Already Have (no need to buy)

- WiFi router — Pi and Kasa devices connect to your existing network
- The `pi_gateway/` code in this repo — pull it onto the Pi after setup
- A laptop/PC with an SD card reader to flash the Pi OS

---

## Setup Order

1. Flash **Raspberry Pi OS Lite (64-bit)** to the SD card using the Raspberry Pi Imager app
2. Enable SSH and WiFi credentials in the Imager before flashing
3. Plug in Pi, SSH in, `git clone` this repo, `pip install -r pi_gateway/requirements.txt`
4. Plug Kasa devices into the wall, set them up in the Kasa mobile app, then assign static IPs in your router
5. Fill in `pi_gateway/config.yaml` with PC MAC address and Kasa IPs
6. Run `python3 pi_gateway/main.py` to test, then install the systemd service for autostart
