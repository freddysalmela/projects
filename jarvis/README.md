# J.A.R.V.I.S

A JARVIS-style voice interface for Claude, styled after the Iron Man HUD.

## Setup

```bash
cd jarvis
npm install
npm run dev
```

Open the app, click **CONFIG**, and enter:

- **Anthropic API key** — required. Get one at https://console.anthropic.com/
- **ElevenLabs API key** — optional. If left blank, spoken replies fall back to
  your browser's built-in text-to-speech. With a key set, replies are read
  aloud using ElevenLabs instead.
- **ElevenLabs voice ID** — which voice to use (defaults to a stock voice).

Keys are stored only in `localStorage` in your browser — nothing is committed
to the repo or sent anywhere except directly from your browser to Anthropic /
ElevenLabs.

## Using it

Press and hold **HOLD TO TALK**, speak, and release. Your speech is
transcribed locally in the browser (Web Speech API — Chrome works best), sent
to Claude, and the reply is displayed in the comm log and read aloud.

## Notes

- Speech recognition requires a Chromium-based browser (Web Speech API is not
  supported in Firefox/Safari).
- Calls to the Anthropic and ElevenLabs APIs are made directly from the
  browser, which is fine for personal local use but means your API keys are
  exposed to browser devtools/extensions on your machine.
