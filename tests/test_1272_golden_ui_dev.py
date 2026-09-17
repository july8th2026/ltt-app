"""Golden UI — khu API (/developers/*) và trang tài liệu công khai (17/09/2026).

Chốt những gì đợt này sửa, theo HÀNH VI render chứ không theo câu chữ:

1. **Viên trạng thái đúng màu cho MỌI enum** (`_dev_tt.html`). Enum API giữ
   nguyên văn (`running`, `succeeded` là giá trị JSON khách đọc lại), nhưng mỗi
   giá trị phải có lớp màu và nghĩa tiếng Việt cho trình đọc màn hình. Trước
   đây `dev_usage.html` chỉ biết held/settled/refunded ⇒ `error` và `done`
   cùng một viên xám.
2. **Không control lồng control** trong thẻ công cụ (axe `nested-interactive`,
   serious): liên kết "Tài liệu"/"Thử ngay" không được nằm trong `<summary>`.
3. **Mọi trang khu API có phụ đề ở CÙNG một chỗ** (`.dev-dan` dưới `h1`).
4. **Trang công khai**: có `<title>` riêng, số theo quy ước Việt (`5.000đ`,
   không `5,000đ`), không inline style / hex thô.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from tests.test_197_developer_api_tab import _register, portal  # noqa: F401

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


# ── 1. Viên trạng thái ──────────────────────────────────────────────────────

ENUM = {
    "job": ["queued", "running", "done", "error", "cancelled", "succeeded", "failed"],
    "so": ["held", "settled", "refunded"],
    "khoa": ["active", "expired", "disabled", "revoked"],
    "giao": ["pending", "sending", "delivered", "failed", "dead"],
}


@pytest.fixture(scope="module")
def dtt():
    from server.templating import templates
    return templates.env.get_template("_dev_tt.html").make_module({})


@pytest.mark.parametrize("loai,gia_tri", [(k, v) for k, vs in ENUM.items() for v in vs])
def test_moi_enum_co_lop_mau_va_nghia(dtt, loai, gia_tri):
    html = str(dtt.tt(gia_tri, loai))
    lop = re.search(r'class="dev-tt ([a-z]*)"', html)
    assert lop and lop.group(1) in {"ok", "canh", "loi", "tat", "tin"}, (loai, gia_tri, html)
    # Chữ thật vẫn là enum nguyên văn — đó là giá trị API.
    assert f">{gia_tri}<" in html
    # Và có nghĩa cho người đọc: title + chữ ẩn cho trình đọc màn hình.
    assert 'title="' in html and 'class="sr-only"' in html, html


def test_trang_thai_ket_thuc_khac_mau_nhau(dtt):
    """`done` và `error` từng in giống hệt nhau ở /developers/usage."""
    lop = {v: re.search(r'dev-tt ([a-z]*)', str(dtt.tt(v))).group(1)
           for v in ("done", "error", "cancelled", "running", "queued")}
    assert len({lop["done"], lop["error"], lop["cancelled"]}) == 3, lop
    assert lop["running"] != lop["done"] and lop["queued"] != lop["done"], lop


def test_gia_tri_la_khong_bi_giau(dtt):
    html = str(dtt.tt("khong_biet"))
    assert ">khong_biet<" in html and 'class="dev-tt "' in html


@pytest.mark.parametrize("ma,lop", [(200, "ok"), (404, "canh"), (429, "canh"), (503, "loi")])
def test_ma_http(dtt, ma, lop):
    html = str(dtt.http(ma))
    assert f'class="dev-tt {lop}"' in html and 'class="sr-only"' in html


def test_css_co_sac_dang_xu_ly():
    assert re.search(r"\.dev-tt\.tin\{[^}]*--status-info", CSS)


@pytest.mark.parametrize("tep", ["dev_usage.html", "dev_jobs.html", "dev_keys.html",
                                 "dev_webhooks.html", "dev_logs.html", "dev_overview.html",
                                 "dev_log_detail.html"])
def test_trang_dung_macro_chung_khong_tu_chep_bang_mau(tep):
    noi = _doc(tep)
    assert '{% import "_dev_tt.html" as dtt %}' in noi
    # Bảng màu chép tay kiểu `{'succeeded':'ok', ...}.get(` là thứ đã lệch.
    assert not re.search(r"\{'[a-z]+':'(ok|canh|loi|tat)'", noi), tep


# ── 2. Thẻ công cụ: không liên kết trong <summary> ─────────────────────────

def test_khong_lien_ket_trong_summary_o_template():
    noi = _doc("dev_tools.html")
    for khoi in re.findall(r"<summary>(.*?)</summary>", noi, flags=re.S):
        assert "<a " not in khoi, "lien ket nam trong <summary> (axe nested-interactive)"
    assert "event.stopPropagation" not in noi


# ── 3. Render thật: phụ đề + thẻ công cụ + mọi trang khu API ───────────────

TRANG_DEV = ["/developers", "/developers/quickstart", "/developers/pricing",
             "/developers/playground", "/developers/cli", "/developers/docs",
             "/developers/tools", "/developers/tools/image.thumbnail",
             "/developers/projects", "/developers/keys", "/developers/settings",
             "/developers/privacy", "/developers/logs", "/developers/jobs",
             "/developers/usage", "/developers/notifications", "/developers/webhooks"]


def test_moi_trang_khu_api_co_phu_de_cung_mot_cho(portal):  # noqa: F811
    _register(portal, f"gu-dev-{uuid.uuid4().hex[:6]}@example.com")
    thieu, inline = [], {}
    for duong in TRANG_DEV:
        r = portal.get(duong)
        assert r.status_code == 200, (duong, r.status_code)
        dau = re.search(r'<div class="dev-dau">(.*?)</div>\s*(?:<div class="dev-dau-nut">|</div>)',
                        r.text, flags=re.S)
        if not dau or 'class="dev-dan"' not in dau.group(1):
            thieu.append(duong)
        # Phần nội dung khu API (sau thanh bên) không còn inline style, trừ màu
        # chấm của biểu đồ vòng (giá trị dữ liệu).
        than = r.text.split('<div class="app-main">', 1)[-1].split("<footer", 1)[0]
        con = [s for s in re.findall(r'style="([^"]*)"', than)
               if not s.startswith("background:") ]
        if con:
            inline[duong] = con
    assert thieu == [], f"trang thieu phu de .dev-dan: {thieu}"
    assert inline == {}, inline


def test_the_cong_cu_render_khong_long_control(portal):  # noqa: F811
    _register(portal, f"gu-the-{uuid.uuid4().hex[:6]}@example.com")
    trang = portal.get("/developers/tools").text
    assert 'class="dev-tool-o"' in trang
    for khoi in re.findall(r"<summary>(.*?)</summary>", trang, flags=re.S):
        assert "<a " not in khoi
    assert 'href="/developers/tools/image.thumbnail"' in trang
    assert 'href="/developers/playground?tool=image.thumbnail"' in trang


def test_chi_tiet_cong_cu_muc_luc_la_danh_sach_dieu_huong(portal):  # noqa: F811
    _register(portal, f"gu-ml-{uuid.uuid4().hex[:6]}@example.com")
    trang = portal.get("/developers/tools/image.thumbnail").text
    nav = re.search(r'<ul class="dev-muc-luc">(.*?)</ul>', trang, flags=re.S)
    assert nav, "muc luc khong con la danh sach"
    # Mỗi neo trong mục lục phải có đích trên trang (trước đây `#model` luôn
    # có dù thẻ Model chỉ render khi công cụ có model).
    for neo in re.findall(r'href="#([a-z-]+)"', nav.group(1)):
        assert f'id="{neo}"' in trang, f"neo #{neo} khong co dich"


# ── 4. Trang tài liệu công khai ─────────────────────────────────────────────

@pytest.fixture()
def khach(portal):  # noqa: F811
    """Khach CHUA dang nhap, nhung co CSDL (`/status/api` doc bang cong cu)."""
    return portal


@pytest.mark.parametrize("duong", ["/gia-api", "/api-dieu-khoan", "/huong-dan",
                                   "/huong-dan/cong-cu", "/status/api"])
def test_trang_cong_khai_co_title_rieng_va_mot_h1(khach, duong):
    r = khach.get(duong)
    assert r.status_code == 200
    title = re.search(r"<title>(.*?)</title>", r.text, flags=re.S).group(1).strip()
    assert title != "LTT AI Studio", f"{duong}: <title> chung chung"
    assert r.text.count("<h1") == 1, duong


@pytest.mark.parametrize("duong", ["/gia-api", "/api-dieu-khoan"])
def test_so_theo_quy_uoc_viet(khach, duong):
    r = khach.get(duong)
    main = r.text.split("<main", 1)[1].split("</main>", 1)[0]
    chu = re.sub(r"<[^>]+>", " ", main)
    assert not re.search(r"\d,\d{3}\b", chu), re.findall(r"\S*\d,\d{3}\S*", chu)[:5]
    # Đối chứng: trang THẬT SỰ có số hàng nghìn — không thì phép đo trên rỗng.
    assert re.search(r"\d\.\d{3}\b", chu), f"{duong}: khong co so hang nghin nao de do"


@pytest.mark.parametrize("tep", ["gia_api.html", "api_dieu_khoan.html", "status_api.html",
                                 "huong_dan.html", "huong_dan_cong_cu.html", "_cam_chon.html"])
def test_template_cong_khai_khong_inline_style_va_hex(tep):
    noi = _doc(tep)
    assert "style=" not in noi, tep
    assert '"{:,}".format' not in noi, tep
    # Hex thô trong mã template (ngoài chú thích Jinja).
    ma = re.sub(r"\{#.*?#\}", "", noi, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{6}\b", ma), tep


def test_status_api_khong_in_tieu_de_hai_lan(khach):
    trang = khach.get("/status/api").text
    assert 'class="pagebar"' not in trang
    assert trang.count("Tình trạng API</") == 1


# ── CSS: khối DEV chỉ dùng token ────────────────────────────────────────────

def test_khoi_css_dev_chi_dung_token():
    assert "/* === Golden UI song song: DEV === */" in CSS
    khoi = CSS.split("/* === Golden UI song song: DEV === */", 1)[1]
    # Khối kết thúc ở khối song song tiếp theo (nếu các nhánh khác nối thêm).
    khoi = khoi.split("/* === Golden UI song song:", 1)[0]
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", khoi)


def test_o_bieu_tuong_cong_cu_khong_con_hex_tho():
    """DL-002: một bảng màu ấm — ô biểu tượng công cụ từng mang teal/xanh/tím hex."""
    luat = re.findall(r"\.khu-dev \.tool-icon[^{]*\{[^}]*\}", CSS)
    assert luat, "khong tim thay luat .tool-icon"
    for l in luat:
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", l), l
