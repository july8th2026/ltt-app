"""
cost.py — giá credit cho CHAT AI STUDIO.

Đăng nhập ChatGPT Plus (login) ⇒ **KHÔNG có chi phí USD theo token** (chỉ giới hạn
quota tuần của tài khoản). Vì vậy credit ở đây là **GIÁ BÁN do mình đặt** để tạo
doanh thu + điều tiết dùng chung quota — không phải passthrough chi phí.

Giá phẳng, admin chỉnh sau (Q31: 1 credit = 100đ):
  - mỗi lượt chat (text): CREDIT_PER_MESSAGE
  - mỗi ảnh sinh trong lượt: CREDIT_PER_IMAGE (cộng thêm)
Giữ chỗ CREDIT_PER_MESSAGE trước khi chạy; quyết toán = message + số_ảnh × ảnh.
"""
from __future__ import annotations

CREDIT_PER_MESSAGE = 3      # mỗi lượt chat text
CREDIT_PER_IMAGE = 20       # mỗi ảnh sinh trong phiên (nặng quota hơn)
MAX_IMAGES_PER_TURN = 4     # cap số ảnh tính phí trong 1 lượt (chống balance âm sâu)


def reserve_credit() -> int:
    """Giữ chỗ trước mỗi lượt (chưa biết có ảnh hay không)."""
    return CREDIT_PER_MESSAGE


def settle_credit(n_images: int = 0) -> int:
    """Giá thật của một lượt = 1 message + n ảnh."""
    return CREDIT_PER_MESSAGE + max(0, int(n_images)) * CREDIT_PER_IMAGE
