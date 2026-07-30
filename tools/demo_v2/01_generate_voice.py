"""
Demo v2 — Voice-over generator (edge-tts)

Generates one MP3 file per scene using Microsoft Edge TTS (free, high quality).

Usage:
    .venv\\Scripts\\python.exe tools\\demo_v2\\01_generate_voice.py
    .venv\\Scripts\\python.exe tools\\demo_v2\\01_generate_voice.py --lang vi

Output:
    tools/demo_v2/output/voice/01_opening.mp3
    tools/demo_v2/output/voice/02_privacy_terms.mp3
    ... etc

Voices used:
    English: en-US-AriaNeural (clear female, professional)
    Alt English: en-US-GuyNeural (male)
    Vietnamese: vi-VN-HoaiMyNeural (female)
    Alt Vietnamese: vi-VN-NamMinhNeural (male)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows cmd
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import edge_tts

from tools.demo_v2.scene_config import SCENES


OUT_DIR = Path(__file__).resolve().parent / "output" / "voice"

VOICES = {
    "en":     "en-US-AriaNeural",       # default English, professional female
    "en_m":   "en-US-GuyNeural",        # English male alternative
    "vi":     "vi-VN-HoaiMyNeural",     # Vietnamese female
    "vi_m":   "vi-VN-NamMinhNeural",    # Vietnamese male
}


async def generate_one(scene_id: str, text: str, voice: str, out_path: Path,
                       rate: str = "+0%", volume: str = "+0%"):
    """Generate one MP3 using edge-tts."""
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
    await communicate.save(str(out_path))


async def main_async(lang: str, voice: str, rate: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Voice: {voice} | Language: {lang} | Rate: {rate}")
    print(f"Output dir: {OUT_DIR}")
    print()

    for scene in SCENES:
        text = scene.voice_vi if lang == "vi" else scene.voice_en
        if not text.strip():
            print(f"  [SKIP] {scene.id} — no voice text for lang={lang}")
            continue
        out = OUT_DIR / f"{scene.id}.mp3"
        print(f"  Generating: {scene.id}.mp3 ({len(text)} chars)")
        try:
            await generate_one(scene.id, text, voice, out, rate=rate)
            size_kb = out.stat().st_size / 1024
            print(f"    -> {size_kb:.1f} KB")
        except Exception as exc:
            print(f"    [FAIL] {type(exc).__name__}: {exc}")

    print()
    print(f"Done. {len(SCENES)} files in {OUT_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Generate voice-over MP3s for demo")
    parser.add_argument("--lang", default="en", choices=["en", "vi"],
                        help="Language: en (default) or vi")
    parser.add_argument("--gender", default="f", choices=["f", "m"],
                        help="Voice gender: f (default) or m")
    parser.add_argument("--rate", default="-5%",
                        help="Speech rate adjustment (e.g. '-10%%' to slow down, '+10%%' to speed up). Default '-5%%' for clarity.")
    args = parser.parse_args()

    voice_key = args.lang + ("_m" if args.gender == "m" else "")
    voice = VOICES[voice_key]

    asyncio.run(main_async(args.lang, voice, args.rate))


if __name__ == "__main__":
    main()
