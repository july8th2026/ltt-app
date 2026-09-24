"""ASV V6 pha 18 — Voice Browser: tim, hai nguon, lam moi, trang thai rong/chua mau.

⚠️ Phia client, cac phep kiem o day DOC VAN BAN ma nguon (kho khong co bo chay
   JS — `PHA06_KIEN_TRUC_GUI.md` §8). Chung chot *"ma co noi X"*; hanh vi that
   duoc chung minh bang trinh duyet that o `PHA18_VOICE_BROWSER.md` §3.
"""
from __future__ import annotations

import re
from pathlib import Path

from tests import test_423_asv_giao_dien as _mt

GOC = Path(__file__).resolve().parents[1]
JS = (GOC / "server/static/asv/giong.js").read_text(encoding="utf-8")
moi_truong = _mt.moi_truong


def _trang(moi_truong):
    return moi_truong[1].get("/auto-scan-video/").text


def _o_giong(van):
    return re.search(r'<select[^>]*\bid="asv-giong"[^>]*>(.*?)</select>', van, re.S).group(1)


def test_moi_giong_mang_NGUON_va_TEN_de_loc(moi_truong):
    muc = re.findall(r"<option\b[^>]*>", _o_giong(_trang(moi_truong)))
    assert muc
    for m in muc:
        assert re.search(r'data-nguon="(mau|rieng)"', m), m
        assert 'data-ten="' in m, m


def test_giong_CHUA_CO_MAU_NGHE_duoc_danh_dau_ngay_trong_danh_sach(moi_truong):
    """⭐ Truoc pha 18 khach chi biet sau khi chon roi bam "Nghe thu"."""
    khoi = _o_giong(_trang(moi_truong))
    for m in re.finditer(r"<option\b([^>]*)>([^<]*)</option>", khoi):
        co_nghe = "data-nghe=" in m.group(1)
        assert ("chưa có mẫu nghe" in m.group(2)) is (not co_nghe), m.group(0)[:160]


def test_o_TIM_va_nut_NGUON_KHONG_di_theo_form(moi_truong):
    """⛔ Day la cach NHIN danh sach, khong phai du lieu cua lan chay."""
    van = _trang(moi_truong)
    tim = re.search(r'<input[^>]*id="asv-tim-giong"[^>]*>', van).group(0)
    assert " name=" not in tim
    nut = re.findall(r"<button[^>]*data-nguon-giong[^>]*>", van)
    assert len(nut) == 3
    assert all('type="button"' in n and " name=" not in n for n in nut)


def test_nut_LAM_MOI_tro_toi_danh_muc_da_loc_theo_chu_so_huu(moi_truong):
    van = _trang(moi_truong)
    url = re.search(r'id="asv-giong-lam-moi"[^>]*data-url="([^"]+)"', van).group(1)
    r = moi_truong[1].get(url)
    assert r.status_code == 200
    ds = r.json()["giong"]
    assert ds and all({"ma", "ten", "la_mau"} <= set(g) for g in ds)


def test_KHONG_con_giong_nao_khop_thi_CHAN_gui():
    """🔴 Loi co san truoc pha 18: 0 giong khop ma giong da AN van duoc gui di.

    ⚠️ **Ban nay do TINH CHAT, ban cu do CACH GO — va ban cu da bao dong gia.**
       No chot hai chuoi nguyen van: `"setCustomValidity(rong ?"` va
       `"conLai === 0"`. `c5f331fa` (23/09) viet lai dung ba dong do de noi HAI
       cau thay vi mot (`giong_khong_khop` khi het giong sau BO LOC,
       `giong_het_lan` khi het giong trong LAN) — `var rong = conLai === 0`
       thanh `var cau = conLai ? "" : (...)`. Cai chan gui **khong he mat**; chi
       cai ten bien mat. Bai nay do tu 23/09 den 24/09 va to cao khong dung ai.

    ⇒ Menh de duoc chot o day: trong `locGiong`, `oGiong.setCustomValidity` duoc
      goi voi mot gia tri tinh TU `conLai` (so giong con khop), va gia tri do
      RONG khi con giong. Doi ten bien, tach them cau, doi thong diep — tat ca
      di qua. Bo mat cai chan gui, hoac chan theo mot con so khac, thi do.

    ⛔ Phep kiem nay van chi doc van ban ma nguon (xem docstring dau tep): no
       chung minh *"ma co noi dieu do"*, khong phai *"trinh duyet lam dieu do"*.
    """
    than = JS[JS.index("function locGiong"):JS.index("function capNhatNghe")]

    goi = re.search(r"oGiong\.setCustomValidity\(\s*([A-Za-z_$][\w$]*)\s*\)", than)
    assert goi, "locGiong khong con dat `oGiong.setCustomValidity(<bien>)`"

    bien = goi.group(1)
    gan = re.search(r"\bvar\s+" + re.escape(bien) + r"\s*=\s*([^;]+);", than)
    assert gan, f"khong tim thay cho gan `{bien}` trong `locGiong`"

    biv = gan.group(1)
    assert "conLai" in biv, (
        f"`{bien}` khong tinh tu `conLai` — cai chan gui dang doc mot con so "
        f"khac voi so giong con khop: {biv!r}")
    assert re.search(r'(""|\'\')', biv), (
        f"`{bien}` khong bao gio rong — o giong se KHONG BAO GIO gui duoc: {biv!r}")


def _ma_khong_chu_thich(van: str) -> str:
    """⚠️ Bo chu thich TRUOC khi quet: chinh dong giai thich luat nay co nhac
       `<option value="">`, va mot bo do quet van ban se bao dong tren no."""
    van = re.sub(r"/\*.*?\*/", "", van, flags=re.S)
    return re.sub(r"(^|\s)//[^\n]*", r"\1", van)


def test_KHONG_them_muc_rong_de_bieu_dien_trang_thai_rong():
    """`test_447` cam muc rong trong o giong; trang thai rong di bang validity.

    Menh de DUONG: moi muc dung lai lay `value` tu `g.ma` cua may chu.
    """
    ma = _ma_khong_chu_thich(JS)
    assert "o.value = g.ma;" in ma
    assert '<option value=""' not in ma and 'value = ""' not in ma


def test_tim_KHONG_DAU_ke_ca_chu_d():
    than = JS[JS.index("function khongDau"):JS.index("function laRieng")]
    assert 'normalize("NFD")' in than and "đ" in than


def test_lam_moi_GIU_danh_sach_cu_khi_may_chu_tra_RONG():
    than = JS[JS.index("function lamMoi"):]
    assert "if (!ds.length) throw" in than
    assert than.index("if (!ds.length) throw") < than.index('oGiong.textContent = ""')


def test_tu_lam_moi_khi_tab_duoc_nhin_lai_CO_TRAN_nhip():
    assert "visibilitychange" in JS and "30000" in JS
