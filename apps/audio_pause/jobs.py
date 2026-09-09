"""Handler chạy trong worker cho `audio_pause.run`.

Mỏng có chủ ý: giải tệp vào, gọi `services/chen_lang.chay()`, đẩy kết quả lên
kho, dựng phản hồi. Nghiệp vụ ở service — cùng hàm mà GUI và Macro Node gọi.

⚠️ App này có **hai** đầu ra (audio + transcript), và cả hai đều P0. Trả về một
mình tệp âm thanh là làm đứt mạch cho bước sau.
"""
from __future__ import annotations

import io
import logging
import tempfile
import uuid
from pathlib import Path

from platform_core import storage

from .services import chen_lang

log = logging.getLogger("apps.audio_pause.jobs")


class LoiAudioPause(RuntimeError):
    """Lỗi nghiệp vụ — worker biến thành job `error`, có hoàn phần giữ chỗ."""


def _tai_ve(khoa: str, thu_muc: Path) -> Path:
    kho = storage.get_storage()
    duoi = Path(str(khoa)).suffix or ".wav"
    dich = thu_muc / f"vao{duoi}"
    with kho.open(str(khoa)) as nguon, open(dich, "wb") as f:
        for khoi in iter(lambda: nguon.read(1024 * 1024), b""):
            f.write(khoi)
    return dich


def handle(params: dict, ctx=None) -> dict:
    yc = chen_lang.chuan_hoa(params)
    owner = str((params or {}).get("owner_id") or "chung")

    def tien_do(pt: int, mo_ta: str) -> None:
        if ctx is not None and hasattr(ctx, "progress"):
            ctx.progress(pt, mo_ta)

    with tempfile.TemporaryDirectory(prefix="audio_pause_") as tam:
        thu_muc = Path(tam)
        try:
            duong = _tai_ve(yc.duong_audio, thu_muc)
        except (OSError, KeyError, ValueError) as e:
            raise LoiAudioPause(f"khong doc duoc audio: {e}") from e

        try:
            ket = chen_lang.chay(
                chen_lang.YeuCau(
                    duong_audio=str(duong), ke_hoach=yc.ke_hoach,
                    ngon_ngu=yc.ngon_ngu, nguong_khop=yc.nguong_khop,
                    min_pause_ms=yc.min_pause_ms, max_pause_ms=yc.max_pause_ms,
                    min_gap_s=yc.min_gap_s, model=yc.model),
                thu_muc, tien_do=tien_do)
        except chen_lang.LoiChenLang as e:
            raise LoiAudioPause(str(e)) from e

        # ⛔ Đẩy lên kho TRONG `with`: ra khỏi khối là thư mục tạm bị xoá, và
        #    `ket.duong_audio_ra` trỏ vào một tệp không còn tồn tại. Một lỗi
        #    trông như "kho hỏng" trong khi nó là một lỗi thứ tự.
        khoa_ra = f"audio_pause/{owner}/{uuid.uuid4().hex}.wav"
        with open(ket.duong_audio_ra, "rb") as f:
            storage.get_storage().put(khoa_ra, io.BytesIO(f.read()))

    log.info("audio_pause xong job=%s khop=%d truot=%d lang=%dms",
             getattr(ctx, "job_id", "?"), ket.so_moc_khop, ket.so_moc_truot,
             ket.tong_lang_ms)
    ra = ket.as_result()
    ra["audio"] = khoa_ra
    return ra
