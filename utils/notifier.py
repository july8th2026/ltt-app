"""
Telegram notification helper.

Sends bot messages via the Telegram Bot API (no extra dependencies — uses
urllib from stdlib).

Architecture (P1 upgrade):
  - Single background sender thread drains a bounded Queue (maxsize=50).
  - `_send_async()` does non-blocking queue.put_nowait(); drops silently if full
    (flood protection when many workers fail simultaneously).
  - Rate-limit sleep is inside the sender thread — no lock held while sleeping.

Config keys (all optional — notifier silently does nothing if bot_token is empty):
    telegram_bot_token      : "123456:ABC-DEF..."
    telegram_chat_id        : "-100123456789"
    notify_on_error         : true/false   (default true)
    notify_on_token_expiry  : true/false   (default true)
    notify_on_complete      : true/false   (default false)
"""
from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_NOTIFIER: Optional["TelegramNotifier"] = None
_NOTIFIER_LOCK = threading.Lock()

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Rate-limit: at most 1 message per 3 s (Telegram limits ~30 msg/s to group)
_MIN_SEND_INTERVAL_S = 3.0

# P3: characters that must be escaped in MarkdownV2 content (not in format markers)
_MD2_ESCAPE_RE = re.compile(r'([_\[\]()~>#\+\-=|{}.!\\])')


def _escape_md2(text: str) -> str:
    """Escape special chars inside user-supplied content for MarkdownV2."""
    return _MD2_ESCAPE_RE.sub(r'\\\1', str(text))


