"""Golden UI song song — khu VPS (màn máy/cài đặt/console) và admin tự dựng.

Chốt những lỗi đã soi thấy trên giao diện thật (Playwright + axe, 17/09/2026,
seed `tools/golden_ui_dev.py` có 4 máy VPS ở 4 trạng thái):

* trang một máy / cài Windows / console **không có `h1`**;
* nút "Xoá vĩnh viễn" nền `--status-danger` chữ trắng (axe color-contrast);
* khung console `aria-label` mà không có role (axe aria-prohibited-attr), và khi
  mất kết nối chỉ còn một khối đen trống;
* chấm nhật ký VPS mọi dòng đều đỏ (teal -> brand) nên dòng "xấu" không nổi;
* admin: dòng rỗng căn giữa trong colspan rộng 680px bị cắt ở 390px; thông báo
  cấp credit/API key dùng hex màu nền sáng (#b91c1c/#1a7f37) trên nền tối;
  "Xoá" gói nạp cùng kiểu với "Bật/Tắt"; chip model đang bật nền đỏ như lỗi.

Đọc tệp nguồn, không dựng app: nhanh, và không chạm provider nào.
"""
from __future__ import annotations

import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
TPL = GOC / "server" / "templates"
CSS = (GOC / "server" / "static" / "ltt.css").read_text(encoding="utf-8")
ADMIN_PY = (GOC / "server" / "admin.py").read_text(encoding="utf-8")


def _doc(ten: str) -> str:
    return (TPL / ten).read_text(encoding="utf-8")


def _khoi_song_song() -> str:
    i = CSS.index("/* === Golden UI song song: VPS-ADMIN === */")
    return CSS[i:]


# ── VPS ──────────────────────────────────────────────────────────────────────

def test_dai_danh_tinh_may_la_h1_cho_ca_ba_trang():
    mac = _doc("_vps_mac.html")
    assert re.search(r'<h1 class="vps-dinh-h1">\{\{ may\.ten or may\.id\[:8\] \}\}</h1>', mac)
    for ten in ("vps_chi_tiet.html", "vps_cai_dat.html", "vps_console.html"):
        t = _doc(ten)
        assert "mac.dinh_may(" in t, ten
        assert "<h1" not in t, f"{ten}: h1 thu hai ngoai dai danh tinh"


def test_nut_xoa_vinh_vien_khong_con_nen_status_danger_chu_trang():
    t = _doc("vps_chi_tiet.html")
    assert "background:var(--status-danger)" not in t
    assert re.search(r'class="btn btn-nguy-dac" type="submit">\{\{ _\("Xoá vĩnh viễn"\) \}\}', t)
    luat = re.search(r"\.btn\.btn-nguy-dac\{([^}]*)\}", _khoi_song_song()).group(1)
    assert "var(--brand-fill)" in luat and not re.search(r"(^|;)color:", luat), \
        "giu chu trang cua .btn (4,84:1 tren --brand-fill); --text-primary chi 4,4:1"


def test_o_xac_nhan_pha_huy_co_ten_truy_cap():
    t = _doc("vps_chi_tiet.html")
    o = re.findall(r'<input class="inp" name="xac_nhan"[^>]*>', t, flags=re.S)
    assert len(o) == 3 and all("aria-label=" in x for x in o)


def test_alert_quan_sat_cu_co_bien_the_khong_vien_trang():
    t = _doc("vps_chi_tiet.html")
    assert 'class="alert u-mb14"' not in t
    assert 'class="alert alert-info u-mb14"' in t
    assert re.search(r"\.alert-info\{[^}]*--status-info-border", CSS)


def test_cham_nhat_ky_trung_tinh_chi_dong_xau_moi_do():
    thuong = re.search(r"\.vps-nhat-ky \.cham\{([^}]*)\}", CSS).group(1)
    assert "--text-muted" in thuong and "teal" not in thuong
    assert re.search(r"\.vps-nhat-ky li\.xau \.cham\{background:var\(--status-danger\)\}", CSS)


def test_console_co_role_lop_phu_loi_va_giu_nguyen_giao_thuc():
    t = _doc("vps_console.html")
    assert re.search(r'id="khung" class="vps-cs-khung" tabindex="0" role="application"', t)
    assert 'id="tt" role="status" aria-live="polite"' in t
    assert 'id="cs-bao" hidden' in t and 'id="nut-noi-lai-khung"' in t
    # Trình bày thôi: không tự nối lại, vẫn tải lại trang để xin vé mới.
    assert t.count("location.reload()") == 2
    assert not re.search(r"^\s*rfb\.connect\(", t, flags=re.M)
    assert 'baoKhung.hidden = !(lop === "b-err" || lop === "b-grey")' in t


