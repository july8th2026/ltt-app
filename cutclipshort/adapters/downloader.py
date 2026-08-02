"""Video downloader adapter — YouTube/TikTok/Drive → local file.

Supports:
  - YouTube, TikTok, Instagram, Twitter, etc. via yt-dlp
  - Google Drive public links via gdown
  - Direct video URLs via urllib

Downloads to a local file, then feeds into the existing analysis pipeline.
"""

from __future__ import annotations

import logging
import re
import urllib.request
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── URL pattern detection ──────────────────────────────────────────

_YTDLP_DOMAINS = {
    "youtube.com", "youtu.be", "m.youtube.com",
    "tiktok.com", "vm.tiktok.com",
    "instagram.com",
    "twitter.com", "x.com",
    "facebook.com", "fb.watch",
    "vimeo.com",
    "dailymotion.com",
    "twitch.tv",
    "reddit.com",
    "bilibili.com",
}

_DRIVE_PATTERN = re.compile(
    r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)"
)

_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".ts"}


class DownloadError(Exception):
    """Download failed."""
    pass


class DriveNotPublicError(DownloadError):
    """Google Drive file is not shared publicly."""
    pass


class DownloaderNotInstalledError(DownloadError):
    """Required downloader library is not installed."""
    pass


# ── Progress callback type ─────────────────────────────────────────

ProgressCallback = Callable[[float, str, str], None]
# (percent 0-100, speed str, eta str)


# ── Source detection ───────────────────────────────────────────────

def detect_source(url: str) -> str:
    """Detect source type from URL.

    Returns: 'ytdlp', 'drive', 'direct', or 'unknown'
    """
    url = url.strip()
    if not url:
        return "unknown"

    # Google Drive
    if _DRIVE_PATTERN.search(url):
        return "drive"

    # yt-dlp supported sites
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        # Strip www.
        domain = domain.removeprefix("www.")
        if domain in _YTDLP_DOMAINS:
            return "ytdlp"
        # Any other URL with video extension → direct
        if any(parsed.path.lower().endswith(ext) for ext in _VIDEO_EXTENSIONS):
            return "direct"
        # Try yt-dlp for any URL (it supports 1000+ sites)
        if parsed.scheme in ("http", "https") and "." in domain:
            return "ytdlp"
    except Exception:
        pass

    return "unknown"


def check_available() -> dict[str, bool]:
    """Check which download backends are installed."""
    result = {"ytdlp": False, "gdown": False}
    try:
        import yt_dlp  # noqa: F401
        result["ytdlp"] = True
    except ImportError:
        pass
    try:
        import gdown  # noqa: F401
        result["gdown"] = True
    except ImportError:
        pass
    return result


# ── Info extraction (no download) ──────────────────────────────────

def extract_info(url: str) -> dict[str, Any]:
    """Extract video metadata without downloading.

    Returns dict with: title, duration, thumbnail, source_type, url
    """
    source = detect_source(url)

    if source == "ytdlp":
        return _extract_info_ytdlp(url)
    elif source == "drive":
        return _extract_info_drive(url)
    elif source == "direct":
        return {"title": Path(url).stem, "duration": 0, "source_type": "direct", "url": url}
    else:
        raise DownloadError(
            "URL không được hỗ trợ.\n"
            "Hỗ trợ: YouTube, TikTok, Instagram, Twitter, Vimeo, Google Drive."
        )


def _extract_info_ytdlp(url: str) -> dict:
    """Extract info via yt-dlp without downloading."""
    try:
        import yt_dlp
    except ImportError:
        raise DownloaderNotInstalledError(
            "Chưa cài yt-dlp. Chạy: pip install yt-dlp"
        )

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise DownloadError("Không lấy được thông tin video.")
            return {
                "title": info.get("title", "Video"),
                "duration": info.get("duration", 0) or 0,
                "thumbnail": info.get("thumbnail", ""),
                "uploader": info.get("uploader", ""),
                "resolution": f"{info.get('width', '?')}x{info.get('height', '?')}",
                "source_type": "ytdlp",
                "url": url,
            }
    except yt_dlp.utils.DownloadError as e:
        err = str(e).lower()
        if "private" in err or "sign in" in err:
            raise DownloadError("Video ở chế độ riêng tư, không tải được.")
        if "age" in err:
            raise DownloadError("Video bị giới hạn tuổi, không tải được.")
        raise DownloadError(f"Không tải được video: {e}")


