"""
TikTokDirectUploader — uploads video as a direct public (or SELF_ONLY) post.

Endpoint: POST /v2/post/publish/video/init/
Required scope: video.publish

Privacy levels:
    PUBLIC_TO_EVERYONE      — requires app audit (TikTok "Direct Post" review)
    FOLLOWER_OF_CREATOR     — requires audit
    MUTUAL_FRIEND_FRIENDS   — requires audit
    SELF_ONLY               — available without audit (for testing / unaudited apps)

If the configured privacy_level is not SELF_ONLY and the app has not passed
audit, TikTok returns error code "privacy_level_option_mismatch". The uploader
catches this and raises a clear RuntimeError with instructions.

Upload flow: identical to TikTokDraftUploader (init → chunk upload → poll),
but uses a different endpoint and includes privacy_level in post_info.
"""
from __future__ import annotations

import math
import os
import threading
from typing import Callable, Optional

from core.tiktok.client import TikTokClient, TikTokError
from core.tiktok.status_poller import poll_until_done

_INIT_URL   = "/v2/post/publish/video/init/"
_CHUNK_SIZE = 64 * 1024 * 1024   # 64 MB — TikTok's max single-chunk size.
# Previously 10 MB caused "The total chunk count is invalid" error for videos
# in the 10-64 MB range — TikTok's current spec prefers single-chunk for any
# video ≤ 64 MB, and chunked-upload only for larger files.

# Mapping from user-friendly strings → TikTok API enum values
_PRIVACY_MAP = {
    "public":    "PUBLIC_TO_EVERYONE",
    "followers": "FOLLOWER_OF_CREATOR",
    "friends":   "MUTUAL_FRIEND_FRIENDS",
    "private":   "SELF_ONLY",
    "self_only": "SELF_ONLY",
    # Pass TikTok enum directly if already correct
    "PUBLIC_TO_EVERYONE":    "PUBLIC_TO_EVERYONE",
    "FOLLOWER_OF_CREATOR":   "FOLLOWER_OF_CREATOR",
    "MUTUAL_FRIEND_FRIENDS": "MUTUAL_FRIEND_FRIENDS",
    "SELF_ONLY":             "SELF_ONLY",
}
_DEFAULT_PRIVACY = "SELF_ONLY"   # safe default for unaudited apps


class TikTokDirectUploader:
    """
    Uploads a video to TikTok as a direct post.

    Returns (publish_id, post_url).
    post_url is "" until TikTok provides a shareable link
    (currently the API does not return it; users find it in the app).
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
        self._client   = client
        self._config   = config
        self._stop     = stop_event
        self._log      = on_log      or (lambda m, l: None)
        self._status   = on_status   or (lambda m: None)
        self._progress = on_progress or (lambda done, total: None)

    def upload(self, task: dict) -> tuple[str, str]:
        """
        Upload video and create a direct TikTok post.

        Returns (publish_id, post_url).
        Raises TikTokError or InterruptedError.
        """
        video_path = task.get("video_path", "")
        if not os.path.isfile(video_path):
            raise FileNotFoundError(f"File không tồn tại: {video_path}")

        title         = str(task.get("title",         ""))[:150]
        description   = str(task.get("description",   ""))[:2200]
        privacy_raw   = str(task.get("privacy_level",
                           task.get("privacy", "SELF_ONLY")))
        privacy_level = _PRIVACY_MAP.get(privacy_raw, _DEFAULT_PRIVACY)

        # Collect hashtag keywords → append to description as #tags
        keywords_raw = str(task.get("keywords", "")).strip()
        if keywords_raw:
            tags = " ".join(
                f"#{k.strip().lstrip('#')}"
                for k in keywords_raw.replace(",", " ").split()
                if k.strip()
            )
            if tags and tags not in description:
                description = f"{description}\n{tags}".strip()

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
        # Commercial / branded content toggle
        brand_content = _bool_field("tiktok_commercial_content", "tiktok_commercial_content")
        # AI-generated content disclosure (advisory — log notice; no API field in v2)
        is_ai = str(task.get("is_ai_generated", "")).lower() in ("true", "1", "yes")
        if is_ai:
            self._log(
                "[TikTok] Nội dung AI được đánh dấu — hãy bật nhãn 'AI generated content' "
                "trong TikTok app sau khi đăng.",
                "warning",
            )

        video_size   = os.path.getsize(video_path)
        chunk_size   = video_size if video_size <= _CHUNK_SIZE else _CHUNK_SIZE
        total_chunks = math.ceil(video_size / chunk_size)

        self._log(
            f"[TikTok Direct] Upload: {os.path.basename(video_path)} "
            f"({video_size:,} bytes, privacy={privacy_level}"
            f"{', commercial' if brand_content else ''}"
            f"{', AI' if is_ai else ''})",
            "upload",
        )
        self._status(f"[TikTok] Init direct upload ({privacy_level})...")

        # ── Phase 1: Init ──────────────────────────────────────────────────
        post_info: dict = {
            "title":            title or description[:150],
            "description":      description,
            "privacy_level":    privacy_level,
            "disable_duet":     disable_duet,
            "disable_comment":  disable_comment,
            "disable_stitch":   disable_stitch,
        }
        # Only include brand_content_toggle when explicitly true — omitting it
        # is equivalent to false and avoids unnecessary API fields.
        if brand_content:
            post_info["brand_content_toggle"] = True

        init_payload = {
            "post_info": post_info,
            "source_info": {
                "source":            "FILE_UPLOAD",
                "video_size":        video_size,
                "chunk_size":        chunk_size,
                "total_chunk_count": total_chunks,
            },
        }

        self._check_stop()
        try:
            data = self._client.post(_INIT_URL, init_payload)
        except TikTokError as exc:
            if "privacy_level_option_mismatch" in exc.error_code.lower():
                raise RuntimeError(
                    f"TikTok từ chối privacy_level='{privacy_level}'.\n"
                    "App chưa qua kiểm duyệt Direct Post — chỉ dùng được SELF_ONLY.\n"
                    "Đổi 'tiktok_privacy_level' thành 'SELF_ONLY' trong Cài đặt, "
                    "hoặc dùng 'post_type=tiktok_draft' để gửi vào inbox."
                ) from exc
            raise

        publish_id = str(data.get("publish_id", ""))
        upload_url = str(data.get("upload_url", ""))

        if not publish_id or not upload_url:
            from utils.logger import safe_response_repr
            raise TikTokError(
                f"TikTok không trả về publish_id/upload_url: {safe_response_repr(data)}",
                error_code="init_failed",
            )

        self._log(f"[TikTok Direct] publish_id={publish_id}", "info")
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
            f"[TikTok Direct] Đăng thành công — publish_id={publish_id}",
            "success",
        )
        # TikTok API v2 does not return a public URL in the response.
        # Returning publish_id as the "external_post_id" for tracking.
        return publish_id, ""

    # ── Internal helpers ───────────────────────────────────────────────────

    def _upload_chunks(
        self,
        path: str,
        total_size: int,
        chunk_size: int,
        upload_url: str,
    ):
        """OPT-04 fix: delegates to shared utility to avoid code duplication."""
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
