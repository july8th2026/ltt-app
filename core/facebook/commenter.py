"""
FacebookCommenter — post a comment on a Facebook video just published
by the same authenticated page.

Stage 7 of the Facebook publish workflow. Mirrors core/tiktok/commenter.py
pattern for symmetry — same CommentResult dataclass, same guarantees:
  • NEVER raises on API failures (would lose successful publish)
  • Returns CommentResult with success / skipped / error info
  • Validates input before sending
  • Honours stop_event for cancellation
  • Maps Graph API error codes via core/facebook/error_codes.py

API
───
Endpoint:    POST {GRAPH_BASE}/{version}/{video_id}/comments
Auth:        Page access_token (NOT user token)
Body:        {"message": "<comment text>"}
Response:    {"id": "<comment_id>"} on success

Requires page permission: pages_manage_engagement (covered by the default
pages_manage_posts scope our app requests).

Limits
──────
- Max length: ~8000 characters (FB limit; we cap at 8000 to be safe)
- Empty / whitespace-only → skipped (not an error)
- Rate-limit: subject to Page-level limits (error code 32)

Common error codes (mapped to friendly Vietnamese via error_codes.py):
  190  access_token_invalid
  200  permission_denied (missing pages_manage_engagement)
  4/17/32  rate limit / quota
  368  spam_detected (account in Facebook timeout)
  100  parameter (e.g. empty message or invalid video_id)
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

from core.graph_client import GraphClient, GraphError


# Conservative limits (FB Help center says ~8k chars; we cap at 8000)
_MAX_COMMENT_LEN = 8000
_MIN_COMMENT_LEN = 1


@dataclass
class CommentResult:
    """Outcome of a single FB comment-post attempt.

    Same shape as core.tiktok.commenter.CommentResult for cross-platform
    audit log consistency.
    """
    success:    bool
    skipped:    bool = False         # True when comment was empty / disabled
    comment_id: str = ""             # Graph-assigned id on success
    error_code: str = ""             # Graph error code or our own
    message:   str = ""              # human-readable
    text:      str = ""              # what we tried to post


class FacebookCommentError(Exception):
    """Raised only for programmer errors (bad config, missing client).

    API failures DO NOT raise — they return CommentResult(success=False).
    """


class FacebookCommenter:
    """Post a comment to a Facebook video the authenticated page owns.

    Designed to be called AFTER a successful publish, using the SAME page
    access_token that uploaded the video.

    Parameters
    ----------
    client : GraphClient
        Configured Graph API client (with correct version).
    page_access_token : str
        Page-level OAuth token. Must have pages_manage_engagement permission.
    stop_event : threading.Event, optional
        Cancellation signal; checked before API call.
    on_log : callable(msg, level), optional
        Log callback.
    on_status : callable(msg), optional
        Status bar callback for the GUI.
    """

    def __init__(
        self,
        client: GraphClient,
        page_access_token: str,
        stop_event: Optional[threading.Event] = None,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        comment_delay_min_s: float = 0.0,    # 0 = disabled (test/legacy default)
        comment_delay_max_s: float = 0.0,    # production sets via config
    ):
        if client is None:
            raise FacebookCommentError(
                "FacebookCommenter requires a GraphClient"
            )
        if not page_access_token or not str(page_access_token).strip():
            raise FacebookCommentError(
                "FacebookCommenter requires a page_access_token"
            )
        self._client = client
        self._token  = str(page_access_token).strip()
        self._stop   = stop_event
        self._log    = on_log    or (lambda m, l: None)
        self._status = on_status or (lambda m: None)
        # Anti-spam P4.3: human-like comment timing. Setting BOTH to 0
        # disables the delay (legacy behaviour, used in unit tests).
        self._delay_min_s = max(0.0, float(comment_delay_min_s))
        self._delay_max_s = max(self._delay_min_s, float(comment_delay_max_s))

    def _compute_comment_delay(self) -> float:
        """Random delay in [delay_min, delay_max]; 0 if disabled."""
        if self._delay_max_s <= 0:
            return 0.0
        import random
        return random.uniform(self._delay_min_s, self._delay_max_s)

    def _sleep_interruptible(self, seconds: float):
        """Sleep that wakes up early if stop_event is set. Polled at 1 s."""
        import time as _time
        end = _time.time() + seconds
        while _time.time() < end:
            if self._stop is not None and self._stop.is_set():
                return
            _time.sleep(min(1.0, end - _time.time()))

    # ── Public API ─────────────────────────────────────────────────────────

    def post_comment(
        self,
        video_id: str,
        text: str,
    ) -> CommentResult:
        """Post a single comment under *video_id*.

        Args:
            video_id: the FB video_id returned by GraphUploader.upload().
            text:     comment body. Empty → skipped.

        Returns:
            CommentResult — always; never raises on API errors.
        """
        text = (text or "").strip()

        # 1. Validate input (no API call yet)
        validation = self._validate(text)
        if validation is not None:
            return validation

        if not video_id or not str(video_id).strip():
            return CommentResult(
                success=False, skipped=False,
                error_code="missing_video_id",
                message="Không có video_id — không thể đăng comment",
                text=text,
            )

        # 2. Stop check
        if self._stop is not None and self._stop.is_set():
            return CommentResult(
                success=False, skipped=False,
                error_code="user_cancelled",
                message="Đã huỷ trước khi đăng comment",
                text=text,
            )

        # 2b. Anti-spam Phase 4.3: human-like delay before the comment.
        # Real users post a video, glance at the feed, then comment seconds
        # to a minute later. Bots that comment within 1-2 s of upload trip
        # a clear pattern. Default 30-180 s, configurable; 0 = disabled.
        delay = self._compute_comment_delay()
        if delay > 0:
            self._status(f"[FB] Chờ {delay:.0f}s trước khi comment (anti-pattern)...")
            self._log(f"[FB Comment] Delay {delay:.0f}s anti-pattern", "info")
            self._sleep_interruptible(delay)
            if self._stop is not None and self._stop.is_set():
                return CommentResult(
                    success=False, skipped=False,
                    error_code="user_cancelled",
                    message="Đã huỷ trong lúc chờ comment delay",
                    text=text,
                )

        # 3. Call API
        self._log(f"[FB Comment] Đang đăng: {text[:60]}...", "info")
        self._status("[FB] Đang đăng comment...")

        try:
            data = self._client.post(
                f"{str(video_id).strip()}/comments",
                data={"message": text},
                token=self._token,
            )
        except GraphError as exc:
            return self._handle_graph_error(exc, text)
        except Exception as exc:
            self._log(
                f"[FB Comment] Lỗi không xác định: {exc}",
                "warning",
            )
            return CommentResult(
                success=False, skipped=False,
                error_code="unexpected_error",
                message=str(exc),
                text=text,
            )

        # 4. Parse response — Graph returns {"id": "<page_id>_<comment_id>"}
        comment_id = str(data.get("id", "") or data.get("comment_id", ""))
        if not comment_id:
            self._log(
                "[FB Comment] API trả OK nhưng không có comment_id",
                "warning",
            )

        self._log(
            f"[FB Comment] ✅ Đã đăng (id={comment_id or '?'})",
            "success",
        )
        return CommentResult(
            success=True, skipped=False,
            comment_id=comment_id,
            error_code="",
            message="OK",
            text=text,
        )

    # ── Validation ─────────────────────────────────────────────────────────

    @staticmethod
    def _validate(text: str) -> Optional[CommentResult]:
        """Return CommentResult to short-circuit, or None to proceed."""
        # Empty → SKIP (not an error)
        if not text:
            return CommentResult(
                success=True, skipped=True,
                message="Comment rỗng — bỏ qua",
                text="",
            )

        # Length cap
        if len(text) > _MAX_COMMENT_LEN:
            return CommentResult(
                success=False, skipped=False,
                error_code="comment_too_long",
                message=(
                    f"Comment quá dài ({len(text)} ký tự, "
                    f"giới hạn {_MAX_COMMENT_LEN})"
                ),
                text=text,
            )

        return None

    # ── Error handling ─────────────────────────────────────────────────────

    def _handle_graph_error(
        self,
        exc: GraphError,
        text: str,
    ) -> CommentResult:
        """Translate GraphError to a CommentResult with friendly message."""
        # Extract numeric code
        code = getattr(exc, "code", 0) or 0
        try:
            code_int = int(code)
        except (ValueError, TypeError):
            code_int = 0

        # Map code → friendly message
        try:
            from core.facebook.error_codes import get_friendly_message
            friendly = get_friendly_message(code_int, fallback=str(exc))
        except Exception:
            friendly = str(exc)

        # Special hints by code
        if code_int in (190, 102, 104):
            level = "warning"
            self._log(
                "[FB Comment] Token Page hết hạn / không hợp lệ",
                level,
            )
        elif code_int in (200, 10):
            level = "warning"
            self._log(
                "[FB Comment] Thiếu quyền pages_manage_engagement",
                level,
            )
        elif code_int in (4, 17, 32, 613):
            level = "warning"
            self._log(
                f"[FB Comment] Rate limit code={code_int}",
                level,
            )
        elif code_int in (368,):
            level = "warning"
            self._log(
                "[FB Comment] Page bị FB tạm khóa do vi phạm cộng đồng",
                level,
            )
        else:
            level = "warning"
            self._log(
                f"[FB Comment] Graph API lỗi code={code_int}: {exc}",
                level,
            )

        return CommentResult(
            success=False, skipped=False,
            error_code=str(code_int) if code_int else "graph_error",
            message=friendly,
            text=text,
        )
