"""Khu quan tri: dieu huong dung chung + cac mien tu khai view cua minh.

`VIEWS` la danh sach DUY NHAT ma `server/admin.py:setup_admin` lap qua de dang
ky trang cua cac mien moi. Them mot trang vao mot mien co san thi sua dung tep
mien do; them ca mot MIEN moi thi them dung mot dong o day — va do la dung luc
nen buoc nguoi ta dung lai suy nghi.

Xem `docs/admin_mvp_v3/04_EXTENSION_CONTRACT.md`.
"""

from __future__ import annotations

from server.routes.admin import he_thong as _he_thong
from server.routes.admin import khach_hang as _khach_hang

VIEWS = (
    *_khach_hang.VIEWS,
    *_he_thong.VIEWS,
)

__all__ = ["VIEWS"]
