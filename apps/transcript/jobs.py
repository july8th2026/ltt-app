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
                    model=yc.model),
                tien_do=tien_do)
        except phien_am.LoiPhienAm as e:
            # Lỗi nghiệp vụ: nói rõ, đừng để nó thành một traceback trống nghĩa
            # trong nhật ký worker.
            raise LoiTranscript(str(e)) from e

    log.info("transcript xong job=%s doan=%d ngon_ngu=%s",
             getattr(ctx, "job_id", "?"), len(ket.doan), ket.ngon_ngu)
    return ket.as_result()
