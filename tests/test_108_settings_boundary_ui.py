import re
"""H15.S2.3 — ranh giới operator, và trang Tình trạng hệ thống.

## ⛔ VIẾT LẠI 2026-08-26 — tệp này từng kiểm một trang KHÔNG CÒN TỒN TẠI

Bản cũ đọc `server/routes/settings.py` và `server/templates/settings.html`. Cả
hai là **trang cấu hình CỦA APP socialbot**, đi cùng nó ở Q108. Từ đó tệp này
ném `FileNotFoundError` ngay dòng đầu — nhưng chỉ lộ ra ở lượt `pytest` đầy đủ
đầu tiên chạy sau đợt xoá.

## ⭐ Và khi sửa thì lộ ra thứ đáng giá hơn hẳn phép kiểm hỏng

Ba template vẫn trỏ `href="/settings"` — `_header.html` và **hai** chỗ trong
`home.html` — tất cả sau `{% if is_admin(request) %}`.

Route đó không còn: `GET /settings` trả **404**. Nghĩa là **mọi admin** đều thấy
một mục "Cấu hình hệ thống" dẫn vào hư không, từ Q108 tới nay.

Cùng lớp lỗi với `/ltt-llm` (INV-9): *một liên kết được dựng từ giả định rằng
đích của nó tồn tại, và không phép kiểm nào canh giả định đó.* Khác một điểm
đáng nói: `/ltt-llm` sinh tự động từ manifest, còn `/settings` được **viết tay
trong template** — nên luật linter bắt `/ltt-llm` không bắt được cái này.

⇒ Phép kiểm cuối tệp này đóng đúng khoảng trống đó cho template.

`server/templates/settings.html` (12,8 KB) cũng đã xoá — không mã nào render nó.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_status_require_operator_not_only_login():
    """Trang Tình trạng hệ thống phơi thông tin vận hành — đăng nhập là chưa đủ."""
    status = _read("server/routes/status.py")
    assert "Depends(require_login)" not in status
    assert "Depends(require_operator)" in status


def test_user_shell_hides_operator_links():
    # Golden UI P1-01 (16/09): menu tài khoản của HAI khung là MỘT tệp
    # `_menu_tai_khoan.html` — liên kết vận hành chốt ở đó, sau `_la_admin`.
    header = _read("server/templates/_header.html")
    menu = _read("server/templates/_menu_tai_khoan.html")
    home = _read("server/templates/home.html")
    assert '{% include "_menu_tai_khoan.html" %}' in header
    assert "{%- set _la_admin = is_admin(request) -%}" in menu
    assert re.search(r'\{% if _la_admin %\}<a href="/status"', menu)
    assert "is_admin(request)" in home and 'href="/status"' in home


def test_trang_status_co_hop_dong_tiep_can_duoc():
    status = _read("server/templates/status.html")
    assert 'aria-live' in status or 'role="status"' in status or "<table" in status


def test_KHONG_template_nao_tro_vao_mot_route_da_bien_mat():
    """⛔ Bất biến sinh ra từ một lỗi thật: `/settings` là 404 cho mọi admin.

    Route `server/routes/settings.py` đi cùng socialbot (Q108); ba liên kết trỏ
    vào nó thì ở lại. Không phép kiểm nào canh, vì liên kết viết tay trong
    template không đi qua `nav_entries()` — nơi luật linter của INV-9 canh.

    ⭐ Phép kiểm này CỐ Ý hẹp: chỉ chốt đúng những đường đã từng biến mất, thay
       vì cố dựng lại bảng route rồi so. Dựng bảng route ở đây là chép lại một
       thứ FastAPI đã có, và bản chép thứ hai luôn là bản trôi dạt — chưa kể
       phiên bản Starlette này không mở `_IncludedRouter` ra được, nên phép đếm
       qua nó cho ra số sai (đã đo 25/08).
    """
    da_go = ("/settings",)
    for ten in ("_header.html", "home.html", "base.html"):
        noi_dung = _read(f"server/templates/{ten}")
        for duong in da_go:
            assert f'href="{duong}"' not in noi_dung, (
                f"{ten} van tro vao {duong} — route do da bien mat cung socialbot "
                "(Q108) va tra 404")
