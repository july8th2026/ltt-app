"""
Facebook demo — Teleprompter (voice-driven, per-video).

Records ONE of the 3 App Review videos at a time. For the selected video it:
  1. Shows the on-screen action checklist (left) + voice text + timer (right)
  2. Plays each scene's voice MP3 (OBS captures it via desktop audio)
  3. Auto-advances when the MP3 finishes (+1.5s buffer)

Run on a second monitor while OBS records the main screen showing the bot.

Prerequisites:
    1. gen_voice.py has been run (MP3s exist in output/voice/)
    2. OBS set to capture screen + desktop audio, recording started

Usage:
    .venv\\Scripts\\python.exe tools\\demo_fb\\teleprompter.py --video 1
    .venv\\Scripts\\python.exe tools\\demo_fb\\teleprompter.py --video 2 --lang vi
    .venv\\Scripts\\python.exe tools\\demo_fb\\teleprompter.py --video 3 --no-autoplay

Save each recording as: pages_show_list.mp4 / pages_manage_posts.mp4 /
pages_read_engagement.mp4
"""
from __future__ import annotations

import argparse
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from typing import Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.demo_fb.fb_scenes import Scene, VIDEO_TITLES, scenes_for_video  # noqa: E402

VOICE_DIR = Path(__file__).resolve().parent / "output" / "voice"
BUFFER_S  = 1.5

FB_BLUE = "#1877F2"
BG      = "#0d1117"
CARD    = "#161b22"


class AudioPlayer:
    def __init__(self):
        self._ok = False
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._mixer = pygame.mixer
            self._ok = True
        except Exception as exc:
            print(f"[WARN] Audio init failed: {exc} — teleprompter still works, no sound.")

    def play(self, mp3: Path):
        if not self._ok or not mp3.exists():
            return
        try:
            self._mixer.music.load(str(mp3))
            self._mixer.music.play()
        except Exception as exc:
            print(f"[WARN] play failed: {exc}")

    def is_busy(self) -> bool:
        try:
            return bool(self._ok and self._mixer.music.get_busy())
        except Exception:
            return False

    def stop(self):
        if self._ok:
            try:
                self._mixer.music.stop()
            except Exception:
                pass


def _mp3_duration_s(mp3: Path) -> float:
    if not mp3.exists():
        return 0.0
    try:
        import pygame
        return pygame.mixer.Sound(str(mp3)).get_length()
    except Exception:
        pass
    try:
        return mp3.stat().st_size / (128 * 1024 / 8)
    except Exception:
        return 0.0


