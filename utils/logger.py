import logging
import os
import re
from collections import deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from threading import Lock

# ─── Sensitive data redaction ─────────────────────────────────────────────────
# Patterns that must NEVER appear in log files.
# Each pattern is replaced with the corresponding redacted label.
_REDACT_RULES: list[tuple[re.Pattern, str]] = [
    # Bearer token in Authorization header
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]{10,}", re.IGNORECASE), "Bearer ***"),
    # access_token key-value (JSON, query string, or keyword arg)
    (re.compile(r'access_token["\':\s=]+[A-Za-z0-9._\-]{10,}', re.IGNORECASE),
     "access_token=***"),
    # refresh_token key-value
    (re.compile(r'refresh_token["\':\s=]+[A-Za-z0-9._\-]{10,}', re.IGNORECASE),
     "refresh_token=***"),
    # client_secret key-value
    (re.compile(r'client_secret["\':\s=]+[A-Za-z0-9._\-]{10,}', re.IGNORECASE),
     "client_secret=***"),
    # TikTok open_id (format: "open_id": "xxx") — not a token but PII
    # Intentionally NOT redacted — needed for debugging account issues.
]


def _redact(text: str) -> str:
    """Replace sensitive patterns in *text* with redacted placeholders."""
    for pattern, replacement in _REDACT_RULES:
        text = pattern.sub(replacement, text)
    return text


# Keys that must never appear in raw form when an API response dict is
# stringified for logging or exception messages.
_SENSITIVE_RESPONSE_KEYS = frozenset({
    "access_token", "refresh_token", "client_secret", "open_id",
    "code", "code_verifier", "code_challenge", "upload_url",
})


def safe_response_repr(payload, *, max_len: int = 300) -> str:
    """
    Render an API response dict for inclusion in logs/exceptions with all
    sensitive fields ([[redacted]]). Non-dict inputs are passed through
    str() and still scrubbed by the regex redaction layer.
    """
    if isinstance(payload, dict):
        scrubbed = {
            k: ("***" if k in _SENSITIVE_RESPONSE_KEYS else v)
            for k, v in payload.items()
        }
        text = str(scrubbed)
    else:
        text = str(payload)
    text = _redact(text)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _setup_file_logger(log_dir: str = "logs") -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")
    logger = logging.getLogger("FacebookBot")
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


# Global in-memory ring-buffer shared across all BotLogger instances.
# Allows MonitorTab to display recent activity without reading the log file.
_GLOBAL_BUFFER: deque = deque(maxlen=500)
_GLOBAL_LOCK = Lock()


class BotLogger:
    ICONS: dict[str, str] = {
        "info":    "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error":   "❌",
        "debug":   "🔍",
        "upload":  "📤",
        "browser": "🌐",
        "login":   "🔐",
        "wait":    "⏳",
        "done":    "🏁",
        "video":   "🎬",
        "link":    "🔗",
        "retry":   "🔄",
        "page":    "📄",
        "thumb":   "🖼",
        "fb":      "📘",
        "sheet":   "📊",
        "drive":   "☁️",
        "queue":   "📋",
    }

    def __init__(self, callback=None, log_dir: str = "logs"):
        self._callback = callback
        self._file_logger = _setup_file_logger(log_dir)

    def _emit(self, level: str, msg: str) -> str:
        icon = self.ICONS.get(level, "•")
        ts = datetime.now().strftime("%H:%M:%S")
        # Redact sensitive data BEFORE writing to any output
        safe_msg = _redact(str(msg))
        formatted = f"[{ts}] {icon} {safe_msg}"
        self._file_logger.info(formatted)
        # Append to global ring-buffer (skip debug to keep buffer clean)
        if level != "debug":
            with _GLOBAL_LOCK:
                _GLOBAL_BUFFER.append({"ts": ts, "level": level, "msg": safe_msg,
                                        "formatted": formatted})
        if self._callback:
            self._callback(formatted, level)
        return formatted

    def info(self, msg: str)    -> str: return self._emit("info",    msg)
    def success(self, msg: str) -> str: return self._emit("success", msg)
    def warning(self, msg: str) -> str: return self._emit("warning", msg)
    def error(self, msg: str)   -> str: return self._emit("error",   msg)
    def debug(self, msg: str)   -> str: return self._emit("debug",   msg)
    def upload(self, msg: str)  -> str: return self._emit("upload",  msg)
    def browser(self, msg: str) -> str: return self._emit("browser", msg)
    def login(self, msg: str)   -> str: return self._emit("login",   msg)
    def wait(self, msg: str)    -> str: return self._emit("wait",    msg)
    def done(self, msg: str)    -> str: return self._emit("done",    msg)
    def video(self, msg: str)   -> str: return self._emit("video",   msg)
    def link(self, msg: str)    -> str: return self._emit("link",    msg)
    def retry(self, msg: str)   -> str: return self._emit("retry",   msg)
    def page(self, msg: str)    -> str: return self._emit("page",    msg)
    def thumb(self, msg: str)   -> str: return self._emit("thumb",   msg)
    def fb(self, msg: str)      -> str: return self._emit("fb",      msg)
    def sheet(self, msg: str)   -> str: return self._emit("sheet",   msg)
    def drive(self, msg: str)   -> str: return self._emit("drive",   msg)
    def queue(self, msg: str)   -> str: return self._emit("queue",   msg)


def get_recent_logs(n: int = 100) -> list[dict]:
    """Return the last *n* log entries from the global ring-buffer."""
    with _GLOBAL_LOCK:
        entries = list(_GLOBAL_BUFFER)
    return entries[-n:]
