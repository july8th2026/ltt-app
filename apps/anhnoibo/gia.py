"""gia.py — BÍ DANH. Thân mã nay ở `platform_core/image_gen/gia.py`.

🔴 NÂNG LÊN NỀN TẢNG 09/09/2026 (pha 06.3). `taoanh` và `thumbnail` sau khi di
   trú sang LTT_IMAGE bán **cùng một model** với app này, nên phải đọc **cùng
   một bảng giá** — mà `.importlinter` cấm app import app. Tệp này giữ nguyên
   tên và đường import cũ nên `anhnoibo` không đổi một dòng.

⛔ Đừng thêm mã vào đây — mọi thay đổi ở `platform_core/image_gen/gia.py`, nếu
   không ta lại có đúng hai bảng giá mà tệp kia cảnh báo.
"""
from __future__ import annotations

from platform_core.image_gen.gia import (  # noqa: F401
    CHE_DO_THAM_CHIEU, CREDIT_MOI_ANH, HE_SO_THAM_CHIEU, PHIEN_BAN_GIA,
    SO_ANH_TOI_DA, bang_gia, he_so, tinh, uoc_tran)

__all__ = ["PHIEN_BAN_GIA", "CREDIT_MOI_ANH", "HE_SO_THAM_CHIEU",
           "SO_ANH_TOI_DA", "CHE_DO_THAM_CHIEU", "he_so", "tinh", "uoc_tran",
           "bang_gia"]
