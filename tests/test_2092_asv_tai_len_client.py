"""asv-final L_TAI_LEN — hop dong phia client cua tai len nhieu phan.

Hanh vi that (dut mang -> tiep tuc) duoc kiem bang trinh duyet — xem
`docs/auto_scan_video_final/L_TAI_LEN.md`. O day chot nhung bat bien doc duoc
tu ma nguon, de mot lan sua sau khong go mat chung trong im lang.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from tests import asv_js

GOC = Path(__file__).resolve().parents[1]
VENDOR = GOC / "server" / "static" / "vendor" / "spark-md5-3.0.2"
MAU = GOC / "apps" / "auto_scan_video" / "templates" / "asv_trang_chinh.html"


def _js() -> str:
    return asv_js.doc("asv/tai_len.js")


def _than(js: str, dau: str) -> str:
    i = js.index(dau)
    return js[i:js.index("\n  }\n", i)]


def test_TIEP_TUC_hoi_may_chu_phan_nao_da_co_truoc_khi_mo_luot_moi():
    than = _than(_js(), "function batDauHoacTiepTuc(f)")
    assert "nhoLay(f)" in than
    # GET trang thai TRUOC; chi mo luot moi khi khong co/khong con.
    assert than.index('goc + "/" + encodeURIComponent(id)') < than.rindex("return moi()")
    assert "mt.co === f.size" in than, "tiep tuc luot cua mot tep KHAC"


def test_chi_gui_phan_CON_THIEU():
    than = _than(_js(), "function taiNhieuPhan(f)")
    assert "mt.da_co" in than
    assert "if (co[so]) continue;" in than
    assert '"/xong"' in than


def test_nho_upload_id_theo_DANH_TINH_tep_va_localStorage_boc_try():
    js = _js()
    k = _than(js, "function khoaTep(f)")
    for truong in ("f.name", "f.size", "f.lastModified", "f.type"):
        assert truong in k
    for ham in ("function nhoLay(f)", "function nhoDat(f, id)"):
        assert "try" in _than(js, ham), f"{ham}: localStorage co the nem (private mode)"
    # Xong thi quen, de lan chon lai cung tep khong "tiep tuc" mot luot da dong.
    assert 'nhoDat(f, "")' in _than(js, "function taiNhieuPhan(f)")


def test_MOI_phan_co_Content_MD5_tu_thu_vien_da_thanh_danh():
    js = _js()
    assert "SparkMD5.ArrayBuffer.hash(buf, true)" in _than(js, "function md5Phan(phan)")
    assert "md5: md5" in _than(js, "function guiPhan(mt, f, so, daXong)")
    # Tien do tinh theo CA tep, khong reset ve 0 moi phan.
    assert "(daXong + e.loaded)" in _than(js, "function dayLen(ve, phan, daXong, tong)")


def test_thu_vien_MD5_dung_ban_da_ghi_nguon_va_duoc_nap_TRUOC_module():
    tep = VENDOR / "spark-md5.min.js"
    nguon = (VENDOR / "NGUON.txt").read_text(encoding="utf-8")
    m = re.search(r"sha256\(spark-md5\.min\.js\) = ([0-9a-f]{64})", nguon)
    assert m and hashlib.sha256(tep.read_bytes()).hexdigest() == m.group(1)
    assert (VENDOR / "LICENSE").is_file()
    van = MAU.read_bytes().decode("utf-8")
    assert van.index("vendor/spark-md5-3.0.2/spark-md5.min.js") < van.index(
        "{% for tep in asv_studio_js %}")


def test_chuoi_tiep_tuc_co_trong_bang_dich():
    van = MAU.read_bytes().decode("utf-8")
    assert '"tai_tiep_tuc"' in van
    assert 't("tai_tiep_tuc"' in _js()
