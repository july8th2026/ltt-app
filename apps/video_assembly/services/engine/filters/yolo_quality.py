import os
from ...tuong_thich.log import info, exc

def filter_by_yolo(cfg: dict, clips: list[dict]) -> list[dict]:
    fcfg = cfg.get("filters", {})
    if not fcfg.get("enable_yolo", False):
        return clips
    model_path = fcfg.get("yolo_model_path","") or os.environ.get("YOLO_MODEL_PATH","")
    if not model_path:
        info("yolo_skip", reason="no model path")
        return clips
    try:
        from ultralytics import YOLO
        model = YOLO(model_path)
        kept=[]
        for c in clips:
            res = model.predict(source=c["frame"], verbose=False)
            ok = True
            if res and hasattr(res[0], "boxes") and res[0].boxes is not None:
                ok = len(res[0].boxes) > 0
            c["yolo_ok"] = ok
            kept.append(c)
        ok_count = sum(1 for c in kept if c.get("yolo_ok"))
        info("yolo_filter", ok=ok_count, total=len(clips))
        return kept if kept else clips
    except Exception as e:
        exc("yolo_filter_failed_skip", e)
        return clips
