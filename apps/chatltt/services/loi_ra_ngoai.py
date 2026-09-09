"""loi_ra_ngoai.py — BÍ DANH. Thân mã nay ở `platform_core/loi_ra_ngoai.py`.

🔴 NÂNG LÊN NỀN TẢNG 08/09/2026 — AI CLEAN REBUILD V2 pha 05.7.

`chataistudio` di trú sang `runtime_noi_bo.luong` cũng cần đúng lớp lọc này, mà
`.importlinter` cấm app import app (contract `app-doc-lap-voi-nhau`). Ba lựa chọn:

    chep sang chataistudio  -> HAI BAN cua mot module BAO MAT. Do la cho te
                               nhat de co hai ban: chung se troi khoi nhau, va
                               ban troi ra sau la ban KHONG duoc `test_846` canh.
    bo qua                  -> ro lai dung lo da do duoc 07/09
    nang len platform_core  -> [x] chon cai nay

⭐ Tệp này giữ nguyên **tên và đường import cũ**, nên `test_846`,
   `services/luot.py`, `services/tao_media.py` và `routes/_p_nghien_cuu.py`
   không đổi một dòng nào. Hợp đồng của app không đổi; chỉ **nơi giữ chân lý**
   đổi.

⛔ Đừng thêm mã vào tệp này. Mọi thay đổi về *chữ cho người dùng khi lỗi* phải
   xảy ra ở `platform_core/loi_ra_ngoai.py` — nếu không ta lại có hai bản,
   đúng thứ việc nâng này vừa gỡ.
"""
from __future__ import annotations

from platform_core.loi_ra_ngoai import (CAU, MAC_DINH,  # noqa: F401
                                            cau, hinh_dang)

__all__ = ["CAU", "MAC_DINH", "cau", "hinh_dang"]
