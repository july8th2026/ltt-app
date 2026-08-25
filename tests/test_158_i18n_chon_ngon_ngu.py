"""
H24 Pha 0 — chọn ngôn ngữ và tiền tố đường dẫn.

Khoá ba nhóm tính chất, theo thứ tự nguy hiểm giảm dần:

1. **Đường miễn trừ không bao giờ mang tiền tố.** PayOS gọi vào một URL cố định;
   gắn `/en/` vào là khách trả tiền mà không nhận credit. Cùng loại lỗi với
   `return_url=PLACEHOLDER` (2026-08-06) — bên ngoài luôn gọi đúng URL ta đưa.
2. **Lựa chọn tường minh của người dùng không bị máy đoán ghi đè.** Lỗi phổ biến
   nhất của web đa ngôn ngữ: người dùng bấm đổi sang tiếng Anh, tải lại trang thì
   IP Việt Nam đẩy về tiếng Việt, đổi mãi không được.
3. **Suy luận đúng thứ tự** và không sập khi thiếu tín hiệu.
"""
from __future__ import annotations

import pytest

from platform_core import i18n


# ── 1. Đường miễn trừ ────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", [
    "/webhooks/payment/payos",
    "/health/ready",
    "/health/live",
    "/static/ltt.css",
    "/assets/app.js",
    "/favicon.ico",
    "/robots.txt",
    "/oauth/facebook/callback",
    "/api/jobs/123",
])
def test_duong_mien_tru_khong_bao_gio_mang_tien_to(path):
    assert i18n.duoc_mien_tru(path) is True
    assert i18n.them_tien_to(path, i18n.EN) == path, (
        f"{path} bi gan tien to — he thong ben ngoai goi vao se truot")


def test_webhook_thanh_toan_la_duong_nguy_hiem_nhat():
    """Tách riêng cho rõ: hỏng đường này = khách trả tiền, không nhận credit."""
    p = "/webhooks/payment/payos"
    for lang in i18n.NGON_NGU:
        assert i18n.them_tien_to(p, lang) == p


@pytest.mark.parametrize("path", ["/nap", "/login", "/", "/jobs/abc"])
def test_duong_thuong_khong_bi_mien_tru_nham(path):
    assert i18n.duoc_mien_tru(path) is False


# ── 2. Tiền tố ───────────────────────────────────────────────────────────────
def test_tach_tien_to():
    assert i18n.tach_tien_to("/en/nap") == ("/nap", "en")
    assert i18n.tach_tien_to("/en") == ("/", "en")
    assert i18n.tach_tien_to("/en/") == ("/", "en")
    assert i18n.tach_tien_to("/nap") == ("/nap", None)
    assert i18n.tach_tien_to("/") == ("/", None)


def test_tach_tien_to_khong_an_nham_duong_bat_dau_bang_en():
    """`/entity` không phải `/en` + `/tity`."""
    assert i18n.tach_tien_to("/entity") == ("/entity", None)
    assert i18n.tach_tien_to("/english-page") == ("/english-page", None)


def test_them_tien_to():
    assert i18n.them_tien_to("/nap", "en") == "/en/nap"
    assert i18n.them_tien_to("/", "en") == "/en"
    assert i18n.them_tien_to("/nap", "vi") == "/nap"        # goc o duong goc
    assert i18n.them_tien_to("/en/nap", "vi") == "/nap"     # doi nguoc lai
    assert i18n.them_tien_to("/en/nap", "en") == "/en/nap"  # khong nhan doi


def test_them_tien_to_giu_query_string():
    """Mất query string là mất `?next=`, `?orderCode=` — hỏng luồng quay lại."""
    assert i18n.them_tien_to("/login?next=/nap", "en") == "/en/login?next=/nap"
    assert i18n.them_tien_to("/nap/don/x?orderCode=1", "en") == "/en/nap/don/x?orderCode=1"


def test_them_tien_to_khong_dung_url_tuyet_doi():
    for u in ("https://pay.payos.vn/abc", "http://x.test/y"):
        assert i18n.them_tien_to(u, "en") == u


