import cv2
from ...tuong_thich.log import info
from ...tuong_thich.ffmpeg import probe_duration

def _motion_score(video_path: str, sample_fps: int=2) -> float:
    dur = probe_duration(video_path)
    cap = cv2.VideoCapture(video_path)
    try:
        step = max(1.0/sample_fps, 0.2)
        prev = None
        scores = []
        t = 0.0
        while t < min(dur, 8.0):
            cap.set(cv2.CAP_PROP_POS_MSEC, t*1000.0)
            ok, frame = cap.read()
            if not ok: break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                diff = cv2.absdiff(prev, gray)
                scores.append(float(diff.mean()))
            prev = gray
            t += step
        return float(sum(scores)/len(scores)) if scores else 0.0
    finally:
        cap.release()

def _auto_threshold(scores: list[float]) -> float:
    # conservative: drop bottom ~10%
    if not scores: return 0.0
    s = sorted(scores)
    k = max(1, int(len(s)*0.10))
    return s[k-1]

def filter_by_motion(cfg: dict, clips: list[dict]) -> list[dict]:
    fcfg = cfg.get("filters", {})
    if not fcfg.get("enable_motion", True):
        return clips
    sample_fps = int(cfg.get("clip", {}).get("uniform_fps", 2))
    for c in clips:
        # Dùng file_abs (absolute path) nếu có, fallback sang file (relative)
        video_path = c.get("file_abs") or c["file"]
        c["motion_score"] = _motion_score(video_path, sample_fps=sample_fps)
    scores = [c["motion_score"] for c in clips]
    thr = fcfg.get("motion_threshold", None)
    if thr is None:
        thr = _auto_threshold(scores)
    kept = [c for c in clips if c["motion_score"] >= float(thr)]
    info("motion_filter", threshold=float(thr), kept=len(kept), total=len(clips))
    return kept if kept else clips  # never drop all
