"""H39/G10 — điều khoản LTT VPS phải khớp thứ phần mềm THỰC SỰ thi hành.

## Vì sao bộ test này tồn tại

Điều khoản là một **lời hứa có hậu quả pháp lý**. Một con số trong đó lệch khỏi
mã nguồn không hỏng như một cái bug — nó hỏng như một cam kết không giữ được, và
nó chỉ lộ ra khi có tranh chấp, tức lúc tệ nhất.

Trang này đã xảy ra một lần ở quy mô nhỏ hơn: trang bán hứa *"sao lưu hằng tuần"*
trong khi **không có mã nào làm việc đó**, và chính `cost.py` trong cùng kho lại
viết rằng ta *không có* backup. Hai file nói ngược nhau, và file nói sai là file
khách đọc.

Nên mọi con số vận hành trong điều khoản đều bị chốt ở đây, đối chiếu với hằng số
thật. Đổi giá, đổi hạn mức, đổi thời hạn ân hạn mà quên sửa điều khoản → gate đỏ.

## Vì sao điều khoản nằm ở `docs/lttstudios-website/` chứ không trong app

Quy tắc có sẵn của nền tảng (`public_api/governance.py`): *"a second copy of a
legal promise is a second promise, and the two will differ"*. Văn bản pháp lý
sống ở trang web, app chỉ **liên kết** tới. Bộ test này đọc thẳng tệp HTML đó —
làm được vì trang web nằm trong chính kho này.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

VI = Path("docs/lttstudios-website/vi/legal/vps-terms.html")
EN = Path("docs/lttstudios-website/legal/vps-terms.html")


def _doc(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def vi() -> str:
    return _doc(VI)


@pytest.fixture(scope="module")
def en() -> str:
    return _doc(EN)


# ── 1. Cả hai bản đều tồn tại và cùng cấu trúc ──────────────────────────────

def test_co_ca_hai_ngon_ngu():
    """Trang VI trỏ sang EN bằng nút đổi ngôn ngữ. Thiếu bản EN là một liên kết
    chết ngay trên trang pháp lý."""
    assert VI.exists() and EN.exists()


def test_hai_ban_cung_so_muc(vi, en):
    """Lệch số mục nghĩa là một bản có điều khoản mà bản kia không có — và khách
    đọc bản nào thì tin bản đó."""
    assert len(re.findall(r"<h2>", vi)) == len(re.findall(r"<h2>", en))


def test_hai_ban_tro_sang_nhau(vi, en):
    assert "/legal/vps-terms.html" in vi
    assert "/vi/legal/vps-terms.html" in en


# ── 2. Chu kỳ, ân hạn, xoá ──────────────────────────────────────────────────

def test_chu_ky_khop_ma(vi, en):
    from apps.vps.cost import CHU_KY_NGAY

    assert f"<strong>{CHU_KY_NGAY} ngày</strong>" in vi
    assert f"<strong>{CHU_KY_NGAY} days</strong>" in en


def test_an_han_truoc_khi_xoa_khop_ma(vi, en):
    """Con số quan trọng nhất trang: quá hạn này là **xoá vĩnh viễn**. Hứa 7 mà
    mã xoá sau 3 là xoá dữ liệu của khách sớm bốn ngày so với thoả thuận."""
    from apps.vps.services.billing import AN_HAN_TRUOC_KHI_XOA_NGAY as N

    assert f"<strong>{N} ngày</strong>" in vi
    assert f"<strong>{N} days</strong>" in en


def test_noi_ro_XOA_LA_KHONG_KHOI_PHUC_DUOC(vi, en):
    """Không nói rõ thì khách cho rằng "chắc vẫn cứu được" — và họ chỉ biết là
    không khi đã muộn."""
    assert "không khôi phục được" in vi.lower()
    assert "cannot restore" in en.lower()


# ── 3. Giá và cấu hình từng gói ─────────────────────────────────────────────

def test_gia_va_cau_hinh_moi_goi_khop_ma(vi, en):
    from apps.vps.cost import PLANS, credit_thang

    for p in PLANS:
        gia_vi = f"{p.gia_thang_vnd:,}".replace(",", ".") + "đ"
        gia_en = f"{p.gia_thang_vnd:,}₫"
        assert gia_vi in vi, f"{p.id}: thieu gia {gia_vi} trong ban VI"
        assert gia_en in en, f"{p.id}: thieu gia {gia_en} trong ban EN"

        tin = credit_thang(p.id)
        assert f"{tin:,}".replace(",", ".") in vi, f"{p.id}: thieu so credit"
        assert f"{tin:,}" in en, f"{p.id}: thieu so credit (EN)"

        for ban, don in ((vi, "vCPU"), (en, "vCPU")):
            assert f"{p.vcpu} {don}" in ban, f"{p.id}: thieu {p.vcpu} vCPU"
        for ban in (vi, en):
            assert f"{p.ram_mb // 1024} GB RAM" in ban, f"{p.id}: thieu RAM"


def test_han_muc_bang_thong_moi_goi_khop_ma(vi, en):
    from apps.vps.cost import PLANS

    for p in PLANS:
        so = f"{p.bang_thong_gb:,}".replace(",", ".")
        assert f"{so} GB" in vi, f"{p.id}: thieu bang thong {so} GB (VI)"
        assert f"{p.bang_thong_gb:,} GB" in en, f"{p.id}: thieu bang thong (EN)"


def test_gia_dia_them_khop_ma(vi, en):
    from apps.vps.cost import DIA_THEM_MOI_LO_GB, GIA_MOI_LO_DIA_VND

    assert f"<strong>{DIA_THEM_MOI_LO_GB} GB</strong>" in vi
    assert f"{GIA_MOI_LO_DIA_VND:,}".replace(",", ".") + "đ" in vi
    assert f"<strong>{DIA_THEM_MOI_LO_GB} GB</strong>" in en


def test_ty_gia_credit_khop_ma(vi, en):
    from platform_core.billing_math import VND_PER_CREDIT

    assert f"1 credit = {VND_PER_CREDIT} đồng" in vi
    assert f"1 credit = {VND_PER_CREDIT} VND" in en


# ── 4. Hạn mức kỹ thuật ─────────────────────────────────────────────────────

def test_toc_do_khi_bi_ham_khop_KICH_BAN_ROUTER(vi, en):
    """Con số này nằm trong `cai-dat-router.sh`, không phải trong Python — nên nó
    là chỗ dễ trôi nhất: sửa router mà không ai nghĩ tới trang điều khoản."""
    kb = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    byte = int(re.search(r'TOC_GIAM="(\d+)"', kb).group(1))
    mb = byte // 1024 ** 2
    assert f"<strong>{mb} MB/giây</strong>" in vi
    assert f"<strong>{mb} MB/second</strong>" in en


def test_cong_thu_bi_chan_khop_KICH_BAN_ROUTER(vi, en):
    kb = Path("tools/vps_gateway/cai-dat-router.sh").read_text(encoding="utf-8")
    cong = [c.strip() for c in
            re.search(r"tcp dport \{ ([^}]+) \}", kb).group(1).split(",")]
    assert len(cong) == 3, cong
    for ban in (vi, en):
        for c in cong:
            assert c in ban, f"dieu khoan khong noi cong {c} bi chan"


def test_ham_toc_chu_khong_TINH_THEM_TIEN(vi, en):
    """Mã hãm tốc chứ không tính tiền vượt. Điều khoản phải nói đúng thế, vì
    "vượt hạn mức" ở nhà cung cấp khác thường có nghĩa là **hoá đơn**."""
    assert "không tính thêm tiền" in vi.lower()
    assert "not charge overage" in en.lower()


# ── 5. Ảnh chụp ─────────────────────────────────────────────────────────────

def test_nhip_va_so_ban_anh_chup_khop_ma(vi, en):
    from apps.vps.services.sao_luu import GIU, MOI_NGAY

    assert f"<strong>mỗi {MOI_NGAY} ngày</strong>" in vi
    assert f"<strong>{GIU} bản</strong>" in vi
    assert f"<strong>every {MOI_NGAY} days</strong>" in en
    assert f"keep <strong>{GIU}</strong>" in en


def test_noi_ro_anh_chup_KHONG_phai_sao_luu(vi, en):
    """Đúng cái sai mà trang bán từng mắc. Ảnh chụp nằm cùng kho với đĩa gốc:
    kho hỏng là mất cả hai."""
    assert "không thay thế bản sao lưu" in vi.lower()
    assert "does not replace your own backup" in en.lower()
    assert "cùng kho lưu trữ" in vi.lower()


def test_noi_ro_anh_chup_chi_giu_thu_DA_XUONG_DIA(vi, en):
    """Đo thật 24/08: tệp ghi ba giây trước khi chụp **không có** trong ảnh.
    Mô tả tính năng này là "khôi phục về đúng phút đó" là mô tả sai."""
    assert "đã ghi xuống đĩa" in vi.lower()
    assert "reached the disk" in en.lower()


# ── 6. Giấy phép Windows — rủi ro lớn nhất, phải nói thẳng ──────────────────

def test_noi_ro_GIA_KHONG_bao_gom_giay_phep_Windows(vi, en):
    """Đĩa cài đang dùng là bản **Evaluation** của Microsoft (180 ngày). Không nói
    ra thì khách mặc định cho rằng giá đã gồm giấy phép — và đó là kỳ vọng dẫn
    thẳng tới một lần đòi hoàn tiền, hoặc tệ hơn."""
    assert "KHÔNG bao gồm giấy phép Windows" in vi
    assert "does NOT include a Windows licence" in en
    assert "Evaluation" in vi and "Evaluation" in en


def test_noi_ro_khach_TU_DAT_mat_khau_va_nen_tang_KHONG_biet(vi, en):
    assert "không biết mật khẩu của bạn" in vi.lower()
    assert "do not know your password" in en.lower()


# ── 7. Console và dữ liệu ───────────────────────────────────────────────────

def test_han_ve_console_khop_ma(vi, en):
    from apps.vps.services.console import HAN_VE_GIAY

    assert f"{HAN_VE_GIAY} giây" in vi
    assert f"{HAN_VE_GIAY} seconds" in en


def test_noi_ro_KHONG_cam_ket_uptime(vi, en):
    """Trang bán đã nói "best effort". Điều khoản phải nói cùng một điều, nếu
    không thì bản nào là lời hứa thật?"""
    assert "không cam kết thời gian hoạt động" in vi.lower()
    assert "no uptime commitment" in en.lower()


# ── 8. Không hứa thứ chưa có ────────────────────────────────────────────────

def test_KHONG_hua_hoa_don_dien_tu(vi, en):
    """Hoá đơn điện tử theo Nghị định 123/2020 phải phát hành qua nhà cung cấp
    được cấp phép và đăng ký với cơ quan thuế. Ta **chưa có** thứ đó, nên điều
    khoản chỉ được nói tới **sao kê**, không được dùng chữ "hoá đơn"."""
    assert "hoá đơn" not in vi.lower() and "hóa đơn" not in vi.lower()
    assert "invoice" not in en.lower()
    assert "sao kê" in vi.lower()
    assert "statement" in en.lower()


def test_KHONG_hua_SLA(vi, en):
    for ban in (vi, en):
        assert "99," not in ban and "99.9" not in ban, "khong duoc hua con so uptime"


# ── 9. Khách phải THẤY điều khoản trước khi bấm thuê ────────────────────────

def test_trang_ban_DAN_lien_ket_dieu_khoan():
    """Một liên kết điều khoản ở chân trang là một liên kết không ai bấm. Nó phải
    nằm **ngay dưới nút thuê**, và nói rõ bấm là đồng ý."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "public_links.vps_terms" in t, "trang ban khong dan toi dieu khoan VPS"
    # Trang dan toi dieu khoan o HAI cho, va ca hai deu dung:
    #   - khoi cho khach an danh (doc truoc khi quyet dinh tao tai khoan)
    #   - ngay duoi nut "Tao may" (clickwrap: bam la dong y)
    # Nen kiem cai SAU nut, khong kiem cai dau tien tim thay.
    i_nut = t.index('_("Tạo máy")')
    assert "public_links.vps_terms" in t[i_nut:], (
        "thieu lien ket dieu khoan NGAY DUOI nut tao may")
    assert "đồng ý với" in t[i_nut:]


