"""Giá của `lttvideo` — **một mức phẳng, chỉnh được, theo giây video**.

⛔ WanGP **không có bất kỳ khái niệm tiền nào** (tìm `credit|budget|price|cost`
   trong `shared/api.py`, `shared/mcp_server.py` — không có định nghĩa nào). Đây
   là phần LTT phải tự có.

⭐ **Vì sao phẳng chứ không phái sinh từ giá vốn.** Bản trước tính:

       giây video → giây GPU → USD → × hệ số bán → credit

   Bốn phép nhân, và **mỗi phép cần một hằng số đo được**. Chuỗi ấy chỉ đúng khi
   cả bốn còn đúng; đổi một tham số sinh (độ phân giải, số bước, profile) là
   `GIAY_GPU_MOI_GIAY_VIDEO` sai ngay, mà **không có gì đỏ lên** — đúng vết xe
   `V-017` của V3 mà chính tệp này từng cảnh báo, rồi vẫn đi vào.

   Giai đoạn này dùng **nội bộ**, chưa bán. Một mức phẳng chỉnh được thì:
     · không có tham số ẩn nào làm nó sai;
     · đọc bảng giá là biết ngay sẽ trừ bao nhiêu;
     · đổi giá = sửa **một** số.

📌 Khi nào quay lại giá theo giá vốn: lúc mở bán ra ngoài. Lúc đó cần một phép
   đo `giây GPU / giây video` ở **đúng cấu hình sản xuất** — xem
   `docs/VIDEO_AI_V2/PLAN_TOAN_DIEN_THEO_TAI_LIEU_WANGP.md` §4.
"""
from __future__ import annotations

import math

#: 🔧 **Núm chỉnh giá — sửa đúng số này, không sửa chỗ nào khác.**
#:
#: Đặt 2026-09-06 theo chỉ đạo chủ dự án: giai đoạn nội bộ, giá là một lựa chọn
#: vận hành chứ không phải một phép tính. Chưa neo vào giá vốn.
CREDIT_MOI_GIAY_VIDEO: int = 30

#: Giá thật của pod A100 SXM 80GB ở `US-KS-2`, đo 2026-09-06 (`costPerHr` mà
#: RunPod trả về lúc tạo pod — **không** phải `lowestPrice` của GraphQL, con số
#: đó báo $1,39 và đã sai).
#:
#: ⚠️ **Không tham gia vào giá bán.** Giữ ở đây vì nó là *chi phí* — thứ cần biết
#:    để so với `CREDIT_MOI_GIAY_VIDEO` khi mở bán. Đừng phái sinh giá từ nó lúc
#:    này; hai con số đang cố ý độc lập.
USD_MOI_GIO_GPU: float = 1.59


def uoc_credit(*, giay_video: float) -> int:
    """Số credit giữ chỗ cho một video dài `giay_video` giây."""
    if giay_video <= 0:
        raise ValueError("giay_video must be > 0")
    return max(1, math.ceil(giay_video * CREDIT_MOI_GIAY_VIDEO))


def quyet_toan_credit(*, giay_video_giao: float, tran: int | None = None) -> int:
    """Số credit thật sự trừ, theo **số giây video đã giao**.

    ⭐ Giao gì trừ nấy. Không giao được gì (huỷ, hỏng) thì **0** — người dùng
       không trả tiền cho một tệp không tồn tại.

    `tran` là số đã giữ chỗ. ⛔ Không bao giờ trừ nhiều hơn số đã báo trước: nếu
    kết quả dài hơn dự kiến thì phần vượt là rủi ro của LTT, không phải của
    khách.
    """
    if giay_video_giao < 0:
        raise ValueError("giay_video_giao must not be negative")
    if giay_video_giao == 0:
        return 0
    credit = max(1, math.ceil(giay_video_giao * CREDIT_MOI_GIAY_VIDEO))
    if tran is not None:
        credit = min(credit, tran)
    return credit