class Teleprompter(tk.Tk):
    def __init__(self, scenes: list[Scene], video_no: int, lang: str, autoplay: bool):
        super().__init__()
        self.scenes = scenes
        self.video_no = video_no
        self.lang = lang
        self.autoplay = autoplay
        self.idx = 0
        self.playing = False
        self.scene_start_time: Optional[float] = None
        self.scene_duration_s = 0.0
        self.audio = AudioPlayer()
        self._tick_id: Optional[str] = None
        self._adv_id: Optional[str] = None

        self.title(f"FB Screencast Teleprompter — VIDEO {video_no}")
        self.geometry("1024x760")
        self.configure(bg=BG)

        self.f_title = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.f_prog  = tkfont.Font(family="Consolas", size=12)
        self.f_act   = tkfont.Font(family="Segoe UI", size=13)
        self.f_voice = tkfont.Font(family="Segoe UI", size=12, slant="italic")
        self.f_btn   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.f_timer = tkfont.Font(family="Consolas", size=38, weight="bold")

        self._build_ui()
        self._render()

        self.bind("<space>", lambda e: self._play())
        self.bind("<Right>", lambda e: self._next())
        self.bind("<Left>",  lambda e: self._prev())
        self.bind("<Escape>", lambda e: self._cancel())

    def _build_ui(self):
        top = tk.Frame(self, bg=BG); top.pack(fill="x", padx=18, pady=(16, 6))
        self.title_lbl = tk.Label(top, text="", font=self.f_title, fg=FB_BLUE,
                                  bg=BG, anchor="w"); self.title_lbl.pack(side="left")
        self.prog_lbl = tk.Label(top, text="", font=self.f_prog, fg="#888", bg=BG)
        self.prog_lbl.pack(side="right")

        self.perm_lbl = tk.Label(self, text="", font=("Segoe UI", 11, "bold"),
                                 fg="#4caf50", bg=BG, anchor="w")
        self.perm_lbl.pack(fill="x", padx=18, pady=(0, 4))

        mid = tk.Frame(self, bg=BG); mid.pack(fill="both", expand=True, padx=18, pady=8)

        left = tk.Frame(mid, bg=CARD, bd=1, relief="solid")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(left, text=" ON-SCREEN ACTIONS", font=("Segoe UI", 10, "bold"),
                 fg=FB_BLUE, bg=CARD, anchor="w").pack(fill="x", padx=10, pady=(10, 4))
        self.act_text = tk.Text(left, wrap="word", font=self.f_act, fg="#e6e6e6",
                                bg=CARD, bd=0, padx=12, pady=8, spacing1=4, spacing3=4)
        self.act_text.pack(fill="both", expand=True, padx=4, pady=(0, 10))

        right = tk.Frame(mid, bg=CARD, bd=1, relief="solid", width=380)
        right.pack(side="right", fill="y"); right.pack_propagate(False)
        tk.Label(right, text=" TIMING", font=("Segoe UI", 10, "bold"),
                 fg=FB_BLUE, bg=CARD, anchor="w").pack(fill="x", padx=10, pady=(10, 4))
        self.timer_lbl = tk.Label(right, text="00:00", font=self.f_timer,
                                  fg=FB_BLUE, bg=CARD); self.timer_lbl.pack(pady=4)
        self.dur_lbl = tk.Label(right, text="", font=self.f_prog, fg="#888", bg=CARD)
        self.dur_lbl.pack(pady=(0, 10))
        self.auto_lbl = tk.Label(right, text="", font=("Segoe UI", 10, "italic"),
                                 fg="#4caf50", bg=CARD); self.auto_lbl.pack(pady=(0, 8))
        tk.Label(right, text=" VOICE-OVER", font=("Segoe UI", 10, "bold"),
                 fg=FB_BLUE, bg=CARD, anchor="w").pack(fill="x", padx=10, pady=(10, 4))
        self.voice_text = tk.Text(right, wrap="word", font=self.f_voice, fg="#c8d0db",
                                  bg=CARD, bd=0, padx=12, pady=8)
        self.voice_text.pack(fill="both", expand=True, padx=4, pady=(0, 10))

        bottom = tk.Frame(self, bg=BG); bottom.pack(fill="x", padx=18, pady=(6, 14))
        self.prev_btn = tk.Button(bottom, text="◀ Previous", font=self.f_btn,
                                  bg="#30363d", fg="#e0e0e0", bd=0, padx=16, pady=8,
                                  command=self._prev); self.prev_btn.pack(side="left", padx=(0, 6))
        self.play_btn = tk.Button(bottom, text="▶ Play + Timer (Space)", font=self.f_btn,
                                  bg="#1a7f37", fg="white", bd=0, padx=16, pady=8,
                                  command=self._play); self.play_btn.pack(side="left", padx=6)
        self.next_btn = tk.Button(bottom, text="Next ▶", font=self.f_btn, bg=FB_BLUE,
                                  fg="white", bd=0, padx=16, pady=8,
                                  command=self._next); self.next_btn.pack(side="right")

        tk.Label(self, text="Space=Play  •  →=Next  •  ←=Prev  •  Esc=Cancel",
                 font=("Segoe UI", 9), fg="#666", bg=BG).pack(fill="x", padx=18, pady=(0, 8))

    def _render(self):
        s = self.scenes[self.idx]
        self.title_lbl.config(text=s.title)
        self.prog_lbl.config(text=f"VIDEO {self.video_no} — Scene {self.idx+1}/{len(self.scenes)}")
        self.perm_lbl.config(text=f"🎯 Permission: {s.permission}")

        mp3 = VOICE_DIR / f"{s.id}.mp3"
        dur = _mp3_duration_s(mp3)
        self.scene_duration_s = dur + BUFFER_S if dur > 0 else s.duration_s
        self.dur_lbl.config(text=(f"Voice {dur:.1f}s + {BUFFER_S:.0f}s buffer"
                                  if dur > 0 else f"Planned {s.duration_s:.0f}s (no MP3)"))

        self.act_text.config(state="normal"); self.act_text.delete("1.0", "end")
        for i, a in enumerate(s.on_screen, 1):
            self.act_text.insert("end", f"{i:2}.  {a}\n")
        self.act_text.config(state="disabled")

        txt = s.voice_en if self.lang == "en" else (s.voice_vi or s.voice_en)
        self.voice_text.config(state="normal"); self.voice_text.delete("1.0", "end")
        self.voice_text.insert("end", txt); self.voice_text.config(state="disabled")

        self.timer_lbl.config(text="00:00", fg=FB_BLUE)
        self.scene_start_time = None; self.playing = False
        self.audio.stop(); self._cancel_after()
        self.auto_lbl.config(text="⚡ Auto-advance ON" if self.autoplay else "(manual)")
        self.prev_btn.config(state="normal" if self.idx > 0 else "disabled")
        self.next_btn.config(text="Finish" if self.idx == len(self.scenes)-1 else "Next ▶")
        self.play_btn.config(text="▶ Play (Space)", bg="#1a7f37", state="normal")

    def _cancel_after(self):
        for attr in ("_tick_id", "_adv_id"):
            aid = getattr(self, attr, None)
            if aid:
                try: self.after_cancel(aid)
                except Exception: pass
                setattr(self, attr, None)

    def _play(self):
        if self.playing:
            return
        mp3 = VOICE_DIR / f"{self.scenes[self.idx].id}.mp3"
        if mp3.exists(): self.audio.play(mp3)
        else: print(f"[WARN] no voice: {mp3}")
        self.playing = True
        self.scene_start_time = time.perf_counter()
        self.play_btn.config(text="Recording... ⏺", bg="#9a2a2f", state="disabled")
        self._tick()

    def _tick(self):
        if not self.playing or self.scene_start_time is None:
            return
        elapsed = time.perf_counter() - self.scene_start_time
        remaining = self.scene_duration_s - elapsed
        if remaining < 0:
            self.timer_lbl.config(text=f"+{int(abs(remaining)):02d}s", fg="#ffb84d")
        else:
            self.timer_lbl.config(text=f"{int(remaining):02d}s", fg=FB_BLUE)
        if self.autoplay and (not self.audio.is_busy()) and elapsed >= self.scene_duration_s:
            self._adv_id = self.after(200, self._auto_advance); return
        self._tick_id = self.after(100, self._tick)

    def _auto_advance(self):
        self._next() if self.idx < len(self.scenes)-1 else self._finish()

    def _next(self):
        self.audio.stop(); self._cancel_after()
        if self.idx < len(self.scenes)-1:
            self.idx += 1; self._render()
            if self.autoplay: self.after(800, self._play)
        else:
            self._finish()

    def _prev(self):
        self.audio.stop(); self._cancel_after()
        if self.idx > 0:
            self.idx -= 1; self._render()

    def _finish(self):
        self.audio.stop(); self._cancel_after()
        self.title_lbl.config(text=f"✅ VIDEO {self.video_no} done — STOP OBS now")
        self.play_btn.config(state="disabled"); self.next_btn.config(state="disabled")
        self.timer_lbl.config(text="DONE", fg="#4caf50")
        self.after(5000, self.destroy)

    def _cancel(self):
        self.audio.stop(); self._cancel_after(); self.destroy()


def main():
    p = argparse.ArgumentParser(description="FB screencast teleprompter (per video)")
    p.add_argument("--video", type=int, required=True, choices=[1, 2, 3],
                   help="Which video to record: 1=pages_show_list, "
                        "2=pages_manage_posts, 3=pages_read_engagement")
    p.add_argument("--lang", default="en", choices=["en", "vi"])
    p.add_argument("--no-autoplay", action="store_true")
    args = p.parse_args()

    scenes = scenes_for_video(args.video)
    if not scenes:
        print(f"No scenes for video {args.video}"); return
    missing = [s.id for s in scenes if not (VOICE_DIR / f"{s.id}.mp3").exists()]
    if missing:
        print(f"[WARN] Missing voice MP3s: {missing}")
        print("      Run: .venv\\Scripts\\python.exe tools\\demo_fb\\gen_voice.py")
    print(f"VIDEO {args.video} — {VIDEO_TITLES[args.video]} — {len(scenes)} scenes")
    Teleprompter(scenes, args.video, args.lang, not args.no_autoplay).mainloop()


if __name__ == "__main__":
    main()
