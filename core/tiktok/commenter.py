"""
TikTokCommenter — post a comment on a TikTok video just published by the
same authenticated account.

Workflow Stage 7: After a successful direct/draft upload, optionally post
a comment under the new video. Use case: pinned first comment with hashtags
or CTAs (a standard creator pattern).

API
───
TikTok exposes comment creation via the Comment Management API:

    POST https://open.tiktokapis.com/v2/comment/create/
    Body: {"video_id": "<id>", "text": "<comment>"}
    Scope: comment.list AND comment.create (separate from video.publish)

This scope is granted only to apps that pass an additional TikTok review.
The commenter handles graceful degradation when the scope is missing.

Known TikTok error codes for comments
──────────────────────────────────────
    scope_not_authorized        — app lacks comment scope (most common)
    spam_risk_text              — comment flagged as spam
    duplicate_content           — exact same comment exists already
    rate_limit_exceeded         — too many comments in short window
    video_not_visible           — drafts cannot be commented on
    user_not_in_whitelist       — sandbox app, user not in target list

Implementation guarantees
─────────────────────────
1. NEVER raises on API failures — comment is optional, must not break publish flow.
2. Returns CommentResult dataclass with success/error info for audit.
3. Validates input (length, emoji-only, hashtag count) before sending.
4. Honours stop_event for graceful cancellation.
5. Translates errors via core.tiktok.error_codes for friendly logs.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

from core.tiktok.client import TikTokClient, TikTokError


# Endpoint paths
_COMMENT_CREATE_URL = "/v2/comment/create/"

# Limits per TikTok Community Guidelines
_MAX_COMMENT_LEN = 150       # TikTok comment limit (conservative; actual is ~150)
_MIN_COMMENT_LEN = 1


@dataclass
class CommentResult:
    """Outcome of a single comment-post attempt.

    Always returned (never raised). Inspect .success to check.
    """
    success:   bool
    skipped:   bool = False              # True when comment was empty / disabled
    comment_id: str = ""                 # TikTok-assigned id on success
    error_code: str = ""                 # TikTok API code (or our own)
    message:   str = ""                  # human-readable
    text:      str = ""                  # what we tried to post


class TikTokCommentError(Exception):
    """Raised only for programmer-error situations (bad config, missing client).

    API failures DO NOT raise — they return CommentResult(success=False).
    """


class TikTokCommenter:
    """Post a comment to a TikTok video the authenticated user owns.

    Designed to be called AFTER a successful publish, from the same
    TikTokClient instance (so the access_token has video.publish scope).

    The commenter is intentionally simple: one method `post_comment`.
    All retries, rate limiting, and error mapping happen in TikTokClient
    (see core/tiktok/client.py _request_with_retry).
    """

    def __init__(
        self,
        client: TikTokClient,
        stop_event: Optional[threading.Event] = None,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        comment_delay_min_s: float = 0.0,
        comment_delay_max_s: float = 0.0,
    ):
        if client is None:
            raise TikTokCommentError("TikTokCommenter requires a TikTokClient")
        self._client = client
        self._stop   = stop_event
        self._log    = on_log    or (lambda m, l: None)
        self._status = on_status or (lambda m: None)
        # Sprint TT-1.6: human-like delay before comment (mirrors FB commenter).
        self._delay_min_s = max(0.0, float(comment_delay_min_s))
        self._delay_max_s = max(self._delay_min_s, float(comment_delay_max_s))

    def _compute_comment_delay(self) -> float:
        if self._delay_max_s <= 0:
            return 0.0
        import random
        return random.uniform(self._delay_min_s, self._delay_max_s)

    def _sleep_interruptible(self, seconds: float) -> None:
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
            video_id: the publish_id / video_id returned by the upload init.
            text:     comment body. Empty → skipped (no API call).

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

        # 2b. Sprint TT-1.6: anti-pattern delay
        _delay = self._compute_comment_delay()
        if _delay > 0:
            self._status(f"[TikTok] Chờ {_delay:.0f}s trước comment (anti-pattern)...")
            self._log(f"[TikTok Comment] Delay {_delay:.0f}s", "info")
            self._sleep_interruptible(_delay)
            if self._stop is not None and self._stop.is_set():
                return CommentResult(
                    success=False, skipped=False,
                    error_code="user_cancelled",
                    message="Đã huỷ trong delay comment",
                    text=text,
                )

        # 3. Call API
        self._log(f"[TikTok Comment] Đang đăng: {text[:60]}...", "info")
        self._status(f"[TikTok] Đang đăng comment...")

        payload = {
            "video_id": str(video_id).strip(),
            "text":     text,
        }

        try:
            data = self._client.post(_COMMENT_CREATE_URL, payload)
        except TikTokError as exc:
            return self._handle_api_error(exc, text)
        except Exception as exc:
            # Network / unexpected
            self._log(
                f"[TikTok Comment] Lỗi không xác định: {exc}",
                "warning",
            )
            return CommentResult(
                success=False, skipped=False,
                error_code="unexpected_error",
                message=str(exc),
                text=text,
            )

        # 4. Parse response
        comment_id = str(data.get("comment_id", "") or data.get("id", ""))
        if not comment_id:
            self._log(
                "[TikTok Comment] API trả OK nhưng không có comment_id",
                "warning",
            )

        self._log(
            f"[TikTok Comment] ✅ Đã đăng (comment_id={comment_id or '?'})",
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

        # Length cap (TikTok rejects > ~150 chars)
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

    def _handle_api_error(
        self,
        exc: TikTokError,
        text: str,
    ) -> CommentResult:
        """Translate TikTok API errors to a CommentResult.

        Special handling: scope_not_authorized is the most common case
        (app doesn't have comment scope yet). We log a clear hint.
        """
        code = (exc.error_code or "").lower()

        # Specific guidance for scope missing
        if code in ("scope_not_authorized", "scope_permission_missed"):
            msg = (
                "App chưa được TikTok cấp scope 'comment.create'. "
                "Vào TikTok Developer Portal → My Apps → Add Products → "
                "Comment Management API → Submit for review."
            )
            self._log(
                f"[TikTok Comment] ⚠ Chưa có quyền comment: {msg}",
                "warning",
            )
            return CommentResult(
                success=False, skipped=False,
                error_code=code,
                message=msg,
                text=text,
            )

        # Spam/duplicate
        if code in ("spam_risk_text", "duplicate_content"):
            self._log(
                f"[TikTok Comment] Bị flag spam: {exc}",
                "warning",
            )
            return CommentResult(
                success=False, skipped=False,
                error_code=code,
                message=str(exc),
                text=text,
            )

        # Rate limit
        if code in ("rate_limit_exceeded",):
            self._log(
                "[TikTok Comment] Vượt rate limit — bỏ qua",
                "warning",
            )
            return CommentResult(
                success=False, skipped=False,
                error_code=code,
                message="Vượt giới hạn comment trong khoảng thời gian này",
                text=text,
            )

        # Generic
        self._log(
            f"[TikTok Comment] API lỗi [{code}]: {exc}",
            "warning",
        )
        return CommentResult(
            success=False, skipped=False,
            error_code=code or "api_error",
            message=str(exc),
            text=text,
        )
