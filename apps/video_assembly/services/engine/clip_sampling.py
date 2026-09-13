import os, json, math, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
from PIL import Image
from ..tuong_thich.log import info, warn, exc
from ..tuong_thich.paths import ensure_dir
from ..tuong_thich.ffmpeg import probe_duration


# Default clip config (engine-side fallback)
_DEFAULT_CLIP_CFG = {
    "uniform_fps": 2,
    "sampling": "motion_peak",  # "motion_peak" | "middle" | ...
}


def _extract_frame_ffmpeg(video_path: str, t: float, out_png: str) -> bool:
    """Extract a single frame; return True on success, False on failure (do not crash whole job)."""
    cmd = ["ffmpeg","-y","-hide_banner","-loglevel","error","-i", video_path, "-ss", f"{t:.3f}", "-frames:v","1", "-q:v","2", out_png]
    # [Phase 7] timeout=30s — extract 1 frame phải < 5s, > 30s = chắc chắn hang
    try:
        p = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        try:
            if os.path.exists(out_png):
                os.remove(out_png)
        except Exception:
            pass
        warn("clip_sampling_extract_timeout", video=video_path, t=round(float(t), 3))
        return False
    if p.returncode != 0:
        try:
            if os.path.exists(out_png):
                os.remove(out_png)
        except Exception:
            pass
        warn("clip_sampling_extract_failed", video=video_path, t=round(float(t),3), err=(p.stdout or "").strip()[:400])
        return False
    return True


def _motion_peak_time(video_path: str, sample_fps: int=2) -> float:
    dur = probe_duration(video_path)
    if dur <= 0.1:
        return 0.0
    cap = cv2.VideoCapture(video_path)
    try:
        step = max(1.0/sample_fps, 0.2)
        prev = None
        best = (0.0, 0.0)  # (score, time)
        t = 0.0
        while t < min(dur, 8.0):
            cap.set(cv2.CAP_PROP_POS_MSEC, t*1000.0)
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                diff = cv2.absdiff(prev, gray)
                score = float(diff.mean())
                if score > best[0]:
                    best = (score, t)
            prev = gray
            t += step
        return float(best[1])
    finally:
        cap.release()


def sample_clip_frames(cfg: dict, video_dir: str, out_dir: str) -> list[dict]:
    ensure_dir(out_dir)
    clip_files = [f for f in os.listdir(video_dir) if f.lower().endswith(".mp4")]
    clip_files.sort()

    # ✅ Robust: avoid KeyError if 'clip' is missing in cfg
    ccfg = cfg.get("clip")
    if not isinstance(ccfg, dict):
        warn("clip_sampling_missing_clip_cfg", err="cfg['clip'] missing; using engine defaults", default=_DEFAULT_CLIP_CFG)
        ccfg = dict(_DEFAULT_CLIP_CFG)
    else:
        # merge defaults (do not overwrite existing)
        merged = dict(_DEFAULT_CLIP_CFG)
        merged.update(ccfg)
        ccfg = merged

    sample_fps = int(ccfg.get("uniform_fps", 2))
    sampling_mode = (ccfg.get("sampling") or "motion_peak").strip().lower()

    items = []

    # DEBUG: Log video_dir for troubleshooting
    max_workers = int(cfg.get("clip", {}).get("parallel_workers", 6))
    info(
        "clip_sampling_start",
        video_dir=video_dir,
        video_dir_abs=os.path.abspath(video_dir),
        total_files=len(clip_files),
        sampling=sampling_mode,
        uniform_fps=sample_fps,
        parallel_workers=max_workers,
    )

    video_dir_basename = os.path.basename(video_dir)

    def _process_one_clip(f):
        """Process a single clip: probe → sample → extract frame. Thread-safe."""
        vp = os.path.join(video_dir, f)
        dur = probe_duration(vp)
        if dur <= 0.05:
            return None  # skip bad duration

        if sampling_mode == "motion_peak":
            t = _motion_peak_time(vp, sample_fps=sample_fps)
        elif sampling_mode == "middle":
            t = max(0.0, dur / 2.0)
        else:
            t = max(0.0, min(1.0, dur / 2.0))

        frame_path = os.path.join(out_dir, os.path.splitext(f)[0] + ".png")
        ok = _extract_frame_ffmpeg(vp, t, frame_path)
        if not ok:
            return None

        rel_path = os.path.join(video_dir_basename, f)
        return {
            "file": rel_path,
            "file_abs": vp,
            "name": f,
            "duration": dur,
            "sample_t": t,
            "frame": frame_path,
            "motion_score": None,
            "phash": None,
            "yolo_ok": True,
            "feat": None,
            "used": 0,
        }

    # ── Parallel processing ──
    # Each worker: probe_duration (ffprobe) + motion_peak (cv2) + extract_frame (ffmpeg)
    # All are I/O-bound subprocess calls → ThreadPoolExecutor is ideal
    # [Phase 9] Collect failures (None result HOẶC exception) → raise nếu có miss.
    # Trước đây silent skip → sequential_timeline báo "thiếu video" 30 phút sau.
    results_map = {}  # index → result, to preserve original order
    failures: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {pool.submit(_process_one_clip, f): i for i, f in enumerate(clip_files)}
        done_count = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            done_count += 1
            fname = clip_files[idx]
            try:
                result = future.result()
                if result is not None:
                    results_map[idx] = result
                else:
                    # _process_one_clip trả None khi probe_duration fail HOẶC extract fail
                    failures.append({"file": fname, "error": "probe<0.05s or extract failed"})
                    warn("clip_sampling_clip_dropped", file=fname,
                         reason="probe_duration_or_extract_failed")
            except Exception as e:
                failures.append({"file": fname, "error": str(e)[:300]})
                warn("clip_sampling_worker_error", file=fname, error=str(e)[:200])
            # Progress log every 20 clips
            if done_count % 20 == 0 or done_count == len(clip_files):
                info("clip_sampling_progress",
                     done=done_count, total=len(clip_files), failed=len(failures))

    # Rebuild items list in original sorted order
    for idx in sorted(results_map.keys()):
        items.append(results_map[idx])

    # DEBUG: Log first 3 clips
    for item in items[:3]:
        info(
            "clip_sample_added",
            name=item["name"],
            rel_path=item["file"],
            abs_path=item["file_abs"],
            duration=round(item["duration"], 2),
            sample_t=round(float(item["sample_t"]), 3),
        )

    # [Phase 9] FAIL LOUD nếu có file bị drop — đối xứng với fix sanitize_folder.
    # Engine sau (sequential_timeline) sẽ không biết "thiếu video do drop ở sampling"
    # vs "thiếu video gốc" → phải báo chính xác stage này.
    if failures:
        info(
            "clip_sampling_dropped_files",
            total=len(clip_files),
            ok=len(items),
            failed=len(failures),
            failed_files=[f["file"] for f in failures],
        )
        names = ", ".join(f["file"] for f in failures[:5])
        if len(failures) > 5:
            names += f" ... (+{len(failures) - 5} more)"
        raise RuntimeError(
            f"clip_sampling: {len(failures)}/{len(clip_files)} files failed. "
            f"Failed: [{names}]. First error: {failures[0]['error']}"
        )

    info("clip_sampling_done", clips=len(items))
    return items
