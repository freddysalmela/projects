"""Run this once to list all your ElevenLabs voices and their IDs.
Usage: venv\Scripts\python.exe list_voices.py
"""
from dotenv import load_dotenv
load_dotenv()
import os
from elevenlabs.client import ElevenLabs

key = os.environ.get("ELEVENLABS_API_KEY", "")
if not key:
    print("ELEVENLABS_API_KEY not set in .env")
    raise SystemExit(1)

client = ElevenLabs(api_key=key)
voices = client.voices.get_all().voices

print(f"\n{'NAME':<22} {'VOICE ID':<30} {'GENDER':<8} ACCENT")
print("-" * 75)
for v in sorted(voices, key=lambda x: x.name or ""):
    labels = v.labels or {}
    print(f"{v.name:<22} {v.voice_id:<30} {labels.get('gender','?'):<8} {labels.get('accent','')}")

print(f"\n{len(voices)} voices found.")
print("\nAdd your chosen voice ID to .env:")
print("  ELEVENLABS_VOICE_ID=paste_id_here\n")
