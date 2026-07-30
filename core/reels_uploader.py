"""
Facebook Reels Uploader via Graph API.

Upload flow (different from feed video):
  1. POST /{page_id}/video_reels?upload_phase=start
        → {upload_url, video_id}
  2. PUT upload_url (raw binary video — no multipart)
  3. POST /{page_id}/video_reels?upload_phase=finish + metadata
        → publish / schedule

Reference:
  https://developers.facebook.com/docs/video-api/reels-publishing-api
"""
from __future__ import annotations

import os
import threading
import time
from typing import Callable, Optional

import requests

from core.graph_client import GraphClient, GraphError, GRAPH_BASE
from core.token_store import AccountInfo, PageInfo
from core.utils import (
    build_description,
    check_stop as _check_stop_fn,
    graph_api_version,
    interruptible_sleep,
    parse_schedule,
)
from utils.logger import BotLogger

_CHUNK_SIZE = 8 * 1024 * 1024   # 8 MB


class ReelsUploader:
    """
    Uploads a video as a Facebook Reel to a Page.
    Returns (video_url, video_id) on success — same contract as GraphUploader.
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
            account_id=str(getattr(account, "fb_user_id", "") or ""),
            config=config,
        )

    # ── Public ─────────────────────────────────────────────────────────────────

    def upload(self, task: dict) -> tuple[str, str]:
        """
        Full Reels upload flow.
        Returns (video_url, video_id) on success.
        """
        video_path = task.get("video_path", "")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"File video không tồn tại: {video_path}")
        file_size = os.path.getsize(video_path)
        if file_size == 0:
            raise ValueError(f"File video rỗng (0 bytes): {video_path}")

        fname = os.path.basename(video_path)
        self.logger.upload(
            f"[Reels] Bắt đầu upload: {fname} "
            f"({file_size / (1024*1024):.1f} MB) → Page: {self.page.name}"
        )
        self.on_status(f"[Reels] Khởi tạo phiên upload: {fname}")

        # ── Phase 1: Start ────────────────────────────────────────────────────
        upload_url, video_id = self._start_session(task)
        self.logger.upload(f"[Reels] upload_url nhận được, video_id: {video_id}")

        # ── Phase 2: Binary upload ────────────────────────────────────────────
        self._binary_upload(video_path, file_size, upload_url)

        # ── Phase 3: Finish / publish ─────────────────────────────────────────
        self.on_status("[Reels] Hoàn tất và đăng Reel...")
        self._finish_session(video_id, task)

        # Prefer canonical permalink_url from Graph API — fall back to constructed
        # template URL when the API call fails (network, token, vanity URL Pages).
        video_url = self._try_fetch_permalink(video_id)
        if not video_url:
            video_url = f"https://www.facebook.com/{self.page.id}/videos/{video_id}"

        self.logger.success(f"[Reels] Upload xong: {video_url}")
        self.on_status(f"[Reels] Xong: {video_url}")
        return video_url, video_id

    def _try_fetch_permalink(self, video_id: str) -> str:
        """Fetch canonical permalink_url for a Reels video. Returns '' on failure."""
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
                f"[Reels] Không lấy được permalink_url ({exc}), dùng URL construct"
            )
            return ""

    # ── Private ─────────────────────────────────────────────────────────────────

    def _start_session(self, task: dict) -> tuple[str, str]:
        """Phase 1: initialise upload session."""
        title = task.get("title", "")
        data = {
            "upload_phase": "start",
            "clip_title":   title or os.path.splitext(
                os.path.basename(task.get("video_path", "reel")))[0],
        }
        resp = self._client.post(
            f"{self.page.id}/video_reels",
            data=data,
            token=self.page.access_token,
        )
        upload_url = resp.get("upload_url", "")
        video_id   = resp.get("video_id",   "")
        if not upload_url:
            from utils.logger import safe_response_repr
            raise RuntimeError(
                f"[Reels] Không nhận được upload_url: {safe_response_repr(resp)}"
            )
        return upload_url, video_id

    def _binary_upload(self, video_path: str, file_size: int, upload_url: str):
        """Phase 2: PUT raw binary video to upload_url."""
        self.on_status("[Reels] Đang upload binary...")
        self._check_stop()

        offset = 0
        session = requests.Session()
        session.headers["User-Agent"] = "LTTStudio/1.0"

        with open(video_path, "rb") as f:
            while offset < file_size:
                self._check_stop()
                chunk = f.read(_CHUNK_SIZE)
                end = offset + len(chunk)

                pct = int(offset / file_size * 100) if file_size else 0
                self.on_status(
                    f"[Reels] Upload {pct}% ({end/(1024*1024):.0f}/{file_size/(1024*1024):.0f} MB)..."
                )

                headers = {
                    "Content-Type":  "application/octet-stream",
                    "Authorization": f"OAuth {self.page.access_token}",
                    "offset":        str(offset),
                    "file_size":     str(file_size),
                }
                # P3: retry each chunk up to 3 times on transient HTTP errors
                _MAX_CHUNK_RETRIES = 3
                for _attempt in range(_MAX_CHUNK_RETRIES):
                    resp = session.put(
                        upload_url, data=chunk, headers=headers, timeout=120
                    )
                    if resp.status_code in (200, 201):
                        break
                    if _attempt < _MAX_CHUNK_RETRIES - 1:
                        wait = 5 * (_attempt + 1)
                        self.logger.warning(
                            f"[Reels] Chunk @{offset} HTTP {resp.status_code}, "
                            f"retry sau {wait}s (lần {_attempt + 1}/{_MAX_CHUNK_RETRIES})"
                        )
                        self._sleep(wait)
                        self._check_stop()
                    else:
                        raise RuntimeError(
                            f"[Reels] Binary upload thất bại HTTP {resp.status_code} "
                            f"sau {_MAX_CHUNK_RETRIES} lần: {resp.text[:200]}"
                        )

                self.on_progress(end, file_size)
                offset = end

        self.logger.upload("[Reels] Binary upload hoàn tất")

    def _finish_session(self, video_id: str, task: dict):
        """Phase 3: finish / schedule / publish."""
        data = {
            "upload_phase": "finish",
            "video_id":     video_id,
        }

        desc_raw = task.get("description", "")
        keywords = task.get("keywords", "")
        full_desc = build_description(desc_raw, keywords)
        if full_desc:
            data["description"] = full_desc

        schedule = task.get("schedule", "")
        if schedule:
            dt = parse_schedule(schedule)
            if dt and dt.timestamp() > time.time():
                data["video_state"]            = "SCHEDULED"
                data["scheduled_publish_time"] = str(int(dt.timestamp()))
            else:
                data["video_state"] = "PUBLISHED"
        else:
            data["video_state"] = "PUBLISHED"

        self._client.post(
            f"{self.page.id}/video_reels",
            data=data,
            token=self.page.access_token,
        )

    def _check_stop(self):
        _check_stop_fn(self.stop_event)

    def _sleep(self, seconds: float):
        interruptible_sleep(self.stop_event, seconds)
