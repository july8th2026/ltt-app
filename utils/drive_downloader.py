"""
Tải video từ Google Drive public share link về thư mục local.
Hỗ trợ file lớn (>100 MB) qua confirmation token (virus scan warning).
Retry tự động 3 lần. Cache theo file_id.
Không dùng gdown — dùng requests thuần để kiểm soát tốt hơn.

CHANGELOG (2026-05-26):
  - Fix virus-scan flow mới (2024+): parse HTML form để lấy UUID và
    endpoint mới `drive.usercontent.google.com/download`. Code cũ chỉ
    thử `confirm=t` → Google trả lại HTML virus warning lần 2 → bot
    lưu HTML 2-3 KB thành .mp4 → log thấy "0.0 MB" giả successfully.
  - Validate magic bytes (MP4/MOV/WebM/MKV/AVI/FLV) sau khi tải.
  - Min size threshold 10 KB — chặn HTML error pages lọt qua.
  - Distinguish retryable (network) vs fatal (logic) errors — fail
    nhanh khi không thể tải, không retry vô ích.
  - Re-check Content-Type của response thứ 2 — fail rõ ràng thay vì
    lưu rác. Error messages chỉ rõ nguyên nhân + cách fix.
  - Cache cleanup tự động xóa file rác từ lần fail trước.
"""
from __future__ import annotations

import html
import logging
import os
import re
import time
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)

_DOWNLOAD_BASE       = "https://drive.google.com/uc"
_USERCONTENT_BASE    = "https://drive.usercontent.google.com/download"
_CHUNK_SIZE          = 1024 * 1024  # 1 MB
_MAX_RETRIES         = 3
_RETRY_DELAY         = 5.0

# File nhỏ hơn ngưỡng này coi là không phải video hợp lệ (likely HTML error page).
# Threshold 10 KB: HTML virus-scan warning ~2-5 KB, HTML 404 page ~1-2 KB,
# trong khi video MP4 nhỏ nhất hợp lệ (ftyp box + 1 sample) cũng > 10 KB.
_MIN_VIDEO_SIZE      = 10 * 1024

# Magic bytes của các định dạng video phổ biến (whitelist).
# Tham khảo: https://en.wikipedia.org/wiki/List_of_file_signatures
_VIDEO_SIGNATURES = (
    # (offset, signature_bytes, format_name)
    (4,  b"ftyp",           "MP4/MOV/M4V"),         # ISO Base Media (MP4, MOV, M4V)
    (0,  b"\x1a\x45\xdf\xa3", "WebM/MKV"),          # EBML (WebM, MKV)
    (0,  b"RIFF",           "AVI"),                  # AVI (full check at offset 8 = "AVI ")
    (0,  b"FLV",            "FLV"),                  # Flash Video
    (0,  b"\x00\x00\x01\xba", "MPEG-PS"),           # MPEG Program Stream
    (0,  b"\x00\x00\x01\xb3", "MPEG-VS"),           # MPEG Video Stream
)


class DriveDownloadError(RuntimeError):
    """Lỗi tải file Drive. retryable=False → không retry (lỗi logic, 4xx, content sai)."""
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def _extract_file_id(url: str) -> Optional[str]:
    """Trích xuất Google Drive file ID từ các dạng URL phổ biến."""
    if not url or not url.strip():
        return None
    url = url.strip()

    # /file/d/{id}  (phổ biến nhất)
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    # id={id} trong query string
    try:
        qs = parse_qs(urlparse(url).query)
        if "id" in qs:
            return qs["id"][0]
    except Exception:
        pass

    # [?&]id=... dạng regex fallback
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url)
    if m:
        return m.group(1)

    return None


def _is_valid_video_file(path: str) -> tuple[bool, str]:
    """
    Kiểm tra file có phải video hợp lệ qua magic bytes.
    Trả về (is_valid, format_or_reason).

    HTML thường bắt đầu bằng b"<!DOC", b"<html", b"<HTML" → không match
    bất kỳ signature video nào → reject.
    """
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError as exc:
        return False, f"không đọc được file: {exc}"

    if len(head) < 8:
        return False, f"file quá ngắn ({len(head)} bytes)"

    for offset, sig, fmt in _VIDEO_SIGNATURES:
        if head[offset:offset + len(sig)] == sig:
            # AVI cần check thêm "AVI " tại offset 8
            if fmt == "AVI" and head[8:12] != b"AVI ":
                continue
            return True, fmt

    # Cung cấp hex của 8 byte đầu để debug
    head_hex = head[:8].hex(" ")
    # Phát hiện HTML để báo lỗi rõ hơn
    head_lower = head[:8].lower()
    if head_lower.startswith((b"<!doc", b"<html", b"<head", b"<?xml")):
        return False, f"HTML error page (header={head_hex})"
    return False, f"không phải video (header={head_hex})"


