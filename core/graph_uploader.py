"""
Facebook Graph API Resumable Video Uploader.

Upload flow (3-phase):
  start    → POST /{page_id}/videos?upload_phase=start&file_size=N
  transfer → POST /{page_id}/videos?upload_phase=transfer (loop per chunk)
  finish   → POST /{page_id}/videos?upload_phase=finish + metadata

Advantages over Selenium:
  - Resume on network drop (start from last start_offset)
  - 3-5x faster than browser upload
  - Zero bot-detection risk
  - Concurrent uploads possible
"""
from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

from core.graph_client import GraphClient, GraphError
from core.token_store import AccountInfo, PageInfo
from core.utils import (
    build_description,
    check_stop as _check_stop_fn,
    graph_api_version,
    interruptible_sleep,
    parse_schedule,
)
from utils.logger import BotLogger

CHUNK_SIZE = 8 * 1024 * 1024       # 8 MB per chunk
MAX_RETRIES_CHUNK = 3               # retries per chunk on network error

# Status-poll timeout scaling: 60s base + 1s per 5 MB, capped at 600s (10 min)
_STATUS_TIMEOUT_BASE_S    = 60
_STATUS_TIMEOUT_PER_MB_S  = 0.2     # 1 second per 5 MB
_STATUS_TIMEOUT_MAX_S     = 600


def _compute_status_timeout(file_size_bytes: int) -> int:
    """Scale the wait-for-ready timeout by file size.

    A 100 MB video → 80 s; 500 MB → 160 s; 2 GB → 460 s; ≥3 GB → 600 s cap.
    The 120 s hardcoded default was too tight for videos > 300 MB on slow
    FB processing windows.
    """
    mb = max(0, file_size_bytes) / (1024 * 1024)
    estimated = _STATUS_TIMEOUT_BASE_S + int(mb * _STATUS_TIMEOUT_PER_MB_S)
    return min(estimated, _STATUS_TIMEOUT_MAX_S)


