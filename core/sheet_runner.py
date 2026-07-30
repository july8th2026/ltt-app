"""
Orchestrator chính: quét Google Sheet → download Drive → upload FB → writeback.
Chạy trong daemon thread; dừng bằng stop_event.

Luồng mỗi job:
  1. sheet_client.get_next_pending_row()
  2. drive_downloader.download(video_url)
  3. thumbnail_fetcher.fetch(thumbnail_url)
  4. upload_engine.run(task)
  5. sheet_client.mark_done / mark_error
  6. post_comment nếu có
  7. Dọn file tạm
  8. Sleep job_delay_seconds
"""

import json
import os
import random
import threading
import time
import traceback
from datetime import datetime, timezone

from core.rate_limiter import QuotaExceededError, RateLimiter
from core.utils import (
    check_stop as _check_stop_fn,
    get_platform_config,
    interruptible_sleep,
)
from utils.drive_downloader import DriveDownloader
from utils import thumbnail_fetcher
from utils.logger import BotLogger
from utils.sheet_client import SheetClient


class SheetRunner:
    """
    Vòng lặp chính điều phối toàn bộ luồng Sheet → Upload.

    Callbacks (đều được gọi từ worker thread, GUI cần dùng self.after):
        on_log(msg, level)         — log entry
        on_status(msg)             — trạng thái ngắn hiển thị trên status bar
        on_job_start(task)         — bắt đầu 1 job mới
        on_job_done(task, link)    — job thành công
        on_job_error(task, error)  — job thất bại
        on_idle()                  — không còn job, đang chờ
        on_stopped()               — đã dừng hẳn
    """

    def __init__(
        self,
        config: dict,
        page_name: str,
        sheet_tab: str,
        stop_event: threading.Event,
        on_log=None,
        on_status=None,
        on_job_start=None,
        on_job_done=None,
        on_job_error=None,
        on_idle=None,
        on_stopped=None,
        rate_limiter: RateLimiter = None,
        platform_filter: str = "",
        sheet_id: str = "",
        page_id: str = "",
        account_id: str = "",
    ):
        self.config          = config
        self.page_name       = page_name
        # Disambiguation IDs — when two accounts share admin on a same-named
        # page, page_name alone returns the wrong (account, token) pair. When
        # page_id is set, the runner uses find_page_by_id() instead of
        # find_page_by_name(), guaranteeing the right token.
        # account_id is informational (for log clarity).
        self.page_id         = (page_id or "").strip()
        self.account_id      = (account_id or "").strip()
        self.sheet_tab       = sheet_tab
        # Per-worker spreadsheet id for multi-sheet mode. Empty string =
        # legacy single-sheet mode (falls back to config["sheet_id"]).
        self.sheet_id        = (sheet_id or "").strip()
        self.stop_event      = stop_event
        # Empty = legacy mode (any platform). "facebook"/"tiktok" = restrict
        # this runner to rows matching that platform only.
        self.platform_filter = (platform_filter or "").strip().lower()

        self.on_log       = on_log       or (lambda m, l: None)
        self.on_status    = on_status    or (lambda m: None)
        self.on_job_start = on_job_start or (lambda t: None)
        self.on_job_done  = on_job_done  or (lambda t, l: None)
        self.on_job_error = on_job_error or (lambda t, e: None)
        self.on_idle      = on_idle      or (lambda: None)
        self.on_stopped   = on_stopped   or (lambda: None)

        self.logger       = BotLogger(callback=self.on_log)
        self._sheet       = SheetClient(config, sheet_id_override=self.sheet_id or None)
        self._downloader  = DriveDownloader(config)
        # BUG #1 fix (audit): use get_platform_config so single-worker mode
        # respects tt_* overrides when platform_filter="tiktok". Previously
        # this fallback path read raw config keys → TikTok single-worker mode
        # silently used FB rate-limit values.
        _p = self.platform_filter or "facebook"
        self._rate_limiter = rate_limiter or RateLimiter(
            max_concurrent             = int(config.get("max_concurrent_uploads_per_page", 1)),
            min_interval_s             = float(get_platform_config(config, _p, "min_interval_per_page_s", 30.0)),
            min_inter_page_interval_s  = float(get_platform_config(config, _p, "min_inter_page_interval_s", 0.0)),
            jitter_s                   = float(get_platform_config(config, _p, "jitter_s", 0.0)),
            active_hours_start         = int(get_platform_config(config, _p, "active_hours_start", 0)),
            active_hours_end           = int(get_platform_config(config, _p, "active_hours_end", 0)),
            max_posts_per_page_per_day    = int(get_platform_config(config, _p, "max_posts_per_page_per_day", 0)),
            max_posts_per_account_per_day = int(get_platform_config(config, _p, "max_posts_per_account_per_day", 0)),
            timezone_name                 = str(config.get("timezone", "Asia/Ho_Chi_Minh")),
        )

        # ── Auto-retry state (K-6) ────────────────────────────────────────────
        self._max_retries  = int(config.get("max_retries", 3))
        # Delay in seconds for each successive attempt (attempt 1, 2, 3+)
        self._retry_delays = [300, 900, 3600]   # 5 min, 15 min, 60 min
        # row_idx → attempt count (how many retries scheduled so far)
        self._retry_attempt: dict[int, int] = {}
        # row_idx → time.time() when retry is allowed
        self._retry_ready: dict[int, float] = {}
        # P2: persistent retry state path (survives bot restart)
        # Multi-sheet: include short sheet_id prefix to avoid collision when
        # two different sheets have a tab with the same name.
        _safe_tab = "".join(c if c.isalnum() or c in "-_" else "_" for c in sheet_tab)
        _sid_for_path = (self.sheet_id or config.get("sheet_id", "") or "default")[:8]
        _safe_sid = "".join(c if c.isalnum() or c in "-_" else "_" for c in _sid_for_path)
        self._retry_state_path = os.path.join(
            "data", f"retry_{_safe_sid}_{_safe_tab}.json"
        )
        self._load_retry_state()

    # ─── Entry point ──────────────────────────────────────────────────────────

    def run(self):
        """Chạy trong daemon thread — gọi start() để khởi động."""
        self.logger.sheet(f"Sheet Runner bắt đầu — tab: {self.sheet_tab}")
        self.on_status("Kết nối Google Sheet...")

        try:
            self._sheet.connect()
            if self.sheet_tab:
                self._sheet.switch_tab(self.sheet_tab)
            self.logger.sheet("Kết nối sheet OK ✓")
        except Exception as e:
            self.logger.error(f"Không thể kết nối sheet: {e}")
            self.on_status(f"❌ Sheet: {str(e)[:60]}")
            self.on_stopped()
            return

        while not self.stop_event.is_set():
            try:
                self._tick()
            except InterruptedError:
                break
            except QuotaExceededError as e:
                # Page hit its daily cap — sleep an hour before next probe so
                # we don't hammer the same exception every 30 s for the rest
                # of the day. (Quota resets at midnight in configured TZ.)
                self.logger.warning(f"⏸ {e}")
                self.on_status("⏸ Quota đạt mức ngày — tạm dừng 1 giờ")
                self._interruptible_sleep(3600)
            except Exception as e:
                self.logger.error(f"Lỗi vòng lặp: {e}")
                self.logger.debug(traceback.format_exc())
                self._interruptible_sleep(30)

        self.logger.done("Sheet Runner đã dừng")
        self.on_status("Đã dừng")
        self.on_stopped()

    # ─── K-6: Auto-retry helpers ──────────────────────────────────────────────

    @staticmethod
    def _is_retryable_error(err: str) -> bool:
        """
        Classify whether an error is worth retrying automatically.
        Non-retryable: auth/token/permission/file errors, user-stop,
                       TikTok compliance violations (is_permanent=True).
        Retryable: network, rate-limit, temporary server errors.
        Default (unclassified): not retried (safer).

        TikTokComplianceError.__str__() → "[ERR_CODE] message", so the
        pattern "[err_" (lowercased) uniquely identifies compliance errors.
        """
        err_lower = err.lower()
        non_retryable_kws = (
            "token", "oauth", "permission", "restricted", "not allowed",
            "expired", "invalid_token", "filenotfounderror", "file không tồn tại",
            "dừng bởi người dùng", "interruptederror",
            # TikTok TikTokComplianceError codes — all have is_permanent=True
            "[err_",
        )
        for kw in non_retryable_kws:
            if kw in err_lower:
                return False
        retryable_kws = (
            "429", "rate limit", "rate_limit", "ratelimit",
            "network", "connection", "timeout", "timed out",
            "temporarily", "try again", "service unavailable",
            "503", "502", "500", "read error", "chunked",
        )
        for kw in retryable_kws:
            if kw in err_lower:
                return True
        return False

    def _get_retry_delay(self, attempt: int) -> float:
        """Delay seconds for the given attempt (1-based). P2: adds ±10% jitter."""
        idx = min(attempt - 1, len(self._retry_delays) - 1)
        base = float(self._retry_delays[idx])
        jitter = random.uniform(-base * 0.1, base * 0.1)
        return max(10.0, base + jitter)

    # ── P2: Retry state persistence ───────────────────────────────────────────

    def _save_retry_state(self):
        """Persist in-memory retry dicts to JSON so restarts don't lose state."""
        try:
            os.makedirs(os.path.dirname(self._retry_state_path), exist_ok=True)
            state = {
                "attempt": {str(k): v for k, v in self._retry_attempt.items()},
                "ready":   {str(k): v for k, v in self._retry_ready.items()},
            }
            with open(self._retry_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as exc:
            self.logger.debug(f"[Retry] Không lưu được trạng thái retry: {exc}")

    def _load_retry_state(self):
        """Load persisted retry state; stale entries (ready < now-1h) are discarded."""
        try:
            if not os.path.exists(self._retry_state_path):
                return
            with open(self._retry_state_path, encoding="utf-8") as f:
                state = json.load(f)
            cutoff = time.time() - 3600  # discard entries older than 1h
            self._retry_attempt = {
                int(k): v for k, v in state.get("attempt", {}).items()
            }
            self._retry_ready = {
                int(k): v for k, v in state.get("ready", {}).items()
                if v > cutoff
            }
            if self._retry_ready:
                self.logger.sheet(
                    f"[Retry] Khôi phục {len(self._retry_ready)} hàng chờ retry từ lần trước"
                )
        except Exception as exc:
            self.logger.debug(f"[Retry] Không đọc được trạng thái retry: {exc}")

    def _process_retries(self):
        """Reset RETRY-marked rows whose delay has elapsed so they get re-queued."""
        if not self._retry_ready:
            return
        now = time.time()
        ready = [r for r, t in self._retry_ready.items() if t <= now]
        for row_idx in ready:
            del self._retry_ready[row_idx]
            attempt = self._retry_attempt.get(row_idx, 1)
            self.logger.sheet(
                f"Thử lại hàng #{row_idx} (lần {attempt}/{self._max_retries})"
            )
            try:
                self._sheet.clear_retry_status(row_idx)
            except Exception as e:
                self.logger.warning(f"Không thể reset trạng thái hàng #{row_idx}: {e}")

    def _tick(self):
        """Một iteration: lấy job → xử lý → delay."""
        self._process_retries()
        self.on_status("Quét hàng chờ trong sheet...")
        try:
            task = self._sheet.get_next_pending_row(
                platform_filter=self.platform_filter,
            )
        except Exception as e:
            self.logger.error(f"Lỗi đọc sheet: {e}")
            self._interruptible_sleep(60)
            return

        if not task:
            pending = self._sheet.count_pending(platform_filter=self.platform_filter)
            msg = f"Không có job — {pending} hàng đang chờ thời gian lên lịch"
            self.logger.sheet(msg)
            self.on_status(msg)
            self.on_idle()
            self._interruptible_sleep(60)
            return

        row_idx = task["row_idx"]
        self.logger.queue(f"Job mới: hàng #{row_idx} — {task.get('title','')[:50]}")
        self.on_job_start(task)
        self._sheet.mark_running(row_idx)

        # ── Session lock (Round 1.1) ──────────────────────────────────────
        # Acquire per-target lock BEFORE download to fail fast when another
        # bot instance is using the same account. Resolved from task without
        # needing TokenStore lookup so we don't pay the cost on every tick.
        _pre_platform = (task.get("platform", "facebook") or "facebook").lower().strip()
        _pre_target = (
            str(task.get("tiktok_account", "") or task.get("account", "")).strip()
            if _pre_platform == "tiktok"
            else (task.get("target_page", "").strip() or self.page_name)
        )
        _session_lock_obj = None
        if (
            self.config.get("anti_spam_session_lock_enabled", True)
            and _pre_target
        ):
            try:
                from core.session_lock import SessionLock, SessionLockError
                _session_lock_obj = SessionLock(
                    account_id=_pre_target, platform=_pre_platform,
                )
                _session_lock_obj.acquire()
            except SessionLockError as _lock_exc:
                self.logger.warning(
                    f"[Session Lock] Hàng #{row_idx} bỏ qua — "
                    f"target '{_pre_target}' đang bị instance khác giữ: {_lock_exc}"
                )
                self._sheet.mark_skipped(
                    row_idx, "Locked by other bot instance",
                )
                self.on_job_done(task, "")
                return
            except Exception as _lock_exc:
                # Never block on lock failure — log and continue
                self.logger.debug(f"[Session Lock] init skipped: {_lock_exc}")
                _session_lock_obj = None

        video_path  = None
        thumb_path  = None
        video_link  = ""
        fb_video_id = ""
        _upload_start = 0.0

        try:
            # ── Tải video từ Drive ──────────────────────────────────────────
            video_url = task.get("video_url", "")
            if not video_url:
                raise ValueError("Cột video_url rỗng — không có gì để tải")

            self.on_status("Đang tải video từ Google Drive...")
            self.logger.drive(f"Tải: {video_url[:60]}...")
            video_path = self._downloader.download(
                video_url,
                on_log=lambda m: self.logger.drive(m),
            )
            self._check_stop()

            # ── Tải thumbnail từ URL ──────────────────────────────────────
            thumb_url = task.get("thumbnail_url", "")
            if thumb_url:
                self.on_status("Tải thumbnail...")
                thumb_path = thumbnail_fetcher.fetch(
                    thumb_url,
                    log=lambda m: self.logger.thumb(m),
                )
            self._check_stop()

            # ── Chuẩn bị task dict cho upload engine ───────────────────────
            # Ưu tiên cột target_page của hàng; fallback về page_name cấu hình
            effective_page = task.get("target_page", "").strip() or self.page_name

            # ── Content dedup (Phase 1.1) ─────────────────────────────────
            # Reject uploads that would re-post the same video to the same
            # target — protects against accidental row duplicates and the
            # strong FB spam signal triggered by repeated content.
            # Disable via config: anti_spam_dedup = false.
            _platform_str = task.get("platform", "facebook").lower().strip() or "facebook"
            _target_for_dedup = (
                str(task.get("tiktok_account", "") or task.get("account", "")).strip()
                if _platform_str == "tiktok"
                else effective_page
            )
            if self.config.get("anti_spam_dedup", True) and _target_for_dedup:
                from core.content_history import get_default_store as _ch_store
                from core.content_history import hash_video_bytes, hash_caption
                from core.perceptual_hash import perceptual_video_hash
                _vh  = hash_video_bytes(video_path)
                _ch  = hash_caption(task.get("title", ""), task.get("description", ""))
                _ph  = perceptual_video_hash(video_path)
                _store = _ch_store()
                # Strict SHA-256 dedup (identical re-uploads)
                if _store.has_been_posted(
                    video_hash=_vh, target_id=_target_for_dedup,
                    platform=_platform_str, within_days=30,
                ):
                    self.logger.warning(
                        f"[Anti-Spam] Hàng #{row_idx} bỏ qua — video đã đăng lên "
                        f"'{_target_for_dedup}' trong 30 ngày qua (SHA duplicate)."
                    )
                    self._sheet.mark_skipped(row_idx, "Duplicate content (SHA)")
                    self.on_job_done(task, "")
                    return
                # Sprint A2: fuzzy perceptual-hash dedup (re-encoded variants)
                _pmatch = _store.has_perceptual_match(
                    _ph, target_id=_target_for_dedup, within_days=30,
                )
                if _pmatch:
                    self.logger.warning(
                        f"[Anti-Spam] Hàng #{row_idx} bỏ qua — video tương đồng "
                        f"(pHash match {_pmatch[:12]}…) đã đăng '{_target_for_dedup}'."
                    )
                    self._sheet.mark_skipped(row_idx, "Duplicate content (pHash)")
                    self.on_job_done(task, "")
                    return
                # Store the pHash on the row for the post-success record_posted call
                self._current_phash = _ph

                # Sprint A3: cross-target duplicate warning. Same SHA on
                # ≥ N different targets recently = page-farm pattern even
                # if no single target has a duplicate. Warns + Telegram.
                try:
                    from datetime import timedelta
                    cutoff_iso = (
                        datetime.now(timezone.utc) - timedelta(days=7)
                    ).isoformat()
                    with _store._connect() as _c:
                        _other_targets = _c.execute(
                            """SELECT DISTINCT target_id FROM content_history
                               WHERE video_hash = ? AND target_id != ?
                                 AND uploaded_at >= ?""",
                            (_vh, _target_for_dedup, cutoff_iso),
                        ).fetchall()
                    if len(_other_targets) >= int(
                        self.config.get("anti_spam_cross_target_warn_threshold", 3)
                    ):
                        targets_str = ", ".join(t[0] for t in _other_targets[:5])
                        self.logger.warning(
                            f"⚠ [Anti-Spam Cross-Target] Video {_vh[:12]}… "
                            f"đã upload {len(_other_targets)} target khác trong 7d: "
                            f"{targets_str}. FB có thể flag page-farm — "
                            f"khuyến nghị variation."
                        )
                        try:
                            from utils.notifier import get_notifier
                            get_notifier().notify_page_throttled(
                                _target_for_dedup,
                                drop_pct=0,   # not a real drop; reuse channel
                            )
                        except Exception:
                            pass
                except Exception as _exc:
                    self.logger.debug(f"[A3] cross-target check skipped: {_exc}")

            # Sprint A4: Video light variation (per-target unique file).
            # Default off (off|metadata_pad|ffmpeg|auto). When enabled, swap
            # the upload path to a varied copy so FB sees different content.
            _variation_mode = str(
                self.config.get("anti_spam_video_variation_mode", "off")
            ).strip().lower()
            if _variation_mode != "off" and _target_for_dedup:
                try:
                    from core.video_variation import vary_video
                    _vr = vary_video(
                        video_path, _target_for_dedup, mode=_variation_mode,
                    )
                    if _vr.changed:
                        self.logger.upload(
                            f"[Anti-Spam Variation] {_vr.method} → {_vr.out_path}"
                        )
                        video_path = _vr.out_path
                except Exception as _exc:
                    self.logger.debug(f"[A4] variation skipped: {_exc}")

            # Sprint A1: caption auto-rotation. Builds a per-(target, video, day)
            # deterministic variant so retries reproduce identical text, and
            # different target/day combos look different to FB.
            _final_title = task.get("title", "")
            _final_desc  = task.get("description", "")
            if self.config.get("caption_rotator_enabled", True) and _target_for_dedup:
                try:
                    from core.caption_rotator import (
                        CaptionRotator, CaptionRotationConfig,
                    )
                    rotator = CaptionRotator(
                        CaptionRotationConfig.from_app_config(self.config)
                    )
                    _seed_hash = locals().get("_ph", "") or locals().get("_vh", "")
                    _final_title = rotator.variant_for(
                        _final_title,
                        target_id=_target_for_dedup, video_hash=_seed_hash,
                    )
                    _final_desc  = rotator.variant_for(
                        _final_desc,
                        target_id=_target_for_dedup, video_hash=_seed_hash,
                    )
                except Exception as _exc:
                    # Never block on caption rotation; fall through to original.
                    self.logger.debug(f"[CaptionRotator] skipped: {_exc}")

            upload_task = {
                "video_path":  video_path,
                "page":        effective_page,
                # Disambiguation IDs — upload_engine uses page_id (unique) for
                # token lookup when set, avoiding the page-name collision bug
                # where two accounts admin the same Page.
                "page_id":     self.page_id,
                "account_id":  self.account_id,
                "title":       _final_title,
                "description": _final_desc,
                "keywords":    task.get("keywords", ""),
                "thumbnail":   thumb_path or "",
                "privacy":     "Công khai",
                "schedule":    task.get("schedule", ""),        # P0: forward schedule
                "post_type":   task.get("post_type", "feed"),   # P0: forward post_type
                "comment":     task.get("comment", ""),          # P0: let engine handle
                "row_idx":     row_idx,                          # P7: audit log tracing
            }

            # ── Upload (platform-agnostic via publisher registry) ───────────
            _platform = task.get("platform", "facebook").lower().strip() or "facebook"

            # TikTok-specific fields: forward per-row columns and remove the
            # Facebook-specific "privacy" key so ComplianceGuard reads the
            # correct TikTok privacy_level (falls back to config if not set).
            _tiktok_confirmed_at_was_empty = False
            if _platform == "tiktok":
                # BUG-01 fix: sheet uses "tiktok_account" column; fall back to "account"
                upload_task["account"] = (
                    str(task.get("account", "")).strip()
                    or str(task.get("tiktok_account", "")).strip()
                )
                upload_task["privacy_level"] = (
                    str(task.get("privacy_level", "")).strip()
                    or str(task.get("tiktok_privacy_level", "")).strip()
                )
                # Read existing user_confirmed_at from sheet row
                _existing_confirmed = (
                    str(task.get("user_confirmed_at", "")).strip()
                    or str(task.get("tiktok_confirmed_at", "")).strip()
                )
                upload_task["user_confirmed_at"] = _existing_confirmed
                # Track whether it was empty so we auto-fill after publish
                _tiktok_confirmed_at_was_empty = not _existing_confirmed
                upload_task["is_ai_generated"] = (
                    str(task.get("is_ai_generated", "")).strip()
                    or str(task.get("tiktok_is_ai_generated", "")).strip()
                )
                upload_task["tiktok_commercial_content"] = (
                    str(task.get("tiktok_commercial_content", "")).strip()
                )
                # Per-post interaction overrides (sheet can override global config)
                for _flag in ("tiktok_disable_duet", "tiktok_disable_comment",
                               "tiktok_disable_stitch"):
                    _val = str(task.get(_flag, "")).strip()
                    if _val:
                        upload_task[_flag] = _val
                # Stage 7: optional first comment (auto-pinned-style)
                # Reads col_comment from sheet — same key used for Facebook.
                upload_task["comment"] = (
                    str(task.get("comment", "")).strip()
                    or str(task.get("tiktok_comment", "")).strip()
                )
                # Remove FB-specific privacy value; ComplianceGuard uses privacy_level
                upload_task.pop("privacy", None)

            self.on_status(f"Đang upload lên {_platform.title()}...")

            # ── Page warm-up cap (Phase 3.2) ─────────────────────────────
            # New FB pages get heavier spam scrutiny. Apply the recommended
            # daily cap from the warm-up curve. Skip the row (mark_skipped)
            # when today's count for this page already meets the cap.
            # FB only — TikTok doesn't have a page concept here.
            if (
                _platform == "facebook"
                and self.config.get("anti_spam_warmup_enabled", True)
                and _target_for_dedup
            ):
                try:
                    from core.token_store import get_default_store as _ts
                    from core.page_warmup import (
                        get_warmup_advice, effective_daily_cap,
                    )
                    from core.graph_client import GraphClient
                    from core.utils import graph_api_version
                    # Prefer page_id (unambiguous) over page_name when worker
                    # has been configured with the new disambiguated identity.
                    _store_for_warmup = _ts()
                    if self.page_id:
                        account, page = _store_for_warmup.find_page_by_id(self.page_id)
                    else:
                        account, page = _store_for_warmup.find_page_by_name(effective_page)
                    if page is not None:
                        gc = GraphClient(version=graph_api_version(self.config))
                        advice = get_warmup_advice(
                            page.id,
                            graph_client       = gc,
                            page_access_token  = page.access_token,
                        )
                        user_cap = int(self.config.get("max_posts_per_page_per_day", 0))
                        cap = effective_daily_cap(advice, user_cap)
                        if cap > 0:
                            today = self._rate_limiter.daily_count(effective_page)
                            if today >= cap:
                                self.logger.warning(
                                    f"[Anti-Spam Warmup] '{effective_page}' "
                                    f"({advice.age_days}d age) đạt cap {today}/{cap} "
                                    f"hôm nay → bỏ qua hàng #{row_idx}"
                                )
                                self._sheet.mark_skipped(
                                    row_idx,
                                    f"Warmup cap ({advice.age_days}d, {today}/{cap})",
                                )
                                self.on_job_done(task, "")
                                return
                except Exception as _exc:
                    # Never block on warmup check errors — log and continue
                    self.logger.debug(f"[Warmup] check skipped: {_exc}")

            # ── TikTok account warm-up (Sprint TT-1.2) ────────────────────
            # Parallel to the FB warm-up above but uses audit-log first-seen
            # as the age proxy (TikTok API doesn't expose creation time).
            if (
                _platform == "tiktok"
                and self.config.get("anti_spam_warmup_enabled", True)
                and _target_for_dedup
            ):
                try:
                    from core.tiktok.account_warmup import (
                        get_warmup_advice as _tt_warmup,
                        effective_daily_cap as _tt_eff_cap,
                    )
                    _tt_advice = _tt_warmup(_target_for_dedup)
                    _tt_user_cap = int(self.config.get(
                        "tt_max_posts_per_account_per_day",
                        self.config.get("max_posts_per_page_per_day", 0),
                    ))
                    _tt_cap = _tt_eff_cap(_tt_advice, _tt_user_cap)
                    if _tt_cap > 0:
                        _tt_today = self._rate_limiter.daily_count(_target_for_dedup)
                        if _tt_today >= _tt_cap:
                            self.logger.warning(
                                f"[TT Warmup] '{_target_for_dedup}' "
                                f"({_tt_advice.age_days}d) đạt cap {_tt_today}/{_tt_cap} "
                                f"→ bỏ qua hàng #{row_idx}"
                            )
                            self._sheet.mark_skipped(
                                row_idx,
                                f"TT warmup cap ({_tt_advice.age_days}d)",
                            )
                            self.on_job_done(task, "")
                            return
                except Exception as _exc:
                    self.logger.debug(f"[TT Warmup] skipped: {_exc}")

            # ── Circuit breaker check (Phase 1.3) ────────────────────────
            # Block the publish if the breaker for this account is OPEN.
            # Key uses platform+target so FB and TT pause independently and
            # so a healthy page is unaffected by a sibling's failures.
            if self.config.get("anti_spam_circuit_breaker", True) and _target_for_dedup:
                from core.circuit_breaker import (
                    get_default_breaker as _cb_default,
                )
                _cb_key = f"{_platform}:{_target_for_dedup}"
                _breaker = _cb_default()
                if not _breaker.allow(_cb_key):
                    remain = _breaker.seconds_until_allowed(_cb_key)
                    self.logger.warning(
                        f"[CircuitBreaker] OPEN → '{_cb_key}'. "
                        f"Còn {remain:.0f}s nữa mới retry. Bỏ qua hàng #{row_idx}."
                    )
                    self._sheet.mark_skipped(
                        row_idx, f"Circuit breaker OPEN ({remain:.0f}s)",
                    )
                    self.on_job_done(task, "")
                    return
            else:
                _cb_key = ""

            from core.publisher_registry import get_publisher
            _publisher = get_publisher(
                platform     = _platform,
                config       = self.config,
                stop_event   = self.stop_event,
                on_log       = self.on_log,
                on_status    = self.on_status,
                rate_limiter = self._rate_limiter,
            )
            # P1: measure accurate upload-only time via global metrics delta
            from core.rate_limiter import get_global_page_metrics
            _metrics_before = get_global_page_metrics()
            _wall_start = time.time()
            _pub_result = _publisher.publish(upload_task)
            _wall_elapsed = time.time() - _wall_start
            _metrics_after = get_global_page_metrics()
            _delta_upload = (
                _metrics_after.get(effective_page, {}).get("total_upload_s", 0)
                - _metrics_before.get(effective_page, {}).get("total_upload_s", 0)
            )
            duration_s  = round(_delta_upload if _delta_upload > 0 else _wall_elapsed, 1)
            video_link  = _pub_result.external_post_url
            fb_video_id = _pub_result.external_post_id

            # P1: timezone-aware uploaded_at (respect user's config timezone)
            try:
                from zoneinfo import ZoneInfo
                _tz = ZoneInfo(self.config.get("timezone", "Asia/Ho_Chi_Minh"))
            except Exception:
                from datetime import timezone as _tzmod
                _tz = _tzmod.utc
            uploaded_at = datetime.now(_tz).strftime("%Y-%m-%d %H:%M:%S")

            # For TikTok: determine fine-grained status for col_tiktok_status.
            # DRAFT_UPLOADED → inbox draft (needs creator action in TikTok app)
            # PRIVATE_POSTED → direct post visible only to creator (SELF_ONLY)
            # FOLLOWERS_POSTED → visible to followers (FOLLOWER_OF_CREATOR)
            # PUBLISHED → public or mutual-friends post
            _tiktok_status = ""
            if _platform == "tiktok":
                _privacy_lvl = str(upload_task.get("privacy_level", "SELF_ONLY")).strip()
                if _pub_result.status == "draft":
                    _tiktok_status = "DRAFT_UPLOADED"
                elif _privacy_lvl == "SELF_ONLY":
                    _tiktok_status = "PRIVATE_POSTED"
                elif _privacy_lvl == "FOLLOWER_OF_CREATOR":
                    _tiktok_status = "FOLLOWERS_POSTED"
                else:
                    _tiktok_status = "PUBLISHED"

            # For TikTok: if tiktok_confirmed_at was empty in the sheet, write
            # the publish timestamp as the audit-trail consent record.
            _confirmed_at_to_write = uploaded_at if _tiktok_confirmed_at_was_empty else ""
            self._sheet.mark_done(
                row_idx, video_link,
                fb_video_id=fb_video_id,
                uploaded_at=uploaded_at,
                duration_s=duration_s,
                platform=_platform,
                confirmed_at=_confirmed_at_to_write,
                tiktok_status=_tiktok_status,
            )
            self.logger.success(
                f"Hàng #{row_idx} DONE — {video_link} "
                f"(id={fb_video_id}, {duration_s:.0f}s)"
            )
            # Record circuit-breaker success — closes HALF_OPEN state quickly
            # and resets cooldown for the next failure burst.
            if _cb_key:
                try:
                    from core.circuit_breaker import get_default_breaker as _cb_default
                    _cb_default().record_success(_cb_key)
                except Exception:
                    pass

            # Record into content-history so future runs can detect duplicates.
            # Wrapped in try/except: a logging failure must never roll back a
            # successful upload.
            if self.config.get("anti_spam_dedup", True) and _target_for_dedup:
                try:
                    from core.content_history import (
                        get_default_store as _ch_store,
                        hash_video_bytes, hash_caption,
                    )
                    from core.perceptual_hash import perceptual_video_hash
                    _ch_store().record_posted(
                        video_hash   = hash_video_bytes(video_path),
                        caption_hash = hash_caption(
                            task.get("title", ""), task.get("description", "")
                        ),
                        target_id    = _target_for_dedup,
                        platform     = _platform,
                        publish_id   = fb_video_id or video_link,
                        # Sprint A2: persist pHash for fuzzy dedup on future uploads
                        p_hash       = locals().get("_current_phash", "") or perceptual_video_hash(video_path),
                    )
                except Exception as _exc:
                    self.logger.debug(
                        f"[Anti-Spam] content_history.record_posted failed (non-fatal): {_exc}"
                    )
            # Clear any retry tracking for this row
            self._retry_attempt.pop(row_idx, None)
            self._retry_ready.pop(row_idx, None)
            self._save_retry_state()
            self.on_job_done(task, video_link)
            # NOTE: comment is forwarded to engine via upload_task["comment"]
            # Engine posts it for feed; skips for reels. No duplicate here.

        except InterruptedError:
            self._sheet.mark_error(row_idx, "Dừng bởi người dùng")
            raise

        except Exception as e:
            err = str(e)
            effective_page = task.get("target_page", "").strip() or self.page_name
            attempt = self._retry_attempt.get(row_idx, 0) + 1

            # Record circuit-breaker failure — drives the OPEN-state decision.
            # Guarded by hasattr so we don't NameError if exception fired
            # before _cb_key was assigned (e.g. download failure).
            if locals().get("_cb_key"):
                try:
                    from core.circuit_breaker import get_default_breaker as _cb_default
                    _br = _cb_default()
                    _state_before = _br.state(_cb_key)
                    _br.record_failure(_cb_key)
                    _state_after  = _br.state(_cb_key)
                    # GAP-7: notify Telegram only on CLOSED→OPEN transition
                    # (avoids spam on every subsequent failure in the same cycle).
                    if _state_before == "closed" and _state_after == "open":
                        try:
                            from utils.notifier import get_notifier
                            get_notifier().notify_circuit_open(
                                _cb_key, _br.seconds_until_allowed(_cb_key),
                            )
                        except Exception:
                            pass
                except Exception:
                    pass

            # GAP-7: notify on FB abuse-grade errors (368/322). These have
            # different cooldown semantics from circuit breaker so we alert
            # even if the breaker didn't trip yet.
            try:
                from core.graph_client import GraphError
                if isinstance(e, GraphError):
                    from core.adaptive_backoff import is_abuse_signal
                    if is_abuse_signal(getattr(e, "code", 0)):
                        from utils.notifier import get_notifier
                        get_notifier().notify_abuse_signal(
                            target     = locals().get("_target_for_dedup", "?"),
                            error_code = str(getattr(e, "code", "?")),
                            message    = str(e)[:200],
                        )
            except Exception:
                pass

            if self._is_retryable_error(err) and attempt <= self._max_retries:
                # Schedule retry with jitter (P2)
                self._retry_attempt[row_idx] = attempt
                delay = self._get_retry_delay(attempt)
                self._retry_ready[row_idx] = time.time() + delay
                delay_min = delay / 60
                self.logger.warning(
                    f"Hàng #{row_idx} lỗi tạm thời (lần {attempt}/{self._max_retries}), "
                    f"thử lại sau {delay_min:.0f} phút: {err[:80]}"
                )
                self._sheet.mark_retry(row_idx, attempt, self._max_retries, err)
                self._save_retry_state()  # P2: persist
            else:
                # Permanent failure (non-retryable or max retries exceeded)
                self._retry_attempt.pop(row_idx, None)
                self._retry_ready.pop(row_idx, None)
                self._save_retry_state()  # P2: persist
                self.logger.error(f"Hàng #{row_idx} lỗi: {err}")
                self._sheet.mark_error(row_idx, err)
                self.on_job_error(task, err)
                try:
                    from utils.notifier import get_notifier
                    get_notifier().notify_job_error(effective_page, row_idx, err)
                except Exception as _notify_err:
                    # MEH-02 fix: log instead of silently swallowing notifier failures
                    self.logger.debug(
                        "Notifier.notify_job_error thất bại (bỏ qua): %s", _notify_err
                    )

        finally:
            # ── Release session lock (Round 1.1) ────────────────────────────
            if _session_lock_obj is not None:
                try:
                    _session_lock_obj.release()
                except Exception as _exc:
                    self.logger.debug(f"[Session Lock] release: {_exc}")

            # ── Dọn file tạm ────────────────────────────────────────────────
            if self.config.get("delete_video_after_upload", True) and video_path:
                DriveDownloader.delete(video_path)
                self.logger.drive(f"Đã xóa file tạm: {os.path.basename(video_path or '')}")

        # ── Delay trước job tiếp theo ──────────────────────────────────────
        delay = int(self.config.get("job_delay_seconds", 900))
        self.logger.sheet(f"Hoàn thành. Chờ {delay}s trước job tiếp theo...")
        self.on_status(f"Chờ {delay}s...")
        self._interruptible_sleep(delay)

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _post_comment_safe(self, video_url: str, comment: str, page_name: str = ""):
        """Đăng comment qua Graph API."""
        self.logger.fb("Đăng comment...")
        if not page_name:
            return
        try:
            from core.token_store import TokenStore
            from core.graph_uploader import GraphUploader
            ts = TokenStore()
            account, page = ts.find_page_by_name(page_name)
            if account and page and account.is_token_valid():
                video_id = video_url.rstrip("/").split("/")[-1]
                uploader = GraphUploader(
                    account=account, page=page,
                    config=self.config, stop_event=self.stop_event,
                    logger=self.logger,
                )
                uploader.post_comment(video_id, comment)
        except Exception as e:
            self.logger.warning(f"Lỗi đăng comment: {e}")

    def _interruptible_sleep(self, seconds: float):
        interruptible_sleep(self.stop_event, seconds)

    def _check_stop(self):
        _check_stop_fn(self.stop_event)


class SheetRunnerThread:
    """
    Bọc SheetRunner trong daemon thread.
    Giao diện duy nhất ra ngoài: start() / stop() / is_running.
    """

    def __init__(self, runner: SheetRunner):
        self._runner = runner
        self._thread: threading.Thread | None = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._runner.run, daemon=True)
        self._thread.start()

    def stop(self):
        self._runner.stop_event.set()

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