def _parse_virus_scan_form(html_text: str) -> tuple[Optional[str], dict]:
    """
    Parse HTML form trả về từ Google Drive virus scan warning.

    Form mẫu (2024+):
        <form action="https://drive.usercontent.google.com/download" method="get">
          <input name="id"      value="...">
          <input name="export"  value="download">
          <input name="confirm" value="t">
          <input name="uuid"    value="<UUID>">
          <input name="at"      value="...">  (đôi khi có)
        </form>

    Trả về (action_url, params_dict). action_url=None nếu không tìm thấy form.
    """
    # Tìm action của form download (Google đôi khi có nhiều form trong cùng HTML)
    action: Optional[str] = None
    m_action = re.search(
        r'<form[^>]*\bid=["\']?download-form["\']?[^>]*\baction=["\']([^"\']+)["\']',
        html_text, re.IGNORECASE,
    )
    if not m_action:
        # Fallback: form đầu tiên có action chứa "download"
        m_action = re.search(
            r'<form[^>]*\baction=["\']([^"\']*download[^"\']*)["\']',
            html_text, re.IGNORECASE,
        )
    if m_action:
        action = html.unescape(m_action.group(1))

    # Extract tất cả <input name="X" value="Y"> (cả 2 thứ tự attr)
    params: dict = {}
    for m in re.finditer(
        r'<input\b[^>]*\bname=["\']([^"\']+)["\'][^>]*\bvalue=["\']([^"\']*)["\']',
        html_text, re.IGNORECASE,
    ):
        params[m.group(1)] = html.unescape(m.group(2))
    # Thử chiều ngược lại: value trước, name sau
    for m in re.finditer(
        r'<input\b[^>]*\bvalue=["\']([^"\']*)["\'][^>]*\bname=["\']([^"\']+)["\']',
        html_text, re.IGNORECASE,
    ):
        params.setdefault(m.group(2), html.unescape(m.group(1)))

    return action, params