def _extract_info_drive(url: str) -> dict:
    """Extract info from Google Drive link."""
    match = _DRIVE_PATTERN.search(url)
    if not match:
        raise DownloadError("Link Google Drive không hợp lệ.")

    file_id = match.group(1)
    # Try HEAD request to check if accessible
    check_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    try:
        req = urllib.request.Request(check_url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            # Google returns HTML login page for private files
            if "text/html" in content_type:
                raise DriveNotPublicError(
                    "\u26a0 File Google Drive ch\u01b0a \u0111\u01b0\u1ee3c chia s\u1ebb c\u00f4ng khai.\n"
                    "H\u00e3y b\u1eadt chia s\u1ebb c\u00f4ng khai (Anyone with the link) r\u1ed3i th\u1eed l\u1ea1i."
                )
            size = int(resp.headers.get("Content-Length", 0))
    except (urllib.error.URLError, urllib.error.HTTPError):
        # Can't HEAD → might be large file with virus scan warning
        size = 0

    return {
        "title": f"Drive file {file_id[:8]}...",
        "duration": 0,
        "size_bytes": size,
        "source_type": "drive",
        "file_id": file_id,
        "url": url,
    }


# ── Download ───────────────────────────────────────────────────────

def download(
    url: str,
    output_dir: Path,
    progress_callback: ProgressCallback | None = None,
    cancel_flag: list | None = None,
) -> Path:
    """Download video from URL to output_dir. Returns local file path.

    Args:
        url: Video URL (YouTube, Drive, direct)
        output_dir: Directory to save file
        progress_callback: (percent, speed_str, eta_str)
        cancel_flag: [bool] — set [True] to cancel

    Returns:
        Path to downloaded video file

    Raises:
        DownloadError: on failure
        DriveNotPublicError: if Drive file not public
        DownloaderNotInstalledError: if yt-dlp/gdown not installed
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    source = detect_source(url)

    if source == "ytdlp":
        return _download_ytdlp(url, output_dir, progress_callback, cancel_flag)
    elif source == "drive":
        return _download_drive(url, output_dir, progress_callback)
    elif source == "direct":
        return _download_direct(url, output_dir, progress_callback)
    else:
        raise DownloadError("URL không được hỗ trợ.")


def _download_ytdlp(
    url: str, output_dir: Path,
    progress_callback: ProgressCallback | None,
    cancel_flag: list | None,
) -> Path:
    """Download via yt-dlp (YouTube, TikTok, Instagram, etc.)."""
    try:
        import yt_dlp
    except ImportError:
        raise DownloaderNotInstalledError(
            "Chưa cài yt-dlp.\nChạy: pip install yt-dlp"
        )

    downloaded_file = [None]

    def _progress_hook(d: dict) -> None:
        if cancel_flag and cancel_flag[0]:
            raise DownloadError("Đã hủy tải xuống.")

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            pct = (downloaded / total * 100) if total > 0 else 0
            speed = d.get("_speed_str", "")
            eta = d.get("_eta_str", "")
            if progress_callback:
                progress_callback(pct, speed, eta)

        elif d["status"] == "finished":
            downloaded_file[0] = d.get("filename", "")
            if progress_callback:
                progress_callback(100.0, "", "Xong!")

    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).80s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [_progress_hook],
        # Retry on failure
        "retries": 3,
        "fragment_retries": 3,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        err = str(e).lower()
        if "private" in err or "sign in" in err:
            raise DownloadError("Video ở chế độ riêng tư.")
        if "age" in err:
            raise DownloadError("Video bị giới hạn tuổi.")
        raise DownloadError(f"Tải xuống thất bại: {e}")

    # Find the output file
    if downloaded_file[0] and Path(downloaded_file[0]).exists():
        result = Path(downloaded_file[0])
        # yt-dlp may have created .mp4 by merging
        mp4_path = result.with_suffix(".mp4")
        if mp4_path.exists():
            return mp4_path
        return result

    # Fallback: find newest file in output_dir
    files = sorted(output_dir.glob("*.*"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        if f.suffix.lower() in _VIDEO_EXTENSIONS:
            return f

    raise DownloadError("Tải xong nhưng không tìm thấy file video.")


def _download_drive(
    url: str, output_dir: Path,
    progress_callback: ProgressCallback | None,
) -> Path:
    """Download from Google Drive (public link only)."""
    try:
        import gdown
    except ImportError:
        raise DownloaderNotInstalledError(
            "Chưa cài gdown.\nChạy: pip install gdown"
        )

    match = _DRIVE_PATTERN.search(url)
    if not match:
        raise DownloadError("Link Google Drive không hợp lệ.")

    file_id = match.group(1)
    download_url = f"https://drive.google.com/uc?id={file_id}"
    output_path = str(output_dir / f"drive_{file_id[:12]}.mp4")

    if progress_callback:
        progress_callback(0, "", "Đang tải từ Drive...")

    try:
        result = gdown.download(
            download_url,
            output_path,
            quiet=True,
            fuzzy=True,
        )
    except Exception as e:
        err_str = str(e).lower()
        if "access denied" in err_str or "permission" in err_str or "cannot" in err_str:
            raise DriveNotPublicError(
                "\u26a0 File Google Drive ch\u01b0a \u0111\u01b0\u1ee3c chia s\u1ebb c\u00f4ng khai.\n"
                "H\u00e3y b\u1eadt chia s\u1ebb c\u00f4ng khai (Anyone with the link) r\u1ed3i th\u1eed l\u1ea1i."
            )
        raise DownloadError(f"Tải từ Drive thất bại: {e}")

    if result is None or not Path(result).exists():
        raise DriveNotPublicError(
            "\u26a0 File Google Drive ch\u01b0a \u0111\u01b0\u1ee3c chia s\u1ebb c\u00f4ng khai.\n"
            "H\u00e3y b\u1eadt chia s\u1ebb c\u00f4ng khai (Anyone with the link) r\u1ed3i th\u1eed l\u1ea1i."
        )

    if progress_callback:
        progress_callback(100.0, "", "Xong!")

    return Path(result)


def _download_direct(
    url: str, output_dir: Path,
    progress_callback: ProgressCallback | None,
) -> Path:
    """Download direct video URL via urllib."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "video.mp4"
    output_path = output_dir / filename

    if progress_callback:
        progress_callback(0, "", "Đang tải...")

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(output_path, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0 and progress_callback:
                        pct = downloaded / total * 100
                        speed = ""
                        progress_callback(pct, speed, "")
    except Exception as e:
        raise DownloadError(f"Tải xuống thất bại: {e}")

    if progress_callback:
        progress_callback(100.0, "", "Xong!")

    return output_path
