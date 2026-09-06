"""Giá của `lttvideo` — quy giây GPU thành credit.

⛔ WanGP **không có bất kỳ khái niệm tiền nào** (kiểm bằng cách tìm symbol
   `credit|budget|price|cost` trong `shared/api.py`, `shared/mcp_server.py`,
   `wangp-agent/SKILL.md` — không có định nghĩa nào). Đây là phần LTT phải tự có.

🔴 **Mọi số tiền phái sinh từ MỘT hằng số đo được.** Bài học `V-017` của V3: giá
   A100 được gõ tay vào một chỗ, rồi mọi thứ phái sinh từ nó, và khi nó sai thì
   cả bảng ngân sách sai theo mà **không có gì đỏ lên**.

⚠️ `USD_MOI_GIO_GPU` dưới đây là giá **đo được** của lượt P01 (A100 SXM ở
   `US-KS-2`, `costPerHr` mà RunPod trả về khi tạo pod), **không** phải giá bảng.
   Bảng giá GraphQL báo $1,39 trong khi hoá đơn thật là $1,59 — đừng dùng bảng.

📌 Đổi lớp GPU (`O-006`) ⇒ đổi đúng hằng số này, không đổi chỗ nào khác.
"""
from __future__ import annotations

import math

#: Giá thật của pod A100 SXM 80GB ở `US-KS-2`, đo 2026-09-06 (`costPerHr`).
#: ⛔ Không phải `lowestPrice` của GraphQL — con số đó báo $1,39 và đã sai.
USD_MOI_GIO_GPU: float = 1.59

#: Q31: 1 credit = 100 đồng. Tỉ giá quy USD → credit của nền tảng.
#: ⚠️ Con số này thuộc chính sách thương mại; nó ở đây vì `lttvideo` là app đầu
#:    tiên tính tiền theo **giây GPU thuê ngoài** thay vì theo token của provider.
CREDIT_MOI_USD: float = 260.0

#: Hệ số giá bán trên giá vốn (`V-003` của V3: bán = 2 × giá vốn).
HE_SO_BAN: float = 2.0

#: Thời gian sinh mỗi giây video, đo ở P01: 20 bước × 79,8 giây cho 5,06 giây
#: video ⇒ ~316 giây GPU mỗi giây video, ở `profile 4`.
#: 🔴 Đây là số của `profile 4` — hồ sơ CHẬM NHẤT. `profile 3` (đã chốt) chưa đo
#:    được vì `US-KS-2` hết A100. Dùng số này để **ước cao**, đúng vai trò của
#:    giữ chỗ; quyết toán vẫn theo giây GPU thật.
GIAY_GPU_MOI_GIAY_VIDEO: float = 316.0


def _usd_sang_credit(usd: float) -> int:
    return max(1, math.ceil(usd * CREDIT_MOI_USD))


def uoc_credit(*, giay_video: float) -> int:
    """Ước **cao** để giữ chỗ trước khi chạy.

    ⭐ Giữ chỗ phải ước **cao**: trừ thiếu rồi đòi thêm là chuyện không làm được
       khi video đã sinh xong.
    """
    if giay_video <= 0:
        raise ValueError("giay_video must be > 0")
    giay_gpu = giay_video * GIAY_GPU_MOI_GIAY_VIDEO
    usd = giay_gpu / 3600.0 * USD_MOI_GIO_GPU * HE_SO_BAN
    return _usd_sang_credit(usd)


def quyet_toan_credit(*, giay_gpu: float, tran: int | None = None) -> int:
    """Số credit thật sự trừ, tính theo **giây GPU đã chạy**.

    `tran` là số đã giữ chỗ. ⛔ Không bao giờ trừ nhiều hơn số đã báo cho người
    dùng — nếu chạy lâu hơn dự kiến thì phần vượt là rủi ro của LTT, không phải
    của khách.
    """
    if giay_gpu < 0:
        raise ValueError("giay_gpu must not be negative")
    usd = giay_gpu / 3600.0 * USD_MOI_GIO_GPU * HE_SO_BAN
    credit = _usd_sang_credit(usd)
    if tran is not None:
        credit = min(credit, tran)
    return credit