# ── 3. Thứ tự ưu tiên ────────────────────────────────────────────────────────
def test_tien_to_thang_tat_ca():
    """URL là sự thật cuối cùng — link chia sẻ phải mở đúng ngôn ngữ người gửi thấy."""
    assert i18n.chon(tien_to="en", cookie="vi", ho_so="vi",
                     quoc_gia="VN", accept_language="vi") == "en"


def test_lua_chon_cua_nguoi_dung_khong_bi_may_ghi_de():
    """Người Việt (IP VN, trình duyệt tiếng Việt) tự chọn tiếng Anh thì phải GIỮ.

    Đây là lỗi kinh điển: bấm đổi ngôn ngữ, tải lại trang, bị đẩy về như cũ.
    """
    assert i18n.chon(cookie="en", quoc_gia="VN", accept_language="vi-VN") == "en"


def test_ho_so_tai_khoan_thang_quoc_gia():
    """Theo người, không theo máy — đi công tác nước ngoài vẫn giữ ngôn ngữ."""
    assert i18n.chon(ho_so="vi", quoc_gia="US", accept_language="en-US") == "vi"


def test_cookie_thang_ho_so():
    assert i18n.chon(cookie="en", ho_so="vi") == "en"


# ── 4. Suy từ quốc gia ───────────────────────────────────────────────────────
def test_quoc_gia_vn_ra_tieng_viet():
    assert i18n.chon(quoc_gia="VN") == "vi"
    assert i18n.chon(quoc_gia="vn") == "vi"          # khong phan biet hoa thuong


@pytest.mark.parametrize("ma", ["US", "JP", "DE", "SG", "KR", "GB"])
def test_quoc_gia_khac_ra_tieng_anh(ma):
    assert i18n.chon(quoc_gia=ma) == "en"


def test_khong_dinh_vi_duoc_thi_xet_tiep_trinh_duyet():
    """CF trả XX (Tor/VPN/mạng lạ) → chưa kết luận, hỏi Accept-Language."""
    assert i18n.tu_quoc_gia("XX") is None
    assert i18n.tu_quoc_gia("T1") is None            # Tor
    assert i18n.tu_quoc_gia("") is None
    assert i18n.chon(quoc_gia="XX", accept_language="vi-VN,vi;q=0.9") == "vi"


def test_khong_co_tin_hieu_nao_thi_ra_mac_dinh_VI():
    """Chốt lại 25/08 theo yêu cầu chủ sản phẩm: mặc định là **tiếng Việt**.

    ⚠️ ĐÂY LÀ MỘT QUYẾT ĐỊNH ĐÃ ĐẢO. Chốt cũ là `en`, với lý do thật: *"khách
       nước ngoài gặp trang tiếng Việt thì không đọc nổi cả nút đổi ngôn ngữ"*.

    ⭐ Lý do đó không còn đúng vì `_doi_ngon_ngu.html` ghi nhãn bằng **chính ngôn
       ngữ đích** — nút tiếng Anh ghi `English`, không phải "Tiếng Anh". Người
       không đọc được tiếng Việt vẫn nhận ra chữ đó.

    ⛔ Và tầng này CHỈ chạy khi bốn tầng trên đều im. Trình duyệt khai bất kỳ
       ngôn ngữ nào — kể cả tiếng Nhật — vẫn ra `en` ở tầng `Accept-Language`;
       xem `test_accept_language_ngon_ngu_LA_van_ra_en`.
    """
    assert i18n.chon() == "vi"
    assert i18n.MAC_DINH == "vi"


def test_accept_language_ngon_ngu_LA_van_ra_en():
    """🔴 Một tín hiệu CÓ mà bị coi như KHÔNG CÓ — lỗi `test_159` bắt được.

    `ja-JP` không khớp `vi` lẫn `en`, nhưng nó **không phải im lặng**: trình duyệt
    vừa khai rõ người dùng đọc tiếng Nhật. Đẩy ca đó xuống tầng mặc định (nay là
    tiếng Việt) là đưa trang tiếng Việt cho người đọc tiếng Nhật.
    """
    for header in ("ja-JP,ja;q=0.9", "ko-KR", "fr-FR,fr;q=0.8", "zh-CN"):
        assert i18n.tu_accept_language(header) == "en", header
    # Im lang that su thi van la None -> roi xuong mac dinh.
    assert i18n.tu_accept_language("") is None


