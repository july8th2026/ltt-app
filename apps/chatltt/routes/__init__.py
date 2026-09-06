"""
routes/ — bề mặt HTTP của ChatLTT, tách theo màn (AGENTS.md §8.1). CHỈ lo HTTP.

    _chung.py        router + helper (uid, CSRF cho JSON, JSON no-store, lỗi → mã)
    _p_trang.py      GET /chatltt          vỏ React (Phase 08) · GET /api/danh-muc
    _p_hoi_thoai.py  /api/hoi-thoai/*      tạo · liệt kê/tìm · sự thật · đổi tên · lưu trữ · xoá · chọn lá
    _p_luot.py       /api/hoi-thoai/{id}/luot · /api/luot/{id}/stream · /api/luot/{id}/dung
    _p_duyet.py      /api/duyet/dang-cho · /api/duyet/{id}   (H44 P04)
    _p_tep.py        /api/hoi-thoai/{id}/tep · .../{up}/trich · DELETE /api/tep/{id}  (B1)
    _p_media.py      /api/bao-gia · /api/hoi-thoai/{id}/tao · /api/luot/{id}/trang-thai
                     · /tai-san/{key} (cua DUY NHAT phuc vu anh/tieng)

Nền tảng chỉ cần biến `router`. Import từng mảnh để handler đăng ký **trước
khi** nền tảng gắn router vào FastAPI.
"""
from apps.chatltt.routes._chung import router
from apps.chatltt.routes import (  # noqa: F401,E402  (import de dang ky route)
    _p_trang, _p_hoi_thoai, _p_luot, _p_media, _p_duyet, _p_tep)

__all__ = ["router"]
