"""
ui_constants.py — exact labels, colours and enums lifted from the desktop UI.

Ported verbatim from `gui/` so the web reproduces the desktop rather than an
approximation of it. Every value here has a cited source. When the desktop
and this file disagree, the desktop is right and this file is the bug.

Sources:
  gui/main_window.py      — tab list, status bar
  gui/sheet_runner_tab.py — card titles, worker columns, state colours
  gui/result_tabs.py      — log levels, result statuses, worker colours
  gui/operation_tab.py    — manual-publish cards, privacy + post-type enums
"""
from __future__ import annotations

# ── Palette (gui/*, verbatim hex) ─────────────────────────────────────────────
COLORS = {
    "page_bg":        "#0d1117",   # action bar, list bodies
    "tab_bg":         "#161b22",   # main tabview content
    "result_tab_bg":  "#111827",   # ResultTabs content
    "card":           "#1a1f2e",
    "card_header":    "#1e2640",
    "table_header":   "#1a2744",
    "border":         "#2d3748",
    "muted":          "#4a5568",
    "muted2":         "#6B7280",
    "row_even":       "#161b22",
    "row_odd":        "#0f1419",
    "text":           "#D0D8E4",
    "col_header":     "#90CAF9",
    "sheet_alias":    "#E8C547",
    "filename":       "#B0BEC5",
    "link":           "#64B5F6",
    "link_hover":     "#90CAF9",
    "brand":          "#4A90D9",
    "footer":         "#3d4a5c",
    "green":          "#4CAF50",
    "amber":          "#FF9800",
    "red":            "#F44336",
    "blue":           "#2196F3",
    "fb":             "#1565C0",
    "fb_hover":       "#1976D2",
    "tt":             "#6A0DAD",
    "tt_hover":       "#7B1FA2",
    "add":            "#1B5E20",
    "add_hover":      "#2E7D32",
    "danger":         "#7F1D1D",
    "danger_hover":   "#991B1B",
    "ghost":          "#37474F",
    "ghost_hover":    "#546E7A",
    "blink_dim":      "#1a3a1a",
    "idle_dot":       "#2d3748",
}

# ── Card accents / titles (gui/sheet_runner_tab.py) ───────────────────────────
SHEET_CARDS = (
    ("workers", "⚙️  WORKERS (đa sheet / tab / page)", "#1565C0"),
    ("status",  "📡  TRẠNG THÁI HIỆN TẠI",             "#00695C"),
    ("queue",   "📋  HÀNG ĐỢI (xem trước)",            "#6A1B9A"),
)

# Worker-list column headers. The account column label differs per platform.
SHEET_WORKER_COLUMNS = ("●", "Sheet", "Tab", "{account}", "Trạng thái")
ACCOUNT_COL_HEADER = {"facebook": "Page FB", "tiktok": "TikTok Account"}
ACCOUNT_SELECTOR_LABEL = {"facebook": "Page:", "tiktok": "TT Account:"}

QUEUE_COLUMNS = ("#", "Hàng", "Tiêu đề", "Schedule")

MAX_WORKERS = 20          # gui/sheet_runner_tab.py::_MAX_WORKERS

# ── Worker states (gui/sheet_runner_tab.py::_WORKER_STATE_COLORS) ─────────────
WORKER_STATE_COLORS = {
    "idle":       "#4a5568",
    "connecting": "#FF9800",
    "running":    "#4CAF50",
    "stopping":   "#FF9800",
    "stopped":    "#6B7280",
    "error":      "#F44336",
}
WORKER_STATE_DEFAULT_COLOR = "#4a5568"

WORKER_STATE_TEXT = {
    "idle":       "⏸ Sẵn sàng",
    "connecting": "🔌 Kết nối...",
    "running":    "▶ Đang chạy",
    "waiting":    "⏳ Chờ job",
}

# ── Log levels (gui/result_tabs.py::LOG_COLORS) ───────────────────────────────
LOG_COLORS = {
    "success": "#4CAF50", "done": "#4CAF50",
    "error":   "#F44336",
    "warning": "#FF9800", "warn": "#FF9800", "wait": "#FF9800", "retry": "#FF9800",
    "upload":  "#2196F3", "browser": "#2196F3",
    "login":   "#9C27B0", "profile": "#9C27B0",
    "link":    "#00BCD4", "video": "#00BCD4",
    "page":    "#4A90D9", "fb": "#4A90D9",
    "thumb":   "#FF7043",
    "info":    "#FFFFFF",
    "debug":   "#9E9E9E",
    "sheet":   "#4A90D9",
    "queue":   "#00BCD4",
    "drive":   "#00BCD4",
}
LOG_LEVEL_DEFAULT_COLOR = "#FFFFFF"

# Per-worker log colours, cycling for W7+ (gui/result_tabs.py::WORKER_COLORS)
WORKER_LOG_COLORS = ("#00BCD4", "#8BC34A", "#FF9800", "#E91E63", "#CE93D8", "#03A9F4")

# Log filter buttons and the levels each one shows (_FILTER_LEVELS)
LOG_FILTERS = (
    ("all",   "Tất cả", None),
    ("ok",    "✅ OK",  ("success", "done", "link", "video", "upload", "fb", "page")),
    ("error", "❌ Lỗi", ("error",)),
    ("warn",  "⚠️ Warn", ("warning", "warn", "wait", "retry")),
)

