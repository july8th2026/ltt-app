"""
TikTok upload shared utilities.

OPT-04 fix: _upload_chunks was duplicated identically in uploader_draft.py
and uploader_direct.py. Extracted here so both uploaders use the same
implementation.
"""
from __future__ import annotations

from typing import Callable, Optional


def upload_video_in_chunks(
    *,
    path: str,
    total_size: int,
    chunk_size: int,
    upload_url: str,
    client,
    check_stop: Optional[Callable[[], None]] = None,
    on_log:     Optional[Callable[[str, str], None]] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_status:   Optional[Callable[[str], None]] = None,
) -> None:
    """Upload a local video file to TikTok's upload URL in chunks.

    Uses Content-Range headers so the server can reassemble chunks in order.

    Parameters
    ----------
    path         : local file path to upload
    total_size   : total file size in bytes (from os.path.getsize)
    chunk_size   : chunk size in bytes (TikTok recommends multiples of 1 MB)
    upload_url   : pre-signed PUT URL returned by TikTok's init endpoint
    client       : TikTokClient instance with `put_binary(url, chunk, ...)`
    check_stop   : optional callable that raises InterruptedError on cancel
    on_log       : optional (message, level) callback for chunk-level logs
    on_progress  : optional (current_offset, total) callback for UI progress
    on_status    : optional (status_message) callback for human-readable status

    Raises
    ------
    InterruptedError    : if check_stop() raises
    Any TikTokError     : propagated from client.put_binary on HTTP errors
    """
    _log    = on_log    or (lambda m, l: None)
    _prog   = on_progress or (lambda c, t: None)
    _status = on_status  or (lambda m: None)
    _stop   = check_stop or (lambda: None)

    with open(path, "rb") as fh:
        offset = 0
        chunk_idx = 0
        while offset < total_size:
            _stop()
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            end = offset + len(chunk) - 1
            cr  = f"bytes {offset}-{end}/{total_size}"
            _log(f"[TikTok] Chunk {chunk_idx + 1}: {cr}", "upload")
            client.put_binary(
                upload_url, chunk,
                content_type  = "video/mp4",
                content_range = cr,
            )
            offset    += len(chunk)
            chunk_idx += 1
            _prog(offset, total_size)
            _status(f"[TikTok] Đang upload: {offset / total_size * 100:.0f}%")
