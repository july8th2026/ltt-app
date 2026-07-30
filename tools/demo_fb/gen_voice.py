"""
Facebook demo — voice-over generator (edge-tts, free).

Generates one MP3 per scene from fb_scenes.py into output/voice/.

Usage:
    .venv\\Scripts\\python.exe tools\\demo_fb\\gen_voice.py            # English (default)
    .venv\\Scripts\\python.exe tools\\demo_fb\\gen_voice.py --lang vi  # Vietnamese
    .venv\\Scripts\\python.exe tools\\demo_fb\\gen_voice.py --gender m # male voice

Voices:
    English  : en-US-AriaNeural (f) / en-US-GuyNeural (m)
    Vietnamese: vi-VN-HoaiMyNeural (f) / vi-VN-NamMinhNeural (m)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import edge_tts  # noqa: E402

from tools.demo_fb.fb_scenes import ALL_SCENES, VIDEO_TITLES, scenes_for_video  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent / "output" / "voice"

VOICES = {
    "en":   "en-US-AriaNeural",
    "en_m": "en-US-GuyNeural",
    "vi":   "vi-VN-HoaiMyNeural",
    "vi_m": "vi-VN-NamMinhNeural",
}


async def _gen(text: str, voice: str, out_path: Path, rate: str):
    await edge_tts.Communicate(text=text, voice=voice, rate=rate).save(str(out_path))


async def main_async(lang: str, voice: str, rate: str):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Voice: {voice} | Lang: {lang} | Rate: {rate}")
    print(f"Output: {OUT_DIR}\n")

    ok = 0
    for scene in ALL_SCENES:
        text = scene.voice_vi if lang == "vi" else scene.voice_en
        if not text.strip():
            print(f"  [SKIP] {scene.id} — no {lang} text")
            continue
        out = OUT_DIR / f"{scene.id}.mp3"
        try:
            await _gen(text, voice, out, rate)
            print(f"  ✓ {scene.id}.mp3  ({out.stat().st_size/1024:.1f} KB)")
            ok += 1
        except Exception as exc:
            print(f"  ✗ {scene.id}: {type(exc).__name__}: {exc}")

    print(f"\nDone: {ok}/{len(ALL_SCENES)} MP3s.")
    for v in (1, 2, 3):
        ids = [s.id for s in scenes_for_video(v)]
        print(f"  VIDEO {v} ({VIDEO_TITLES[v]}): {', '.join(ids)}")


def main():
    p = argparse.ArgumentParser(description="Generate FB demo voice-overs")
    p.add_argument("--lang", default="en", choices=["en", "vi"])
    p.add_argument("--gender", default="f", choices=["f", "m"])
    p.add_argument("--rate", default="-5%", help="Speech rate, e.g. -10%% slower")
    args = p.parse_args()
    voice = VOICES[args.lang + ("_m" if args.gender == "m" else "")]
    asyncio.run(main_async(args.lang, voice, args.rate))


if __name__ == "__main__":
    main()
