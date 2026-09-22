"""Handler chạy trong worker cho `transcript.run`.

⭐ Tệp này **mỏng có chủ ý**. Nó chuyển tham số, giải tệp đầu vào, gọi
`services/phien_am.chay()`, rồi dựng kết quả. Toàn bộ nghiệp vụ ở service — và
đó chính là thứ làm cho GUI, Macro Node và API cho **cùng một kết quả**: cả ba
đi vào cùng một hàm.

⛔ Đừng thêm một nhánh "nếu gọi từ Node thì..." ở đây. Một nhánh như thế là chỗ
   đầu tiên ba đường bắt đầu trôi khỏi nhau, và nó trôi **im lặng**.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from platform_core import storage

from .gia import uoc_luong_credit
from .services import phien_am

log = logging.getLogger("apps.transcript.jobs")


class LoiTranscript(RuntimeError):
    """Lỗi nghiệp vụ — worker biến thành job `error`, có hoàn phần giữ chỗ."""


def _giai_audio(khoa: str, thu_muc: Path) -> Path:
    """Khoá lưu trữ → một tệp cục bộ trong thư mục tạm của lượt chạy.

    ⚠️ Tên tệp tạm là **ngẫu nhiên**, nên mọi thứ khoá theo đường dẫn sẽ trượt.
       Đó đúng là lý do `platform_core.stt` cache theo **hash nội dung**.
    """
    kho = storage.get_storage()
    duoi = Path(str(khoa)).suffix or ".wav"
    dich = thu_muc / f"vao{duoi}"
    with kho.open(str(khoa)) as nguon, open(dich, "wb") as f:
        # Chép theo khối: một tệp âm thanh dài không được nạp cả vào RAM của
        # worker, nơi có thể đang có ba job khác cùng chạy.
        for khoi in iter(lambda: nguon.read(1024 * 1024), b""):
            f.write(khoi)
    return dich


def _quyet_toan(job_id: str, thoi_luong_s: float) -> int:
    """Giá thật theo thời lượng đo lại, KHÔNG vượt phần đã giữ (Q84).

    Không giữ thêm sau báo giá: tệp đã được đo ở route/`measured_from`, nên giá
    thật chỉ lệch làm tròn; nếu lệch lên thì khách được lợi, không bị thu thêm.
    """
    that = uoc_luong_credit(thoi_luong_s)
    if not job_id:
        return that
    from platform_core import credit
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        da_giu = int(credit.so_da_giu(db, job_id) or 0)
    finally:
        db.close()
    return min(that, da_giu) if da_giu > 0 else that


def handle(params: dict, ctx=None) -> dict:
    """`params` theo `ToolSpec.params_schema`; `ctx` do worker đưa vào."""
    yc = phien_am.chuan_hoa(params)

    def tien_do(pt: int, mo_ta: str) -> None:
        if ctx is not None and hasattr(ctx, "progress"):
            ctx.progress(pt, mo_ta)

    with tempfile.TemporaryDirectory(prefix="transcript_") as tam:
        thu_muc = Path(tam)
        try:
            duong = _giai_audio(yc.duong_audio, thu_muc)
        except (OSError, KeyError, ValueError) as e:
            raise LoiTranscript(f"khong doc duoc audio: {e}") from e

        try:
            ket = phien_am.chay(
                phien_am.YeuCau(
                    duong_audio=str(duong),
                    ngon_ngu=yc.ngon_ngu, min_s=yc.min_s, max_s=yc.max_s,
                    kem_khoang_lang=yc.kem_khoang_lang,
                    chu_khoang_lang=yc.chu_khoang_lang,
                    nguong_khoang_lang=yc.nguong_khoang_lang,
                    model=yc.model, he=yc.he),
                tien_do=tien_do)
        except phien_am.LoiPhienAm as e:
            # Lỗi nghiệp vụ: nói rõ, đừng để nó thành một traceback trống nghĩa
            # trong nhật ký worker.
            raise LoiTranscript(str(e)) from e

    job_id = str(getattr(ctx, "job_id", "") or "")
    ra = ket.as_result()
    ra["credit_cost"] = _quyet_toan(job_id, ket.thoi_luong_s)
    log.info("transcript xong job=%s doan=%d ngon_ngu=%s credit=%s",
             job_id or "?", len(ket.doan), ket.ngon_ngu, ra["credit_cost"])
    return ra