class DriveDownloader:
    """
    Tải file từ Google Drive public share link.
    Xử lý confirmation token cho file lớn bị Google chặn virus scan.
    Cache theo file_id — tải lại nếu file đã tồn tại và là video hợp lệ.

    Usage:
        dl = DriveDownloader(config)
        local_path = dl.download(drive_url, on_progress=cb, on_log=log_fn)
    """

    def __init__(self, config: dict):
        self.dest_dir = config.get("temp_video_dir", "temp_videos")
        os.makedirs(self.dest_dir, exist_ok=True)

    # ─── Public ──────────────────────────────────────────────────────────────

    def download(
        self,
        url: str,
        on_progress: Optional[Callable[[float, float], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        Tải file từ Drive URL.

        on_progress(downloaded_mb, total_mb) — gọi mỗi chunk
        on_log(message)                       — gọi khi có log

        Trả về đường dẫn file local.
        Raises DriveDownloadError với message tiếng Việt rõ ràng.
        """
        log = on_log or (lambda m: None)

        if not url or not url.strip():
            raise DriveDownloadError("URL video Drive bị rỗng", retryable=False)

        file_id = _extract_file_id(url.strip())
        if not file_id:
            raise DriveDownloadError(
                f"Không trích xuất được file ID từ URL: {url}", retryable=False,
            )

        # Dùng cache nếu đã tải (đã validate magic bytes + size)
        cached = self._find_cached(file_id, log)
        if cached:
            log(f"Dùng file đã tải: {os.path.basename(cached)}")
            return cached

        dest = os.path.join(self.dest_dir, f"{file_id}.mp4")
        log(f"Bắt đầu tải từ Drive (ID: {file_id})")

        self._download_with_retry(file_id, dest, on_progress, log)

        size_mb = os.path.getsize(dest) / (1024 * 1024)
        log(f"Tải xong {size_mb:.1f} MB → {os.path.basename(dest)}")
        return dest

    @staticmethod
    def delete(path: str):
        """Xóa file tạm sau khi upload xong."""
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # ─── Internal ────────────────────────────────────────────────────────────

    def _download_with_retry(
        self,
        file_id: str,
        output_path: str,
        on_progress: Optional[Callable],
        log: Callable,
    ):
        import requests

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                self._do_download(file_id, output_path, on_progress, requests, log)
                return
            except DriveDownloadError as exc:
                last_exc = exc
                # Lỗi logic (4xx, HTML response, magic bytes sai) → fail nhanh
                if not exc.retryable:
                    log(f"❌ Lỗi không thể retry: {exc}")
                    break
                log(f"Lần {attempt}/{_MAX_RETRIES} thất bại (retryable): {exc}")
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAY * attempt
                    log(f"Thử lại sau {wait:.0f}s...")
                    time.sleep(wait)
            except Exception as exc:
                # Network/timeout/connection errors → retry
                last_exc = exc
                log(f"Lần {attempt}/{_MAX_RETRIES} thất bại: {exc}")
                if attempt < _MAX_RETRIES:
                    wait = _RETRY_DELAY * attempt
                    log(f"Thử lại sau {wait:.0f}s...")
                    time.sleep(wait)

        # Cleanup file dở (nếu có) — tránh cache rác
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

        # Bóc DriveDownloadError ra thay vì wrap thêm tầng
        if isinstance(last_exc, DriveDownloadError):
            raise last_exc
        raise DriveDownloadError(
            f"Tải từ Drive thất bại sau {_MAX_RETRIES} lần (ID={file_id}): {last_exc}",
            retryable=False,
        )

    def _do_download(
        self,
        file_id: str,
        output_path: str,
        on_progress: Optional[Callable],
        requests_mod,
        log: Callable,
    ):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        session = requests_mod.Session()
        # User-Agent giống browser — Google đôi khi trả flow khác cho bot signature
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

        params = {"export": "download", "id": file_id}

        try:
            response = session.get(
                _DOWNLOAD_BASE, params=params, stream=True, timeout=60,
            )
        except requests_mod.exceptions.RequestException as exc:
            # Lỗi network → retryable
            raise DriveDownloadError(f"Lỗi kết nối Drive: {exc}", retryable=True)

        # 4xx → fatal (file không tồn tại / bị restrict)
        if 400 <= response.status_code < 500:
            self._raise_fatal_for_status(response, file_id)
        # 5xx → retryable
        if response.status_code >= 500:
            raise DriveDownloadError(
                f"Drive server lỗi {response.status_code}", retryable=True,
            )

        content_type = response.headers.get("Content-Type", "")

        # ── File lớn → Google trả HTML virus-scan warning, cần parse form ──
        if "text/html" in content_type:
            log("Phát hiện trang virus-scan warning — xử lý form xác nhận...")
            response = self._handle_virus_scan(
                session, response, file_id, requests_mod, log,
            )
            # Sau khi handle, response phải là binary stream — nếu vẫn HTML thì fail
            ct2 = response.headers.get("Content-Type", "")
            if "text/html" in ct2:
                # Đọc 1 phần để log debug
                preview = response.text[:200] if hasattr(response, "text") else ""
                raise DriveDownloadError(
                    "Drive vẫn trả HTML sau bước xác nhận virus-scan. "
                    "Kiểm tra: (1) link còn tồn tại, "
                    "(2) đã share 'Anyone with the link' (không phải Restricted), "
                    "(3) file không bị Google flag vi phạm. "
                    f"Preview: {preview[:120]}",
                    retryable=False,
                )

        # ── Stream chunks vào file ──
        total = int(response.headers.get("content-length", 0))
        done  = 0

        try:
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if on_progress and total > 0:
                            on_progress(done / (1024 * 1024), total / (1024 * 1024))
        except requests_mod.exceptions.RequestException as exc:
            raise DriveDownloadError(
                f"Lỗi network khi stream chunks: {exc}", retryable=True,
            )

        # ── Validate file sau khi tải (Layer 2 + 3) ──
        size_bytes = os.path.getsize(output_path)

        # Layer 3: size threshold
        if size_bytes < _MIN_VIDEO_SIZE:
            raise DriveDownloadError(
                f"File chỉ {size_bytes/1024:.1f} KB (< {_MIN_VIDEO_SIZE/1024:.0f} KB tối thiểu) — "
                f"có thể là HTML error page. Kiểm tra quyền chia sẻ Drive.",
                retryable=False,
            )

        # Layer 2: magic bytes
        is_valid, fmt_or_reason = _is_valid_video_file(output_path)
        if not is_valid:
            raise DriveDownloadError(
                f"File tải về không phải video hợp lệ: {fmt_or_reason}. "
                "Drive có thể đã trả error page thay vì video.",
                retryable=False,
            )
        log(f"Định dạng video: {fmt_or_reason} ✓")

    # ── Virus scan handler (Google Drive 2024+ flow) ────────────────────────

    def _handle_virus_scan(
        self,
        session,
        first_response,
        file_id: str,
        requests_mod,
        log: Callable,
    ):
        """
        Xử lý trang virus-scan warning của Google Drive.

        Flow (2024+):
          1. Parse form trong HTML body → lấy action URL + params (gồm UUID)
          2. GET action URL với đầy đủ params
          3. Nếu thành công → response là binary stream của video
          4. Nếu vẫn HTML → throw DriveDownloadError (xử lý ở caller)

        Fallback (Google flow cũ ~2020-2022):
          - Tìm cookie `download_warning_*` → dùng làm confirm token
          - Hoặc thử `confirm=t` rỗng
        """
        action, form_params = _parse_virus_scan_form(first_response.text)

        # ── Strategy 1: Modern flow — submit form với UUID ──
        if action and "uuid" in form_params:
            log(f"Form params: {list(form_params.keys())}")
            try:
                response = session.get(
                    action, params=form_params, stream=True, timeout=120,
                )
            except requests_mod.exceptions.RequestException as exc:
                raise DriveDownloadError(
                    f"Lỗi network khi submit form virus-scan: {exc}",
                    retryable=True,
                )
            if 400 <= response.status_code < 500:
                self._raise_fatal_for_status(response, file_id)
            if response.status_code >= 500:
                raise DriveDownloadError(
                    f"Drive server lỗi {response.status_code} sau confirm",
                    retryable=True,
                )
            return response

        # ── Strategy 2: Legacy flow — cookie download_warning_* ──
        legacy_token = self._extract_confirm_token(first_response)

        if legacy_token:
            log(f"Dùng legacy confirm token: {legacy_token[:8]}...")
            params = {"export": "download", "id": file_id, "confirm": legacy_token}
            try:
                response = session.get(
                    _DOWNLOAD_BASE, params=params, stream=True, timeout=120,
                )
            except requests_mod.exceptions.RequestException as exc:
                raise DriveDownloadError(
                    f"Lỗi network khi confirm legacy: {exc}", retryable=True,
                )
            if 400 <= response.status_code < 500:
                self._raise_fatal_for_status(response, file_id)
            return response

        # ── Cả 2 strategy đều fail → có thể Google đổi format ──
        raise DriveDownloadError(
            "Không parse được form virus-scan của Drive (không tìm thấy UUID "
            "và không có legacy confirm token). Google có thể đã đổi format — "
            "cần update bot.",
            retryable=False,
        )

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_confirm_token(response) -> Optional[str]:
        """Extract a legacy Drive confirmation token from cookies or HTML."""
        for key, val in getattr(response, "cookies", {}).items():
            if key.startswith("download_warning"):
                return val
        match = re.search(
            r"confirm=([^&\"'<>\s]+)",
            str(getattr(response, "text", "")),
        )
        return match.group(1) if match else None

    @staticmethod
    def _raise_fatal_for_status(response, file_id: str):
        """Ném DriveDownloadError(retryable=False) cho 4xx với message thân thiện."""
        code = response.status_code
        if code == 404:
            raise DriveDownloadError(
                f"Drive trả 404 — file ID {file_id} không tồn tại hoặc đã bị xóa. "
                "Kiểm tra link còn hoạt động không.",
                retryable=False,
            )
        if code == 403:
            raise DriveDownloadError(
                f"Drive trả 403 — không có quyền truy cập file {file_id}. "
                "Đổi quyền chia sẻ thành 'Anyone with the link → Viewer'.",
                retryable=False,
            )
        if code == 401:
            raise DriveDownloadError(
                f"Drive trả 401 — yêu cầu đăng nhập. File {file_id} "
                "không public, hoặc đang yêu cầu OAuth.",
                retryable=False,
            )
        raise DriveDownloadError(
            f"Drive trả lỗi {code} cho file {file_id}", retryable=False,
        )

    def _find_cached(self, file_id: str, log: Callable = None) -> Optional[str]:
        """
        Tìm file đã tải trong cache. CHỈ trả về nếu:
          - File tồn tại
          - Size >= MIN_VIDEO_SIZE
          - Magic bytes là video hợp lệ

        Tự động cleanup file rác (size nhỏ hoặc không phải video) từ lần fail trước.
        """
        log = log or (lambda m: None)
        if not os.path.isdir(self.dest_dir):
            return None
        for fname in os.listdir(self.dest_dir):
            if not fname.startswith(file_id):
                continue
            full = os.path.join(self.dest_dir, fname)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue

            # Cleanup file rác
            if size < _MIN_VIDEO_SIZE:
                try:
                    os.remove(full)
                    log(f"Dọn cache rác: {fname} ({size} bytes)")
                except Exception:
                    pass
                continue

            is_valid, _ = _is_valid_video_file(full)
            if not is_valid:
                try:
                    os.remove(full)
                    log(f"Dọn cache file không hợp lệ: {fname}")
                except Exception:
                    pass
                continue

            return full
        return None
