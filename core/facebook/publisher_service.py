"""
FacebookPublisher — implements Publisher for the Facebook platform.

Thin adapter: all real upload logic lives in UploadEngine (Graph API /
Reels API) and is unchanged.  This class wraps run_sync() and converts
its (url, id) tuple into a PublishResult, then runs Stage 7 (optional
post-publish comment) with structured audit events.

Stage 7 comment behaviour:
  • Skips silently when task["comment"] is empty
  • Skips for Reels posts (FB doesn't reliably support Reels comments
    via Graph API — kept for backward compatibility with tests)
  • Calls FacebookCommenter (new module) for parity with TikTok flow
  • Writes audit events: facebook_comment_posted / _skipped / _failed
  • NEVER raises — comment failure must NOT lose successful publish_id
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from core.publisher import Publisher, PublishResult
from core.upload_engine import UploadEngine


class FacebookPublisher(Publisher):
    """Publish a video to a Facebook Page via Graph API or Reels API."""

    platform_name = "facebook"

    def __init__(
        self,
        config: dict,
        stop_event: threading.Event,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        rate_limiter=None,
    ):
        self._config       = config
        self._stop_event   = stop_event
        self._on_log       = on_log    or (lambda msg, lvl: None)
        self._on_status    = on_status or (lambda msg: None)
        self._rate_limiter = rate_limiter

    def publish(self, task: dict) -> PublishResult:
        """
        Delegate upload to UploadEngine.run_sync().

        UploadEngine ALREADY calls uploader.post_comment() internally for feed
        posts (see core/upload_engine.py:160). This new path adds:
          1. Audit events for every comment attempt
          2. Friendly Vietnamese error mapping
          3. Stop-event cancellation
          4. CommentResult dataclass propagated to audit log

        Exceptions from UploadEngine propagate UNCHANGED so that SheetRunner._tick()
        can apply its retry / mark_error logic.
        """
        # ── Strip comment from task BEFORE engine.run_sync so UploadEngine's
        # built-in post_comment call (engine.py:160) is bypassed.  We handle
        # commenting ourselves below to get audit events + friendly errors.
        comment_text = str(task.get("comment", "") or "").strip()
        task_for_upload = dict(task)
        if comment_text:
            task_for_upload["comment"] = ""    # disable engine inline call

        engine = UploadEngine(
            config       = self._config,
            stop_event   = self._stop_event,
            on_log       = self._on_log,
            on_status    = self._on_status,
            on_result    = lambda t, s, lnk: None,
            on_done      = lambda: None,
            on_error     = lambda msg: None,
            rate_limiter = self._rate_limiter,
        )

        # Audit: attempt → success/failure. Until now FB had no publish-level
        # JSONL events (only comment-level), making volume monitoring blind to
        # the actual upload stage. TikTok already emits these — this brings parity.
        self._log_audit_publish_attempt(task)
        try:
            video_url, video_id = engine.run_sync(task_for_upload)
        except Exception as exc:
            self._log_audit_publish_failed(task, type(exc).__name__, str(exc)[:300])
            raise

        result = PublishResult(
            success           = True,
            external_post_id  = video_id,
            external_post_url = video_url,
            status            = "published",
        )
        self._log_audit_publish_success(task, video_id, video_url)

        # ── Stage 7: optional post-publish comment ─────────────────────────
        # Gated behind fb_comment_enabled (default OFF): commenting needs the
        # pages_manage_engagement permission, deliberately excluded from the App
        # Review submission. Skip (with audit) until that permission is approved.
        post_type = str(task.get("post_type", "feed")).lower().strip()
        comment_enabled = bool(self._config.get("fb_comment_enabled", False))
        if comment_text and not comment_enabled:
            self._on_log(
                "[FB] Bỏ qua comment — tính năng đang TẮT "
                "(fb_comment_enabled=false, chờ duyệt pages_manage_engagement)",
                "info",
            )
            self._log_audit_skipped(task, video_id, "comment_feature_disabled")
        elif comment_text and post_type != "reels":
            self._maybe_post_comment(
                task         = task,
                video_id     = video_id,
                video_url    = video_url,
                comment_text = comment_text,
            )
        elif comment_text and post_type == "reels":
            self._on_log(
                "[FB] Bỏ qua comment — Reels không hỗ trợ comment qua API",
                "info",
            )
            self._log_audit_skipped(task, video_id, "reels_no_comment")

        return result

    # ── Stage 7 helpers ────────────────────────────────────────────────────

    def _maybe_post_comment(
        self,
        task: dict,
        video_id: str,
        video_url: str,
        comment_text: str,
    ) -> None:
        """Run FacebookCommenter + audit. Never raises.

        Looks up page access token from TokenStore (single decrypt via
        get_default_store singleton).
        """
        from core.token_store import get_default_store
        from core.facebook.commenter import (
            FacebookCommenter, FacebookCommentError, CommentResult,
        )
        from core.graph_client import GraphClient
        from core.utils import graph_api_version

        page_name = str(task.get("page", "")).strip()
        if not page_name:
            self._on_log(
                "[FB Comment] Bỏ qua — task không có page_name",
                "warning",
            )
            self._log_audit_failed(task, video_id, "missing_page", "no page in task")
            return

        try:
            store = get_default_store()
            account, page = store.find_page_by_name(page_name)
            if account is None or page is None:
                self._on_log(
                    f"[FB Comment] Không tìm thấy page '{page_name}' để lấy token",
                    "warning",
                )
                self._log_audit_failed(
                    task, video_id, "page_not_found",
                    f"page '{page_name}' missing in store",
                )
                return

            client = GraphClient(
                version=graph_api_version(self._config),
                timeout=60,
                max_retries=2,
            )
            commenter = FacebookCommenter(
                client            = client,
                page_access_token = page.access_token,
                stop_event        = self._stop_event,
                on_log            = self._on_log,
                on_status         = self._on_status,
                # P4.3 anti-spam: human-like delay before commenting.
                comment_delay_min_s = float(self._config.get("fb_comment_delay_min_s", 0)),
                comment_delay_max_s = float(self._config.get("fb_comment_delay_max_s", 0)),
            )
            comment_result = commenter.post_comment(video_id, comment_text)
        except FacebookCommentError as exc:
            self._on_log(
                f"[FB Comment] Cấu hình sai: {exc}",
                "warning",
            )
            self._log_audit_failed(task, video_id, "config_error", str(exc))
            return
        except Exception as exc:
            self._on_log(
                f"[FB Comment] Lỗi bất ngờ (đã bỏ qua): {exc}",
                "warning",
            )
            self._log_audit_failed(
                task, video_id, type(exc).__name__, str(exc)[:300],
            )
            return

        # ── Audit based on result type
        if comment_result.success and not comment_result.skipped:
            self._log_audit_posted(
                task, video_id, comment_result.comment_id, comment_text,
            )
        elif comment_result.skipped:
            self._log_audit_skipped(
                task, video_id, comment_result.message,
            )
        else:
            self._log_audit_failed(
                task, video_id,
                comment_result.error_code or "comment_failed",
                comment_result.message,
            )

    # ── Audit event helpers ────────────────────────────────────────────────

    def _audit_kwargs(self, task: dict, video_id: str) -> dict:
        """Build common audit fields. Mirrors tiktok publisher_service pattern."""
        return dict(
            log_path     = str(self._config.get("audit_log_path", "")),
            open_id      = str(task.get("page", "")),       # using page name as id
            display_name = str(task.get("page", "")),
            row_idx      = task.get("row_idx", ""),
            post_type    = str(task.get("post_type", "feed")),
            privacy_level= str(task.get("privacy", "")),
        )

    def _log_audit_posted(
        self, task: dict, video_id: str, comment_id: str, text: str,
    ) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_comment_posted",
                publish_id = video_id,
                details    = {
                    "comment_id": comment_id,
                    "text_len":   len(text),
                },
                **self._audit_kwargs(task, video_id),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (posted): %s", _exc
            )

    def _log_audit_skipped(
        self, task: dict, video_id: str, reason: str,
    ) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_comment_skipped",
                publish_id = video_id,
                details    = {"reason": reason},
                **self._audit_kwargs(task, video_id),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (skipped): %s", _exc
            )

    def _log_audit_failed(
        self, task: dict, video_id: str, error_code: str, message: str,
    ) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_comment_failed",
                publish_id = video_id,
                error_code = error_code,
                details    = {"message": message[:300]},
                **self._audit_kwargs(task, video_id),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (failed): %s", _exc
            )

    # ── Publish-level audit events (parity with TikTok publisher) ──────────

    def _log_audit_publish_attempt(self, task: dict) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_publish_attempt",
                details = {
                    "video_file": str(task.get("video_path", ""))[-120:],
                    "has_comment": bool(str(task.get("comment", "") or "").strip()),
                },
                **self._audit_kwargs(task, ""),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (publish_attempt): %s", _exc
            )

    def _log_audit_publish_success(
        self, task: dict, video_id: str, video_url: str,
    ) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_publish_success",
                publish_id = video_id,
                details    = {"video_url": video_url},
                **self._audit_kwargs(task, video_id),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (publish_success): %s", _exc
            )

    def _log_audit_publish_failed(
        self, task: dict, error_code: str, message: str,
    ) -> None:
        try:
            from utils.audit_logger import append_event
            append_event(
                "facebook_publish_failed",
                error_code = error_code,
                details    = {"message": message[:300]},
                **self._audit_kwargs(task, ""),
            )
        except Exception as _exc:
            import logging as _lg
            _lg.getLogger(__name__).debug(
                "audit_logger.append_event failed (publish_failed): %s", _exc
            )