MAX_LOG_LINES = 500       # gui/result_tabs.py
MAX_RESULT_ROWS = 1000

# ── Result statuses (gui/result_tabs.py) ──────────────────────────────────────
STATUS_LABELS = {
    "success": "✅ Thành công",
    "error":   "❌ Lỗi",
    "stopped": "⏸ Dừng",
    "running": "⏳ Đang chạy",
    "pending": "🕐 Chờ",
}
STATUS_COLORS = {
    "success": "#4CAF50",
    "error":   "#F44336",
    "stopped": "#FF9800",
    "running": "#2196F3",
    "pending": "#9E9E9E",
}
STATUS_DEFAULT_COLOR = "#FFFFFF"

RESULT_COLUMNS = ("#", "Page", "File video", "Trạng thái", "Link", "Giờ")

# ── Manual publish (gui/operation_tab.py) ─────────────────────────────────────
# Labels are hardcoded Vietnamese in the desktop source (never translated).
PRIVACY_OPTIONS = (
    ("Công khai", "EVERYONE"),
    ("Bạn bè",    "FRIENDS"),
    ("Riêng tư",  "SELF"),
)
PRIVACY_DEFAULT_LABEL = "Công khai"
PRIVACY_FALLBACK_ENUM = "SELF"          # unknown label -> safest option

TIKTOK_POST_OPTIONS = (
    ("Draft — Inbox (an toàn)",        "tiktok_draft",  ""),
    ("Direct — Riêng tư (SELF_ONLY)",  "tiktok_direct", "SELF_ONLY"),
    ("Direct — Người theo dõi",        "tiktok_direct", "FOLLOWER_OF_CREATOR"),
    ("Direct — Công khai (cần audit)", "tiktok_direct", "PUBLIC_TO_EVERYONE"),
)
TIKTOK_POST_DEFAULT_LABEL = "Draft — Inbox (an toàn)"
TIKTOK_AUDIT_HINT = "⚠ App chưa qua audit — chỉ Draft & Private"

VIDEO_EXTS_FB = (".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm", ".m4v")
VIDEO_EXTS_TT = (".mp4", ".mov", ".webm")
IMAGE_EXTS    = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

FB_MAX_VIDEO_BYTES = 10 * 1024 ** 3     # Graph API limit
TT_MAX_VIDEO_BYTES = 4 * 1024 ** 3
TT_MAX_DURATION_S  = 600
FB_TITLE_LIMIT = 100
FB_DESC_LIMIT  = 5000
TT_CAPTION_LIMIT = 2200

# TikTok privacy labels shown in the consent dialog
TIKTOK_PRIVACY_LABELS = {
    "SELF_ONLY":             "🔒  Chỉ mình tôi xem (SELF_ONLY)",
    "MUTUAL_FOLLOW_FRIENDS": "🤝  Bạn bè chung (MUTUAL_FRIEND_FRIENDS)",
    "FOLLOWER_OF_CREATOR":   "👥  Người theo dõi (FOLLOWER_OF_CREATOR)",
    "PUBLIC_TO_EVERYONE":    "🌐  Công khai (PUBLIC_TO_EVERYONE)",
}


def log_colour(level: str, message: str = "") -> str:
    """Colour for a log line, reproducing gui/result_tabs.py::_pick_tag.

    A line starting with "[W<n>]" gets a per-worker colour cycling every 6
    workers; otherwise the level decides.
    """
    import re
    m = re.match(r"\[W(\d+)\]", message or "")
    if m:
        idx = (int(m.group(1)) - 1) % len(WORKER_LOG_COLORS)
        return WORKER_LOG_COLORS[idx]
    return LOG_COLORS.get((level or "").lower(), LOG_LEVEL_DEFAULT_COLOR)


def is_worker_line(message: str) -> bool:
    import re
    return bool(re.match(r"\[W(\d+)\]", message or ""))


def severity_prefix(level: str) -> str:
    """Severity marker for a worker log line (gui/result_tabs.py::
    _severity_prefix).

    A `[W3] Lỗi ...` line is coloured by worker, not by level, so without this
    marker an error inside a worker line is indistinguishable from routine
    chatter. The desktop added it for exactly that reason; it must not be lost
    on the web, where the log is the only window into a running job.
    """
    lvl = (level or "").lower()
    if lvl == "error":
        return "✖ "
    if lvl in ("warning", "warn"):
        return "⚠ "
    return ""


def worker_state_view(state: str, current_job: str = "", last_msg: str = "",
                      jobs_done: int = 0, jobs_error: int = 0) -> tuple:
    """(text, colour) for a worker row — mirrors _on_worker_update."""
    colour = WORKER_STATE_COLORS.get(state, WORKER_STATE_DEFAULT_COLOR)
    if state == "running":
        text = f"▶ {current_job[:14]}" if current_job else (last_msg[:16] or state)
    elif state == "stopped":
        text = f"⏹ {jobs_done}✓ {jobs_error}✗"
    elif state == "error":
        text = f"❌ {last_msg[:14]}"
    elif state in WORKER_STATE_TEXT:
        text = WORKER_STATE_TEXT[state]
    else:
        text = last_msg[:16] or state
    return text, colour
