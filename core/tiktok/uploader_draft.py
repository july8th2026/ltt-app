"""
TikTokDraftUploader — uploads video to the creator's inbox (draft mode).

Endpoint: POST /v2/post/publish/inbox/video/init/
Required scope: video.upload

The video lands in the creator's TikTok app inbox as a draft.
The creator reviews and posts it manually (no privacy restriction).
This is the safe upload path for apps that have not passed TikTok's
"Direct Post" audit.

Upload flow:
  1. Init  — POST init endpoint with file metadata → publish_id + upload_url
  2. Upload — PUT raw bytes to upload_url in chunks (Content-Range)
  3. Poll   — POST status endpoint until PROCESS_SUCCESS / SEND_TO_USER_INBOX
"""
from __future__ import annotations

import math
import os
import threading
from typing import Callable, Optional

from core.tiktok.client import TikTokClient, TikTokError
from core.tiktok.status_poller import poll_until_done

_INIT_URL     = "/v2/post/publish/inbox/video/init/"
_CHUNK_SIZE   = 64 * 1024 * 1024   # 64 MB (TikTok max). Single-chunk upload for
                                   # videos ≤ 64 MB to avoid invalid_params errors
                                   # on the chunked-upload path. (Was 10 MB.)
_MIN_CHUNK    = 5  * 1024 * 1024   # 5 MB minimum per TikTok spec


class TikTokDraftUploader:
    """
    Uploads a video file to the TikTok creator's draft inbox.

    Returns (publish_id, "") — draft uploads have no public URL until
    the creator chooses to post.
    """

    def __init__(
        self,
        client: TikTokClient,
        config: dict,
        stop_event: Optional[threading.Event] = None,
        on_log: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        on_progress: Optional[Callable] = None,
    ):
        self._client    = client
        self._config    = config
        self._stop      = stop_event
        self._log       = on_log      or (lambda m, l: None)
        self._status    = on_status   or (lambda m: None)
        self._progress  = on_progress or (lambda done, total: None)

    def upload(self, task: dict) -> tuple[str, str]:
        """
        Upload video from task["video_path"] to inbox.

        Returns (publish_id, post_url).
        post_url is "" for drafts (no public link until posted by creator).
        Raises TikTokError or InterruptedError.
        """
        video_path = task.get("video_path", "")
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"File không tồn tại: {video_path}")

        title       = str(task.get("title",       ""))[:150]
        description = str(task.get("description", ""))[:2200]

        # Per-post interaction flags: task value overrides global config
        def _bool_field(task_key: str, cfg_key: str) -> bool:
            task_val = str(task.get(task_key, "")).lower()
            if task_val in ("true", "1", "yes"):
                return True
            if task_val in ("false", "0", "no"):
                return False
            return bool(self._config.get(cfg_key, False))

        disable_duet    = _bool_field("tiktok_disable_duet",    "tiktok_disable_duet")
        disable_comment = _bool_field("tiktok_disable_comment", "tiktok_disable_comment")
        disable_stitch  = _bool_field("tiktok_disable_stitch",  "tiktok_disable_stitch")

        # AI-generated content advisory
        if str(task.get("is_ai_generated", "")).lower() in ("true", "1", "yes"):
            self._log(
                "[TikTok Draft] Nội dung AI — hãy bật nhãn 'AI generated content' "
                "trong TikTok app khi duyệt bản nháp.",
                "warning",
            )

        video_size = os.path.getsize(video_path)
        chunk_size = self._resolve_chunk_size(video_size)
        total_chunks = math.ceil(video_size / chunk_size)

        self._log(
            f"[TikTok Draft] Bắt đầu upload: {os.path.basename(video_path)} "
            f"({video_size:,} bytes, {total_chunks} chunk)",
            "upload",
        )
        self._status(f"[TikTok] Init draft upload...")

        # ── Phase 1: Init ──────────────────────────────────────────────────
        init_payload = {
            "post_info": {
                "title":            title or description[:150],
                "description":      description,
                "disable_duet":     disable_duet,
                "disable_comment":  disable_comment,
                "disable_stitch":   disable_stitch,
                # Draft has no privacy_level — creator sets it when posting
            },
            "source_info": {
                "source":       "FILE_UPLOAD",
                "video_size":   video_size,
                "chunk_size":   chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        self._check_stop()
        data = self._client.post(_INIT_URL, init_payload)

        publish_id = str(data.get("publish_id", ""))
        upload_url = str(data.get("upload_url", ""))

        if not publish_id or not upload_url:
            from utils.logger import safe_response_repr
            raise TikTokError(
                f"TikTok không trả về publish_id/upload_url: {safe_response_repr(data)}",
                error_code="init_failed",
            )

        self._log(f"[TikTok Draft] publish_id={publish_id}", "info")
        self._status(f"[TikTok] Đang upload video ({total_chunks} chunk)...")

        # ── Phase 2: Upload chunks ─────────────────────────────────────────
        self._upload_chunks(video_path, video_size, chunk_size, upload_url)

        # ── Phase 3: Poll status ───────────────────────────────────────────
        self._status("[TikTok] Đang chờ TikTok xử lý video...")
        poll_until_done(
            client          = self._client,
            publish_id      = publish_id,
            poll_interval_s = float(self._config.get("tiktok_poll_interval_s", 5)),
            timeout_s       = float(self._config.get("tiktok_upload_timeout_s", 600)),
            on_log          = self._log,
            stop_event      = self._stop,
        )

        self._log(
            f"[TikTok Draft] Upload hoàn tất — publish_id={publish_id}",
            "success",
        )
        return publish_id, ""   # no public URL for drafts

    # ── Internal helpers ───────────────────────────────────────────────────

    def _upload_chunks(
        self,
        path: str,
        total_size: int,
        chunk_size: int,
        upload_url: str,
    ):
        """Upload file in chunks using Content-Range headers.

        OPT-04 fix: delegates to shared utility to avoid code duplication.
        """
        from core.tiktok.upload_utils import upload_video_in_chunks
        upload_video_in_chunks(
            path        = path,
            total_size  = total_size,
            chunk_size  = chunk_size,
            upload_url  = upload_url,
            client      = self._client,
            check_stop  = self._check_stop,
            on_log      = self._log,
            on_progress = self._progress,
            on_status   = self._status,
        )

    def _check_stop(self):
        if self._stop and self._stop.is_set():
            raise InterruptedError("Dừng bởi người dùng")

    @staticmethod
    def _resolve_chunk_size(video_size: int) -> int:
        """
        Choose chunk size:
        - Single-chunk if file fits in 10 MB
        - Otherwise 10 MB chunks (within TikTok [5 MB, 64 MB] bounds)
        """
        if video_size <= _CHUNK_SIZE:
            return video_size
        return _CHUNK_SIZE
