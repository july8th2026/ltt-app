"""
tren_gpu.py — model có THẬT SỰ chạy trên GPU không? (H38, sau sự cố 23/08)

🔴 VÌ SAO FILE NÀY TỒN TẠI. Ngày 23/08 máy B tắt không sạch, CUDA hỏng cả máy, và
   `llama.cpp` **lặng lẽ rơi về CPU**. Không có gì báo:

     `/live`                    -> {"ok": true}
     `/health`                  -> thuong_nguon.ma = 200
     `llama-swap /running`      -> state: "ready"
     moi luot goi               -> 200

   Chỉ có một con số nói thật: **VRAM**. `llama-server` giữ 23 GB **RAM chủ**
   trong khi GPU ở 1.153 MiB / 24.576 và tải 3 %.

   Triệu chứng là **chậm**, không phải **lỗi** — và đó là loại hỏng tệ nhất, vì
   mọi chốt sống/chết đều xanh. Phép đo "thời gian tới token đầu tiên" với một
   prompt 22k token chạy **mười phút không ra một chữ**, và mọi bảng điều khiển
   vẫn xanh trong suốt mười phút đó.

⭐ ĐÂY LÀ HỌ HÀNG CỦA BÀI HỌC P6, NẶNG HƠN MỘT BẬC. P6: card bẩn ⇒ trọng số tràn
   một phần sang RAM chủ ⇒ 18,2 tok/s thay vì 63,3, không lỗi nào báo. Lần này
   **toàn bộ** model ở RAM chủ. Cùng một cách hỏng, cùng một cách phát hiện: đừng
   hỏi phần mềm nó có khoẻ không, hãy **đo VRAM**.

⛔ KHÔNG DÙNG CHỐT NÀY ĐỂ TỪ CHỐI YÊU CẦU. Nó là chốt **quan sát**, không phải
   chốt vào cửa. Một model chạy CPU vẫn trả lời đúng, chỉ chậm; từ chối phục vụ
   sẽ biến một sự cố hiệu năng thành một sự cố ngừng dịch vụ. Việc của nó là làm
   cho sự cố **nhìn thấy được**.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

#: Model 27B lượng tử hoá Q4 chiếm ~15–20 GB VRAM khi nạp đúng. Đo thật 22/08:
#: cấu hình đích chạm 23,9 GB ở đỉnh, ~20 GB lúc nghỉ.
#:
#: 5.000 MB là ngưỡng ĐỦ THẤP để không bao giờ báo nhầm khi model nạp chưa xong,
#: và ĐỦ CAO để không thể nhầm với nền desktop (1.515–1.612 MiB đo được).
VRAM_TOI_THIEU_MB = 5_000


@dataclass(frozen=True)
class PhanXuGpu:
    #: `None` = **không biết** (không hỏi được nvidia-smi, hoặc không model nào
    #: đang nạp). Đừng biến "không biết" thành "không sao" — xem `dang_lo`.
    tren_gpu: Optional[bool]
    vram_dung_mb: Optional[int]
    co_model_nap: bool
    ly_do: str = ""

    @property
    def dang_lo(self) -> bool:
        """Chỉ `True` khi **chắc chắn** có model nạp mà VRAM lại thấp.

        ⛔ "Không biết" KHÔNG phải "đáng lo". Cảnh báo dựa trên phỏng đoán sẽ bị
           người trực học cách bỏ qua, và lúc đó kênh cảnh báo chết — cùng lý do
           `job_runner` không đếm 429 vào cảnh báo (QT-2).
        """
        return self.tren_gpu is False


def kiem(*, co_model_nap: bool,
         doc_vram: Callable[[], Optional[int]],
         nguong_mb: int = VRAM_TOI_THIEU_MB) -> PhanXuGpu:
    """Model đang nạp mà VRAM thấp ⇒ nó đang ở RAM chủ.

    `co_model_nap` phải đến từ `llama-swap /running`, không phải từ phỏng đoán:
    không model nào nạp thì VRAM thấp là **bình thường**, không phải sự cố.
    """
    if not co_model_nap:
        return PhanXuGpu(None, None, False, "khong co model nao dang nap")

    vram = doc_vram()
    if vram is None:
        return PhanXuGpu(None, None, True, "khong hoi duoc nvidia-smi")

    if vram < nguong_mb:
        return PhanXuGpu(
            False, vram, True,
            f"model dang nap nhung VRAM chi {vram} MB (< {nguong_mb}) — "
            f"gan nhu chac chan no da roi ve CPU, va se cham hang chuc lan")
    return PhanXuGpu(True, vram, True, "")