def test_vet_topbar_vps_khong_con_opacity_inline():
    for ten in ("vps_chi_tiet.html", "vps_cai_dat.html", "vps_console.html"):
        t = _doc(ten)
        assert "opacity:.7" not in t and "opacity:.45" not in t, ten
        assert 'class="vps-vet-goc"' in t, ten


def test_vps_khong_them_lai_style_inline_da_chuyen():
    cam = ("font-size:1.35rem;margin:0 0 14px", "cursor:pointer;font-size:.9em",
           "width:100%;margin-top:10px", "font-weight:600;text-align:left",
           "list-style:none;padding:0", "opacity:.45;cursor:not-allowed;text-align:center",
           "margin:0;font-size:15px", "width:170px")
    for ten in ("vps.html", "vps_chi_tiet.html", "vps_cai_dat.html", "vps_console.html"):
        for m in re.finditer(r'style="([^"]*)"', _doc(ten)):
            assert m.group(1).rstrip(";") not in cam, f"{ten}: {m.group(0)}"
    assert "#c92a2a" not in _doc("vps.html")


def test_menu_sap_co_noi_bang_chu():
    assert re.search(r'<span class="sap-co">\{\{ m\.nhan \}\} <span class="sap-co-nhan">'
                     r"\{\{ _\('Sắp có'\) \}\}</span></span>", _doc("vps_base.html"))


def test_seed_dev_co_may_vps_nhieu_trang_thai_khong_ghim_ho_so():
    seed = (GOC / "tools" / "golden_ui_dev.py").read_text(encoding="utf-8")
    for tt in ("dang_chay", "da_tat", "dang_tao", "loi"):
        assert f'trang_thai="{tt}"' in seed
    # Không ghim hồ sơ hạ tầng => mọi đường điều khiển từ chối trước khi chạm mạng.
    assert "infrastructure_profile_id" not in seed and "PINNED" not in seed


# ── Admin tự dựng ────────────────────────────────────────────────────────────

def test_admin_dong_rong_khong_can_giua_bi_cat():
    assert "text-align:center>" not in ADMIN_PY
    assert "padding:26px;text-align:center" not in ADMIN_PY
    assert ADMIN_PY.count("o-trong-chu") >= 6
    khoi = _khoi_song_song()
    assert re.search(r"\.o-trong-chu\{[^}]*position:sticky", khoi)
    assert re.search(r"@media \(max-width:720px\)\{\.tablewrap td\.o-trong\{text-align:left!important", khoi)
    for p in (TPL / "admin").glob("api_*.html"):
        for m in re.finditer(r'<td colspan="\d+" class="muted[^"]*">([^<]*)', p.read_text(encoding="utf-8")):
            assert not m.group(1).strip(), f"{p.name}: chu rong khong boc o-trong-chu: {m.group(1)[:40]!r}"


def test_admin_thong_bao_khong_dung_hex_nen_sang():
    for hex_ in ("#b91c1c", "#1a7f37", "#92400e"):
        assert hex_ not in ADMIN_PY, hex_
    assert ADMIN_PY.count('class="alert alert-err"') >= 7
    assert ADMIN_PY.count('class="alert alert-ok"') >= 3


def test_admin_xoa_goi_la_nut_nguy_hiem():
    assert '"danger" if op == "delete" else "ghost"' in ADMIN_PY


def test_admin_chip_model_dang_bat_trung_tinh():
    assert '"adm-chip-model" if m.is_active else "m"' in ADMIN_PY
    assert re.search(r"\.chip\.adm-chip-model\{[^}]*--surface-interactive", _khoi_song_song())


def test_admin_style_inline_lap_da_thanh_lop():
    cam = ('style="display:inline"', 'style="font-size:12px"', 'style="font-size:11px"',
           'style="margin:22px 0 10px"', 'style="font-size:26px;font-weight:700"',
           'style="text-align:right"', 'style="max-width:640px"')
    for c in cam:
        assert c not in ADMIN_PY, c
    # Còn lại chỉ là style ĐỘNG (màu provider, bề rộng thanh health) + một chấm pill.
    assert len(re.findall(r'style="', ADMIN_PY)) <= 3
    for p in (TPL / "admin").glob("*.html"):
        t = p.read_text(encoding="utf-8")
        assert not re.search(r'style="width:\d+px"', t), p.name
