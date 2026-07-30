"""
Verify demo video — extract frames tại 14 timestamp quan trọng + show.

Usage:
    python scripts/_verify_demo_video.py "C:\\path\\to\\your_demo.mp4"

Hoặc gọi từ Claude với file path. Script extract 14 PNG vào folder
data/_verify_frames/ rồi báo lại — Claude đọc từng frame để verify.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)

# 14 cảnh BẮT BUỘC + timestamp (theo timing-reference)
SCENES = [
    ("01_opening",        "00:00:05", "Opening slide"),
    ("02_privacy_url",    "00:00:25", "Privacy URL trên browser"),
    ("02_terms_url",      "00:00:32", "Terms URL trên browser"),
    ("03_bot_overview",   "00:00:42", "9 tabs bot"),
    ("04a_continue_btn",  "00:00:52", "Nút 'Continue with TikTok' + logo"),
    ("04b_disclosure",    "00:00:58", "Pre-OAuth Disclosure Modal ⭐"),
    ("04c_tt_authorize",  "00:01:12", "TT authorize page (URL bar tiktok.com)"),
    ("04d_account_in_list", "00:01:28", "Account klcloset96 hiện trong list"),
    ("05_audit_dashboard", "00:01:38", "Audit Dashboard 11 ✅"),
    ("06_form_filled",     "00:02:00", "Manual TT form đã fill"),
    ("07a_dialog_open",    "00:02:18", "Consent dialog mở ra ⭐"),
    ("07b_privacy_dropdown", "00:02:25", "Privacy DROPDOWN (mở ra)"),
    ("07c_toggles_ai_branded", "00:02:32", "3 toggles + AI + Branded ⭐"),
    ("08_upload_success",  "00:02:55", "Upload thành công + video trên TT"),
    ("09_disconnect",      "00:03:08", "Disconnect/revoke flow"),
]


def have_ffmpeg() -> bool:
    """Check ffmpeg trên PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_frames(video_path: Path, out_dir: Path) -> list[tuple[str, Path, str]]:
    """Extract 14 frames tại các timestamp định nghĩa.

    Returns: list of (scene_id, frame_path, description)
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, Path, str]] = []

    for scene_id, ts, desc in SCENES:
        frame_file = out_dir / f"{scene_id}.png"
        # ffmpeg -ss <timestamp> -i <input> -frames:v 1 <output>
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", ts, "-i", str(video_path),
            "-frames:v", "1",
            # Resize xuống 1280x720 để tiết kiệm chỗ + Claude đọc nhanh
            "-vf", "scale=1280:720",
            str(frame_file),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=20, capture_output=True)
            results.append((scene_id, frame_file, desc))
            print(f"  ✅ {scene_id:<25}  @ {ts}  → {frame_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {scene_id}  @ {ts}  → FAIL: {e.stderr.decode()[:200]}")
            results.append((scene_id, None, desc))
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {scene_id}  @ {ts}  → TIMEOUT")
            results.append((scene_id, None, desc))
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/_verify_demo_video.py <path_to_demo.mp4>")
        sys.exit(2)

    video_path = Path(sys.argv[1])
    if not video_path.exists():
        print(f"❌ File không tồn tại: {video_path}")
        sys.exit(2)

    if not have_ffmpeg():
        print("❌ Thiếu ffmpeg trên PATH. Cài: https://ffmpeg.org/download.html")
        sys.exit(2)

    out_dir = ROOT / "data" / "_verify_frames"
    print(f"📹 Video: {video_path}")
    print(f"📁 Output: {out_dir}")
    print(f"🎬 Extract 14 frames…")
    print()

    results = extract_frames(video_path, out_dir)
    ok = sum(1 for _, p, _ in results if p is not None)
    print()
    print(f"📊 Extracted {ok}/{len(SCENES)} frames")
    print(f"📁 Đường dẫn folder: {out_dir}")
    print()
    print("Claude có thể đọc từng frame để verify nội dung.")


if __name__ == "__main__":
    main()