class TelegramNotifier:
    """
    Sends Telegram messages via Bot API using stdlib urllib.
    P1: single sender thread + bounded queue (maxsize=50) replaces thread-per-message.
    P3: MarkdownV2 parse mode with proper escaping.
    """

    def __init__(self, config: dict):
        self._token    = str(config.get("telegram_bot_token", "")).strip()
        self._chat_id  = str(config.get("telegram_chat_id",  "")).strip()
        self._on_error    = bool(config.get("notify_on_error",        True))
        self._on_expiry   = bool(config.get("notify_on_token_expiry", True))
        self._on_complete = bool(config.get("notify_on_complete",     False))
        self._last_sent   = 0.0
        self._enabled     = bool(self._token and self._chat_id)

        # P1: bounded queue + single sender thread
        self._queue: queue.Queue[str] = queue.Queue(maxsize=50)
        self._sender_thread = threading.Thread(
            target=self._sender_loop, daemon=True, name="TelegramSender"
        )
        self._sender_thread.start()

    # ── Public notification helpers ───────────────────────────────────────────

    def notify_token_expiry(self, account_name: str, days_left: int):
        if not self._on_expiry:
            return
        emoji = "⚠️" if days_left > 3 else "🔴"
        name = _escape_md2(account_name)
        self._send_async(
            f"{emoji} *Token sắp hết hạn*\n"
            f"Tài khoản: `{name}`\n"
            f"Còn lại: *{days_left} ngày*\n"
            f"→ Vào tab Tài khoản FB để làm mới\\."
        )

    def notify_token_expired(self, account_name: str):
        if not self._on_expiry:
            return
        name = _escape_md2(account_name)
        self._send_async(
            f"❌ *Token đã hết hạn*\n"
            f"Tài khoản: `{name}`\n"
            f"Bot đã dừng upload cho tài khoản này\\.\n"
            f"→ Kết nối lại ngay\\!"
        )

    def notify_job_error(self, page_name: str, row_idx: int, error: str):
        if not self._on_error:
            return
        page = _escape_md2(page_name)
        short_err = _escape_md2(error[:200])
        self._send_async(
            f"⚠️ *Lỗi upload*\n"
            f"Page: `{page}`  •  Row: \\#{row_idx}\n"
            f"```\n{short_err}\n```"
        )

    def notify_worker_crash(self, worker_idx: int, error: str):
        if not self._on_error:
            return
        short_err = _escape_md2(error[:200])
        self._send_async(
            f"💥 *Worker W{worker_idx} crash*\n"
            f"```\n{short_err}\n```"
        )

    def notify_batch_done(self, jobs_done: int, jobs_error: int):
        if not self._on_complete:
            return
        self._send_async(
            f"✅ *Batch hoàn tất*\n"
            f"Thành công: *{jobs_done}*\n"
            f"Lỗi: *{jobs_error}*"
        )

    # ── Anti-Spam alerts (GAP-7) — routed via notify_on_error so they share
    # the same enable toggle as other operational warnings. ─────────────────

    def notify_circuit_open(self, target: str, cooldown_s: float):
        """Circuit breaker tripped for *target* — bot is auto-pausing."""
        if not self._on_error:
            return
        t = _escape_md2(target)
        mins = max(1, int(cooldown_s / 60))
        self._send_async(
            f"⏸ *Circuit breaker OPEN*\n"
            f"Target: `{t}`\n"
            f"Bot tạm dừng *{mins} phút* để tránh leo thang lỗi\\."
        )

    def notify_abuse_signal(self, target: str, error_code: str, message: str):
        """FB returned an abuse-grade error (368, 322, …) for *target*."""
        if not self._on_error:
            return
        t = _escape_md2(target)
        m = _escape_md2(message[:200])
        self._send_async(
            f"🚨 *FB ABUSE SIGNAL*\n"
            f"Target: `{t}`  •  Code: `{_escape_md2(str(error_code))}`\n"
            f"```\n{m}\n```\n"
            f"→ Page có thể bị shadow ban\\. DỪNG upload page này ngay\\."
        )

    def notify_page_throttled(self, page_name: str, drop_pct: float):
        """Page-health detector flagged a reach drop ≥ threshold."""
        if not self._on_error:
            return
        p = _escape_md2(page_name)
        self._send_async(
            f"🔻 *Page reach giảm bất thường*\n"
            f"Page: `{p}`\n"
            f"Reach giảm *{drop_pct:.0f}%* so với baseline 7 ngày\\.\n"
            f"→ Nghi FB throttle\\. Giảm tần suất post hoặc đổi content\\."
        )

    # ── TikTok-specific alerts (Sprint TT-1.8) ────────────────────────────

    def notify_tiktok_compliance_violation(
        self, account: str, code: str, message: str,
    ):
        """TikTok compliance guard rejected a publish before upload."""
        if not self._on_error:
            return
        a = _escape_md2(account)
        c = _escape_md2(code)
        m = _escape_md2(message[:200])
        self._send_async(
            f"⛔ *TikTok Compliance Violation*\n"
            f"Account: `{a}`  •  Code: `{c}`\n"
            f"```\n{m}\n```\n"
            f"→ Sửa content / cấu hình trước khi thử lại\\."
        )

    def notify_tiktok_audit_required(
        self, account: str, action: str,
    ):
        """TikTok returned an error that requires the user to complete an
        audit step (Sandbox→Production, scope upgrade, etc.)."""
        if not self._on_error:
            return
        a = _escape_md2(account)
        x = _escape_md2(action[:200])
        self._send_async(
            f"🪪 *TikTok cần audit*\n"
            f"Account: `{a}`\n"
            f"Hành động cần làm:\n"
            f"```\n{x}\n```"
        )

    def notify_tiktok_post_blocked(
        self, account: str, reason: str,
    ):
        """TikTok blocked a specific upload (spam_risk_*, daily_cap, etc.).
        Different from full abuse_signal: this is per-post, not account-wide."""
        if not self._on_error:
            return
        a = _escape_md2(account)
        r = _escape_md2(reason[:200])
        self._send_async(
            f"🚫 *TikTok post bị chặn*\n"
            f"Account: `{a}`\n"
            f"Lý do:\n"
            f"```\n{r}\n```\n"
            f"→ Tạm dừng acc này để tránh leo thang\\."
        )

    # ── Core send logic ───────────────────────────────────────────────────────

    def _send_async(self, text: str):
        """Non-blocking: enqueue the message; drop silently if queue is full."""
        if not self._enabled:
            return
        try:
            self._queue.put_nowait(text)
        except queue.Full:
            logger.warning("[Telegram] Queue đầy — bỏ qua thông báo")

    def _sender_loop(self):
        """Single daemon thread: drains the queue, rate-limited."""
        while True:
            try:
                text = self._queue.get(timeout=1.0)
            except queue.Empty:
                continue
            try:
                self._send(text)
            except Exception as exc:
                logger.warning("[Telegram] Sender loop lỗi: %s", exc)
            finally:
                self._queue.task_done()

    def _send(self, text: str):
        """Blocking send with rate-limit and retry (called from sender thread)."""
        elapsed = time.time() - self._last_sent
        if elapsed < _MIN_SEND_INTERVAL_S:
            time.sleep(_MIN_SEND_INTERVAL_S - elapsed)
        self._last_sent = time.time()

        url = _TELEGRAM_API.format(token=self._token)
        payload = json.dumps({
            "chat_id":    self._chat_id,
            "text":       text,
            "parse_mode": "MarkdownV2",   # P3: upgraded from legacy Markdown
        }).encode("utf-8")

        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        return
            except urllib.error.HTTPError as exc:
                logger.warning("[Telegram] HTTP %d: %s", exc.code, exc.reason)
                if exc.code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    return  # non-retryable HTTP error
            except Exception as exc:
                logger.warning("[Telegram] Send lỗi lần %d: %s", attempt + 1, exc)
                time.sleep(2 * (attempt + 1))

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled


# ── Module-level singleton ─────────────────────────────────────────────────

def init_notifier(config: dict) -> "TelegramNotifier":
    """Create / replace the global notifier singleton."""
    global _DEFAULT_NOTIFIER
    with _NOTIFIER_LOCK:
        _DEFAULT_NOTIFIER = TelegramNotifier(config)
    return _DEFAULT_NOTIFIER


def get_notifier() -> "TelegramNotifier":
    """Return the global notifier (creates a no-op one if not yet initialised)."""
    global _DEFAULT_NOTIFIER
    with _NOTIFIER_LOCK:
        if _DEFAULT_NOTIFIER is None:
            _DEFAULT_NOTIFIER = TelegramNotifier({})
    return _DEFAULT_NOTIFIER