def test_lien_ket_dieu_khoan_khai_o_MOT_cho():
    """Viết cứng URL trong template thì lần đổi tên miền sau sẽ bỏ sót đúng chỗ
    này. Nền tảng đã có `PUBLIC_LINKS` cho việc đó."""
    from server.templating import PUBLIC_LINKS

    assert "vps_terms" in PUBLIC_LINKS

    # ⛔ SUA 26/08 — truoc day cho nay ghim
    #    `.endswith("/vi/legal/vps-terms.html")`. Trang web da chuyen sang
    #    "pretty URL" (`/vps-terms/`) va CA BANG `PUBLIC_LINKS` doi theo, nen
    #    phep kiem do do vi mot thay doi CO CHU Y.
    #
    # ⭐ Y dinh cua phep kiem nay khong bao gio la "duong dan phai la chuoi X".
    #    No la: **URL khai o MOT cho**, va template khong duoc viet cung. Nen
    #    chot dung hai dieu do — mot phep kiem ghim chuoi se do lai o lan doi
    #    ten mien sau, va lan do nguoi ta se sua no bang cach ghim chuoi moi.
    assert PUBLIC_LINKS["vps_terms"].startswith("https://")
    assert "vps-terms" in PUBLIC_LINKS["vps_terms"]

    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "lttstudios.com" not in t, (
        "template viet cung mot URL lttstudios.com — dung `public_links` de lan "
        "doi ten mien sau khong bo sot dung cho nay")


