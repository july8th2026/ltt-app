"""
Demo v3 — Teleprompter (Voice-Driven Auto-Advance)

Interactive recording guide. Each scene:
  1. Shows action checklist (left panel)
  2. Shows voice-over text (right panel)
  3. Plays voice MP3 (which OBS records via desktop audio)
  4. AUTO-ADVANCES to next scene when MP3 finishes + 1.5s buffer
  5. Or user can click Next/Previous to manually navigate

Designed to run on SECOND monitor (or phone via Remote Desktop) while
OBS records the main screen showing the bot.

Voice timing:
  - Each scene's effective duration = actual MP3 duration + 1.5s buffer
  - This ensures voice timing matches video timing EXACTLY
  - If user wants different timing, swap MP3 file (e.g. with ElevenLabs version)

Prerequisites:
    1. Run 01_generate_voice.py first (MP3 files must exist)
       — OR drop ElevenLabs MP3 files (same filenames) into output/voice/
    2. Run 02_generate_slides.py (intro/outro slides)
    3. Configure OBS to capture screen + desktop audio
    4. Start OBS recording, then run this script

Usage:
    .venv\\Scripts\\python.exe tools\\demo_v2\\03_teleprompter.py
    .venv\\Scripts\\python.exe tools\\demo_v2\\03_teleprompter.py --lang vi
    .venv\\Scripts\\python.exe tools\\demo_v2\\03_teleprompter.py --no-autoplay
"""
from __future__ import annotations

import argparse
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont
from typing import Optional

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.demo_v2.scene_config import SCENES, Scene  # noqa: E402


VOICE_DIR  = Path(__file__).resolve().parent / "output" / "voice"
SLIDES_DIR = Path(__file__).resolve().parent / "output" / "slides"
BUFFER_S   = 1.5   # extra time after voice ends before auto-advance


# ─── Audio playback (pygame) ─────────────────────────────────────────────────

class AudioPlayer:
    """Minimal MP3 player using pygame.mixer with playback-finished detection."""
    def __init__(self):
        self._ok = False
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._mixer = pygame.mixer
            self._ok = True
        except Exception as exc:
            print(f"[WARN] Audio init failed: {exc}")

    def play(self, mp3_path: Path):
        if not self._ok or not mp3_path.exists():
            return
        try:
            self._mixer.music.load(str(mp3_path))
            self._mixer.music.play()
        except Exception as exc:
            print(f"[WARN] Audio play failed: {exc}")

    def is_busy(self) -> bool:
        """True if music is currently playing (returns False on completion)."""
        if not self._ok:
            return False
        try:
            return self._mixer.music.get_busy()
        except Exception:
            return False

    def stop(self):
        if self._ok:
            try:
                self._mixer.music.stop()
            except Exception:
                pass


def _get_mp3_duration_s(mp3_path: Path) -> float:
    """Return MP3 playback duration in seconds. Falls back to file-size heuristic."""
    if not mp3_path.exists():
        return 0.0
    # Try pygame.mixer.Sound length (most accurate)
    try:
        import pygame
        # mixer should already be initialized
        snd = pygame.mixer.Sound(str(mp3_path))
        return snd.get_length()
    except Exception:
        pass
    # Heuristic fallback: ~128 kbps average for edge-tts MP3
    try:
        return mp3_path.stat().st_size / (128 * 1024 / 8)
    except Exception:
        return 0.0


# ─── Main teleprompter GUI ───────────────────────────────────────────────────