# ── 5. Accept-Language ───────────────────────────────────────────────────────
def test_accept_language_theo_trong_so_q():
    """Trọng số q phải được tôn trọng, không phải cứ lấy cái đầu tiên."""
    assert i18n.tu_accept_language("en-US;q=0.3,vi;q=0.9") == "vi"
    assert i18n.tu_accept_language("vi;q=0.2,en-US;q=0.8") == "en"


def test_accept_language_bo_qua_ngon_ngu_khong_ho_tro():
    """Trình duyệt tiếng Pháp: bỏ qua fr, xét tiếp tới en."""
    assert i18n.tu_accept_language("fr-FR,fr;q=0.9,en;q=0.5") == "en"
    # ⚠️ Đổi 25/08 cùng lúc với việc đảo mặc định sang tiếng Việt. Trước đây dòng
    #    này chốt `None` — và `None` nghĩa là "rơi xuống mặc định". Khi mặc định
    #    còn là `en` thì kết quả cuối vẫn đúng, nên không ai thấy vấn đề. Đổi mặc
    #    định sang `vi` là ca này lập tức sai: người đọc tiếng Nhật nhận trang
    #    tiếng Việt. Xem `test_accept_language_ngon_ngu_LA_van_ra_en`.
    assert i18n.tu_accept_language("ja-JP,ja") == "en"


def test_accept_language_rac_khong_lam_sap():
    for h in ("", "   ", ",,,", "vi;q=abc", "***"):
        assert i18n.tu_accept_language(h) in (None, "vi", "en")


# ── 6. Bộ dịch ───────────────────────────────────────────────────────────────
def test_ngon_ngu_goc_tra_thang_khong_qua_catalog():
    i18n.dat_ngon_ngu("vi")
    assert i18n._("Nạp credit") == "Nạp credit"


def test_thieu_ban_dich_thi_hien_tieng_viet_chu_khong_sap():
    """Thiếu .mo phải làm trang hiện tiếng Việt, KHÔNG được làm sập trang."""
    i18n.xoa_cache()
    i18n.dat_ngon_ngu("en")
    try:
        assert i18n._("Một câu chưa từng được dịch bao giờ") == \
            "Một câu chưa từng được dịch bao giờ"
    finally:
        i18n.xoa_cache()
        i18n.dat_ngon_ngu("vi")


def test_chuan_hoa_bo_ngon_ngu_la():
    assert i18n.chuan_hoa("VI") == "vi"
    assert i18n.chuan_hoa("en") == "en"
    for xau in ("fr", "zz", "", None, "vi-VN"):
        assert i18n.chuan_hoa(xau) is None


# ── 7. Ngoài ngữ cảnh request ────────────────────────────────────────────────
def test_ngoai_request_thi_tra_ngon_ngu_GOC_khong_phai_MAC_DINH():
    """Hai thứ khác nhau, dễ lẫn:

    - `MAC_DINH` (en) là kết luận cho MỘT REQUEST không có tín hiệu nào.
    - Mặc định của ContextVar là ngôn ngữ khi **không ai đặt gì cả**: worker chạy
      job nền, script, test. Ở đó không có "người dùng" nào để mà đoán.

    Để `MAC_DINH` ở đây thì thông báo lỗi của job nền luôn ra tiếng Anh rồi được
    lưu vào CSDL — kể cả với khách Việt, và kể cả trong log. Đã xảy ra thật: 12
    test đổ vì service gọi trực tiếp trả ra tiếng Anh.
    """
    import contextvars
    from platform_core import i18n as m

    def _doc():
        return m.ngon_ngu_hien_tai()

    # Chạy trong context RỖNG — mô phỏng worker/script, không qua middleware.
    ra = contextvars.Context().run(_doc)
    assert ra == m.GOC, (
        f"ngoai request phai tra ngon ngu goc {m.GOC!r}, dang tra {ra!r}")


def test_thong_bao_loi_ngoai_request_giu_tieng_viet():
    import contextvars
    from platform_core import i18n as m

    def _dich():
        return m._("Không đủ credit.")

    assert contextvars.Context().run(_dich) == "Không đủ credit."
