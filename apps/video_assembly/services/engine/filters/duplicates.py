from PIL import Image
import imagehash
from ...tuong_thich.log import info
from collections import deque

def filter_duplicates(cfg: dict, clips: list[dict]) -> list[dict]:
    fcfg = cfg.get("filters", {})
    if not fcfg.get("enable_duplicates", True):
        return clips
    thr = int(fcfg.get("duplicate_phash_threshold", 5))
    seen = deque(maxlen=int(fcfg.get('duplicate_window',50)))
    kept = []
    for c in clips:
        h = imagehash.phash(Image.open(c["frame"]).convert("RGB"))
        c["phash"] = str(h)
        is_dup = False
        for sh in seen:
            if (h - sh) <= thr:
                is_dup = True
                break
        if not is_dup:
            kept.append(c)
            seen.append(h)
    info("dup_filter", kept=len(kept), total=len(clips), thr=thr)
    return kept if kept else clips
