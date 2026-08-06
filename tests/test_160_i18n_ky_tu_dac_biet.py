"""
H24 — chuỗi dịch chứa ký tự đặc biệt không được làm vỡ trang.

Hai lỗi THẬT đã xảy ra, cả hai chỉ lộ lúc render chứ không lộ lúc dịch:

1. **Dấu `%` văn xuôi làm trang trả 500.** Hàm `_()` bản `newstyle` của Jinja
   luôn chạy `rv % variables`, kể cả khi `variables` rỗng. Chuỗi
   "Ổn định hai pass bằng libvidstab · +20%." nổ `ValueError: incomplete format`
   và làm sập trang Nâng cấp video. Sáu test hồi quy bắt được, nhưng chỉ sau khi
   đã dịch xong 609 chuỗi.

2. **Thực thể HTML bị escape hai lần.** Chuỗi dịch có `&larr;`, `&amp;`. Nếu trả
   về `str` thường thì Jinja escape tiếp và người dùng thấy `&amp;larr;`.

Đây là lý do `server/templating.py` KHÔNG dùng thẳng bản `newstyle` mà bọc lại.
"""
from __future__ import annotations

import pytest

from platform_core import i18n


@pytest.fixture()
def moi_truong(monkeypatch):
    monkeypatch.setenv("LTT_ENV", "development")
    i18n.dat_ngon_ngu(i18n.GOC)
    yield
    i18n.dat_ngon_ngu(i18n.GOC)


def _render(chuoi_template: str) -> str:
    from server.templating import templates
    return templates.env.from_string(chuoi_template).render()


# ── 1. Dấu phần trăm ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("chuoi", [
    "Ổn định hai pass bằng libvidstab · +20%.",
    "Nội suy 48/60 FPS rồi upscale · +120%.",
    "Giảm 50% dung lượng",
    "100%",
    "%",
])
def test_dau_phan_tram_khong_lam_vo_trang(moi_truong, chuoi):
    """`_()` khong duoc ap dinh dang `%` khi khong co bien nao."""
    ra = _render('{{ _("' + chuoi + '") }}')
    assert "%" in ra, f"mat dau % trong {chuoi!r}"


def test_hai_chuoi_that_da_lam_sap_trang_nang_cap_video(moi_truong):
    """Hồi quy có tên: đúng hai chuỗi đã làm trang Nâng cấp video trả 500."""
    for s in ("Ổn định hai pass bằng libvidstab · +20%.",
              "Nội suy 48/60 FPS rồi upscale · +120%."):
        assert _render('{{ _("' + s + '") }}')


def test_dau_phan_tram_van_dung_khi_dich_sang_tieng_anh(moi_truong):
    i18n.xoa_cache()
    i18n.dat_ngon_ngu("en")
    try:
        ra = _render('{{ _("Ổn định hai pass bằng libvidstab · +20%.") }}')
        assert "+20%" in ra
    finally:
        i18n.dat_ngon_ngu(i18n.GOC)
        i18n.xoa_cache()


# ── 2. Thực thể HTML ─────────────────────────────────────────────────────────
def test_thuc_the_html_khong_bi_escape_hai_lan(moi_truong):
    """`&larr;` phai ra `&larr;`, khong duoc thanh `&amp;larr;`."""
    ra = _render('{{ _("&larr; Tạo mới") }}')
    assert "&amp;larr;" not in ra, "bi escape hai lan — nguoi dung se thay &amp;larr;"
    assert "&larr;" in ra


def test_thuc_the_amp_khong_bi_escape_hai_lan(moi_truong):
    ra = _render('{{ _("Nguồn &amp; ghi chú nghiên cứu") }}')
    assert "&amp;amp;" not in ra
    assert "&amp;" in ra


# ── 3. Vẫn nội suy được khi CÓ biến ──────────────────────────────────────────
def test_van_noi_suy_duoc_khi_truyen_bien(moi_truong):
    """Bo dinh dang khi khong co bien KHONG duoc lam mat kha nang noi suy."""
    ra = _render('{{ _("Xin chào %(ten)s", ten="Trung") }}')
    assert "Trung" in ra