class GraphUploader:
    """
    Uploads a single video to a Facebook Page via Graph API resumable upload.
    Pass stop_event to support cancellation.
    """

    def __init__(
        self,
        account: AccountInfo,
        page: PageInfo,
        config: dict,
        stop_event: threading.Event,
        logger: BotLogger,
        on_status: Callable[[str], None] = None,
        on_progress: Callable[[int, int], None] = None,
    ):
        self.account     = account
        self.page        = page
        self.config      = config
        self.stop_event  = stop_event
        self.logger      = logger
        self.on_status   = on_status   or (lambda m: None)
        self.on_progress = on_progress or (lambda done, total: None)

        self._client = GraphClient(
            version=graph_api_version(config), timeout=120, max_retries=3,
            # Round 1.4: per-account UA / proxy when network_identity_enabled
            account_id=str(getattr(account, "fb_user_id", "") or ""),
            config=config,
        )

    # ─── Public: upload ───────────────────────────────────────────────────────

    def upload(self, task: dict) -> tuple[str, str]:
        """
        Full upload flow. Returns (video_url, video_id) on success.
        task keys: video_path, title, description, keywords, thumbnail, schedule
        """
        video_path = task.get("video_path", "")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"File video không tồn tại: {video_path}")

        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError(f"File video rỗng (0 bytes): {video_path}")

        fname = os.path.basename(video_path)

        self.logger.upload(
            f"[API] Bắt đầu upload: {fname} "
            f"({file_size / (1024*1024):.1f} MB) → Page: {self.page.name}"
        )
        self.on_status(f"[API] Khởi tạo phiên upload: {fname}")

        # ── 1. Start session ───────────────────────────────────────────────
        session_id, video_id = self._start_session(file_size)
        self.logger.upload(f"[API] Session: {session_id}, video_id: {video_id}")

        # ── 2. Transfer chunks ────────────────────────────────────────────
        self._transfer_chunks(video_path, file_size, session_id)

        # ── 3. Finish + metadata ──────────────────────────────────────────
        self.on_status("[API] Hoàn tất và đăng video...")
        result = self._finish_session(session_id, task)
        final_vid = result.get("video_id") or video_id

        # ── 4. Thumbnail ──────────────────────────────────────────────────
        thumb = task.get("thumbnail", "")
        if thumb and os.path.exists(os.path.abspath(thumb)):
            try:
                self.on_status("[API] Upload thumbnail...")
                self._upload_thumbnail(final_vid, os.path.abspath(thumb))
                self.logger.thumb("[API] Thumbnail OK")
            except Exception as exc:
                self.logger.warning(f"[API] Thumbnail thất bại (bỏ qua): {exc}")

        # ── 5. Verify video status (optional) ────────────────────────────
        ready = False
        if self.config.get("verify_video_after_upload", True):
            timeout_s = _compute_status_timeout(file_size)
            ready = self._wait_for_video_ready(final_vid, timeout_s=timeout_s)

        # ── 6. Build URL — prefer canonical permalink_url when video ready
        video_url = ""
        if ready:
            video_url = self._try_fetch_permalink(final_vid)
        if not video_url:
            video_url = f"https://www.facebook.com/{self.page.id}/videos/{final_vid}"

        self.logger.success(f"[API] Upload xong: {video_url}")
        self.on_status(f"[API] Xong: {video_url}")
        return video_url, final_vid

    # ─── Public: comment ──────────────────────────────────────────────────────

    def post_comment(self, video_id: str, comment_text: str):
        """Post a comment on the video using Graph API."""
        if not comment_text or not comment_text.strip():
            return
        try:
            self._client.post(
                f"{video_id}/comments",
                data={"message": comment_text.strip()},
                token=self.page.access_token,
            )
            self.logger.success(f"[API] Comment đăng OK: {comment_text[:40]}...")
        except GraphError as exc:
            self.logger.warning(f"[API] Comment thất bại: {exc}")

    # ─── Private: upload phases ───────────────────────────────────────────────

    def _start_session(self, file_size: int) -> tuple[str, str]:
        resp = self._client.post(
            f"{self.page.id}/videos",
            data={
                "upload_phase": "start",
                "file_size":    str(file_size),
            },
            token=self.page.access_token,
            video_endpoint=True,
        )
        session_id = resp.get("upload_session_id", "")
        video_id   = resp.get("video_id", "")
        if not session_id:
            from utils.logger import safe_response_repr
            raise RuntimeError(
                f"[API] Không nhận được upload_session_id: {safe_response_repr(resp)}"
            )
        return session_id, video_id

    def _transfer_chunks(self, video_path: str, file_size: int, session_id: str):
        """
        Transfer video file in chunks.
        Queries current offsets each time to support resume after network drop.
        """
        start_offset = 0

        with open(video_path, "rb") as f:
            while start_offset < file_size:
                self._check_stop()

                end_offset = min(start_offset + CHUNK_SIZE, file_size)
                chunk_size = end_offset - start_offset

                f.seek(start_offset)
                chunk = f.read(chunk_size)

                pct = int(start_offset / file_size * 100) if file_size > 0 else 0
                self.logger.upload(
                    f"[API] Chunk {start_offset/(1024*1024):.1f}–"
                    f"{end_offset/(1024*1024):.1f} MB  ({pct}%)"
                )
                self.on_status(f"[API] Upload {pct}% ({end_offset/(1024*1024):.0f}/{file_size/(1024*1024):.0f} MB)...")

                resp = self._post_chunk_with_retry(session_id, start_offset, chunk)

                new_start = int(resp.get("start_offset", end_offset))
                new_end   = int(resp.get("end_offset",   file_size))

                self.on_progress(new_start, file_size)

                if new_start >= file_size or new_start == new_end:
                    break   # All chunks received

                start_offset = new_start

        self.logger.upload("[API] Tất cả chunk đã truyền xong")

    def _post_chunk_with_retry(
        self, session_id: str, start_offset: int, chunk: bytes
    ) -> dict:
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES_CHUNK):
            self._check_stop()
            try:
                resp = self._client.post_multipart(
                    f"{self.page.id}/videos",
                    data={
                        "upload_phase":      "transfer",
                        "upload_session_id": session_id,
                        "start_offset":      str(start_offset),
                    },
                    files={
                        "video_file_chunk": (
                            "chunk.bin", chunk, "application/octet-stream"
                        )
                    },
                    token=self.page.access_token,
                    video_endpoint=True,
                )
                return resp
            except GraphError as exc:
                # P2.1 Adaptive backoff: rate-limit / abuse signals MUST NOT
                # be retried inline. Re-raise so the job-level retry (sheet
                # runner) can apply the proper hours-long cool-down. Chunk-
                # level retry is only useful for transient network blips.
                from core.adaptive_backoff import get_backoff_for_fb_error
                if exc.is_token_error() or exc.is_page_restricted():
                    raise
                policy = get_backoff_for_fb_error(getattr(exc, "code", 0))
                if policy.severity in ("rate", "abuse", "permanent"):
                    self.logger.warning(
                        f"[API] FB error {exc.code} ({policy.severity}) — "
                        f"abort chunk retry, escalate to job-level: {policy.description}"
                    )
                    raise
                last_exc = exc
            except Exception as exc:
                last_exc = exc

            # Transient errors only reach here. Use adaptive cooldown if we
            # have a known code, capped at 120 s to avoid blocking the
            # upload pipeline for too long inside the chunk loop.
            wait = 5 * (attempt + 1)
            if isinstance(last_exc, GraphError):
                from core.adaptive_backoff import get_backoff_for_fb_error
                policy = get_backoff_for_fb_error(getattr(last_exc, "code", 0))
                wait = min(policy.cooldown_s, 120.0) or wait
            self.logger.warning(
                f"[API] Chunk thất bại lần {attempt+1}/{MAX_RETRIES_CHUNK}, "
                f"retry sau {wait:.0f}s: {last_exc}"
            )
            self._sleep(wait)

        raise RuntimeError(
            f"[API] Chunk upload thất bại sau {MAX_RETRIES_CHUNK} lần: {last_exc}"
        )

    def _finish_session(self, session_id: str, task: dict) -> dict:
        data: dict = {
            "upload_phase":      "finish",
            "upload_session_id": session_id,
        }

        title = task.get("title", "")
        if title:
            data["title"] = title

        desc_raw  = task.get("description", "")
        keywords  = task.get("keywords", "")
        full_desc = build_description(desc_raw, keywords)
        if full_desc:
            data["description"] = full_desc

        schedule = task.get("schedule", "")
        if schedule:
            dt = parse_schedule(schedule)
            if dt and dt.timestamp() > time.time():
                data["published"]              = "false"
                data["scheduled_publish_time"] = str(int(dt.timestamp()))
            else:
                data["published"] = "true"
        else:
            data["published"] = "true"

        try:
            resp = self._client.post(
                f"{self.page.id}/videos",
                data=data,
                token=self.page.access_token,
                video_endpoint=True,
            )
        except GraphError as exc:
            raise GraphError(
                f"[finish phase] {exc}",
                code=exc.code, subcode=exc.subcode,
                fbtrace_id=exc.fbtrace_id, raw=exc.raw,
            ) from exc
        return resp

    def _wait_for_video_ready(self, video_id: str, timeout_s: int = 120) -> bool:
        """
        Poll /{video_id}?fields=status until processing completes or times out.

        Returns True when FB reports video_status == "ready"; False on timeout.
        Raises RuntimeError if video ends in 'error' state.

        Caller decides whether to trust the constructed URL (False/timeout)
        or fetch the canonical permalink_url (True).
        """
        self.on_status("[API] Chờ Facebook xử lý video...")
        deadline = time.time() + timeout_s
        poll_interval = 5
        # Retry budget for transient errors during poll — don't give up after a single 5xx.
        consecutive_errors = 0
        _MAX_POLL_ERRORS = 3
        # Dedupe: chỉ log khi status string thay đổi. FB Graph API thường KHÔNG
        # populate processing_progress (đặc biệt Reels), gây log spam 30+ dòng
        # "processing (0%)" giống hệt nhau. Ta nén lại còn 1 dòng đầu + 1 dòng cuối.
        last_logged: str = ""

        while time.time() < deadline:
            self._check_stop()
            try:
                resp = self._client.get(
                    video_id,
                    params={"fields": "status"},
                    token=self.page.access_token,
                )
                consecutive_errors = 0
                status = resp.get("status", {})
                video_status = status.get("video_status", "processing")
                # Ẩn % khi giá trị 0/thiếu — FB ít khi điền field này nên hiện
                # "(0%)" liên tục là gây nhiễu, không phản ánh tiến độ thật.
                try:
                    progress = int(status.get("processing_progress", 0) or 0)
                except (TypeError, ValueError):
                    progress = 0
                progress_str = f" ({progress}%)" if progress > 0 else ""

                line = f"[API] Video status: {video_status}{progress_str}"
                if line != last_logged:
                    self.logger.upload(line)
                    last_logged = line
                # Status bar luôn refresh (tần suất thấp, không spam như log)
                self.on_status(
                    f"[API] Xử lý video: {video_status}{progress_str}..."
                )

                if video_status == "ready":
                    self.logger.success("[API] Video ready ✓")
                    return True
                if video_status == "error":
                    errors = resp.get("status", {}).get("processing_errors", [])
                    raise RuntimeError(
                        f"Facebook từ chối video sau khi upload: {errors}"
                    )
            except (RuntimeError, InterruptedError):
                raise
            except GraphError as exc:
                consecutive_errors += 1
                if exc.is_token_error() or exc.is_page_restricted():
                    # Permanent: token revoked, page restricted — stop polling.
                    self.logger.warning(f"[API] Status poll bị từ chối: {exc}")
                    return False
                if consecutive_errors >= _MAX_POLL_ERRORS:
                    self.logger.warning(
                        f"[API] Status poll thất bại {consecutive_errors} lần liên tiếp, "
                        f"bỏ poll: {exc}"
                    )
                    return False
                self.logger.warning(
                    f"[API] Status poll lỗi tạm ({consecutive_errors}/{_MAX_POLL_ERRORS}): {exc}"
                )
            except Exception as exc:
                consecutive_errors += 1
                if consecutive_errors >= _MAX_POLL_ERRORS:
                    self.logger.warning(
                        f"[API] Status poll lỗi {consecutive_errors} lần, bỏ poll: {exc}"
                    )
                    return False
                self.logger.warning(f"[API] Lỗi kiểm tra status: {exc}")

            interruptible_sleep(self.stop_event, poll_interval)

        self.logger.warning(
            f"[API] Timeout chờ video ready ({timeout_s}s) — "
            "video vẫn đang xử lý trên máy chủ Facebook"
        )
        return False

    def _try_fetch_permalink(self, video_id: str) -> str:
        """Fetch the canonical permalink_url from Graph API.

        Returns the absolute facebook.com URL on success, "" on any failure.
        Caller falls back to the legacy constructed URL when this returns empty.

        Why this matters: the constructed URL
        `https://www.facebook.com/{page_id}/videos/{video_id}` works for most
        Pages but breaks for Pages with vanity URLs, scheduled-but-unpublished
        posts, and certain Reels endpoints. The canonical permalink_url is
        authoritative.
        """
        try:
            resp = self._client.get(
                video_id,
                params={"fields": "permalink_url"},
                token=self.page.access_token,
            )
            permalink = str(resp.get("permalink_url", "") or "").strip()
            if not permalink:
                return ""
            if permalink.startswith("/"):
                return f"https://www.facebook.com{permalink}"
            return permalink
        except Exception as exc:
            self.logger.warning(
                f"[API] Không lấy được permalink_url ({exc}), dùng URL construct"
            )
            return ""

    def _upload_thumbnail(self, video_id: str, thumb_path: str):
        with open(thumb_path, "rb") as f:
            thumb_bytes = f.read()
        mime = "image/jpeg"
        ext = os.path.splitext(thumb_path)[1].lower()
        if ext == ".png":
            mime = "image/png"
        elif ext in (".gif",):
            mime = "image/gif"

        self._client.post_multipart(
            video_id,
            data={},
            files={"thumb": (os.path.basename(thumb_path), thumb_bytes, mime)},
            token=self.page.access_token,
            video_endpoint=False,
        )

    # ─── Private helpers ──────────────────────────────────────────────────────

    def _sleep(self, seconds: float):
        interruptible_sleep(self.stop_event, seconds)

    def _check_stop(self):
        _check_stop_fn(self.stop_event)


