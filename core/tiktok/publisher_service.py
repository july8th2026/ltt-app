"""
TikTokPublisher — implements the Publisher interface for TikTok.

Dispatches to the correct uploader based on task["post_type"]:

    post_type="tiktok_draft"   → TikTokDraftUploader  (inbox, safe for all apps)
    post_type="tiktok_direct"  → TikTokDirectUploader (direct post, needs audit)
    post_type="tiktok"         → alias for "tiktok_direct"

Account lookup:
    task["account"] (open_id) → TikTokTokenStore.get_account()
    If empty, uses the first available account.

Token refresh:
    If access_token has expired, automatically refreshes before uploading.

Audit logging (Phase 7):
    Every publish attempt is logged to data/audit_log.jsonl (JSONL format).
    Events: tiktok_publish_attempt, tiktok_publish_success,
            tiktok_publish_failure, tiktok_compliance_violation,
            tiktok_token_refreshed.
    Override log path via config["tiktok_audit_log_path"].
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from core.publisher import Publisher, PublishResult
from core.tiktok.client import TikTokClient, TikTokError
from core.tiktok.token_store import TikTokAccount, TikTokTokenStore

_DRAFT_POST_TYPES   = frozenset({"tiktok_draft", "draft"})
_DIRECT_POST_TYPES  = frozenset({"tiktok_direct", "tiktok", "direct"})


class TikTokPublisher(Publisher):
    """
    Publish a video to TikTok via Content Posting API v2.

    task keys consumed:
        video_path      — local video file path (required)
        account         — TikTok open_id (optional; uses first account if empty)
        title           — post title (≤150 chars)
        description     — post description (≤2200 chars)
        keywords        — comma-separated hashtags (appended to description)
        post_type       — "tiktok_draft" | "tiktok_direct" | "tiktok"
        privacy_level   — "SELF_ONLY" | "PUBLIC_TO_EVERYONE" | etc. (direct only)
        row_idx         — sheet row index (forwarded to audit log)
    """

    platform_name = "tiktok"

    def __init__(
        self,
        config: dict,
        stop_event: threading.Event,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        rate_limiter=None,
    ):
        self._config       = config
        self._stop         = stop_event
        self._on_log       = on_log    or (lambda m, l: None)
        self._on_status    = on_status or (lambda m: None)
        self._token_store  = TikTokTokenStore()
        # Anti-ban rate limiter (now actually used — was previously ignored).
        # acquire(account_key, account_id=open_id) → enforces per-account
        # interval, daily quota, jitter, active hours. Optional: None = legacy
        # behaviour (no rate limiting). See core/rate_limiter.RateLimiter.
        self._rate_limiter = rate_limiter

    def publish(self, task: dict) -> PublishResult:
        """
        Upload and publish to TikTok.

        Raises TikTokComplianceError (blocking violations), TikTokError,
        FileNotFoundError, RuntimeError, or InterruptedError.

        Audit events fired (never block publishing):
          • tiktok_publish_attempt      — always, after account resolved
          • tiktok_publish_success      — on success
          • tiktok_publish_failure      — on non-compliance exception
          • tiktok_compliance_violation — on TikTokComplianceError
        """
        from core.tiktok.compliance_guard import (
            TikTokComplianceGuard,
            TikTokComplianceError,
        )
        from utils.audit_logger import append_event

        account = self._resolve_account(task)
        account = self._ensure_token_fresh(account)

        # Build a common kwargs dict for all audit calls for this publish job
        _log_path = str(self._config.get("tiktok_audit_log_path", ""))
        _audit_kw = dict(
            log_path      = _log_path,
            open_id       = account.open_id,
            display_name  = account.display_name,
            row_idx       = task.get("row_idx", ""),
            post_type     = str(task.get("post_type", "tiktok_draft")),
            privacy_level = str(task.get("privacy_level", "")),
        )

        # ── Audit: publish attempt ─────────────────────────────────────────────
        append_event("tiktok_publish_attempt", **_audit_kw)

        # ── Anti-ban rate limit (NEW — was missing for TikTok) ─────────────────
        # Acquire BEFORE the upload work. The "page" key for TikTok is the
        # display_name (human-readable). account_id (open_id) drives the
        # per-account daily cap. Released in finally below.
        _rl_key = account.display_name or account.open_id
        _rl_acquired = False
        if self._rate_limiter is not None:
            wait = self._rate_limiter.wait_until_ready(_rl_key)
            if wait > 0:
                self._on_log(
                    f"[TikTok RateLimit] Chờ {wait:.0f}s → {_rl_key}", "info",
                )
                self._on_status(f"[TikTok] Chờ rate-limit {wait:.0f}s...")
            self._rate_limiter.acquire(
                _rl_key, self._stop, account_id=account.open_id,
            )
            _rl_acquired = True

        try:
            # ── Preflight compliance check ─────────────────────────────────────
            # Must run BEFORE the client is created; raises TikTokComplianceError
            # on any blocking violation.  Non-blocking advisories → logged as warnings.
            _guard = TikTokComplianceGuard(self._config)
            _compliance_warnings = _guard.check(task, account)
            for _w in _compliance_warnings:
                self._on_log(f"[Compliance] {_w.code}: {_w.message}", "warning")

            client = TikTokClient(
                access_token = account.access_token,
                on_log       = self._on_log,
                timeout      = int(self._config.get("tiktok_request_timeout_s", 60)),
                # Sprint TT-1.3: per-account UA + proxy when network_identity_enabled
                account_id   = account.open_id,
                config       = self._config,
            )

            post_type = str(task.get("post_type", "tiktok_draft")).lower().strip()

            if post_type in _DRAFT_POST_TYPES:
                result = self._upload_draft(client, task)
            elif post_type in _DIRECT_POST_TYPES:
                result = self._upload_direct(client, task)
            else:
                # Unknown post_type — default to draft (safe)
                self._on_log(
                    f"[TikTok] post_type='{post_type}' không rõ, dùng draft upload",
                    "warning",
                )
                result = self._upload_draft(client, task)

            # ── Audit: publish success ─────────────────────────────────────────
            append_event(
                "tiktok_publish_success",
                publish_id = result.external_post_id,
                **_audit_kw,
            )

            # ── STAGE 7: optional post-publish comment ─────────────────────────
            # Only attempt for direct posts (drafts in inbox can't be commented).
            # Fully optional — does NOT raise on failure (would lose successful publish).
            comment_text = str(task.get("comment", "") or task.get("tiktok_comment", "")).strip()
            if comment_text and post_type in _DIRECT_POST_TYPES:
                self._maybe_post_comment(
                    client       = client,
                    publish_id   = result.external_post_id,
                    comment_text = comment_text,
                    audit_kw     = _audit_kw,
                )
            elif comment_text and post_type in _DRAFT_POST_TYPES:
                self._on_log(
                    "[TikTok] Bỏ qua comment — draft inbox không hỗ trợ comment",
                    "info",
                )

            return result

        except TikTokComplianceError as exc:
            # ── Audit: compliance violation (blocking) ─────────────────────────
            append_event(
                "tiktok_compliance_violation",
                error_code = str(exc.error_code),
                details    = {"message": str(exc.message)},
                **_audit_kw,
            )
            # Sprint TT-1.8: Telegram alert
            try:
                from utils.notifier import get_notifier
                get_notifier().notify_tiktok_compliance_violation(
                    account = account.display_name or account.open_id,
                    code    = str(exc.error_code),
                    message = str(exc.message),
                )
            except Exception:
                pass
            raise

        except Exception as exc:
            # ── Audit: general publish failure ─────────────────────────────────
            _ecode = getattr(exc, "error_code", "") or type(exc).__name__
            append_event(
                "tiktok_publish_failure",
                error_code = str(_ecode),
                details    = {"error": str(exc)[:500]},
                **_audit_kw,
            )
            # Sprint TT-1.8: Telegram alert for abuse-grade TT codes
            try:
                from core.adaptive_backoff import (
                    is_tiktok_abuse_signal, is_tiktok_permanent,
                )
                _code_str = str(_ecode).lower()
                if is_tiktok_abuse_signal(_code_str):
                    from utils.notifier import get_notifier
                    get_notifier().notify_tiktok_post_blocked(
                        account = account.display_name or account.open_id,
                        reason  = f"{_code_str}: {str(exc)[:200]}",
                    )
                elif is_tiktok_permanent(_code_str) and _code_str in (
                    "scope_not_authorized", "privacy_level_option_mismatch",
                    "unaudited_client_can_only_post_to_private_accounts",
                ):
                    from utils.notifier import get_notifier
                    get_notifier().notify_tiktok_audit_required(
                        account = account.display_name or account.open_id,
                        action  = f"{_code_str}: cần audit hoặc đổi config",
                    )
            except Exception:
                pass
            raise

        finally:
            # Release the rate-limit slot whether we succeeded or raised. This
            # also records the daily-count increment used by quota checks.
            if _rl_acquired:
                try:
                    self._rate_limiter.release(_rl_key, account_id=account.open_id)
                except Exception as _exc:
                    import logging as _lg
                    _lg.getLogger(__name__).debug(
                        "rate_limiter.release failed (non-fatal): %s", _exc
                    )

    # ── Stage 7: Comment (optional) ────────────────────────────────────────

    def _maybe_post_comment(
        self,
        client: TikTokClient,
        publish_id: str,
        comment_text: str,
        audit_kw: dict,
    ) -> None:
        """Optional Stage 7: post a comment under the just-published video.

        Never raises — comment failure must NOT bubble up and lose the
        successful publish_id from Stage 4-6.

        Logs result + writes audit event:
          tiktok_comment_posted   on success
          tiktok_comment_skipped  on empty / scope-missing / spam
          tiktok_comment_failed   on unexpected exception
        """
        from utils.audit_logger import append_event
        from core.tiktok.commenter import TikTokCommenter

        try:
            commenter = TikTokCommenter(
                client     = client,
                stop_event = self._stop,
                on_log     = self._on_log,
                on_status  = self._on_status,
                # Sprint TT-1.6: human-like delay before comment
                comment_delay_min_s = float(self._config.get("tt_comment_delay_min_s", 0)),
                comment_delay_max_s = float(self._config.get("tt_comment_delay_max_s", 0)),
            )
            result = commenter.post_comment(publish_id, comment_text)

            if result.success and not result.skipped:
                append_event(
                    "tiktok_comment_posted",
                    publish_id = publish_id,
                    details    = {
                        "comment_id": result.comment_id,
                        "text_len":   len(result.text),
                    },
                    **audit_kw,
                )
            elif result.skipped:
                append_event(
                    "tiktok_comment_skipped",
                    publish_id = publish_id,
                    details    = {"reason": result.message},
                    **audit_kw,
                )
            else:
                # API failure — log but do not break publish flow
                append_event(
                    "tiktok_comment_failed",
                    publish_id = publish_id,
                    error_code = result.error_code,
                    details    = {"message": result.message},
                    **audit_kw,
                )
        except Exception as exc:
            # Last line of defence: a bug in commenter must not break publish
            self._on_log(
                f"[TikTok Comment] Lỗi bất ngờ (đã bỏ qua): {exc}",
                "warning",
            )
            try:
                append_event(
                    "tiktok_comment_failed",
                    publish_id = publish_id,
                    error_code = type(exc).__name__,
                    details    = {"error": str(exc)[:300]},
                    **audit_kw,
                )
            except Exception:
                pass

    # ── Upload dispatchers ─────────────────────────────────────────────────

    def _upload_draft(self, client: TikTokClient, task: dict) -> PublishResult:
        from core.tiktok.uploader_draft import TikTokDraftUploader
        uploader = TikTokDraftUploader(
            client      = client,
            config      = self._config,
            stop_event  = self._stop,
            on_log      = self._on_log,
            on_status   = self._on_status,
        )
        publish_id, post_url = uploader.upload(task)
        return PublishResult(
            success           = True,
            external_post_id  = publish_id,
            external_post_url = post_url,
            status            = "draft",
        )

    def _upload_direct(self, client: TikTokClient, task: dict) -> PublishResult:
        from core.tiktok.uploader_direct import TikTokDirectUploader
        uploader = TikTokDirectUploader(
            client      = client,
            config      = self._config,
            stop_event  = self._stop,
            on_log      = self._on_log,
            on_status   = self._on_status,
        )
        publish_id, post_url = uploader.upload(task)
        return PublishResult(
            success           = True,
            external_post_id  = publish_id,
            external_post_url = post_url,
            status            = "published",
        )

    # ── Account resolution ─────────────────────────────────────────────────

    def _resolve_account(self, task: dict) -> TikTokAccount:
        """Find the TikTokAccount to use for this task."""
        open_id = str(task.get("account", "")).strip()
        if open_id:
            acc = self._token_store.get_account(open_id)
            if acc is None:
                raise RuntimeError(
                    f"Không tìm thấy tài khoản TikTok với open_id='{open_id}'.\n"
                    "Vào tab 🔐 Tài khoản → Kết nối TikTok."
                )
            return acc

        # Fall back to first available account
        accounts = self._token_store.all_accounts()
        if not accounts:
            raise RuntimeError(
                "Chưa kết nối tài khoản TikTok.\n"
                "Vào tab 🔐 Tài khoản → Kết nối TikTok."
            )
        return accounts[0]

    def _ensure_token_fresh(self, account: TikTokAccount) -> TikTokAccount:
        """Refresh access_token if expired. Returns updated account."""
        if account.is_token_valid():
            return account

        self._on_log(
            f"[TikTok] Token của {account.display_name} đã hết hạn — "
            "đang làm mới...",
            "warning",
        )
        try:
            from core.tiktok.auth_manager import TikTokAuthManager
            mgr = TikTokAuthManager(self._config, token_store=self._token_store)
            refreshed = mgr.refresh_access_token(account)

            # ── Audit: token refreshed ─────────────────────────────────────────
            from utils.audit_logger import append_event
            _log_path = str(self._config.get("tiktok_audit_log_path", ""))
            append_event(
                "tiktok_token_refreshed",
                log_path     = _log_path,
                open_id      = refreshed.open_id,
                display_name = refreshed.display_name,
            )
            return refreshed
        except Exception as exc:
            raise RuntimeError(
                f"Token TikTok hết hạn và không thể làm mới: {exc}\n"
                "Vào tab 🔐 Tài khoản → Kết nối lại TikTok."
            ) from exc