class Teleprompter(tk.Tk):
    def __init__(self, scenes: list[Scene], lang: str, autoplay: bool):
        super().__init__()
        self.scenes = scenes
        self.lang = lang
        self.autoplay = autoplay
        self.idx = 0
        self.playing = False
        self.scene_start_time: Optional[float] = None
        self.scene_duration_s: float = 0.0
        self.audio = AudioPlayer()
        self._after_id_tick: Optional[str] = None
        self._after_id_advance: Optional[str] = None

        self.title("Demo Recording Teleprompter v3")
        self.geometry("1024x780")
        self.configure(bg="#0d1117")

        # Fonts
        self.font_title    = tkfont.Font(family="Segoe UI", size=24, weight="bold")
        self.font_progress = tkfont.Font(family="Consolas", size=12)
        self.font_action   = tkfont.Font(family="Segoe UI", size=12)
        self.font_voice    = tkfont.Font(family="Segoe UI", size=12, slant="italic")
        self.font_button   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_timer    = tkfont.Font(family="Consolas", size=38, weight="bold")
        self.font_tt_req   = tkfont.Font(family="Segoe UI", size=10, weight="bold")

        self._build_ui()
        self._render_scene()

        # Keyboard shortcuts
        self.bind("<space>",     lambda e: self._on_play())
        self.bind("<Right>",     lambda e: self._on_next())
        self.bind("<Left>",      lambda e: self._on_prev())
        self.bind("<Escape>",    lambda e: self._cancel_recording())

    # ── UI ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top bar: title + progress
        top = tk.Frame(self, bg="#0d1117")
        top.pack(fill="x", padx=18, pady=(16, 8))
        self.title_lbl = tk.Label(
            top, text="", font=self.font_title, fg="#fe2c55", bg="#0d1117",
            anchor="w", justify="left",
        )
        self.title_lbl.pack(side="left")
        self.progress_lbl = tk.Label(
            top, text="", font=self.font_progress, fg="#888", bg="#0d1117",
        )
        self.progress_lbl.pack(side="right")

        # TikTok requirement badge
        self.tt_req_lbl = tk.Label(
            self, text="", font=self.font_tt_req,
            fg="#25f4ee", bg="#0d1117", anchor="w", justify="left", wraplength=980,
        )
        self.tt_req_lbl.pack(fill="x", padx=18, pady=(0, 4))

        # Middle: actions (left) + timer/voice (right)
        mid = tk.Frame(self, bg="#0d1117")
        mid.pack(fill="both", expand=True, padx=18, pady=8)

        # Left panel — action list
        left = tk.Frame(mid, bg="#161b22", bd=1, relief="solid")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        tk.Label(
            left, text=" ON-SCREEN ACTIONS",
            font=("Segoe UI", 10, "bold"), fg="#25f4ee", bg="#161b22",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))
        self.action_text = tk.Text(
            left, wrap="word", font=self.font_action,
            fg="#e0e0e0", bg="#161b22", bd=0, padx=12, pady=8,
            spacing1=3, spacing3=3,
        )
        self.action_text.pack(fill="both", expand=True, padx=4, pady=(0, 10))

        # Right panel — timer + voice text
        right = tk.Frame(mid, bg="#161b22", bd=1, relief="solid", width=380)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(
            right, text=" TIMING",
            font=("Segoe UI", 10, "bold"), fg="#25f4ee", bg="#161b22",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))

        self.timer_lbl = tk.Label(
            right, text="00:00", font=self.font_timer,
            fg="#fe2c55", bg="#161b22",
        )
        self.timer_lbl.pack(pady=4)

        self.duration_lbl = tk.Label(
            right, text="", font=self.font_progress,
            fg="#888", bg="#161b22",
        )
        self.duration_lbl.pack(pady=(0, 10))

        self.autoplay_lbl = tk.Label(
            right, text="", font=("Segoe UI", 10, "italic"),
            fg="#4caf50", bg="#161b22",
        )
        self.autoplay_lbl.pack(pady=(0, 8))

        tk.Label(
            right, text=" VOICE-OVER TEXT",
            font=("Segoe UI", 10, "bold"), fg="#25f4ee", bg="#161b22",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(10, 4))
        self.voice_text = tk.Text(
            right, wrap="word", font=self.font_voice,
            fg="#c8d0db", bg="#161b22", bd=0, padx=12, pady=8,
        )
        self.voice_text.pack(fill="both", expand=True, padx=4, pady=(0, 10))

        # Bottom: control bar
        bottom = tk.Frame(self, bg="#0d1117")
        bottom.pack(fill="x", padx=18, pady=(8, 16))

        self.prev_btn = tk.Button(
            bottom, text="◀  Previous", font=self.font_button,
            bg="#30363d", fg="#e0e0e0", activebackground="#444c56",
            bd=0, padx=16, pady=8, command=self._on_prev,
        )
        self.prev_btn.pack(side="left", padx=(0, 6))

        self.play_btn = tk.Button(
            bottom, text="▶  Play Voice + Start Timer  (Space)", font=self.font_button,
            bg="#1a7f37", fg="white", activebackground="#2da44e",
            bd=0, padx=16, pady=8, command=self._on_play,
        )
        self.play_btn.pack(side="left", padx=6)

        self.next_btn = tk.Button(
            bottom, text="Next ▶", font=self.font_button,
            bg="#fe2c55", fg="white", activebackground="#ff5478",
            bd=0, padx=16, pady=8, command=self._on_next,
        )
        self.next_btn.pack(side="right")

        # Note
        self.note_lbl = tk.Label(
            self, text="", font=("Segoe UI", 10, "italic"),
            fg="#ffb84d", bg="#0d1117", anchor="w", justify="left", wraplength=980,
        )
        self.note_lbl.pack(fill="x", padx=18, pady=(0, 8))

        # Footer help
        tk.Label(
            self, text="Shortcuts:  Space=Play  •  →=Next  •  ←=Previous  •  Esc=Cancel",
            font=("Segoe UI", 9), fg="#666", bg="#0d1117",
        ).pack(fill="x", padx=18, pady=(0, 8))

    def _render_scene(self):
        s = self.scenes[self.idx]
        self.title_lbl.config(text=s.title + ("  ⭐" if s.critical else ""))
        self.progress_lbl.config(text=f"Scene {self.idx+1}/{len(self.scenes)}   id={s.id}")

        # Measure actual MP3 duration
        mp3 = VOICE_DIR / f"{s.id}.mp3"
        mp3_dur = _get_mp3_duration_s(mp3)
        self.scene_duration_s = mp3_dur + BUFFER_S if mp3_dur > 0 else s.duration_s
        self.duration_lbl.config(
            text=f"Voice MP3: {mp3_dur:.1f}s + buffer {BUFFER_S:.0f}s = {self.scene_duration_s:.1f}s"
            if mp3_dur > 0
            else f"Planned: {s.duration_s:.0f}s (no MP3 file)"
        )

        # TT requirement badge
        self.tt_req_lbl.config(text=f"🎯 {s.tt_req}" if s.tt_req else "")

        # Action list
        self.action_text.config(state="normal")
        self.action_text.delete("1.0", "end")
        for i, action in enumerate(s.on_screen, 1):
            self.action_text.insert("end", f"{i:2}.  {action}\n")
        self.action_text.config(state="disabled")

        # Voice text
        text = s.voice_en if self.lang == "en" else (s.voice_vi or s.voice_en)
        self.voice_text.config(state="normal")
        self.voice_text.delete("1.0", "end")
        self.voice_text.insert("end", text)
        self.voice_text.config(state="disabled")

        # Note
        self.note_lbl.config(text="")

        # Reset timer
        self.timer_lbl.config(text="00:00", fg="#fe2c55")
        self.scene_start_time = None
        self.playing = False
        self.audio.stop()
        self._cancel_pending_after()

        # Autoplay indicator
        if self.autoplay:
            self.autoplay_lbl.config(text="⚡ Auto-advance ON")
        else:
            self.autoplay_lbl.config(text="(manual advance)")

        # Update buttons
        self.prev_btn.config(state="normal" if self.idx > 0 else "disabled")
        self.next_btn.config(
            text="Finish" if self.idx == len(self.scenes) - 1 else "Next ▶"
        )
        self.play_btn.config(text="▶  Play (Space)", bg="#1a7f37", state="normal")

    def _cancel_pending_after(self):
        for attr in ("_after_id_tick", "_after_id_advance"):
            aid = getattr(self, attr, None)
            if aid:
                try:
                    self.after_cancel(aid)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _voice_path(self) -> Path:
        return VOICE_DIR / f"{self.scenes[self.idx].id}.mp3"

    # ── Actions ───────────────────────────────────────────────────────────
    def _on_play(self):
        if self.playing:
            return
        mp3 = self._voice_path()
        if mp3.exists():
            self.audio.play(mp3)
        else:
            print(f"[WARN] Voice file not found: {mp3}")
        self.playing = True
        self.scene_start_time = time.perf_counter()
        self.play_btn.config(text="Recording...  ⏺", bg="#9a2a2f", state="disabled")
        self._tick_timer()

    def _tick_timer(self):
        if not self.playing or self.scene_start_time is None:
            return
        elapsed = time.perf_counter() - self.scene_start_time
        remaining = self.scene_duration_s - elapsed

        # Display timer
        if remaining < 0:
            self.timer_lbl.config(text=f"+{int(abs(remaining)):02d}s", fg="#ffb84d")
        else:
            self.timer_lbl.config(text=f"{int(remaining):02d}s", fg="#25f4ee")

        # Auto-advance when both:
        # (a) MP3 finished playing (audio.is_busy = False), AND
        # (b) buffer time has passed (current scene_duration_s)
        mp3_done = not self.audio.is_busy()
        timeup = elapsed >= self.scene_duration_s

        if self.autoplay and mp3_done and timeup:
            # Advance with small visual delay so user sees timer hit 0
            self._after_id_advance = self.after(200, self._auto_advance)
            return

        self._after_id_tick = self.after(100, self._tick_timer)

    def _auto_advance(self):
        if self.idx < len(self.scenes) - 1:
            self._on_next()
        else:
            # Finished — exit cleanly
            self._on_finish()

    def _on_next(self):
        self.audio.stop()
        self._cancel_pending_after()
        if self.idx < len(self.scenes) - 1:
            self.idx += 1
            self._render_scene()
            if self.autoplay:
                # Auto-start next scene after a brief moment
                self.after(800, self._on_play)
        else:
            self._on_finish()

    def _on_prev(self):
        self.audio.stop()
        self._cancel_pending_after()
        if self.idx > 0:
            self.idx -= 1
            self._render_scene()

    def _on_finish(self):
        self.audio.stop()
        self._cancel_pending_after()
        self.title_lbl.config(text="✅ Recording complete — STOP OBS now")
        self.play_btn.config(state="disabled")
        self.next_btn.config(state="disabled")
        self.timer_lbl.config(text="DONE", fg="#4caf50")
        # Auto-close after 5s
        self.after(5000, self.destroy)

    def _cancel_recording(self):
        self.audio.stop()
        self._cancel_pending_after()
        self.destroy()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Demo recording teleprompter")
    parser.add_argument("--lang", default="en", choices=["en", "vi"],
                        help="Voice/text language: en (default) or vi")
    parser.add_argument("--no-autoplay", action="store_true",
                        help="Disable auto-advance (user clicks Next manually)")
    args = parser.parse_args()

    # Verify voice files
    missing = [s.id for s in SCENES if not (VOICE_DIR / f"{s.id}.mp3").exists()]
    if missing:
        print(f"[WARN] Missing voice files: {missing}")
        print(f"      Run: .venv\\Scripts\\python.exe tools\\demo_v2\\01_generate_voice.py")

    app = Teleprompter(SCENES, lang=args.lang, autoplay=not args.no_autoplay)
    app.mainloop()


if __name__ == "__main__":
    main()
