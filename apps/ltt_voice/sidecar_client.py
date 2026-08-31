"""
sidecar_client.py — gọi cổng giọng ở `127.0.0.1:8120`.

Khuôn lấy từ `apps/chataistudio/sidecar_client.py` đã chạy thật: đọc cổng và
token từ môi trường, không hằng số rải rác, không đường LAN.

⛔ PHÂN BIỆT **BẬN** VỚI **HỎNG**. Đây là bài học đắt nhất của H37 (D-005): khi
   cổng trả 429 vì đang bận, coi đó là *hỏng* sẽ dẫn tới cooldown rồi vô hiệu hoá
   cả đường gọi — một buổi tối nhiều việc là đủ để tự tắt sản phẩm.

   Ở đây `SidecarBan` là một lớp lỗi **riêng**, và nó mang theo `retry_after_s`
   để tầng trên xếp lại chứ không báo lỗi cho khách.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class LoiSidecar(RuntimeError):
    """Cổng hỏng thật, hoặc trả thứ không đọc được."""


class SidecarBan(RuntimeError):
    """Cổng đang bận (429). **KHÔNG PHẢI HỎNG.**"""

    def __init__(self, retry_after_s: float = 5.0):
        super().__init__("Cong giong dang ban")
        self.retry_after_s = retry_after_s


class VanBanQuaDai(ValueError):
    """Cổng từ chối vì vượt trần ký tự (413), trước khi chạm GPU."""


def _co_so() -> str:
    port = (os.environ.get("LTT_VOICE_SIDECAR_PORT") or "8120").strip() or "8120"
    return f"http://127.0.0.1:{port}"


def _token() -> str:
    return (os.environ.get("LTT_VOICE_SIDECAR_TOKEN") or "").strip()


def san_sang() -> bool:
    """Đã cấu hình chưa. Dùng để app tự khai 'chưa thiết lập' thay vì đổ lỗi."""
    return bool(_token())


def _goi(duong: str, body: dict | None = None, *, timeout: float = 900.0,
         nhi_phan: bool = False):
    """Một lượt gọi. Trả `(payload, headers)`.

    `timeout` mặc định rộng vì một bài dài chạy hàng phút — nhưng nó vẫn PHẢI có:
    không có trần thì một cổng treo sẽ giữ một worker vĩnh viễn, và trần runtime
    của job không cứu được vì worker vẫn đang đập nhịp.
    """
    tok = _token()
    if not tok:
        raise LoiSidecar("LTT_VOICE_SIDECAR_TOKEN chua duoc dat tren may chu.")

    du_lieu = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _co_so() + duong, data=du_lieu,
        method="POST" if du_lieu is not None else "GET",
        headers={
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
            # UA không bắt đầu bằng `Python-urllib/` — đây là loopback nên
            # Cloudflare không dính vào, nhưng giữ thói quen một chỗ một kiểu.
            "User-Agent": "ltt-voice/1.0",
        })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            noi_dung = r.read()
            headers = dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        if e.code == 429:
            cho = 5.0
            try:
                cho = float(json.loads(raw).get("retry_after_s") or 5.0)
            except (ValueError, AttributeError, TypeError):
                try:
                    cho = float(e.headers.get("Retry-After") or 5.0)
                except (TypeError, ValueError):
                    pass
            raise SidecarBan(retry_after_s=cho) from e
        if e.code == 413:
            raise VanBanQuaDai(_chi_tiet(raw)) from e
        raise LoiSidecar(f"Cong giong tra {e.code}: {_chi_tiet(raw)}") from e
    except urllib.error.URLError as e:
        raise LoiSidecar(
            "Khong ket noi duoc toi cong giong (dich vu LTTStudioVoice co dang "
            f"chay khong?): {e.reason}") from e

    if nhi_phan:
        return noi_dung, headers
    try:
        return json.loads(noi_dung.decode("utf-8")), headers
    except ValueError as e:
        raise LoiSidecar("Cong giong tra thu khong phai JSON.") from e


def _chi_tiet(raw: bytes) -> str:
    try:
        d = json.loads(raw)
        return str(d.get("detail") or d.get("error") or raw[:200])
    except (ValueError, TypeError):
        return raw[:200].decode("utf-8", "replace")


# ── các cửa ──────────────────────────────────────────────────────────────────

def nang_luc() -> dict:
    d, _ = _goi("/v1/capabilities", timeout=180.0)
    return d


def noi(text: str, *, ref_b64: str | None = None, preset: str | None = None,
        timeout: float = 900.0) -> tuple:
    """Một lượt sinh. Trả `(wav_bytes, headers)`."""
    return _goi("/v1/speech",
                {"text": text, "ref_b64": ref_b64, "preset": preset},
                timeout=timeout, nhi_phan=True)


def noi_lo(texts: list, *, ref_b64: str | None = None,
           preset: str | None = None, timeout: float = 1800.0) -> dict:
    d, _ = _goi("/v1/batch",
                {"texts": list(texts), "ref_b64": ref_b64, "preset": preset},
                timeout=timeout)
    return d


def noi_dai(texts: list, *, ref_b64: str | None = None,
            preset: str | None = None, timeout: float = 1800.0) -> tuple:
    """Nhiều đoạn -> MỘT tệp WAV liền mạch. Trả `(wav_bytes, headers)`.

    Cùng hình dạng trả về với `noi()` — có chủ ý: tầng job chỉ nên có **một**
    nhánh xử lý phản hồi, dù văn bản một đoạn hay tám đoạn.
    """
    return _goi("/v1/speech-dai",
                {"texts": list(texts), "ref_b64": ref_b64, "preset": preset},
                timeout=timeout, nhi_phan=True)


def ghi_danh(duong_wav: str, *, denoise: bool = True,
             timeout: float = 300.0) -> dict:
    d, _ = _goi("/v1/enroll", {"duong_wav": duong_wav, "denoise": denoise},
                timeout=timeout)
    return d


def giong_dung_san() -> list:
    d, _ = _goi("/v1/voices", timeout=180.0)
    return d.get("items", [])
