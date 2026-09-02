"""
routes/ — bề mặt HTTP của ChatLTT, tách theo màn (AGENTS.md §8.1). CHỈ lo HTTP.

    _chung.py        router + helper (uid, CSRF cho JSON, JSON no-store, lỗi → mã)
    _p_trang.py      GET /chatltt          vỏ React (Phase 08) · GET /api/danh-muc
    _p_hoi_thoai.py  /api/hoi-thoai/*      tạo · liệt kê/tìm · sự thật · đổi tên · lưu trữ · xoá · chọn lá
    _p_luot.py       /api/hoi-thoai/{id}/luot · /api/luot/{id}/stream · /api/luot/{id}/dung

Nền tảng chỉ cần biến `router`. Import từng mảnh để handler đăng ký **trước
khi** nền tảng gắn router vào FastAPI.
"""
from apps.chatltt.routes._chung import router
from apps.chatltt.routes import _p_trang, _p_hoi_thoai, _p_luot  # noqa: F401,E402

__all__ = ["router"]
