"""http_cong.py — BÍ DANH. Thân mã nay ở `platform_core/image_gen/http_cong.py`.

🔴 NÂNG LÊN NỀN TẢNG 09/09/2026 (pha 06.2): `taoanh` và `thumbnail` di trú
   sang LTT_IMAGE cũng cần đúng đường này, mà `.importlinter` cấm app
   import app. Tệp này giữ nguyên tên và đường import cũ nên `anhnoibo`
   không đổi một dòng.

⛔ Đừng thêm mã vào đây — mọi thay đổi ở `platform_core/image_gen/http_cong.py`,
   nếu không ta lại có hai bản.
"""
from __future__ import annotations

from platform_core.image_gen.http_cong import (  # noqa: F401
    PROVIDER, _ghi, _voi_db, goi_http)

__all__ = ["PROVIDER", "_ghi", "_voi_db", "goi_http"]
