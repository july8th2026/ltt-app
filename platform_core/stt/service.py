"""Một điểm gọi `faster_whisper` cho các App migrate từ bốn bot.

Ba việc, và **chỉ** ba việc:

    1. nạp model một lần, giữ theo `(model, device, compute_type)`
    2. cache kết quả theo **hash nội dung audio** + model + ngôn ngữ + hồ sơ
    3. áp một **hồ sơ có tên** (`ho_so.py`) rồi gọi `transcribe`

⛔ Nó **không** quyết định tham số. Tham số ở `ho_so.py`, và bên gọi phải nêu
   tên hồ sơ. Xem docstring ở đó về việc vì sao không có mặc định.

⛔ Nó **không** biết App nào tồn tại, không import `apps.*`, không giữ giá,
   không đụng hàng đợi. Cùng ranh giới mà `runtime_noi_bo` giữ.

## Cache theo NỘI DUNG, không theo đường dẫn

Cả ba bot legacy đều cache theo `sha256` nội dung tệp. Giữ nguyên, vì đó là thứ
duy nhất đúng khi cùng một audio tới qua hai đường dẫn tạm khác nhau — chuyện
xảy ra **mỗi lượt** trong một hàng đợi job, nơi tệp được tải về một thư mục tạm
mang tên ngẫu nhiên.

⚠️ Khoá cache **phải** gồm tên hồ sơ. Bản legacy khoá theo `(hash, model, lang)`
   — đúng với chúng, vì mỗi bot chỉ có một hồ sơ. Ở đây sáu hồ sơ dùng chung một
   thư mục cache, nên thiếu tên hồ sơ là **trả kết quả của hồ sơ khác**: cùng
   audio, cùng model, cùng ngôn ngữ, khác `vad_filter` — và không ai phát hiện,
   vì kết quả trông hoàn toàn hợp lệ.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from platform_core.stt import ho_so as _ho_so

log = logging.getLogger("platform_core.stt")

#: Model đã nạp, theo `(model, device, compute_type)`.
_MODEL: dict[tuple[str, str, str], Any] = {}


class LoiSTT(RuntimeError):
    """Không phiên âm được. Bên gọi quyết định đó là lỗi job hay lỗi tham số."""


def _thu_muc_cache() -> Path:
    """Thư mục cache. `LTT_STT_CACHE` ghi đè — dùng cho test và cho máy khác ổ."""
    thu = os.environ.get("LTT_STT_CACHE", "").strip()
    duong = Path(thu) if thu else Path("data") / "stt_cache"
    duong.mkdir(parents=True, exist_ok=True)
    return duong


def bam_audio(duong: str | Path) -> str:
    """`sha256` **nội dung** tệp, đọc theo khối để không nạp cả tệp vào RAM."""
    h = hashlib.sha256()
    with open(duong, "rb") as f:
        for khoi in iter(lambda: f.read(1024 * 1024), b""):
            h.update(khoi)
    return h.hexdigest()


def _tep_cache(bam: str, model: str, ngon_ngu: str, ten_ho_so: str) -> Path:
    lang = ngon_ngu or "auto"
    return _thu_muc_cache() / f"{bam}_{model}_{lang}_{ten_ho_so}.json"


def _hop_le(du_lieu: Any) -> bool:
    """Cache chỉ dùng được khi nó mang đúng hình dạng ta ghi ra.

    Một tệp cache hỏng (ghi dở vì mất điện, sửa tay) **không** được biến thành
    một lượt phiên âm rỗng — đó là cách một lỗi hạ tầng thành một lỗi nội dung.
    """
    return (isinstance(du_lieu, dict)
            and isinstance(du_lieu.get("segments"), list)
            and "language" in du_lieu)


def _nap_model(model: str, device: str, compute_type: str):
    khoa = (model, device, compute_type)
    if khoa in _MODEL:
        return _MODEL[khoa]
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:                      # pragma: no cover - moi truong
        raise LoiSTT(f"thieu `faster_whisper`: {e}") from e
    log.info("nap model STT %s (%s/%s)", model, device, compute_type)
    _MODEL[khoa] = WhisperModel(model, device=device, compute_type=compute_type)
    return _MODEL[khoa]


def go_model() -> None:
    """Nhả mọi model đã nạp. Gọi khi worker cần trả VRAM cho bước sau."""
    _MODEL.clear()


def phien_am(duong_audio: str | Path, *, ten_ho_so: str,
             model: str = "large-v3", ngon_ngu: Optional[str] = None,
             device: str = "cuda", compute_type: str = "float16",
             dung_cache: bool = True) -> dict:
    """Phiên âm một tệp theo một hồ sơ **có tên**.

    Trả `{"language": str, "language_probability": float, "segments": [...]}`,
    mỗi đoạn `{"start", "end", "text", "words": [...]}` — `words` rỗng khi hồ sơ
    tắt `word_timestamps`.

    ⚠️ `ngon_ngu=None` nghĩa là **để whisper tự dò**, không phải "tiếng Anh".
       Nhưng với hồ sơ chọn theo ngôn ngữ (`pause`) thì `None` là một lỗi —
       `ho_so.ten_thuc` từ chối, cố ý.
    """
    tham_so = _ho_so.lay(ten_ho_so, ngon_ngu)
    ten_thuc = _ho_so.ten_thuc(ten_ho_so, ngon_ngu)
    duong = Path(duong_audio)
    if not duong.is_file():
        raise LoiSTT(f"khong co tep audio: {duong}")

    bam = ""
    tep = None
    if dung_cache:
        bam = bam_audio(duong)
        tep = _tep_cache(bam, model, ngon_ngu or "", ten_thuc)
        if tep.is_file():
            try:
                du_lieu = json.loads(tep.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                log.warning("cache STT hong, bo qua: %s (%s)", tep.name, e)
            else:
                if _hop_le(du_lieu):
                    log.info("cache STT trung: %s", tep.name)
                    return du_lieu
                log.warning("cache STT sai hinh dang, bo qua: %s", tep.name)

    mo_hinh = _nap_model(model, device, compute_type)
    tham_so["language"] = ngon_ngu or None
    try:
        cac_doan, thong_tin = mo_hinh.transcribe(str(duong), **tham_so)
        doan = [{
            "start": float(d.start),
            "end": float(d.end),
            "text": str(d.text).strip(),
            "words": [{"start": float(t.start), "end": float(t.end),
                       "text": str(t.word).strip()}
                      for t in (getattr(d, "words", None) or [])],
        } for d in cac_doan]
    except LoiSTT:
        raise
    except Exception as e:                        # noqa: BLE001 - loi cua thu vien
        # Gói lại thành một lớp lỗi của ta, giữ nguyên chuỗi gốc và traceback.
        raise LoiSTT(f"whisper that bai: {type(e).__name__}: {e}") from e

    ket = {
        "language": str(getattr(thong_tin, "language", "") or ngon_ngu or ""),
        "language_probability": float(
            getattr(thong_tin, "language_probability", 0.0) or 0.0),
        "ho_so": ten_thuc,
        "segments": doan,
    }
    if dung_cache and tep is not None:
        try:
            tep.write_bytes((json.dumps(ket, ensure_ascii=False)
                             ).encode("utf-8"))
        except OSError as e:
            # Không ghi được cache là chuyện của đĩa, không phải của kết quả.
            log.warning("khong ghi duoc cache STT: %s (%s)", tep.name, e)
    return ket