def test_trang_ban_CANH_BAO_giay_phep_Windows_ngay_o_khoi_doc_truoc():
    """Người đọc điều khoản là thiểu số. Rủi ro lớn nhất của dịch vụ này phải
    nằm ở chỗ **mọi** khách nhìn thấy."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    i_khoi = t.index('_("Đọc trước khi thuê")')
    i_gp = t.index("KHÔNG bao gồm giấy phép Windows")
    i_het = t.index('_("Máy của tôi")')
    assert i_khoi < i_gp < i_het, "canh bao giay phep phai nam trong khoi doc-truoc"


# ── 10. Trang tạo máy: hai bước, một trang, tóm tắt sống (G8) ───────────────

def test_hien_SO_TRU_va_SO_DU_CON_LAI_truoc_khi_bam():
    """Nền tảng bán theo credit. Bản trước hiện giá bằng **đồng** ở một chỗ, số
    credit ở chỗ khác, và số dư thì chỉ có trên thanh tiêu đề — ba mảnh của cùng
    một phép tính, và khách phải tự cộng để biết bấm xong còn bao nhiêu."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert 'id="tt-gia"' in t, "khong hien so credit se tru"
    assert 'id="tt-conlai"' in t, "khong hien so du con lai sau khi mua"
    assert "so_du_credit(request)" in t


