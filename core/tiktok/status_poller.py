"""
TikTok publish status poller.

Polls POST /v2/post/publish/status/fetch/ until the video reaches
PROCESS_SUCCESS or PROCESS_FAILED, or the timeout expires.

TikTok status values:
    PROCESSING_UPLOAD          — chunks still being received
    PROCESSING_DOWNLOAD        — server pulling video from URL
    PROCESSING_INTERCUT_AND_UPLOAD — server transcoding
    PROCESS_SUCCESS            — done; post is live (or in draft inbox)
    PROCESS_FAILED             — server-side failure
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from core.tiktok.client import TikTokClient, TikTokError

_STATUS_URL = "/v2/post/publish/status/fetch/"

_TERMINAL_OK     = "PROCESS_SUCCESS"
_TERMINAL_FAIL   = "PROCESS_FAILED"
_PENDING_STATUSES = frozenset({
    "PROCESSING_UPLOAD",
    "PROCESSING_DOWNLOAD",
    "PROCESSING_INTERCUT_AND_UPLOAD",
    "SEND_TO_USER_INBOX",          # draft accepted, awaiting user action
})


# Exponential backoff bounds (MEH-06 fix)
_BACKOFF_MIN_S = 3.0      # don't poll faster than every 3s
_BACKOFF_MAX_S = 30.0     # don't wait longer than 30s between polls
_BACKOFF_FACTOR = 1.5     # each retry waits 1.5x longer


def poll_until_done(
    client: TikTokClient,
    publish_id: str,
    *,
    poll_interval_s: float = 5.0,
    timeout_s: float = 600.0,
    on_log: Optional[Callable] = None,
    stop_event=None,
) -> str:
    """
    Block until publish_id reaches a terminal status.

    Uses exponential backoff (MEH-06): starts at poll_interval_s, grows by 1.5x
    after each poll, capped at _BACKOFF_MAX_S. This avoids hammering TikTok's
    status endpoint and tripping their rate limits on long-running uploads.

    Returns the final status string (e.g. "PROCESS_SUCCESS").
    Raises TikTokError on PROCESS_FAILED, timeout, or stop_event.
    """
    log = on_log or (lambda m, l: None)
    deadline = time.time() + timeout_s
    attempt  = 0

    # Initial interval: respect user setting but clamp to safety bounds
    current_interval = max(_BACKOFF_MIN_S, min(float(poll_interval_s), _BACKOFF_MAX_S))

    while True:
        # Check stop_event (InterruptedError propagates to SheetRunner)
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("Dừng bởi người dùng trong lúc chờ TikTok xử lý")

        if time.time() > deadline:
            raise TikTokError(
                f"Quá {timeout_s:.0f}s chờ TikTok xử lý publish_id={publish_id}",
                error_code="timeout",
            )

        attempt += 1
        try:
            data = client.post(_STATUS_URL, {"publish_id": publish_id})
        except TikTokError:
            raise
        except Exception as exc:
            raise TikTokError(
                f"Không thể kiểm tra trạng thái TikTok: {exc}"
            ) from exc

        process_info = data.get("process_info", data)
        status       = str(process_info.get("status", "")).upper()
        uploaded_bytes = process_info.get("uploaded_bytes", 0)

        log(
            f"[TikTok] Trạng thái publish #{attempt}: {status} "
            f"({uploaded_bytes:,} bytes đã nhận, wait={current_interval:.1f}s)",
            "info",
        )

        if status == _TERMINAL_OK:
            return status

        if status == _TERMINAL_FAIL:
            fail_reason = process_info.get("fail_reason", "unknown")
            raise TikTokError(
                f"TikTok từ chối video (publish_id={publish_id}): {fail_reason}",
                error_code="process_failed",
            )

        # For SEND_TO_USER_INBOX the draft is already accepted — treat as success
        if status == "SEND_TO_USER_INBOX":
            log("[TikTok] Video đã vào inbox người dùng (draft mode)", "success")
            return status

        # Still processing — wait then back off for next iteration
        time.sleep(current_interval)
        current_interval = min(current_interval * _BACKOFF_FACTOR, _BACKOFF_MAX_S)
