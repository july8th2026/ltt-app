"""Hai banh coc them ngay 25/08/2026 — va bang chung rang chung CHAN THAT.

⭐ Vi sao mot banh coc phai co test rieng: mot banh coc hong khong bao gi ca. No
   bao PASS, va cai PASS do doc y het mot cai PASS that. Da xay ra dung nhu vay
   voi `check_so_test.py` — no chot SO LUONG, nen hai phien cung tao
   `test_303_*` van duoc bao PASS vi mot va cham cu vua duoc don trong cung
   luot. Tong khong doi, va phep kiem im lang.

   Nen ca hai banh coc o day chot TAP HOP, va ca hai deu co mot phep kiem cho
   dung ca "hoan doi" do: dich mot muc cu + them mot muc moi = tong khong doi,
   phai VAN do.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

GOC = pathlib.Path(__file__).resolve().parent.parent


def _chay(cong_cu: str, *doi_so: str, cwd: pathlib.Path | None = None):
    return subprocess.run([sys.executable, f"tools/{cong_cu}", *doi_so],
                          cwd=cwd or GOC, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


# ── 1. Banh coc BO QUA IM LANG ─────────────────────────────────────────────

def test_bo_qua_hien_tai_dat_moc():
    r = _chay("check_bo_qua.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_bo_qua_IN_HET_danh_sach_chu_khong_chi_in_khi_do():
    """Muc dich cua banh coc nay la lam cho cac cho bo qua NHIN THAY DUOC. Mot
    danh sach chi hien luc hong thi van de nguoi ta song ca nam ma khong biet
    minh dang khong do cai gi — dung nhu hai phep kiem cua `test_293` da song."""
    r = _chay("check_bo_qua.py")
    assert "test_293_vps_dung_lai_cong_vao.py::" in r.stdout, (
        "hai phep kiem chot bo luat nftables phai duoc GOI TEN o moi luot gate")


def test_bo_qua_MOI_lam_do(tmp_path):
    """Bang chung. Khong co phep kiem nay thi banh coc chi la mot y dinh."""
    thu = GOC / "tests" / "zz_thu_banh_coc_bo_qua.py"
    thu.write_text(
        "import pytest\n\n\n"
        '@pytest.mark.skipif(True, reason="thu banh coc")\n'
        "def test_gia_vo():\n    assert True\n", encoding="utf-8")
    try:
        r = _chay("check_bo_qua.py")
        assert r.returncode == 1, "them mot cho bo qua MOI ma van PASS"
        assert "CHO BO QUA MOI" in r.stdout
        assert "zz_thu_banh_coc_bo_qua.py::test_gia_vo" in r.stdout
    finally:
        thu.unlink(missing_ok=True)


# ── 2. Banh coc DICH THIEU BAN EN ──────────────────────────────────────────

def test_dich_thieu_hien_tai_dat_moc():
    r = _chay("check_dich_thieu.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_fuzzy_duoc_DEM_NHU_CHUA_DICH():
    """`msgfmt` bo qua moi muc `#, fuzzy` khi sinh `.mo`. Mot ban dich fuzzy
    khong bao gio toi mat nguoi dung — no giong het `msgstr` rong khi chay, chi
    khac la no TRONG NHU da lam xong khi doc tep `.po`."""
    r = _chay("check_dich_thieu.py")
    assert "fuzzy" in r.stdout, "phai noi ro co bao nhieu muc fuzzy"
    moc = (GOC / "tools" / "check_dich_thieu.moc").read_text(encoding="utf-8")
    assert "FUZZY\t" in moc, "muc fuzzy phai nam trong moc, khong duoc mien"


def test_chuoi_MOI_chua_dich_lam_do():
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    goc = po.read_text(encoding="utf-8")
    try:
        po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                            'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                      encoding="utf-8")
        r = _chay("check_dich_thieu.py")
        assert r.returncode == 1, "them mot chuoi chua dich MOI ma van PASS"
        assert "MUC MOI CHUA DICH" in r.stdout
    finally:
        po.write_text(goc, encoding="utf-8")


def test_HOAN_DOI_van_lam_do_du_TONG_KHONG_DOI():
    """🔴 Chinh la ca lam `check_so_test.py` bao PASS tren mot va cham that.

    Dich mot muc cu VA them mot muc moi trong cung mot luot: tong van dung 279.
    Mot moc dem SO LUONG se noi PASS. Moc dem TAP HOP phai noi FAIL.
    """
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    goc = po.read_text(encoding="utf-8")
    moc = (GOC / "tools" / "check_dich_thieu.moc").read_text(encoding="utf-8")
    mot = next(d.split("\t", 1)[1]
               for d in moc.splitlines() if d.startswith("TRONG\t"))
    truoc = f'msgid "{mot}"\nmsgstr ""'
    if truoc not in goc:                       # muc nhieu dong — bo qua ca nay
        return
    try:
        moi = goc.replace(truoc, f'msgid "{mot}"\nmsgstr "TRANSLATED"', 1)
        po.write_text(moi + '\n#: server/templates/khong_co_that.html:1\n'
                            'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                      encoding="utf-8")
        r = _chay("check_dich_thieu.py")
        assert r.returncode == 1, (
            "hoan doi mot-doi-mot lot qua — moc dang dem SO LUONG chu khong "
            "phai TAP HOP")
        assert "MUC MOI CHUA DICH" in r.stdout
    finally:
        po.write_text(goc, encoding="utf-8")


def test_accept_TU_CHOI_khi_con_muc_moi():
    """`--accept` phai la duong HA moc, khong duoc thanh duong im lang nang no."""
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    goc = po.read_text(encoding="utf-8")
    moc_truoc = (GOC / "tools" / "check_dich_thieu.moc").read_bytes()
    try:
        po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                            'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                      encoding="utf-8")
        r = _chay("check_dich_thieu.py", "--accept")
        assert r.returncode == 1, "--accept nang moc len duoc"
    finally:
        po.write_text(goc, encoding="utf-8")
        (GOC / "tools" / "check_dich_thieu.moc").write_bytes(moc_truoc)


# ── 3. Ca hai phai nam TRONG gate ──────────────────────────────────────────

def test_ca_hai_banh_coc_nam_trong_gate():
    """Mot cong cu khong duoc gate goi la mot cong cu khong ai chay."""
    gate = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "tools/check_bo_qua.py" in gate
    assert "tools/check_dich_thieu.py" in gate


def test_ca_hai_chay_ca_o_che_do_quick():
    """Chung re (doc tep, khong dung CSDL). Ba loi that lot len tau ngay 25/08
    deu lot vi phep kiem CO ma chi song trong `pytest`, thu `--quick` bo qua."""
    gate = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    truoc_quick = gate.split("if not quick:")[0]
    assert "tools/check_bo_qua.py" in truoc_quick
    assert "tools/check_dich_thieu.py" in truoc_quick
