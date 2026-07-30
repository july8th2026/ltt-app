"""
Facebook demo — CapCut production helper.

For an OBS-record → CapCut-edit workflow this:
  1. Measures the real duration of each scene's voice MP3 (pygame).
  2. Builds ONE combined voice track per video (naive MP3 concat) so you drop a
     single audio file per video onto the CapCut timeline.
  3. Writes ASSEMBLY.md — a per-video editing sheet with cumulative timings,
     the short on-screen CAPTION to add as a CapCut text overlay, and which
     screen action each segment covers.

Output:
  output/tracks/video1_pages_show_list.mp3      (combined voice)
  output/tracks/video2_pages_manage_posts.mp3
  output/tracks/video3_pages_read_engagement.mp3
  output/ASSEMBLY.md                            (CapCut editing blueprint)

Usage:
  .venv\\Scripts\\python.exe -m tools.demo_fb.produce
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.demo_fb.fb_scenes import VIDEO_TITLES, scenes_for_video  # noqa: E402

HERE      = Path(__file__).resolve().parent
VOICE_DIR = HERE / "output" / "voice"
TRACK_DIR = HERE / "output" / "tracks"
SHEET     = HERE / "output" / "ASSEMBLY.md"

# Short on-screen captions (CapCut text overlays) — keep punchy, one line each.
CAPTIONS = {
    "v1_01_intro":     "LTTStudios VideoBot — pages_show_list",
    "v1_02_connect":   "① Connect Facebook → grant 3 permissions",
    "v1_03_pages_list":"② GET /me/accounts → your Pages are listed",
    "v2_01_intro":     "pages_manage_posts — publish a video to a Page",
    "v2_02_form":      "① Select Page + local video + title (Public)",
    "v2_03_publish":   "② POST /{page-id}/videos — resumable upload 0→100%",
    "v2_04_verify":    "③ Video is published on the Page",
    "v3_01_intro":     "pages_read_engagement — read insights",
    "v3_02_insights":  "GET /{video-id}/video_insights → metrics table",
}


def _duration_s(mp3: Path) -> float:
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        return pygame.mixer.Sound(str(mp3)).get_length()
    except Exception:
        return mp3.stat().st_size / (128 * 1024 / 8) if mp3.exists() else 0.0


def _fmt(t: float) -> str:
    return f"{int(t)//60:d}:{int(t)%60:02d}.{int((t*10)%10)}"


def main():
    TRACK_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# CapCut Assembly Sheet — Facebook App Review (3 videos)\n",
             "Workflow: OBS records the silent screen actions → import the "
             "combined voice track + add the CAPTION text overlays in CapCut, "
             "timed as below (voice durations are exact).\n"]

    grand = 0.0
    for v in (1, 2, 3):
        scenes = scenes_for_video(v)
        title = VIDEO_TITLES[v]
        track = TRACK_DIR / f"video{v}_{title}.mp3"

        # Combine voice (naive MP3 concat — fine for CapCut re-import)
        with open(track, "wb") as out:
            for s in scenes:
                mp3 = VOICE_DIR / f"{s.id}.mp3"
                if mp3.exists():
                    out.write(mp3.read_bytes())

        total = sum(_duration_s(VOICE_DIR / f"{s.id}.mp3") for s in scenes)
        grand += total
        lines.append(f"\n## VIDEO {v} — `{title}`  ·  total {_fmt(total)} "
                     f"({total:.1f}s)\n")
        lines.append(f"Voice track: `output/tracks/{track.name}`\n")
        lines.append("| # | Start | End | Dur | CAPTION (text overlay) | Screen action |")
        lines.append("|---|-------|-----|-----|------------------------|---------------|")
        cursor = 0.0
        for i, s in enumerate(scenes, 1):
            d = _duration_s(VOICE_DIR / f"{s.id}.mp3")
            start, end = cursor, cursor + d
            cursor = end
            action = s.on_screen[0] if s.on_screen else s.title
            cap = CAPTIONS.get(s.id, s.title)
            lines.append(f"| {i} | {_fmt(start)} | {_fmt(end)} | {d:.1f}s | "
                         f"{cap} | {action} |")

    lines.append(f"\n---\n**Total across 3 videos: {_fmt(grand)} ({grand:.1f}s)**\n")
    lines.append("\n## CapCut steps per video\n"
                 "1. Import the OBS screen recording → trim to the actions.\n"
                 "2. Import `output/tracks/videoN_*.mp3` → place at 0:00 on the audio track.\n"
                 "3. Add a Text overlay for each row above at its Start→End time "
                 "(use the CAPTION column).\n"
                 "4. Align the screen actions to the voice (the voice narrates each step).\n"
                 "5. Export 1280×720 or 1080p, H.264 MP4. Name: `pages_show_list.mp4`, "
                 "`pages_manage_posts.mp4`, `pages_read_engagement.mp4`.\n")

    SHEET.write_text("\n".join(lines), encoding="utf-8")

    print("Combined voice tracks:")
    for v in (1, 2, 3):
        t = TRACK_DIR / f"video{v}_{VIDEO_TITLES[v]}.mp3"
        print(f"  ✓ {t.name}  ({t.stat().st_size/1024:.1f} KB, {_duration_s(t):.1f}s)")
    print(f"\nAssembly sheet: {SHEET}")
    print(f"Grand total: {grand:.1f}s")


if __name__ == "__main__":
    main()
