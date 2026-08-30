"""
ngan_sach.py — từ chối một yêu cầu **trước khi chạm GPU**.

⭐ Khuôn tầng 1 chốt 1.2 của `docs/KHUON_BAN_MODEL_NHA.md`: *"Ngân sách kiểm
   trước khi chạm GPU, vượt trần ⇒ 413 — từ chối một yêu cầu hỏng phải rẻ và dứt
   khoát."*

   Ở H37 (ảnh) bài học là **token**; ở đây là **ký tự**. Cùng một hình dạng: một
   yêu cầu vượt cấu hình đã đo phải bị chặn ở tầng rẻ nhất, không phải bị chặn
   bằng cách làm OOM một card đang phục vụ khách khác.

⛔ ĐỪNG HẠ TRẦN ĐỂ CHO LỌT. Trần ở `tham_so.py` là **trần chất lượng** lấy từ số
   đo, không phải một con số cho đẹp. Muốn nới thì đo lại rồi sửa `tham_so.py` và
   `PHIEN_BAN_THAM_SO`, đừng lách ở đây.
"""
from __future__ import annotations

from . import tham_so


class VuotNganSach(ValueError):
    """Yêu cầu vượt cấu hình đã đo. Ánh xạ ra HTTP 413."""

    def __init__(self, thong_diep: str, *, do_dai: int, tran: int):
        super().__init__(thong_diep)
        self.do_dai = do_dai
        self.tran = tran


def kiem_mot_luot(text: str) -> str:
    """Kiểm một lượt sinh. Trả về text đã strip. Ném `VuotNganSach` nếu vượt.

    ⚠️ Đếm **ký tự sau khi strip**, không đếm byte: tiếng Việt có dấu chiếm nhiều
       byte hơn ký tự, và trần của ta là trần **ngôn ngữ** (bao nhiêu chữ trước
       khi model trôi giọng), không phải trần truyền tải.
    """
    t = (text or "").strip()
    if not t:
        raise VuotNganSach("Van ban rong.", do_dai=0, tran=tham_so.TRAN_KY_TU_MOT_LUOT)
    n = len(t)
    if n > tham_so.TRAN_KY_TU_MOT_LUOT:
        raise VuotNganSach(
            f"Van ban {n} ky tu, vuot tran {tham_so.TRAN_KY_TU_MOT_LUOT} cho mot "
            f"luot sinh. Van ban dai hon phai di duong long-form nhieu luot.",
            do_dai=n, tran=tham_so.TRAN_KY_TU_MOT_LUOT)
    return t


def kiem_mot_lo(texts) -> list:
    """Kiểm một lô. Mỗi phần tử phải qua `kiem_mot_luot`, và lô có trần riêng."""
    ds = list(texts or [])
    if not ds:
        raise VuotNganSach("Lo rong.", do_dai=0, tran=tham_so.TRAN_SO_VAN_BAN_BATCH)
    if len(ds) > tham_so.TRAN_SO_VAN_BAN_BATCH:
        raise VuotNganSach(
            f"Lo {len(ds)} van ban, vuot tran {tham_so.TRAN_SO_VAN_BAN_BATCH}.",
            do_dai=len(ds), tran=tham_so.TRAN_SO_VAN_BAN_BATCH)
    return [kiem_mot_luot(t) for t in ds]
