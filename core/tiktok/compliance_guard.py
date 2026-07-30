"""
compliance_guard.py — TikTok preflight compliance validation.

Must be called BEFORE every TikTok publish operation (draft or direct).
Raises TikTokComplianceError for blocking violations.
Returns a list of ComplianceWarning for non-blocking advisories.

Design goals:
  • Every check has a unique error_code (machine-readable).
  • is_permanent=True → SheetRunner must NOT retry.
  • is_permanent=False → SheetRunner may retry after delay.
  • No token values are ever included in error messages.

Usage (called inside TikTokPublisher.publish()):
    guard = TikTokComplianceGuard(config)
    warnings = guard.check(task, account)   # raises on violation
    for w in warnings:
        on_log(f"[Compliance] {w.message}", "warning")
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

from core.tiktok.token_store import TikTokAccount


# ─── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ComplianceWarning:
    """Non-blocking advisory — log but do not abort the publish."""
    code:    str
    message: str


@dataclass
class TikTokComplianceError(Exception):
    """
    Blocking compliance violation — abort publish immediately.

    Attributes
    ----------
    error_code   : machine-readable identifier (e.g. "ERR_AUDIT_NOT_APPROVED")
    message      : human-readable explanation (safe to show in UI and logs)
    is_permanent : True → do NOT retry (auth errors, policy violations, etc.)
                   False → may retry after a delay (network, temp server errors)
    """
    error_code:   str
    message:      str
    is_permanent: bool = True

    def __post_init__(self):
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.error_code}] {self.message}"


# ─── Valid enum values ─────────────────────────────────────────────────────────

_VALID_PRIVACY = frozenset({
    "SELF_ONLY",
    "FOLLOWER_OF_CREATOR",
    "MUTUAL_FRIEND_FRIENDS",
    "PUBLIC_TO_EVERYONE",
})

_PUBLIC_PRIVACY = frozenset({
    "PUBLIC_TO_EVERYONE",
    "FOLLOWER_OF_CREATOR",
    "MUTUAL_FRIEND_FRIENDS",
})

# post_type values that trigger the direct-post path
_DIRECT_POST_TYPES = frozenset({"tiktok_direct", "tiktok", "direct"})
_DRAFT_POST_TYPES  = frozenset({"tiktok_draft", "draft"})

# TikTok maximum limits
_MAX_CAPTION_LEN = 2_200
_MAX_TITLE_LEN   = 150
_MAX_VIDEO_BYTES = 4 * 1024 * 1024 * 1024   # 4 GB


# ─── Guard class ───────────────────────────────────────────────────────────────

class TikTokComplianceGuard:
    """
    Preflight validator for TikTok publish operations.

    Parameters
    ----------
    config : dict
        The app config dict (used to read audit flags and limits).
    """

    def __init__(self, config: dict):
        self._cfg = config

    # ── Public entry point ─────────────────────────────────────────────────────

    def check(
        self,
        task: dict,
        account: Optional[TikTokAccount],
    ) -> list[ComplianceWarning]:
        """
        Run all compliance checks for *task* against *account*.

        Returns a (possibly empty) list of ComplianceWarning objects.
        Raises TikTokComplianceError on the FIRST blocking violation found.

        Order of checks (most critical first):
          1.  Account presence
          2.  Token validity / refreshability
          3.  Scope sufficiency
          4.  Video file presence and size
          5.  Caption / title length
          6.  Privacy level validity
          7.  Audit-gate checks (public post without audit approval)
          8.  Publish mode consistency
          9.  user_confirmed_at advisory
          10. is_ai_generated advisory
        """
        warnings: list[ComplianceWarning] = []

        # 1. Account
        self._check_account(account)

        # 2. Token — may raise; if refresh needed, caller handles it
        self._check_token(account)

        # 3. Scopes
        self._check_scopes(task, account, warnings)

        # 4. Video file
        self._check_video(task)

        # 5. Caption / title
        self._check_caption(task, warnings)

        # 6. Privacy level
        privacy = self._check_privacy(task, warnings)

        # 7. Audit gate — most important for TikTok compliance
        self._check_audit_gate(task, privacy)

        # 8. Publish mode consistency
        self._check_publish_mode(task, warnings)

        # 9. user_confirmed_at advisory
        self._check_user_confirmation(task, warnings)

        # 10. AI-generated content advisory
        self._check_ai_disclosure(task, warnings)

        # 11. H1 fix: Spam pre-flight check — TikTok rejects spam-flagged content
        self._check_spam_signals(task, warnings)

        # 12. Sprint TT-5 / F1: video properties pre-flight
        self._check_video_properties(task, warnings)

        # 13. Sprint TT-5 / F2: OAuth scope runtime verification
        # (different from existing _check_scopes which validates Token Store
        # field — this one matches granted scopes vs operation requirements)
        self._check_oauth_scopes(task, account, warnings)

        # 14. Sprint TT-5 / F4: watermark heuristic
        self._check_watermark(task, warnings)

        # 15. Sprint TT-5 / F5: audio rights heuristic
        self._check_audio_rights(task, warnings)

        # 16. Sprint TT-5 / F6: caption + hashtag policy
        self._check_content_policy(task, warnings)

        return warnings

    # ─── Sprint TT-5 checks (F1, F2, F4, F5, F6) ────────────────────────────

    def _check_video_properties(self, task: dict, warnings: list) -> None:
        """F1: ffprobe-backed video metadata pre-flight."""
        if not self._cfg.get("anti_spam_video_validate", True):
            return
        try:
            from core.tiktok.video_validator import validate_video, CheckResult
            report = validate_video(task.get("video_path", ""))
            for item in report.items:
                if item.result is CheckResult.FAIL:
                    raise TikTokComplianceError(
                        error_code=f"ERR_VIDEO_{item.name.upper().replace(' ', '_')}",
                        message=f"Video {item.name}: {item.message}. {item.fix_hint}",
                        is_permanent=True,
                    )
                if item.result is CheckResult.WARN:
                    warnings.append(ComplianceWarning(
                        code=f"VID_WARN_{item.name.upper().replace(' ', '_')}",
                        message=f"Video {item.name}: {item.message}",
                    ))
        except TikTokComplianceError:
            raise
        except Exception as exc:
            # validator should never explode the publish — log and continue
            warnings.append(ComplianceWarning(
                code="VID_VALIDATOR_ERROR",
                message=f"Video validator crash (bỏ qua): {exc}",
            ))

    def _check_oauth_scopes(self, task: dict, account, warnings: list) -> None:
        """F2: verify granted OAuth scopes cover the operation."""
        if not self._cfg.get("anti_spam_scope_verify", True):
            return
        try:
            from core.tiktok.scope_verify import check_scopes
            post_type = str(task.get("post_type", "tiktok_draft")).lower().strip()
            if post_type in _DIRECT_POST_TYPES:
                op = "direct_upload"
            else:
                op = "draft_upload"
            granted = list(getattr(account, "scopes", []) or [])
            # Forgiving: when account has NO scopes field populated (legacy
            # accounts connected before this check existed, or tests with
            # mock objects), skip rather than hard-fail. Real OAuth flows
            # always populate scopes; this preserves back-compat.
            if not granted:
                return
            result = check_scopes(op, granted)
            if not result.ok:
                # Missing scope is permanent — user must reconnect
                raise TikTokComplianceError(
                    error_code="ERR_MISSING_SCOPE",
                    message=result.message,
                    is_permanent=True,
                )

            # Optional: comment scope check (warn only — comment is best-effort)
            comment_text = str(task.get("comment", "") or task.get("tiktok_comment", "")).strip()
            if comment_text:
                c_result = check_scopes("comment_post", granted)
                if not c_result.ok:
                    warnings.append(ComplianceWarning(
                        code="WARN_MISSING_COMMENT_SCOPE",
                        message=(
                            f"Thiếu scope comment.create — comment sẽ bị skip. "
                            f"{c_result.message}"
                        ),
                    ))
        except TikTokComplianceError:
            raise
        except Exception as exc:
            warnings.append(ComplianceWarning(
                code="SCOPE_VERIFY_ERROR",
                message=f"Scope verify crash (bỏ qua): {exc}",
            ))

    def _check_watermark(self, task: dict, warnings: list) -> None:
        """F4: filename + encoder watermark heuristic."""
        if not self._cfg.get("anti_spam_watermark_check", True):
            return
        try:
            from core.tiktok.watermark_detector import detect_watermark
            sig = detect_watermark(task.get("video_path", ""))
            if sig.detected:
                # High-confidence → warn loud. Don't block: user may have
                # intentionally exported with watermark.
                warnings.append(ComplianceWarning(
                    code=f"WARN_WATERMARK_{sig.editor_name.upper().replace(' ', '_')}",
                    message=f"{sig.message}. {sig.fix_hint}",
                ))
        except Exception as exc:
            warnings.append(ComplianceWarning(
                code="WATERMARK_DETECT_ERROR",
                message=f"Watermark detector crash (bỏ qua): {exc}",
            ))

    def _check_audio_rights(self, task: dict, warnings: list) -> None:
        """F5: filename + ID3 audio-rights heuristic."""
        if not self._cfg.get("anti_spam_audio_rights_check", True):
            return
        try:
            from core.tiktok.audio_rights import check_audio_rights
            sig = check_audio_rights(task.get("video_path", ""))
            if sig.risk_level == "high":
                # High-risk → warn but don't block (still user's decision)
                warnings.append(ComplianceWarning(
                    code="WARN_AUDIO_COPYRIGHT_HIGH",
                    message=f"{sig.message}. {sig.fix_hint}",
                ))
            elif sig.risk_level == "medium":
                warnings.append(ComplianceWarning(
                    code="WARN_AUDIO_COPYRIGHT_MEDIUM",
                    message=f"{sig.message}. Tags: {list(sig.detected_tags.keys())}",
                ))
        except Exception as exc:
            warnings.append(ComplianceWarning(
                code="AUDIO_RIGHTS_ERROR",
                message=f"Audio rights check crash (bỏ qua): {exc}",
            ))

    def _check_content_policy(self, task: dict, warnings: list) -> None:
        """F6: caption + hashtag policy enforcer."""
        if not self._cfg.get("anti_spam_content_policy", True):
            return
        try:
            from core.tiktok.content_validator import (
                validate_content, CheckResult as _CR,
            )
            caption = " ".join([
                str(task.get("title", "")),
                str(task.get("description", "")),
                str(task.get("keywords", "")),
            ]).strip()
            extra_banned = set(self._cfg.get("tiktok_banned_hashtags", []) or [])
            report = validate_content(caption, extra_banned=extra_banned)
            for item in report.items:
                if item.result is _CR.FAIL:
                    raise TikTokComplianceError(
                        error_code=f"ERR_CONTENT_{item.name.upper().replace(' ', '_')}",
                        message=f"Caption {item.name}: {item.message}. {item.fix_hint}",
                        is_permanent=True,
                    )
                if item.result is _CR.WARN:
                    warnings.append(ComplianceWarning(
                        code=f"CONTENT_WARN_{item.name.upper().replace(' ', '_')}",
                        message=f"Caption {item.name}: {item.message}",
                    ))
        except TikTokComplianceError:
            raise
        except Exception as exc:
            warnings.append(ComplianceWarning(
                code="CONTENT_POLICY_ERROR",
                message=f"Content policy crash (bỏ qua): {exc}",
            ))

    def _check_spam_signals(self, task: dict, warnings: list) -> None:
        """H1 fix: Run spam pre-flight check on caption/description/hashtags.

        Hard blockers (empty caption when not allowed, >30 hashtags, too long
        caption) raise TikTokComplianceError. Soft signals become warnings.
        """
        from core.tiktok.spam_check import check_post_content

        result = check_post_content(
            caption     = str(task.get("title", "") or task.get("description", "")),
            description = str(task.get("description", "")),
            keywords    = str(task.get("keywords", "")),
            allow_empty_caption = True,   # warn but don't block — many drafts are caption-less
        )

        # Blockers → raise
        if result.is_blocked:
            raise TikTokComplianceError(
                error_code = "spam_signals_detected",
                message    = "Nội dung có dấu hiệu spam: " + "; ".join(result.blockers),
            )

        # Warnings → log
        for w in result.warnings:
            warnings.append(ComplianceWarning(
                code    = "spam_warning",
                message = w,
            ))

    # ── Individual checks ──────────────────────────────────────────────────────

    def _check_account(self, account: Optional[TikTokAccount]):
        if account is None:
            raise TikTokComplianceError(
                error_code   = "ERR_NO_ACCOUNT",
                message      = (
                    "No TikTok account connected. "
                    "Please connect an account in the TikTok Accounts tab."
                ),
                is_permanent = True,
            )

    def _check_token(self, account: TikTokAccount):
        if not account.is_token_valid():
            if not account.is_refresh_valid():
                raise TikTokComplianceError(
                    error_code   = "ERR_TOKEN_EXPIRED_NO_REFRESH",
                    message      = (
                        f"TikTok session for '{account.display_name}' has expired and "
                        "cannot be refreshed automatically. "
                        "Please reconnect this account."
                    ),
                    is_permanent = True,
                )
            # Token expired but refresh is still valid → not a hard error;
            # publisher_service will refresh before calling guard or after.
            # We allow it to continue (refresh happens upstream).

    def _check_scopes(
        self,
        task: dict,
        account: TikTokAccount,
        warnings: list,
    ):
        post_type      = str(task.get("post_type", "tiktok_draft")).lower()
        granted        = set(account.scopes)
        required       = {"video.upload"}

        if post_type in _DIRECT_POST_TYPES:
            required.add("video.publish")

        missing = required - granted
        if missing:
            raise TikTokComplianceError(
                error_code   = "ERR_INSUFFICIENT_SCOPE",
                message      = (
                    f"Missing TikTok permission(s): {', '.join(sorted(missing))}. "
                    "Please disconnect and reconnect your TikTok account to grant "
                    "the required permissions."
                ),
                is_permanent = True,
            )

    def _check_video(self, task: dict):
        video_path = str(task.get("video_path", "")).strip()

        if not video_path:
            raise TikTokComplianceError(
                error_code   = "ERR_NO_VIDEO_PATH",
                message      = "No video file path specified in task.",
                is_permanent = True,
            )

        if not os.path.isfile(video_path):
            raise TikTokComplianceError(
                error_code   = "ERR_VIDEO_NOT_FOUND",
                message      = f"Video file not found: {os.path.basename(video_path)}",
                is_permanent = True,
            )

        size = os.path.getsize(video_path)

        if size == 0:
            raise TikTokComplianceError(
                error_code   = "ERR_VIDEO_EMPTY",
                message      = f"Video file is empty: {os.path.basename(video_path)}",
                is_permanent = True,
            )

        if size > _MAX_VIDEO_BYTES:
            raise TikTokComplianceError(
                error_code   = "ERR_VIDEO_TOO_LARGE",
                message      = (
                    f"Video file is {size / 1e9:.1f} GB, which exceeds "
                    f"TikTok's 4 GB limit."
                ),
                is_permanent = True,
            )

    def _check_caption(self, task: dict, warnings: list) -> None:
        caption = str(task.get("description", "")).strip()
        title   = str(task.get("title",       "")).strip()

        if len(caption) > _MAX_CAPTION_LEN:
            raise TikTokComplianceError(
                error_code   = "ERR_CAPTION_TOO_LONG",
                message      = (
                    f"Caption is {len(caption)} characters, which exceeds "
                    f"TikTok's {_MAX_CAPTION_LEN}-character limit. "
                    "Please shorten the caption."
                ),
                is_permanent = True,
            )

        if len(title) > _MAX_TITLE_LEN:
            raise TikTokComplianceError(
                error_code   = "ERR_TITLE_TOO_LONG",
                message      = (
                    f"Title is {len(title)} characters, which exceeds "
                    f"TikTok's {_MAX_TITLE_LEN}-character limit."
                ),
                is_permanent = True,
            )

        if not caption and not title:
            warnings.append(ComplianceWarning(
                code    = "WARN_NO_CAPTION",
                message = "Neither caption nor title is set. TikTok post will have no text.",
            ))

    def _check_privacy(self, task: dict, warnings: list) -> str:
        """Validate privacy_level. Returns the resolved privacy string."""
        from core.config_validator import get_tiktok_publish_mode

        # Per-post privacy takes precedence; fall back to global config
        privacy_raw = (
            str(task.get("privacy_level", "")).strip()
            or str(task.get("privacy", "")).strip()
            or str(self._cfg.get("tiktok_privacy_level", "SELF_ONLY")).strip()
        )

        # Normalise aliases
        _alias = {
            "public":    "PUBLIC_TO_EVERYONE",
            "followers": "FOLLOWER_OF_CREATOR",
            "friends":   "MUTUAL_FRIEND_FRIENDS",
            "private":   "SELF_ONLY",
            "self_only": "SELF_ONLY",
        }
        privacy = _alias.get(privacy_raw.lower(), privacy_raw.upper())

        if privacy not in _VALID_PRIVACY:
            raise TikTokComplianceError(
                error_code   = "ERR_INVALID_PRIVACY",
                message      = (
                    f"Invalid privacy_level '{privacy_raw}'. "
                    f"Must be one of: {', '.join(sorted(_VALID_PRIVACY))}"
                ),
                is_permanent = True,
            )

        return privacy

    def _check_audit_gate(self, task: dict, privacy: str):
        """
        The most critical compliance check.

        Rules:
        ┌─────────────────────────────┬────────────┬─────────────────────────────┐
        │ post_type                   │ privacy    │ audit_approved needed?       │
        ├─────────────────────────────┼────────────┼─────────────────────────────┤
        │ tiktok_draft                │ any        │ NO                           │
        │ tiktok_direct / tiktok      │ SELF_ONLY  │ NO  (safe for unaudited)    │
        │ tiktok_direct / tiktok      │ PUBLIC/etc │ YES — blocked if not approved│
        └─────────────────────────────┴────────────┴─────────────────────────────┘
        """
        from core.config_validator import is_tiktok_audit_approved, is_direct_post_enabled

        post_type    = str(task.get("post_type", "tiktok_draft")).lower().strip()
        is_direct    = post_type in _DIRECT_POST_TYPES
        is_public    = privacy in _PUBLIC_PRIVACY
        audit_ok     = is_tiktok_audit_approved(self._cfg)
        direct_ok    = is_direct_post_enabled(self._cfg)

        # Block direct post entirely if disabled in config
        if is_direct and not direct_ok:
            raise TikTokComplianceError(
                error_code   = "ERR_DIRECT_POST_DISABLED",
                message      = (
                    "Direct TikTok posting is disabled in settings "
                    "('tiktok_enable_direct_post' = false). "
                    "Use draft upload mode (post_type = tiktok_draft) instead, "
                    "or enable direct posting in Settings → TikTok → Audit Control."
                ),
                is_permanent = True,
            )

        # Block public direct post if audit not approved
        if is_direct and is_public and not audit_ok:
            raise TikTokComplianceError(
                error_code   = "ERR_AUDIT_NOT_APPROVED",
                message      = (
                    f"Cannot post with privacy_level='{privacy}' — "
                    "your TikTok app has not been approved for direct public posting. "
                    "Change privacy to SELF_ONLY for testing, "
                    "or use draft upload mode until your app passes TikTok review."
                ),
                is_permanent = True,
            )

    def _check_publish_mode(self, task: dict, warnings: list):
        """Advisory: warn if post_type and tiktok_publish_mode are inconsistent."""
        from core.config_validator import get_tiktok_publish_mode

        mode     = get_tiktok_publish_mode(self._cfg)
        pt       = str(task.get("post_type", "tiktok_draft")).lower()

        if mode == "draft_upload" and pt in _DIRECT_POST_TYPES:
            warnings.append(ComplianceWarning(
                code    = "WARN_MODE_MISMATCH",
                message = (
                    f"Config 'tiktok_publish_mode' is 'draft_upload' but "
                    f"task post_type is '{pt}'. Task value takes precedence."
                ),
            ))

    def _check_user_confirmation(self, task: dict, warnings: list):
        """Advisory: warn if user_confirmed_at is missing."""
        confirmed_at = str(task.get("user_confirmed_at", "")).strip()
        require      = str(self._cfg.get("tiktok_require_user_confirm", "true")).lower()

        if require in ("true", "1", "yes") and not confirmed_at:
            warnings.append(ComplianceWarning(
                code    = "WARN_NO_USER_CONFIRMATION",
                message = (
                    "This TikTok publish job has no 'user_confirmed_at' timestamp. "
                    "TikTok policy requires explicit user consent before each publish."
                ),
            ))

    def _check_ai_disclosure(self, task: dict, warnings: list):
        """Advisory: remind about AI-generated content disclosure."""
        is_ai = str(task.get("is_ai_generated", task.get("tiktok_is_ai_generated", ""))).strip()
        if is_ai.lower() in ("true", "1", "yes"):
            warnings.append(ComplianceWarning(
                code    = "WARN_AI_CONTENT_FLAGGED",
                message = (
                    "This video is marked as AI-generated. "
                    "TikTok requires disclosure of AI-generated content in the post settings."
                ),
            ))
