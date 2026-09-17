"""YOLO adapter for object/person detection.

Wraps ultralytics YOLO with model caching and person detection helpers.
Ported from NerfWarAI's yolo_reframe.py model cache pattern.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cutclipshort.adapters.base import BaseAdapter
from cutclipshort.errors import AdapterError
from cutclipshort.types import PersonDetection

logger = logging.getLogger(__name__)

# Model cache — prevents repeated loads (thread-safe)
import threading
_MODEL_CACHE: dict[str, Any] = {}
_MODEL_LOCK = threading.Lock()


class YOLOAdapter(BaseAdapter):
    """Adapter for YOLO object detection."""

    def __init__(self, model_path: str = "yolov8n.pt") -> None:
        super().__init__()
        self._model_path = model_path

    @property
    def tool_name(self) -> str:
        """Return adapter tool name."""
        return "yolo"

    def _find_executable(self) -> str:
        return "yolo"  # Python library, not CLI

    def check_available(self) -> bool:
        """Check if ultralytics is installed."""
        try:
            import ultralytics  # noqa: F401
            return True
        except ImportError:
            return False

    def get_version(self) -> str | None:
        """Return ultralytics version string or None."""
        try:
            import ultralytics
            return f"ultralytics {ultralytics.__version__}"
        except (ImportError, AttributeError):
            return None

    def get_capabilities(self) -> dict[str, Any]:
        """Return availability and CUDA status."""
        caps: dict[str, Any] = {"available": self.check_available()}
        if caps["available"]:
            try:
                import torch
                caps["cuda"] = torch.cuda.is_available()
            except ImportError:
                caps["cuda"] = False
        return caps

    def set_model_path(self, model_path: str) -> None:
        """Update model path and clear old cache if model changed (thread-safe)."""
        if model_path != self._model_path:
            with _MODEL_LOCK:
                old_path = self._model_path
                if old_path in _MODEL_CACHE:
                    logger.info("Releasing YOLO model: %s", old_path)
                    del _MODEL_CACHE[old_path]
                self._model_path = model_path
            logger.info("YOLO model path updated: %s → %s", old_path, model_path)

    def _resolve_model_path(self) -> str:
        """Resolve model path: prefer bundled local model over auto-download.

        Search order:
        1. If self._model_path is an absolute path and exists, use it directly
        2. <app_root>/models/<model_name>  (bundled with exe)
        3. Fall back to original name (ultralytics will auto-download)
        """
        import sys

        model_name = self._model_path

        # Already an absolute/existing path
        if Path(model_name).is_absolute() and Path(model_name).exists():
            return model_name

        # Find app root (frozen exe or dev)
        if getattr(sys, "frozen", False):
            app_root = Path(sys.executable).parent
        else:
            app_root = Path(__file__).resolve().parent.parent.parent

        # Check bundled models/ directory
        bundled = app_root / "models" / model_name
        if bundled.exists() and bundled.stat().st_size > 1_000_000:
            logger.info("Using bundled YOLO model: %s", bundled)
            return str(bundled)

        return self._persistent_or_name(model_name)

    @staticmethod
    def _persistent_or_name(model_name: str, env: dict | None = None,
                            cwd: Path | None = None) -> str:
        """Weights outside the deploy tree, so they survive `app\\` being replaced.

        🔴 16/09/2026: on production the worker's cwd is `C:\\LTTPlatform\\app`, which
           every deploy deletes. `yolov8n.pt` is shipped there (VAN_CHUYEN) but
           `yolov8s.pt` (higher quality tiers) is not, so ultralytics downloaded
           21.5 MB from GitHub into `app\\` on the first job after EVERY deploy.

        ultralytics 8.4.115 `attempt_download_asset`: an absolute path that does not
        exist yet is downloaded TO that path (`safe_download(..., file=file)`), so
        returning `<dir>/<name>` makes the download happen once and persist.

        Order: a copy in cwd (shipped `yolov8n.pt`) wins; then
        `LTT_YOLO_WEIGHTS_DIR`, else `LTT_DATA_DIR/models/yolo`; no platform env
        (desktop/dev) keeps the old behaviour and returns the bare name.
        """
        import os

        e = os.environ if env is None else env
        here = Path.cwd() if cwd is None else cwd
        if (here / model_name).is_file():
            return model_name
        weights_dir = (e.get("LTT_YOLO_WEIGHTS_DIR") or "").strip()
        if not weights_dir and (e.get("LTT_DATA_DIR") or "").strip():
            weights_dir = str(Path(e["LTT_DATA_DIR"].strip()) / "models" / "yolo")
        if not weights_dir:
            return model_name
        target = Path(weights_dir) / Path(model_name).name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning("YOLO weights dir unusable (%s): %s", type(exc).__name__, target.parent)
            return model_name
        if not target.exists():
            logger.info("YOLO weights not cached, ultralytics will download once to %s", target)
        return str(target)

    def _get_model(self) -> Any:
        """Get or load YOLO model with thread-safe caching."""
        with _MODEL_LOCK:
            if self._model_path in _MODEL_CACHE:
                return _MODEL_CACHE[self._model_path]
            if not self.check_available():
                raise AdapterError(
                    "ultralytics not installed",
                    tool_name="yolo",
                )
            # Clear other cached models to save memory
            for key in list(_MODEL_CACHE.keys()):
                if key != self._model_path:
                    logger.info("Releasing unused YOLO model: %s", key)
                    del _MODEL_CACHE[key]
            from ultralytics import YOLO
            resolved_path = self._resolve_model_path()
            logger.info("Loading YOLO model: %s", resolved_path)
            _MODEL_CACHE[self._model_path] = YOLO(resolved_path)
        return _MODEL_CACHE[self._model_path]

    def detect(
        self,
        frame_or_path: Any,
        *,
        conf: float = 0.35,
        imgsz: int = 640,
        classes: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Run detection on a frame (numpy array) or image path.

        Returns list of detections with bbox, confidence, class info.
        """
        model = self._get_model()
        results = model.predict(
            frame_or_path,
            conf=conf,
            imgsz=imgsz,
            classes=classes,
            verbose=False,
        )

        detections = []
        for result in results:
            for box in result.boxes:
                detections.append({
                    "x": float(box.xyxy[0][0]),
                    "y": float(box.xyxy[0][1]),
                    "w": float(box.xyxy[0][2] - box.xyxy[0][0]),
                    "h": float(box.xyxy[0][3] - box.xyxy[0][1]),
                    "confidence": float(box.conf[0]),
                    "class_id": int(box.cls[0]),
                    "class_name": result.names[int(box.cls[0])],
                })
        return detections

    def detect_persons(
        self,
        frame_or_path: Any,
        *,
        conf: float = 0.35,
        imgsz: int = 640,
        min_area_ratio: float = 0.005,
    ) -> list[PersonDetection]:
        """Detect persons only (class 0) with false-positive filtering.

        Filters:
        1. Class 0 only (person in COCO)
        2. Confidence >= conf threshold
        3. Bounding box area >= min_area_ratio of frame (rejects tiny detections)
        4. Aspect ratio sanity: height > width * 0.5 (humans are taller than wide)

        Returns sorted by area descending (largest person first).
        """
        raw = self.detect(
            frame_or_path,
            conf=conf,
            imgsz=imgsz,
            classes=[0],  # person class
        )

        # Frame area for ratio filtering
        frame_area = imgsz * imgsz  # Approximate (YOLO resizes to imgsz)

        persons = []
        for d in raw:
            w, h = d["w"], d["h"]
            area = w * h

            # Filter 1: too small (noise, far-away objects)
            if area < frame_area * min_area_ratio:
                continue

            # Filter 2: aspect ratio sanity (person should be taller than wide,
            # or at least not extremely horizontal like a bag/furniture)
            if h < w * 0.4:
                continue  # Very horizontal → likely not a standing/sitting person

            persons.append(PersonDetection(
                x=d["x"], y=d["y"], w=w, h=h,
                confidence=d["confidence"],
            ))

        # Sort by area descending (largest person first)
        persons.sort(key=lambda p: p.area, reverse=True)
        return persons
