# Gaia Gateway — Shopping List

Everything needed to run the Pi gateway at the garage entrance.
Search these exact product names on Verkkokauppa, Gigantti, or Amazon.de.

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
| **Micro USB power supply** | 5V / 2.5A, official Pi Foundation supply preferred | €8–12 |
| **Micro USB OTG adapter** | "Micro USB OTG hub" — needed to connect USB mic to Pi Zero | €5–8 |
| **Case for Pi Zero** | Optional but protects the board — search "Raspberry Pi Zero 2 W case" | €5–10 |

---

## Microphone

| Item | Notes | Est. Price |
|------|-------|------------|
| **Mini USB microphone** | Search "mini USB microphone Raspberry Pi" — plug-and-play, no drivers needed | €8–15 |

> Any USB microphone that shows up as a standard audio device on Linux will work. Avoid anything that needs proprietary drivers.

---

## Smart Lights — Shelly (available in Finland)

Shelly is widely available at Verkkokauppa and Amazon.de. Works entirely on your local network — no cloud account required after initial setup.

| Item | Use case | Est. Price (each) |
|------|----------|------------|
| **Shelly Plug S** | Plug your existing lamp into it — easiest option, controls any standard lamp | €18–25 |
| **Shelly 1** | Wire it into a wall switch or light circuit — permanent install, no visible plug | €15–20 |
| **Shelly Dimmer 2** | If you want dimming control on existing dimmable lights | €22–28 |

> **Recommendation:** Start with one **Shelly Plug S** for the garage lights. Plug it in, connect it to your WiFi via the Shelly app, assign a static IP in your router, and you're done.

> Shelly devices have a built-in local REST API — no special library needed. Gaia controls them with a simple web request.

---

## Total Estimate

| Scenario | Cost |
|----------|------|
| Pi Zero 2 W + mic + one Shelly Plug S (minimal) | **~€55–75** |
| Pi Zero 2 W + mic + case + two Shelly Plug S | **~€80–100** |
| Pi 4 2GB instead of Zero (more headroom) | **+€25** |

---

## What You Already Have (no need to buy)

- WiFi router — Pi and Shelly devices connect to your existing network
- The `pi_gateway/` code is already in this repo — pull it onto the Pi after setup
- A laptop/PC with an SD card reader to flash the Pi OS

---

## Setup Order

1. Flash **Raspberry Pi OS Lite (64-bit)** to the SD card using the **Raspberry Pi Imager** app (free, from raspberrypi.com)
2. In the Imager, click the settings gear — set your WiFi name/password and enable SSH before flashing
3. Insert SD card, power on Pi, SSH in: `ssh pi@<pi-ip-address>`
4. `git clone https://github.com/freddysalmela/projects && cd projects/booster/pi_gateway`
5. `pip install -r requirements.txt`
6. Plug Shelly into the wall, set it up in the **Shelly app**, then assign it a static IP in your router
7. Fill in `config.yaml`: PC MAC address + Shelly IP
8. Test: `python3 main.py` — say the wake phrase and watch the lights and PC react
9. Install autostart: `sudo cp gaia-gateway.service /etc/systemd/system/ && sudo systemctl enable --now gaia-gateway`
