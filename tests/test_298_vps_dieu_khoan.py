"""H39/G10 — điều khoản LTT VPS phải khớp thứ phần mềm THỰC SỰ thi hành.

## Vì sao bộ test này tồn tại

Điều khoản là một **lời hứa có hậu quả pháp lý**. Một con số trong đó lệch khỏi
mã nguồn không hỏng như một cái bug — nó hỏng như một cam kết không giữ được, và
nó chỉ lộ ra khi có tranh chấp, tức lúc tệ nhất.

Trang này đã xảy ra một lần ở quy mô nhỏ hơn: trang bán hứa *"sao lưu hằng tuần"*
trong khi **không có mã nào làm việc đó**, và chính `cost.py` trong cùng kho lại
viết rằng ta *không có* backup. Hai file nói ngược nhau, và file nói sai là file
khách đọc.

## 🔴 BỘ TEST NÀY ĐỔI BẢN CHẤT NGÀY 26/08 — đọc kỹ trước khi sửa

Trước đó điều khoản là **hai tệp HTML tĩnh** ở `docs/lttstudios-website/`, mọi
con số gõ tay, và bộ test này đối chiếu **từng con số** với hằng số thật. Nó làm
đúng việc nó khai, nhưng nó chỉ nói cho ta biết **sau khi ta đã quên**.

Nay nội dung sinh từ `apps/vps/dieu_khoan.py`, nơi mỗi con số đến thẳng từ hằng
số mà phần mềm dùng. Nên các phép kiểm số ở dưới **không còn bắt "số đã trôi"**
— chuyện đó không xảy ra được nữa.

⭐ Chúng vẫn có việc, và việc đó không nhỏ: chúng chốt rằng **trang THẬT SỰ HIỆN
   RA con số đó**. Một mục bị xoá nhầm, một vòng lặp template hỏng, một khối
   không render — tất cả đều làm điều khoản im lặng bỏ mất một cam kết, và
   không phép kiểm nào khác thấy.

## Vì sao điều khoản chuyển từ site marketing vào app

`platform_core/public_api/governance.py` có một luật đáng giữ:

> *a second copy of a legal promise is a second promise, and the two will differ*

Luật đó **không** nói văn bản pháp lý phải nằm ở site marketing. Nó nói không
được có **hai** bản. Vẫn đúng một bản — chỉ đổi chỗ ở, và chỗ ở mới tốt hơn theo
một cách đo được: bản WordPress **chưa bao giờ được xuất bản**
(`https://lttstudios.com/vps-terms/` trả 404 suốt từ 25/08) trong khi clickwrap
đã trỏ vào đó. Khách "đồng ý" với một trang không tồn tại, đúng lúc sắp trả tiền.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

#: Giá và số credit hiện **cùng một quy ước ở cả hai ngôn ngữ** (`149.000đ`,
#: `1.490`) — đó là quyết định đã có của nền tảng, ghi ở
#: `server/templating.py:_tien_vnd`: định dạng tiền là **quy ước hiển thị**,
#: không phải chuỗi cần dịch, vì một người đọc bản tiếng Anh vẫn trả bằng đồng.
#:
#: ⚠️ Bản WordPress cũ dùng `149,000₫`. Nó đã đi lệch khỏi phần còn lại của sản
#:    phẩm, và không ai thấy vì nó là bản sao thứ hai.
def _dinh_dang(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _render(duong: str, *, authenticated: bool = True) -> str:
    """HTML thật của một trang, render qua ứng dụng.

    Đọc trang **đã render** chứ không đọc template: một `{% block %}` đặt sai
    chỗ, một biến thiếu, hay một điều kiện chặn cả khối đều làm template *chứa*
    câu chữ mà trang *không* hiện nó. Bộ test này từng bị đúng thứ đó lừa.
    """
    import os
    import tempfile

    from fastapi.testclient import TestClient

    tmp = Path(tempfile.mkdtemp())
    cu = {k: os.environ.get(k) for k in
          ("LTT_DATABASE_URL", "LTT_ENV", "LTT_SESSION_SECRET", "LTT_VPS",
           "TURNSTILE_SECRET_KEY", "LTT_VPS_ROLLOUT")}
    os.environ.update(LTT_DATABASE_URL=f"sqlite:///{(tmp / 'dk.db').as_posix()}",
                      LTT_ENV="development", LTT_SESSION_SECRET="test-dk",
                      LTT_VPS="1", LTT_VPS_ROLLOUT="public")
    os.environ.pop("TURNSTILE_SECRET_KEY", None)
    try:
        import platform_core.db as dbmod
        dbmod.reset_engine()
        import apps.vps.tables       # noqa: F401
        import platform_core.models  # noqa: F401
        dbmod.Base.metadata.create_all(dbmod.get_engine())
        from tests.test_252_vps_giao_dien import _tao_khach, _dang_nhap
        if authenticated:
            _tao_khach(dbmod)
        from server.app import create_app
        with TestClient(create_app(), base_url="https://testserver",
                        follow_redirects=False) as c:
            if authenticated:
                _dang_nhap(c)
            r = c.get(duong)
        if not authenticated:
            assert r.status_code == 303
            assert "/login" in r.headers["location"]
            return r.text
        assert r.status_code == 200, f"{duong} tra {r.status_code}"
        return r.text
    finally:
        for k, v in cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import platform_core.db as dbmod
        dbmod.reset_engine()


@pytest.fixture(scope="module")
def vi() -> str:
    return _render("/vps/dieu-khoan")


@pytest.fixture(scope="module")
def en() -> str:
    return _render("/en/vps/dieu-khoan")


# ── 1. Cả hai bản đều tồn tại và cùng cấu trúc ──────────────────────────────

def test_co_ca_hai_ngon_ngu(vi, en):
    """Cả hai bản phải render 200 — `_render` đã khẳng định điều đó, nên phép
    kiểm này chốt thêm rằng chúng có nội dung thật chứ không phải một vỏ rỗng."""
    assert "<h2>" in vi and "<h2>" in en


def test_hai_ban_cung_so_muc(vi, en):
    """Lệch số mục nghĩa là một bản có điều khoản mà bản kia không có — và khách
    đọc bản nào thì tin bản đó."""
    assert len(re.findall(r"<h2>", vi)) == len(re.findall(r"<h2>", en))


def test_doc_duoc_TRUOC_khi_mua_sau_dang_nhap(vi):
    """D01: authenticated MVP; khách chưa mua vẫn đọc được clickwrap."""
    assert "Điều khoản LTT VPS" in vi
    assert 'name="password"' not in vi


def test_dieu_khoan_an_danh_chuyen_ve_dang_nhap():
    _render("/vps/dieu-khoan", authenticated=False)


def test_KHONG_dung_vo_dieu_khien(vi, en):
    """Menu trái là công cụ của người đã mua. Điều khoản là một văn bản để đọc,
    và một thanh bên cạnh nó chỉ làm người ta đọc kém hơn."""
    for ban in (vi, en):
        assert "app-shell" not in ban and "app-side" not in ban


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
        gia = _dinh_dang(p.gia_thang_vnd) + "đ"
        for ban, ten in ((vi, "VI"), (en, "EN")):
            assert gia in ban, f"{p.id}: thieu gia {gia} trong ban {ten}"

        tin = _dinh_dang(credit_thang(p.id))
        for ban, ten in ((vi, "VI"), (en, "EN")):
            assert tin in ban, f"{p.id}: thieu so credit {tin} ({ten})"

        for ban, don in ((vi, "vCPU"), (en, "vCPU")):
            assert f"{p.vcpu} {don}" in ban, f"{p.id}: thieu {p.vcpu} vCPU"
        for ban in (vi, en):
            assert f"{p.ram_mb // 1024} GB RAM" in ban, f"{p.id}: thieu RAM"


def test_han_muc_bang_thong_moi_goi_khop_ma(vi, en):
    from apps.vps.cost import PLANS

    for p in PLANS:
        so = _dinh_dang(p.bang_thong_gb)
        for ban, ten in ((vi, "VI"), (en, "EN")):
            assert f"{so} GB" in ban, f"{p.id}: thieu bang thong {so} GB ({ten})"


def test_gia_dia_them_khop_ma(vi, en):
    from apps.vps.cost import DIA_THEM_MOI_LO_GB, GIA_MOI_LO_DIA_VND

    for ban in (vi, en):
        assert f"<strong>{DIA_THEM_MOI_LO_GB} GB</strong>" in ban
        assert _dinh_dang(GIA_MOI_LO_DIA_VND) + "đ" in ban


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
    assert "/dieu-khoan" in t, "trang ban khong dan toi dieu khoan VPS"
    # Trang dan toi dieu khoan o HAI cho, va ca hai deu dung:
    #   - khoi cho khach an danh (doc truoc khi quyet dinh tao tai khoan)
    #   - ngay duoi nut "Tao may" (clickwrap: bam la dong y)
    # Nen kiem cai SAU nut, khong kiem cai dau tien tim thay.
    i_nut = t.index('_("Tạo máy")')
    assert "/dieu-khoan" in t[i_nut:], (
        "thieu lien ket dieu khoan NGAY DUOI nut tao may")
    assert "đồng ý với" in t[i_nut:]


def test_lien_ket_dieu_khoan_khai_o_MOT_cho():
    """Viết cứng URL trong template thì lần đổi đường dẫn sau sẽ bỏ sót đúng chỗ
    này.

    ## Ý định của phép kiểm này chưa bao giờ là "đường dẫn phải là chuỗi X"

    Nó đã đổi mốc **hai lần**: `/vi/legal/vps-terms.html` → `/vps-terms/` →
    `/vps/dieu-khoan`. Hai lần đầu nó đỏ vì một thay đổi **có chủ ý**, và mỗi
    lần người sửa lại ghim một chuỗi mới — tức lần sau nó lại đỏ như thế.

    ⭐ Nên chốt đúng **tính chất**: đường dẫn dựng từ **một** nguồn
       (`route_prefix` của manifest), và template không viết cứng tên miền nào.
    """
    t = Path("server/templates/vps.html").read_text(encoding="utf-8")
    assert "{{ app.route_prefix }}/dieu-khoan" in t, (
        "lien ket dieu khoan phai dung tu `route_prefix`, khong viet cung `/vps`")
    assert "lttstudios.com" not in t, (
        "template viet cung mot URL lttstudios.com — dieu khoan nay da chuyen "
        "vao app, khong con o site marketing")

    from server.templating import PUBLIC_LINKS
    assert "vps_terms" not in PUBLIC_LINKS, (
        "`vps_terms` tro toi site marketing; trang do da bi go 26/08 va mot "
        "muc con lai la mot lien ket chet cho ai do dung lai sau")

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
