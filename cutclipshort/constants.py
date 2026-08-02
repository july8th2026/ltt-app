"""App-wide constants, default paths, and limits."""

from __future__ import annotations

from pathlib import Path
import os

# ── Version ──────────────────────────────────────────────────────────────
APP_NAME = "LTT CUT SHORT"
APP_VERSION = "0.1.0"
APP_AUTHOR = "CutClipShort"

# ── Paths ────────────────────────────────────────────────────────────────
APP_DATA_DIR = Path(os.environ.get(
    "CUTCLIPSHORT_DATA_DIR",
    Path.home() / ".cutclipshort",
))
PROJECTS_DIR = APP_DATA_DIR / "projects"
ADAPTER_CACHE_DIR = APP_DATA_DIR / "adapter_cache"
APP_CONFIG_PATH = APP_DATA_DIR / "app_config.yaml"
RECENT_PROJECTS_PATH = APP_DATA_DIR / "recent_projects.json"

# ── Project Structure ────────────────────────────────────────────────────
PROJECT_FILE = "project.json"
PROJECT_SCHEMA_VERSION = 1

DIR_SOURCE = "source"
DIR_CACHE = "cache"
DIR_CANDIDATES = "candidates"
DIR_PLANS = "plans"
DIR_PREVIEWS = "previews"
DIR_THUMBNAILS = "thumbnails"
DIR_SEGMENTS = "segments"
DIR_AUDIO = "audio"
DIR_EXPORTS = "exports"
DIR_LOGS = "logs"

# ── Analysis ─────────────────────────────────────────────────────────────
DEFAULT_SCENE_THRESHOLD = 27.0
DEFAULT_MIN_SCENE_LEN_SEC = 1.5
DEFAULT_MOTION_SAMPLE_FPS = 5
DEFAULT_MOTION_RESIZE = (320, 180)
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_YOLO_MODEL = "yolov8n.pt"
DEFAULT_YOLO_CONF = 0.35
DEFAULT_YOLO_IMGSZ = 640

# ── Editorial ────────────────────────────────────────────────────────────
DEFAULT_MIN_CLIP_DURATION_SEC = 15.0
DEFAULT_MAX_CLIP_DURATION_SEC = 60.0
DEFAULT_TARGET_CLIP_COUNT = 5
DEFAULT_KEEP_RATIO = 0.97

# ── Render ───────────────────────────────────────────────────────────────
DEFAULT_CRF = "18"
DEFAULT_PREVIEW_CRF = "28"
DEFAULT_PREVIEW_HEIGHT = 480
DEFAULT_AUDIO_BITRATE = "192k"
DEFAULT_AUDIO_SAMPLE_RATE = 44100
DEFAULT_AUDIO_CHANNELS = 2
DEFAULT_XFADE_DURATION = 0.3
DEFAULT_LOUDNORM_LUFS = -14.0
DEFAULT_LOUDNORM_TRUE_PEAK_DB = -1.5

# ── Framing ──────────────────────────────────────────────────────────────
DEFAULT_PERSON_TARGET_FRACTION = 0.70
DEFAULT_SMOOTH_ALPHA = 0.07
DEFAULT_MAX_PAN_PX_PER_SEC = 900.0

# ── Evaluation ───────────────────────────────────────────────────────────
DEFAULT_QUALITY_GATE_THRESHOLD = 50.0  # 0-100 composite score

# ── Limits ───────────────────────────────────────────────────────────────
MAX_RECENT_PROJECTS = 20
MAX_PLAN_VERSIONS = 50
SOURCE_HASH_CHUNK_SIZE = 64 * 1024 * 1024  # 64 MB for partial hashing
PREVIEW_TIMEOUT_SEC = 30
RENDER_TIMEOUT_SEC = 300

# ── Job Queue ────────────────────────────────────────────────────────────
DEFAULT_MAX_WORKERS = 4
DEFAULT_IO_WORKERS = 2
