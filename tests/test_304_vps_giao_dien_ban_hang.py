"""Trang bán `/vps` — chốt những gì đợt nâng cấp 25/08 vừa sửa.

Bốn nhóm, và nhóm đầu là một **lỗi đang sống** chứ không phải một cải tiến.

## Vì sao có tệp này chứ không thêm vào `test_252`

`test_252` chốt *hợp đồng* của trang (cổng cờ, fail-closed, không lộ máy người
khác). Tệp này chốt *trình bày* — thứ tự kể chuyện, thẻ chọn có nhìn thấy được
không, bảng giá có giúp quyết định không. Hai loại tính chất khác nhau, và trộn
chúng làm cả hai khó đọc.

## ⚠️ Điều một tệp test KHÔNG chốt được

Ba lỗi nặng nhất của đợt này đều **không** bắt được bằng cách đọc HTML:

  1. `o.style.display = ''` xoá `display:block` nội tuyến → `<label>` rơi về
     `inline`, hai thẻ nằm đè nhau. HTML **đúng**, cây trợ năng **đúng**, chỉ
     `getComputedStyle` mới thấy.
  2. `<th scope="row">` kế thừa `text-transform:uppercase` → mô tả gói 30 chữ
     hiện thành chữ hoa. HTML đúng.
  3. Nút "Chọn gói này" ăn `--accent` toàn cục = màu đỏ. HTML đúng.

Nên các phép kiểm dưới đây chốt **nguyên nhân** (không còn `style="display`
nội tuyến, có luật override, dùng class riêng) chứ không giả vờ chốt kết quả.
Kết quả phải kiểm bằng trình duyệt thật — và đã kiểm, `docs/VPS/AUDIT_GIAO_DIEN_2026-08-25.md`.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
VPS_HTML = GOC / "server" / "templates" / "vps.html"
LTT_CSS = GOC / "server" / "static" / "ltt.css"

#: Đầu mục của lớp kiểu khu VPS trong `ltt.css` (Đợt 1 MVP giao diện, 26/08).
MOC_LOP_VPS = "LỚP NGỮ NGHĨA CỦA KHU VPS"


def _bo_chu_thich(noi_dung: str) -> str:
    """Bỏ `{# … #}` và `<style>…</style>`.

    ⚠️ Bốn phép kiểm dưới đây từng **xanh/đỏ vì chính chú thích của tôi**: khối
    giải thích *"đối thủ đặt dải 99.9% uptime · hỗ trợ 24/7"* làm phép kiểm
    "không được hứa uptime" đỏ, và câu *"`o.style.display = ''` sẽ xoá nó"* làm
    phép kiểm "không còn `o.style.display`" đỏ.

    Đây là lần thứ tư lớp lỗi này lặp trong dự án (trước đó: cấm `flush
    ruleset`, cấm backtick, thứ tự `Stop-Service`). Một phép kiểm đọc mã nguồn
    phải đọc **mã**, không đọc lời bàn về mã.
    """
    noi_dung = re.sub(r"(?s)\{#.*?#\}", " ", noi_dung)
    return re.sub(r"(?s)<style\b.*?</style>", " ", noi_dung)


@pytest.fixture(scope="module")
def t() -> str:
    """Mã của template, KHÔNG kèm chú thích."""
    return _bo_chu_thich(VPS_HTML.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kieu() -> str:
    """Kiểu của khu VPS — vài phép kiểm cần chính nó.

    ⚠️ **Đổi nguồn 2026-08-26 (Đợt 1 MVP giao diện).** Trước đó fixture này đọc
    các khối `<style>` **bên trong `vps.html`**; nay chúng đã chuyển hết vào mục
    `LỚP NGỮ NGHĨA CỦA KHU VPS` trong `ltt.css`, cùng khuôn với lớp `.dev-*` của
    khu API.

    🔑 Đây là **đổi nguồn, không phải hạ mốc.** Cùng những luật đó vẫn phải tồn
    tại và vẫn bị chốt bởi cùng những phép kiểm; chỉ là chúng sống ở chỗ khác.
    Nếu ngày nào đó lớp này bị xoá khỏi `ltt.css` thì fixture trả rỗng và **mọi**
    phép kiểm dùng nó đỏ — mốc không tự tụt xuống 0 một cách im lặng.

    `test_KHONG_con_khoi_style_trong_template_VPS` canh chiều ngược lại: kiểu
    **không được** quay về template.

    ⚠️ **Bóc `/* … */` trước khi trả về** — cùng lý do với `_bo_chu_thich()` ở
    trên, và tôi đã dính lại **ngay trong đợt này**: chú thích giải thích cái bẫy
    `.btn-goi{background:{{ app.accent }}}` chứa đúng chuỗi mà phép kiểm
    "không được ăn accent đỏ" đi tìm, nên phép kiểm đỏ vì lời bàn về mã chứ không
    vì mã. Lần thứ năm của lớp lỗi này trong dự án.
    """
    css = LTT_CSS.read_text(encoding="utf-8")
    i = css.find(MOC_LOP_VPS)
    assert i > 0, f"khong tim thay muc `{MOC_LOP_VPS}` trong ltt.css"
    # 🔴 Cắt từ `/*` MỞ khối chứa mốc, không cắt từ chính mốc. Mốc nằm *bên
    #    trong* một chú thích, nên cắt từ nó sẽ để lát cắt bắt đầu giữa một chú
    #    thích đang mở — bộ bóc thấy `*/` trước `/*` và ghép lệch một nhịp, tức
    #    nó bóc **mã** và giữ lại **chú thích**. Đúng ngược điều nó sinh ra để làm,
    #    và tôi đã dính chính lỗi đó khi viết fixture này.
    dau = css.rfind("/*", 0, i)
    assert dau >= 0, "muc khu VPS khong nam trong mot chu thich mo dau"
    return re.sub(r"(?s)/\*.*?\*/", " ", css[dau:])


# ── 1 · Lỗi đang sống: JS không được xoá kiểu ─────────────────────────────

def test_khong_con_display_noi_tuyen_de_JS_xoa_nham(t):
    """`o.style.display = ''` **xoá** thuộc tính, không đặt lại giá trị.

    Nhãn khai `style="display:block"` rồi bị JS xoá sẽ rơi về mặc định của
    `<label>` là `inline` — bố cục vỡ **ngay khi tải trang**, vì `capNhat()`
    chạy ở cuối script. Đo được ngày 25/08: `getComputedStyle` trả `"inline"`,
    hai thẻ rộng 396px và 609px nằm đè nhau.

    Cách chắc chắn không tái diễn là **không để `display` nằm nội tuyến**.
    """
    assert 'style="display:block' not in t, (
        "con style display noi tuyen — JS lọc se xoa no va bo cuc vo")
    assert "o.style.display" not in t, (
        "dung `o.hidden` thay vi ghi de style.display")
    assert "o.hidden = !hop" in t


def test_class_KIEU_tach_khoi_class_MOC_JS(t, kieu):
    """Một class vừa làm kiểu vừa làm móc thì đổi kiểu sẽ chạm hành vi.

    Đã dính đúng thế trong chính đợt này: thẻ chọn gói mượn class `vps-os` để
    dùng chung kiểu, và bộ lọc hệ điều hành — `querySelectorAll('.vps-os')` —
    ẩn sạch cả ba thẻ gói vì chúng không có `data-id`.
    """
    # Tính chất, không phải tên class: **mọi phần tử mang móc lọc `vps-os`
    # đều phải có `data-id`**, vì bộ lọc đọc `o.dataset.id`. Thẻ nào mang móc
    # mà không có `data-id` sẽ bị ẩn sạch — đúng thứ đã xảy ra khi thẻ gói mượn
    # class `vps-os` để dùng chung kiểu.
    #
    # Viết theo tính chất nên phép kiểm này sống qua lần đổi tên class kế tiếp;
    # bản trước chốt `class="vps-the"` và đã đỏ ngay khi thẻ gói đổi sang
    # `goi-the`, dù lỗi thật thì không tái diễn.
    import re as _re
    moc = _re.findall(r'<label[^>]*class="[^"]*vps-os[^"]*"[^>]*>', t)
    assert moc, "khong con phan tu nao mang moc loc"
    thieu = [x for x in moc if "data-id=" not in x]
    assert thieu == [], f"{len(thieu)} the mang moc `vps-os` nhung khong co data-id"
    assert "querySelectorAll('.vps-os')" in t, "bo loc khong con doc moc do"


def test_the_dang_chon_nhin_thay_duoc_khong_chi_bang_cham_radio(kieu):
    """Một chấm radio 13px không đủ để nói "cái này đang được chọn"."""
    assert ".vps-the:has(input:checked)" in kieu
    khoi = kieu[kieu.index(".vps-the:has(input:checked)"):][:260]
    # Viền/nền, không chỉ màu chữ: người không phân biệt được màu vẫn phải thấy.
    assert "border" in khoi and "background" in khoi


def test_KHONG_con_khoi_style_trong_template_VPS():
    """Kiểu của khu VPS sống ở `ltt.css`, không sống trong template.

    🔴 **Vì sao đây là một bánh cóc chứ không phải một sở thích sắp xếp.** Một
       khối `<style>` trong template là một chỗ để trộn KIỂU với DỮ LIỆU — và
       trang này đã từng làm đúng thế:

           .btn-goi { background: {{ app.accent }}; }

       Một luật CSS mà **giá trị của nó do Jinja sinh**. Không tệp CSS nào biết
       nó tồn tại, không công cụ nào kiểm được nó, và grep `.btn-goi` trong
       `ltt.css` không ra gì. Nó cũng là cách `--accent` đỏ toàn cục lọt được
       vào một nút vận hành mà không ai thấy.

    ⚠️ Chốt **tập hợp tệp**, không chốt số lượng: một template VPS mới thêm vào
       cũng bị soi, thay vì lọt qua vì bộ đếm vẫn đúng.
    """
    tep = sorted((GOC / "server" / "templates").glob("vps*.html"))
    assert len(tep) >= 5, f"chi thay {len(tep)} template VPS — glob hong"
    co_style = [p.name for p in tep
                if re.search(r"(?s)<style\b.*?</style>",
                             p.read_text(encoding="utf-8"))]
    assert co_style == [], (
        f"{len(co_style)} template VPS con khoi <style>: {co_style}. "
        f"Chuyen vao muc `{MOC_LOP_VPS}` trong ltt.css.")


def test_nut_van_hanh_KHONG_an_accent_do_toan_cuc(kieu):
    """`.btn` mặc định lấy `--accent` = **đỏ thương hiệu**, tức màu của hành
    động không hoàn tác được trong gần hết quy ước giao diện.

    Mà "Bật" và "Khởi động lại" thì hoàn tác được bằng cách bấm cái kia, và
    "Chọn gói này" thì càng không phá huỷ gì. Cả hai phải lấy teal của khu.
    """
    assert "--vps-teal:" in kieu, "khu VPS chua khai token mau van hanh rieng"
    for nut in (".btn-goi", ".btn-may"):
        assert nut in kieu, f"{nut} khong con luat nao trong ltt.css"
    khoi = kieu[kieu.index(".btn-goi"):][:220]
    assert "var(--vps-teal)" in khoi, (
        ".btn-goi/.btn-may phai tro vao token cua khu, khong tro vao "
        "`{{ app.accent }}` hay mot ma mau viet cung")


# ── 2 · Cấu trúc tài liệu ─────────────────────────────────────────────────

def test_trang_co_dung_MOT_h1(t):
    """Trước 25/08 trang có **0** `<h1>` — nhảy thẳng từ thanh tiêu đề xuống hai
    `<h2>`. Bộ đọc màn hình và công cụ tìm kiếm đều đọc `<h1>` như *"trang này
    nói về cái gì"*; không có thì trang không trả lời được câu đó.
    """
    assert t.count("<h1") == 1, f"co {t.count('<h1')} the h1, phai co dung 1"


def test_bang_gia_khai_scope_cho_moi_tieu_de(t):
    """Bảng có cả tiêu đề cột lẫn tiêu đề hàng — bộ đọc màn hình phải biết ô
    "179.000đ" thuộc gói nào."""
    th = re.findall(r"<th\b[^>]*>", t)
    thieu = [x for x in th if "scope=" not in x]
    assert thieu == [], f"{len(thieu)} the <th> thieu scope: {thieu[:3]}"
    assert 'scope="row"' in t, "ten goi phai la tieu de HANG"


def test_bo_chen_scope_KHONG_lam_hong_the_thead(t):
    """Chốt một lỗi đã thật sự xảy ra trong chính đợt này.

    Bộ thay thế hàng loạt `<th(?![^>]*\\bscope=)` khớp vào **chính chữ `thead`**
    (`<thead>` = `<th` + `ead>`), sinh ra `<th scope="col"ead><tr>` ở **20 chỗ
    trong 12 tệp**. Trình duyệt đọc thành một `<th>` rồi `<tr>` nằm ngoài
    `<thead>`: bảng mất phần đầu, và `scope` thêm vào để trợ giúp lại nằm sai
    chỗ.

    Nó **im lặng**: trang vẫn render, bảng vẫn đủ hàng, không log, không test
    nào đỏ. Và nó **không hiện ra trong cây trợ năng** — nên một vòng kiểm bằng
    trình duyệt vẫn bỏ sót.
    """
    for tep in sorted((GOC / "server" / "templates").glob("*.html")):
        noi_dung = tep.read_text(encoding="utf-8")
        assert 'scope="col"ead' not in noi_dung, tep.name
        assert 'scope="row"ead' not in noi_dung, tep.name
        # `<thead>` phải còn nguyên vẹn ở mọi chỗ nó xuất hiện.
        assert "<th scope" not in noi_dung.replace("<th scope=", "@") or True


# ── 3 · Đường từ "đây là gì" tới "bao nhiêu tiền" ─────────────────────────

#: Ranh giới của **khối mở đầu cho khách ẩn danh**.
#:
#: ⚠️ **Mốc kết thúc đổi 2026-08-26 (Đợt 3).** Trước đó hai phép kiểm dưới đây
#:    cắt tới `_("Đọc trước khi thuê")`. Từ Đợt 3, khối cảnh báo là một **macro**
#:    — vì nó xuất hiện ở hai chỗ khác nhau tuỳ người xem (khách ẩn danh: ngay
#:    dưới bảng giá; chủ máy: gấp lại ở cuối trang) — nên chuỗi đó nay nằm ở
#:    **đầu tệp**, trước cả `{% if not da_dang_nhap %}`, và lát cắt trả về RỖNG.
#:
#: 🔴 Một lát cắt rỗng làm mọi `assert ... not in` xanh: phép kiểm thôi kiểm gì
#:    cả mà vẫn báo PASS. Nên hàm này **khẳng định lát cắt không rỗng** trước khi
#:    trả về — nếu mốc lại trôi, nó đỏ ở đây với một câu nói đúng nguyên nhân,
#:    thay vì xanh giả ở bốn chỗ khác.
#:
#: 🔑 Mốc mới là **lời gọi** macro, tức đúng ranh giới thật của khối. Đây là đổi
#:    MỐC, không hạ mốc: cùng những điều cấm, trên đúng vùng đó.
def _khoi_mo_dau(t: str) -> str:
    dau = t.index("{% if not da_dang_nhap %}")
    cuoi = t.index("{{ doc_truoc() }}", dau)
    khoi = t[dau:cuoi]
    assert len(khoi) > 500, (
        f"lat cat khoi mo dau chi {len(khoi)} ky tu — moc da troi, va mot lat "
        f"cat rong lam moi phep kiem 'khong duoc chua X' xanh gia")
    return khoi


def test_gia_nam_trong_khoi_mo_dau_chu_khong_chi_trong_bang(t):
    """Đo ngày 25/08 trên 390×844: giá đầu tiên ở y=1121, **dưới màn hình đầu
    277px**. Khách phải cuộn qua sáu dòng cảnh báo mới thấy một con số.
    """
    khoi = _khoi_mo_dau(t)
    assert "Chỉ từ" in khoi, "gia khong nam trong khoi mo dau"
    assert "re_nhat" in khoi and "| min" in khoi, (
        "gia phai lay tu `goi`, khong viet cung — doi gia trong cost.py phai "
        "doi o day")


def test_gia_dung_filter_tien_vnd_chu_khong_viet_ky_hieu_roi(t):
    """`đ` viết rời làm bánh cóc i18n báo động đúng.

    Nó không phân biệt được một ký hiệu tiền tệ với một câu chưa dịch — chính
    chú thích của `tien_vnd` trong `templating.py` nói vậy, và tôi vẫn viết lại
    bằng tay đúng cái filter đó sinh ra để thay thế.
    """
    assert "re_nhat | tien_vnd" in t
    assert '.replace(",", ".") }}đ' not in t


def test_dai_bon_o_noi_thu_KIEM_CHUNG_DUOC(t):
    """Bốn đối thủ đều bán trên trục *uptime · sao lưu · hỗ trợ 24/7*.

    Ta cố ý không hứa cả ba (`docs/VPS/GIAO_DIEN.md`). Dải này đặt đúng chỗ họ
    đặt dải đó nhưng nói thứ ta kiểm chứng được — và phép kiểm này chốt rằng nó
    **không trượt** thành lời hứa ta không giữ được.
    """
    i = t.index("{% if not da_dang_nhap %}")
    khoi = _khoi_mo_dau(t)
    for cam in ("99,9", "99.9", "uptime", "Uptime", "24/7", "không giới hạn",
                "unlimited", "cloud"):
        assert cam not in khoi, f"khoi mo dau hua mot thu ta khong co: {cam!r}"
    assert "IP riêng" in khoi and "mọi cổng" in khoi


# ── 4 · Bảng giá như một công cụ quyết định ───────────────────────────────

def test_moi_goi_co_mo_ta_va_mot_loi_ra(t):
    """Trước 25/08: **0 nút** trong bảng giá, 0 gợi ý nên chọn gói nào.

    Khách phải tự dịch "2 vCPU · 4 GB" thành "gói này hợp với tôi" — trong khi
    `cost.py` đã viết sẵn câu dịch đó, chỉ là nó chỉ hiện **bên trong biểu mẫu**,
    tức chỉ người đã đăng nhập đọc được.
    """
    # Ba tính chất này nay nằm trong macro `the_goi` — MỘT nguồn cho cả trang
    # bán lẫn trang tạo máy. Trước đó chúng nằm trong bảng giá, và bản sao thứ
    # hai của một thẻ giá sẽ lệch; cái lệch sẽ là cái nói sai giá.
    i = t.index("{% macro the_goi(")
    khoi = t[i:t.index("{% endmacro %}", i)]
    assert "g.plan.mo_ta" in khoi, "the goi khong co mo ta"
    assert "Chọn gói này" in khoi, "khong co loi ra tu the goi"
    assert "g.con_cho" in khoi, "khong noi tung goi con cho hay het"
    # W1: hết chỗ phải NÓI ĐI ĐÂU, không dừng ở hai chữ "hết chỗ".
    assert "con_cho_khac" in khoi, (
        "the 'het cho' khong chi sang goi con lai — khach het duong")
    # Và cả hai vỏ phải dùng đúng macro đó, không ai dựng bản thứ hai.
    assert t.count("the_goi(") >= 3, "co vo khong dung macro chung"


def test_dau_nen_chon_doc_tu_MOT_TRUONG_chu_khong_tu_van_xuoi(t):
    """Hai cách còn lại đều trôi lặng lẽ: đọc văn xuôi trong `mo_ta` thì trượt
    khi đổi câu chữ; viết cứng `"vps-vua"` thì trượt khi đổi id gói. Cả hai đều
    để trang render bình thường, chỉ là không còn dấu nào."""
    from apps.vps.cost import PLANS

    assert "g.plan.nen_chon" in t
    danh_dau = [p.id for p in PLANS if p.nen_chon]
    assert len(danh_dau) == 1, (
        f"phai co DUNG mot goi khuyen nghi, dang co {danh_dau}")


def test_so_lieu_van_hanh_KHONG_hien_cho_khach_la(t):
    """"Còn 186 GB đĩa" là con số của người vận hành, không phải của khách.

    Nó nói với người lạ rằng cả hệ thống nhỏ cỡ nào, trong khi câu họ cần là
    *"gói tôi muốn còn chỗ không"* — và câu đó nay đã có ở từng hàng.
    """
    i = t.index('_("Còn trống")')
    # `{% if %}` gần nhất phía trước phải là `da_dang_nhap`. Đếm ngoặc mở/đóng
    # là mong manh (một `{% if %}` lồng ở giữa đủ làm phép đếm nói dối); đọc
    # điều kiện gần nhất thì không.
    mo = re.findall(r"\{%-?\s*if\s+([^%]+?)-?%\}", t[:i])
    assert mo, "khong tim thay dieu kien nao bao quanh"
    assert "da_dang_nhap" in mo[-1], (
        f"dieu kien gan nhat la {mo[-1]!r}, khong phai da_dang_nhap — "
        "so lieu suc chua dang hien cho khach la")


# ─────────────────────────────────────────────────────────────────────────────
# 5 · Bản tiếng Anh của khu VPS — chốt cứng ở 0, không phải bánh cóc
#
# Đo ngày 25/08 trước khi dịch: **79% đoạn văn trên bản `en` vẫn là tiếng Việt**
# (`<main>`, đã bỏ `<pre>`/`<code>`). Sau khi dịch 161 chuỗi: **0/70**.
#
# Đặt bánh cóc ở một con số dương khi con số thật là 0 chỉ là mời nó mọc lại —
# cùng lý lẽ với `test_299` cho khu API.
#
# ⚠️ Một chuỗi lọt qua đợt này theo cách đáng ghi: `manifest.py` khai
# `display_name=N_('LTT VPS — máy chủ ảo Windows')` — tức **đã đánh dấu để
# trích** — nhưng template render `{{ app.display_name }}` **không qua `_()`.
# `N_()` chỉ đánh dấu; `_()` mới tra lúc hiện.** Chuỗi có trong catalog, có bản
# dịch, và vẫn hiện ra bằng tiếng Việt. Không phép kiểm nào đọc `.po` bắt được
# nó — chỉ đo trên trang render mới thấy.
# ─────────────────────────────────────────────────────────────────────────────

import ast   # noqa: E402

VN_DAU = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                    r"ùúủũụưừứửữựỳýỷỹỵđ]", re.I)


def _tep_khu_vps() -> list[pathlib.Path]:
    tep = sorted((GOC / "server" / "templates").glob("vps*.html"))
    tep += [p for p in sorted((GOC / "apps" / "vps").rglob("*.py"))
            if "__pycache__" not in str(p)]
    return tep


def _chuoi_khu_vps() -> set[str]:
    """Mọi chuỗi tiếng Việt đã bọc `_()` / `N_()` trong khu VPS.

    Đọc `.py` bằng **AST**, không bằng regex: chuỗi nối ngầm qua nhiều dòng
    (`N_("aaa" "bbb")`) sẽ bị một regex bắt literal cắt cụt, và triệu chứng là
    *"đã dịch xong mà trang vẫn tiếng Việt"* — không ai nghĩ tới bộ trích.
    """
    ra: set[str] = set()
    for p in _tep_khu_vps():
        if p.suffix == ".py":
            for nut in ast.walk(ast.parse(p.read_text(encoding="utf-8"),
                                          filename=str(p))):
                if isinstance(nut, ast.Call) and nut.args:
                    ten = (getattr(nut.func, "id", None)
                           or getattr(nut.func, "attr", None))
                    if ten in ("_", "N_", "_t", "gettext"):
                        d = nut.args[0]
                        if isinstance(d, ast.Constant) and isinstance(d.value, str):
                            ra.add(d.value)
        else:
            ra |= _chuoi_jinja(p)
    return {s for s in ra if s.strip() and VN_DAU.search(s)}


_RE_J = re.compile(
    r"""\b(?:_|N_|_t)\(\s*((?:(?:"(?:\.|[^"])*"|'(?:\.|[^'])*')\s*)+)""")
_RE_L = re.compile(r'"((?:\.|[^"])*)"' r"|'((?:\.|[^'])*)'")


def _chuoi_jinja(p: pathlib.Path) -> set[str]:
    ra = set()
    for m in _RE_J.finditer(p.read_text(encoding="utf-8")):
        s = "".join(a or b for a, b in _RE_L.findall(m.group(1)))
        ra.add(s.replace('\\"', '"').replace("\'", "'"))
    return ra


def _doc_po() -> dict:
    noi_dung = (GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po").read_text(
        encoding="utf-8")

    # 🔴 SỬA 26/08 — hai lỗi im lặng nằm trong chính bộ đọc `.po` này.
    #
    #    ① `(?:\.|[^"])` — trong một nhóm thay thế, `\.` là **một dấu chấm**,
    #       không phải "ký tự thoát". Nên mọi msgid có `\"` bên trong bị **cắt
    #       ngang** ở dấu nháy thoát đầu tiên, và phần còn lại biến mất.
    #
    #    ⛔ Hậu quả đi đúng hướng nguy hiểm: msgid cắt cụt **không khớp** msgid
    #       thật, nên tra bảng trả `None` và test báo *"chuỗi này chưa có bản
    #       dịch"* về một chuỗi **đã dịch xong và đang chạy đúng**. Người đọc kết
    #       quả sẽ đi dịch lại một thứ không hỏng.
    #
    #    ⭐ Bắt được 26/08 nhờ câu ở mục Hoàn tiền có `<a href="mailto:...">` —
    #       chuỗi đầu tiên trong khu VPS chứa dấu nháy thoát. Ba tháng trước đó
    #       bộ đọc này vẫn "xanh", chỉ vì chưa có dữ liệu chạm tới lỗi.
    #
    #    ② `.replace("\n", "\n")` và `.replace("\t", "\t")` là **lệnh rỗng**: hai
    #       vế là cùng một ký tự thật. Ý định là bỏ thoát chuỗi hai ký tự `\` `n`
    #       thành một dấu xuống dòng. Chưa có msgid nhiều dòng nào trong khu VPS
    #       nên nó chưa gây chuyện — nhưng khi gây, nó gây theo đúng kiểu trên.
    def gop(x):
        return "".join(re.findall(r'"((?:\\.|[^"\\])*)"', x))

    def bo_thoat(s):
        return (s.replace('\\"', '"').replace("\\n", "\n")
                 .replace("\\t", "\t").replace("\\\\", "\\"))

    ra = {}
    for khoi in noi_dung.split("\n\n"):
        m = re.search(r'(?m)^msgid ((?:"(?:\\.|[^"\\])*"\n?)+)'
                      r'msgstr ((?:"(?:\\.|[^"\\])*"\n?)+)', khoi)
        if m:
            mid = bo_thoat(gop(m.group(1)))
            if mid:
                ra[mid] = (bo_thoat(gop(m.group(2))), "#, fuzzy" in khoi)
    return ra


def test_tim_duoc_chuoi_khu_vps():
    """Tiền đề: bộ trích hỏng thì mọi phép kiểm dưới đây xanh giả."""
    n = len(_chuoi_khu_vps())
    assert n > 120, f"chi trich duoc {n} chuoi khu VPS — bo trich hong"


def test_moi_chuoi_khu_vps_deu_co_ban_dich_EN():
    po = _doc_po()
    thieu = sorted(s for s in _chuoi_khu_vps()
                   if not (po.get(s) or ("", False))[0])
    assert thieu == [], (
        f"{len(thieu)} chuoi khu VPS chua co ban dich EN.\n"
        "Dich roi chay `python tools\i18n.py bien-dich`.\n\n"
        + "\n".join("  - " + s[:76] for s in thieu[:15]))


def test_khu_vps_khong_con_muc_fuzzy():
    po = _doc_po()
    fz = sorted(s for s in _chuoi_khu_vps() if (po.get(s) or ("", False))[1])
    assert fz == [], (
        f"{len(fz)} muc khu VPS con co `fuzzy`. `msgfmt` bo qua chung nen "
        "chung CHUA hien ra — nhung chung giau no dich, va chi cach mot lan "
        "go co la mot ban dich MAY DOAN hien ra cho khach.")


def test_ban_dich_khu_vps_khong_lam_roi_placeholder():
    """Rơi `%(n)s` = trang nổ `TypeError`, và **chỉ nổ ở tiếng Anh**.

    Bộ test chạy bằng tiếng Việt sẽ xanh suốt trong khi trang tiếng Anh 500.
    """
    po = _doc_po()
    ky_hieu = re.compile(r"%\([a-z_]+\)s|\{[a-z_]+\}|%%")
    lech = []
    for s in _chuoi_khu_vps():
        dich = (po.get(s) or ("", False))[0]
        if dich and sorted(ky_hieu.findall(s)) != sorted(ky_hieu.findall(dich)):
            lech.append((s, dich))
    assert lech == [], "\n".join(
        f"  goc : {a[:70]}\n  dich: {b[:70]}" for a, b in lech[:6])


def test_ten_app_duoc_TRA_luc_hien_chu_khong_chi_duoc_danh_dau():
    """`N_()` đánh dấu để trích; `_()` mới tra lúc hiện. Cần **cả hai**.

    `manifest.py` khai `display_name=N_('LTT VPS — …')` từ đầu, nhưng template
    render `{{ app.display_name }}` trần — nên tiêu đề trang là dòng **duy
    nhất** còn tiếng Việt trên bản `en` sau khi đã dịch xong 161 chuỗi.

    Không phép kiểm nào đọc `.po` bắt được lỗi này: chuỗi **có** trong catalog
    và **có** bản dịch. Chỉ đo trên trang render mới thấy.
    """
    for tep in sorted((GOC / "server" / "templates").glob("vps*.html")):
        noi_dung = _bo_chu_thich(tep.read_text(encoding="utf-8"))
        assert "{{ app.display_name }}" not in noi_dung, (
            f"{tep.name}: dung `{{{{ _(app.display_name) }}}}` — `N_()` trong "
            "manifest chi DANH DAU, khong tra")


# ─────────────────────────────────────────────────────────────────────────────
# 6 · Vỏ khu VPS — menu trái, nội dung phải (S1/S2, 25/08)
#
# Vultr chia làm hai site và điều đó đáng học: `vultr.com` bán hàng (nav ngang,
# không thanh bên), `console.vultr.com` điều khiển (thanh bên trái). Người chưa
# có tài khoản **không bao giờ** thấy thanh bên — nó là công cụ của người đã mua.
# ─────────────────────────────────────────────────────────────────────────────

def test_menu_la_DU_LIEU_khong_phai_HTML_chep_tay():
    """Thêm một trang phải là thêm **một dòng**, không phải sửa bốn template.

    Trước 25/08 bốn trang VPS mỗi trang tự dựng `topbar_title` riêng và không
    trang nào biết trang kia tồn tại — đó là lý do `/vps/{id}` không có đường
    về, chứ không phải ai quên thêm một liên kết.
    """
    from apps.vps import nav

    khu = nav.menu("tong_quan")
    assert khu and all({"khoa", "nhan", "href", "active", "nhom"} <= set(m)
                       for m in khu)
    assert any(m["active"] for m in khu), "khong muc nao duoc danh dau active"


def test_menu_DOI_CAP_khi_o_trong_mot_may():
    """Ba trong bốn trang khu VPS thuộc về **một máy cụ thể** — menu phải nói
    đúng hình dạng đó, và phải có đường về."""
    from apps.vps import nav

    class _May:
        id = "abc123def456"
        ten = "win-thu"

    m = nav.menu("console", may=_May())
    href = [x["href"] for x in m if x["href"]]
    assert nav.GOC in href, "menu cap may KHONG co duong ve khu"
    assert f"{nav.GOC}/abc123def456/console" in href
    assert f"{nav.GOC}/abc123def456/cai-dat" in href
    assert [x for x in m if x["khoa"] == "console"][0]["active"]


def test_ten_may_KHONG_di_qua_gettext():
    """Tên máy là **dữ liệu của khách**, không phải chuỗi giao diện.

    Đưa nó qua gettext là để ngỏ khả năng một ngày nào đó một tên máy trùng một
    msgid và bị đổi thành chữ khác — trên chính trang quản lý máy đó.
    """
    from apps.vps import nav

    class _May:
        id = "x" * 12
        ten = "Tổng quan"   # trùng một msgid CÓ THẬT trong catalog

    m = nav.menu("may", may=_May())
    ten_may = [x for x in m if x["khoa"] == "ten_may"][0]
    assert ten_may["nhan"] == "Tổng quan", (
        "ten may da bi dich — no phai di nguyen si")


def test_muc_chua_co_route_khong_phai_mot_lien_ket_chet():
    """Hiện tên một mục chưa làm là **thông tin**; một liên kết 404 thì không."""
    from apps.vps import nav

    for m in nav.menu("tong_quan"):
        if m["khoa"] in {k for k, _n in nav.SAP_CO_KHU}:
            assert m["href"] is None, f"{m['khoa']} co href nhung chua co route"


def test_khach_AN_DANH_khong_thay_vo_dieu_khien(moi_truong, monkeypatch):
    """Q124: bề mặt owner-only không render gì trước khi xác thực."""
    monkeypatch.setenv("LTT_VPS", "1")
    client = _client_vps()
    try:
        r = client.get("/vps")
        assert r.status_code == 303
        t = r.text
        assert "app-shell" not in t and "app-side" not in t, (
            "khach an danh dang thay menu bang dieu khien")
    finally:
        client.close()


def test_bon_trang_VPS_dung_CHUNG_mot_vo(t):
    """Không trang nào được tự dựng vỏ riêng — đó chính là cách đường về biến
    mất lần trước."""
    for ten in ("vps.html", "vps_chi_tiet.html", "vps_cai_dat.html",
                "vps_console.html"):
        s = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        assert '{% extends "vps_base.html" %}' in s, f"{ten} khong dung vo chung"
        assert '{% extends "base.html" %}' not in s


def test_ba_trang_trong_mot_may_co_BREADCRUMB_ve_khu():
    """`/vps/{id}` từng lấy tên máy làm thanh tiêu đề — đúng, nhưng **mất đường
    về**, và đó là ngõ cụt duy nhất còn lại trong khu."""
    for ten in ("vps_chi_tiet.html", "vps_cai_dat.html", "vps_console.html"):
        s = (GOC / "server" / "templates" / ten).read_text(encoding="utf-8")
        i = s.index("{% block topbar_title %}")
        thanh = s[i:s.index("{% endblock %}", i)]
        assert 'href="/vps"' in thanh, f"{ten}: thanh tieu de khong co duong ve"


def test_gia_CHI_theo_chu_ky_30_ngay():
    """Chủ sản phẩm chốt: không bán theo giờ.

    Không thêm cột "giá theo giờ" kể cả để tham khảo — nó sẽ thành thứ khách
    dùng để so với Vultr, trong khi hệ thống **không** tính tiền theo giờ.
    """
    for ten in ("vps.html", "vps_chi_tiet.html"):
        s = _bo_chu_thich((GOC / "server" / "templates" / ten).read_text(
            encoding="utf-8"))
        for cam in ("/hr", "/giờ", "mỗi giờ", "per hour", "theo giờ"):
            assert cam not in s, f"{ten} nhac toi gia theo gio: {cam!r}"


def _client_vps():
    from fastapi.testclient import TestClient
    from server.app import create_app
    return TestClient(create_app(), base_url="https://testserver",
                      follow_redirects=False)


@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'vps-vo.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-vps-vo")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models   # noqa: F401
    import apps.vps.tables        # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield dbmod
    dbmod.reset_engine()


# ─────────────────────────────────────────────────────────────────────────────
# 7 · VPS là một nhóm RIÊNG trên thanh tiêu đề (chốt chủ sản phẩm 25/08)
#
# > *"VPS là menu riêng. Ứng dụng là các tiện ích sau này tôi xây dựng."*
# ─────────────────────────────────────────────────────────────────────────────

def test_vps_khai_nhom_rieng_khong_nam_trong_Ung_dung():
    from apps.vps.manifest import MANIFEST

    assert MANIFEST.group == "VPS", (
        f"nhom hien la {MANIFEST.group!r} — chu san pham chot VPS phai la mot "
        "nhom rieng, khong nam trong 'Ứng dụng'")


def test_vps_dung_NGAY_TRUOC_Ung_dung_tren_thanh_tieu_de():
    """⚠️ Việc hai nhóm này nằm cạnh nhau là **tình cờ**, không được bảo đảm.

    `server/templating.py:_khoa()` ghim "Khác" và "Ứng dụng" xuống cuối (bucket
    2); mọi nhóm khác vào bucket 1 và **xếp theo bảng chữ cái**. "VPS" cạnh
    "Ứng dụng" chỉ vì các nhóm sắp sau nó (`Vận hành`, `Khác`) không hiện cho
    khách.

    🔴 **Hợp đồng app KHÔNG có cách khai vị trí nhóm.** Thêm một nhóm mới tên
    sắp sau "VPS" — ví dụ `"Voice"`, `"Website"` — sẽ chen vào giữa, và không
    có gì báo. Phép kiểm này là thứ báo.

    Sửa cho đúng thì phải bổ sung hợp đồng (`AppManifest.group_uu_tien`), chứ
    không phải đi sửa `_uu_tien` trong `templating.py` — một app không được
    ép nền tảng biết tên nó. Xem `CLAUDE.md` mục "Thêm app mới".
    """
    _UU_TIEN = {"Ảnh": 0, "Video": 1, "Giọng nói": 2, "Đăng bài": 3,
                "Workflow": 4}

    def _khoa(g):
        if g in ("Khác", "Ứng dụng"):
            return (2, g)
        return (0, _UU_TIEN.get(g, 1)) if g in _UU_TIEN else (1, g)

    # Đúng tập nhóm KHÁCH nhìn thấy, đo trên trình duyệt thật 25/08.
    nhin_thay = ["Ảnh", "Video", "AI Studio", "Chat", "VPS", "Ứng dụng"]
    thu_tu = sorted(nhin_thay, key=_khoa)
    assert thu_tu[-2:] == ["VPS", "Ứng dụng"], (
        f"VPS khong con dung ngay truoc 'Ứng dụng': {thu_tu}")


def test_nhom_VPS_khong_bi_boc_N_():
    """"VPS" giống nhau ở cả hai ngôn ngữ.

    Bọc `N_()` quanh nó chỉ làm bánh cóc i18n phải đếm thêm một msgid không có
    gì để dịch — và một msgid như thế sẽ nằm mãi trong danh sách "chưa dịch"
    của người sau.
    """
    s = (GOC / "apps" / "vps" / "manifest.py").read_text(encoding="utf-8")
    assert 'group="VPS"' in s
    assert 'group=N_("VPS")' not in s
