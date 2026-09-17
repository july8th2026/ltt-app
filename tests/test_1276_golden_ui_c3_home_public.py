"""Golden UI C3 (17/09) — họ Workspace (trang chủ đã đăng nhập) và Public.

Chốt các khiếm khuyết người chấm độc lập ghi ở vòng v5, bằng mã nguồn + HTML
render thật (không chốt chuỗi hiển thị ngoài ý định):

* cột "Hoạt động / Việc đang chạy / Credit" không còn bị ẩn dưới 1100px;
* tên thẻ 2 dòng thay vì cắt 1 dòng; nhãn "Mở ứng dụng" chữ Việt;
* dải chip cuộn có mép mờ, placeholder ngắn ở khung hẹp;
* `/huong-dan`: mục lục neo, bảng xếp thẻ ở 390, backtick thành <code>;
* bản `/en/` không lọt mô tả tiếng Việt của manifest;
* không dùng emoji ⚠/⛔/⭐/⏱/💰 làm icon ở các trang công khai.
"""
from __future__ import annotations

import gettext
import importlib
import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _doc(ten: str) -> str:
    return re.sub(r"\{#.*?#\}", "", (TPL / ten).read_text(encoding="utf-8"), flags=re.S)


def _khoi_c3() -> str:
    moc = "/* === C3: WORKSPACE-PUBLIC === */"
    assert CSS.count(moc) == 1, "khoi CSS C3 phai dung MOT lan"
    return CSS.split(moc, 1)[1]


def test_rail_xuong_duoi_luoi_thay_vi_an():
    khoi = _khoi_c3()
    m = re.search(r"@media\(max-width:1100px\)\{(.*?)\n\}", khoi, flags=re.S)
    assert m, "thieu media 1100px cua rail"
    assert ".market-rail{display:grid" in m.group(1)
    assert "display:none" not in m.group(1)


def test_ten_the_hai_dong_va_nhan_mo_ung_dung():
    khoi = _khoi_c3()
    assert "-webkit-line-clamp:2" in khoi and "white-space:normal" in khoi
    home = _doc("home.html")
    assert '{{ _("Mở ứng dụng") }}' in home
    assert "_('Mở app')" not in home and '_("Mở app")' not in home


def test_chip_cuon_co_mep_mo_va_placeholder_ngan():
    khoi = _khoi_c3()
    assert ".market-categories.c3-con-tiep{" in khoi and "mask-image" in khoi
    home = _doc("home.html")
    assert "classList.toggle('c3-con-tiep'" in home
    assert "data-placeholder-ngan=" in home


def test_sidebar_chua_phat_hanh_khong_mo_va_nhan_doc_duoc():
    khoi = _khoi_c3()
    assert ".market-nav button.market-deferred:disabled{opacity:1" in khoi
    small = re.search(r"\.market-nav \.market-deferred small\{([^}]*)\}", khoi)
    assert small and "font-size:10px" in small.group(1)


def test_rail_khong_render_emoji_manifest():
    home = _doc("home.html")
    assert "{{ job.app_icon }}" not in home
    assert home.count("ic.icon_app(job.app_icon)") == 2


def test_huong_dan_muc_luc_tro_toi_id_that(khach):
    html = khach.get("/huong-dan").text
    muc_luc = re.search(r'<nav class="c3-muc-luc".*?</nav>', html, flags=re.S)
    assert muc_luc, "thieu muc luc"
    neo = re.findall(r'href="#([\w-]+)"', muc_luc.group(0))
    assert len(neo) >= 8
    for n in neo:
        assert f'id="{n}"' in html, n


def test_huong_dan_backtick_thanh_code(khach):
    html = khach.get("/huong-dan").text
    than = re.sub(r"<(script|style|pre)\b.*?</\1>", "", html, flags=re.S)
    than = re.sub(r"<!--.*?-->", "", than, flags=re.S)
    # chỉ nhìn phần chữ hiển thị trong các mục đọc dữ liệu examples.py
    for id_ in ("ba-cua", "ngu-canh"):
        khoi = than.split(f'id="{id_}"', 1)[1].split('<div class="card"', 1)[0]
        chu = re.sub(r"<[^>]+>", "", khoi)
        assert "`" not in chu, (id_, chu[chu.index("`") - 40: chu.index("`") + 40])
    assert "<code>model_catalog_json</code>" in html


def test_huong_dan_bang_xep_the_o_khung_hep():
    khoi = _khoi_c3()
    assert ".c3-bang-xep tr{display:grid" in khoi
    assert _doc("huong_dan.html").count('class="table c3-bang-xep" role="table"') == 2


@pytest.mark.parametrize("ten", ["huong_dan.html", "huong_dan_cong_cu.html",
                                 "api_dieu_khoan.html", "gia_api.html"])
def test_trang_cong_khai_khong_dung_emoji_lam_icon(ten):
    assert not re.findall("[⚠⛔⭐★⏱\U0001F4B0]", _doc(ten))


def test_gia_api_moi_h2_the_cung_co():
    gia = _doc("gia_api.html")
    assert '<h2 class="u-mt0">' not in gia
    assert gia.count('<h2 class="u-mt0 tl-muc">') >= 6


def test_manifest_hien_tren_catalog_deu_co_ban_dich_en():
    t = gettext.translation("messages", str(GOC / "locale"), languages=["en"])
    thieu = []
    for f in sorted((GOC / "apps").glob("*/manifest.py")):
        m = importlib.import_module(f"apps.{f.parent.name}.manifest").MANIFEST
        for truong in (m.display_name, m.summary):
            if truong and re.search("[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]",
                                    truong, flags=re.I) and t.gettext(truong) == truong:
                thieu.append(f"{m.slug}: {truong[:50]}")
    assert not thieu, thieu


def test_catalog_an_danh_nhan_vong_doi_co_nen_vien():
    khoi = _khoi_c3()
    rule = re.search(r"#catalog-grid \.appcard \.cover \.cbadge\{([^}]*)\}", khoi)
    assert rule and "padding" in rule.group(1) and "border:1px solid" in rule.group(1)


@pytest.fixture(scope="module")
def khach():
    from fastapi.testclient import TestClient

    from server.app import create_app
    return TestClient(create_app())
