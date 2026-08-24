"""
tren_gpu.py — model ảnh có THẬT SỰ chạy trên GPU không? (H37/L3)

🔴 VÌ SAO FILE NÀY TỒN TẠI. Ngày 23/08 máy B tắt không sạch, CUDA hỏng cả máy, và
   `llama.cpp` **lặng lẽ rơi về CPU**. Không có gì báo: mọi chốt sống/chết đều
   xanh, mọi lượt gọi trả `200`, và sự cố chạy **hơn một giờ** trước khi tình cờ
   bị phát hiện trong lúc đo một việc khác.

   Sự cố đó xảy ra ở phía LLM. Nhưng nó là **sự cố của cái máy**, không phải của
   một dịch vụ — CUDA hỏng thì hỏng cho mọi hộ dùng chung card. Phía ảnh chạy
   trên đúng máy đó, và cho tới file này thì **không có chốt nào** bắt được.

   Triệu chứng bên ảnh sẽ còn khó thấy hơn bên chữ: một lượt vẽ vốn đã mất 96
   giây, nên "chậm gấp hàng chục lần" trông giống hệt "máy đang bận" — thứ mà ta
   đã dạy mọi người coi là bình thường.

⭐ CHỐT DUY NHẤT CHẮC CHẮN: **có job đang vẽ mà VRAM lại thấp**.
   Không phải "có model nạp" như bên LLM — ComfyUI chỉ giữ model thường trú **sau**
   lượt vẽ đầu tiên, nên cổng vừa khởi động mà VRAM thấp là chuyện bình thường.
   Đang vẽ thì không có cách nào VRAM thấp.

⛔ KHÔNG DÙNG CHỐT NÀY ĐỂ TỪ CHỐI YÊU CẦU. Nó là chốt **quan sát**. Một model chạy
   CPU vẫn vẽ đúng, chỉ chậm; từ chối phục vụ sẽ biến một sự cố hiệu năng thành
   một sự cố ngừng dịch vụ.

⛔ VÀ "KHÔNG BIẾT" KHÔNG PHẢI "ĐÁNG LO". Cảnh báo dựa trên phỏng đoán sẽ bị người
   trực học cách bỏ qua, và lúc đó kênh cảnh báo chết — cùng lý do cổng không đếm
   429 vào cảnh báo (D-005: bận ≠ hỏng).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

#: HiDream đang vẽ chiếm hàng chục GB VRAM. 5.000 MB là ngưỡng ĐỦ THẤP để không
#: bao giờ báo nhầm giữa lúc nạp trọng số, và ĐỦ CAO để không thể nhầm với nền
#: desktop (đo được 1.515–1.612 MiB trên máy B).
VRAM_TOI_THIEU_MB = 5_000

#: Một job vừa nhận chưa chắc đã bắt đầu lấy mẫu: nó còn xếp hàng trong ComfyUI,
#: còn tải ảnh tham chiếu, còn nạp trọng số. Chỉ kết luận khi nó đã chạy đủ lâu
#: để **không còn cách giải thích nào khác**.
#:
#: 90 giây: dài hơn toàn bộ phần chuẩn bị đo được, ngắn hơn một lượt vẽ (96 giây)
#: nên sự cố vẫn bị bắt ngay trong lượt đầu tiên chứ không phải lượt thứ hai.
CHAY_LAU_TOI_THIEU_S = 90.0


@dataclass(frozen=True)
class PhanXuGpu:
    #: `None` = **không biết** (không hỏi được nvidia-smi, hoặc không job nào đang
    #: vẽ đủ lâu). Đừng biến "không biết" thành "không sao" — xem `dang_lo`.
    tren_gpu: Optional[bool]
    vram_dung_mb: Optional[int]
    co_job_dang_chay: bool
    ly_do: str = ""

    def as_dict(self) -> dict:
        return {"tren_gpu": self.tren_gpu, "vram_dung_mb": self.vram_dung_mb,
                "co_job_dang_chay": self.co_job_dang_chay,
                "dang_lo": self.dang_lo, "ly_do": self.ly_do}

    @property
    def dang_lo(self) -> bool:
        """Chỉ `True` khi **chắc chắn**: đang vẽ đủ lâu mà VRAM vẫn thấp."""
        return self.tren_gpu is False


def kiem(*, giay_dang_chay: Optional[float],
         doc_vram: Callable[[], Optional[int]],
         nguong_mb: int = VRAM_TOI_THIEU_MB,
         lau_toi_thieu_s: float = CHAY_LAU_TOI_THIEU_S) -> PhanXuGpu:
    """`giay_dang_chay` = job chưa kết thúc đã nhận được bao lâu; `None` = không có.

    Đang vẽ mà VRAM thấp ⇒ trọng số đang ở RAM chủ.
    """
    if giay_dang_chay is None:
        return PhanXuGpu(None, None, False, "khong co job nao dang chay")
    if giay_dang_chay < lau_toi_thieu_s:
        # Chưa đủ lâu để loại trừ "đang xếp hàng / đang nạp trọng số".
        return PhanXuGpu(None, None, True,
                         f"job moi chay {giay_dang_chay:.0f}s (< {lau_toi_thieu_s:.0f}s)")

    vram = doc_vram()
    if vram is None:
        return PhanXuGpu(None, None, True, "khong hoi duoc nvidia-smi")

    if vram < nguong_mb:
        return PhanXuGpu(
            False, vram, True,
            f"dang ve {giay_dang_chay:.0f}s nhung VRAM chi {vram} MB "
            f"(< {nguong_mb}) — gan nhu chac chan da roi ve CPU")
    return PhanXuGpu(True, vram, True, "")