def test_MOT_bieu_mau_chu_khong_phai_ba():
    """Ba thẻ gói, mỗi thẻ một nút "Thuê máy này", nghĩa là ba biểu mẫu cho một
    quyết định — và không chỗ nào so được ba gói cạnh nhau."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert t.count('action="{{ app.route_prefix }}/tao"') == 1


def test_KHONG_co_bieu_mau_khi_khong_doc_duoc_suc_chua():
    """Fail-closed, và nó là một tính chất **cấu trúc**: không có `<form>` thì
    không có đường POST, kể cả khi ai đó dựng request bằng tay.

    Bản G8 đầu của tôi hiện biểu mẫu luôn và phá đúng chốt này
    (`test_252::test_khong_doc_duoc_suc_chua_thi_KHONG_cho_tao_may`). Hai thứ bị
    gộp nhầm: *hiện bảng giá* và *cho đặt mua*."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    i_dk = t.index("{% set ban_duoc")
    dong_dk = t[i_dk:t.index("%}", i_dk)]
    # Kiem TINH CHAT, khong kiem nguyen van: dieu kien con phai gom them
    # `da_dang_nhap` (khach an danh khong duoc thay bieu mau), va mot phep kiem
    # so nguyen van se do moi lan them mot ve dung.
    assert "suc_chua" in dong_dk, "dieu kien ban duoc phai gom suc_chua"
    assert "da_dang_nhap" in dong_dk, "khach an danh khong duoc thay bieu mau"
    i_form = t.index('<form method="post"')
    assert i_dk < i_form, "dieu kien phai bao ngoai bieu mau"


def test_HET_CHO_thi_van_hien_BANG_GIA():
    """Khách vào đúng lúc node đầy mà không thấy ta bán gì thì không có lý do
    quay lại. Hết chỗ là trạng thái tạm; một trang bán trống thì không."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "Bảng giá dưới đây vẫn đúng" in t


def test_KHONG_khoa_nut_khi_thieu_credit():
    """Khoá nút thì khách thiếu một credit thấy một nút chết mà không biết vì
    sao. Máy chủ vẫn từ chối và trả về một câu rõ ràng kèm đường đi nạp."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert 'id="tt-nut"' in t
    assert "disabled" not in t[t.index('id="tt-nut"'):t.index('id="tt-nut"') + 200]
    assert 'id="tt-thieu"' in t and "/nap" in t


def test_JS_hong_thi_trang_van_dung_duoc():
    """Danh sách hệ điều hành hiện ĐỦ trong HTML; JS chỉ ẩn bớt. Không có JS thì
    khách vẫn thấy hết, và máy chủ vẫn từ chối tổ hợp sai (`os_images.hop_le`) —
    trang không bao giờ im lặng bán một thứ không cài được."""
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "{% for o in os_ban_duoc %}" in t, "OS phai duoc dung san trong HTML"
    assert "hop_le" in Path("apps/vps/routes.py").read_text(encoding="utf-8")
