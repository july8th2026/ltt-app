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

import os
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


# ⛔ BA TEST DUOI DAY GHI DE `locale/en/LC_MESSAGES/messages.po` THAT.
#
#    Khoi phuc trong `finally` PHAI la `write_bytes`, khong duoc `write_text`.
#    Do that 26/08: ban dau chung dung `write_text(..., encoding="utf-8")`, va
#    tren Windows `Path.write_text` dich LF thanh CRLF. Ban "khoi phuc" khac ban
#    goc **10.465 dong** - nguyen tep, chi doi kieu xuong dong.
#
#    Hai hau qua, ca hai am tham:
#      1. `git status` cua bat ky ai chay pytest bong co mot tep .po sua doi
#         khong hieu tu dau ra;
#      2. `tools/gate.py` lay dau van tay cay o CA HAI DAU => in "CAY DA DOI
#         TRONG LUC CHAY", tuc **mot luot gate 2 gio tu vo hieu hoa chinh no**.
#
# ⭐ Chinh tep nay DA lam dung cho tep `.moc` (`read_bytes`/`write_bytes`) o
#    `test_accept_TU_CHOI_khi_con_muc_moi`. Bai hoc: khi mot tep can byte-exact
#    thi MOI tep trong cung ham deu can - khong chi tep minh nho toi.
#
# ⛔ VA PHAI TRA LAI CA DAU THOI GIAN (`os.utime`), khong chi noi dung.
#    Do that luot sau: `git status` SACH (byte y het) ma gate VAN in
#    "CAY DA DOI TRONG LUC CHAY". Dau van tay cua gate dung
#    `st_mtime`, nen mot lan ghi-lai-y-het van lam no keu. Mot lan
#    gate 2 gio nua bi vo hieu vi dung mot dong nay.

#: Nhung chuoi ma ba test duoi day TU TIEM vao tep that. Neu mot trong so
#: chung CO SAN luc test bat dau thi tep dang mang rac cua mot luot truoc.
_DAU_TIEM = ("Chuoi thu banh coc", "khong_co_that.html")


def _bat_buoc_khong_con_rac(tep) -> None:
    r"""Tep phai SACH truoc khi test tiem vao no — neu khong, do NGAY va noi ro.

    🔴 DAY MOI LA CHO RO RI, va no khong phai `read_text()` nam ngoai `try`.

       Doc TRUOC `try` la DUNG: khong duoc buoc vao `try` khi chua cam mot ban
       sao tot. Neu `read_text()` nem thi cung chua ghi gi, nen khong co gi phai
       khoi phuc — `finally` khong chay cung khong sao.

       Lo that la vong doi HAI luot:

         luot 1: ghi ban tiem -> tien trinh BI GIET -> `finally` khong chay
                 => tep o lai trong cay, dang BAN
         luot 2: `goc = read_text()` doc dung ban BAN do
                 -> `finally` "khoi phuc" ve chinh ban ban ay
                 => rac thanh vinh vien, va moi luot sau deu tai xac nhan no

    ⇒ Ngay 2026-08-29 hai phien `git checkout` ba tep nay **nam lan** va khong
      ai hoi "ai ghi?". Moi lan chi don trieu chung; vong doi tren van nguyen.

    ⭐ Chot bang DAU TIEM chu khong bang `git diff`: mot phep so voi HEAD se bao
       do ca khi ai do dang sua tep do that su — no bien mot hang rao thanh mot
       thu phai tat.
    """
    text = tep.read_text(encoding="utf-8", errors="replace")
    con = [d for d in _DAU_TIEM if d in text]
    if con:
        raise AssertionError(
            f"{tep.name} con dau tiem cua mot luot test truoc: {con}. "
            f"Mot luot bi giet giua chung da de lai no, va neu chay tiep thi "
            f"ban 'khoi phuc' se dong bang chinh ban rac nay. "
            f"Chay: git checkout -- {tep.relative_to(GOC).as_posix()}")


def test_chuoi_MOI_chua_dich_lam_do():
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    _bat_buoc_khong_con_rac(po)
    goc = po.read_text(encoding="utf-8")
    goc_byte = po.read_bytes()      # khoi phuc phai BYTE-EXACT — xem chu thich duoi
    goc_mtime = po.stat().st_mtime_ns   # ...VA phai tra lai ca DAU THOI GIAN
    try:
        po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                            'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                      encoding="utf-8")
        r = _chay("check_dich_thieu.py")
        assert r.returncode == 1, "them mot chuoi chua dich MOI ma van PASS"
        assert "MUC MOI CHUA DICH" in r.stdout
    finally:
        po.write_bytes(goc_byte)
        os.utime(po, ns=(goc_mtime, goc_mtime))


def test_HOAN_DOI_van_lam_do_du_TONG_KHONG_DOI():
    """🔴 Chinh la ca lam `check_so_test.py` bao PASS tren mot va cham that.

    Dich mot muc cu VA them mot muc moi trong cung mot luot: tong van dung 279.
    Mot moc dem SO LUONG se noi PASS. Moc dem TAP HOP phai noi FAIL.
    """
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    _bat_buoc_khong_con_rac(po)
    goc = po.read_text(encoding="utf-8")
    goc_byte = po.read_bytes()      # khoi phuc phai BYTE-EXACT — xem chu thich duoi
    goc_mtime = po.stat().st_mtime_ns   # ...VA phai tra lai ca DAU THOI GIAN
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
        po.write_bytes(goc_byte)
        os.utime(po, ns=(goc_mtime, goc_mtime))


def test_accept_TU_CHOI_khi_con_muc_moi():
    """`--accept` phai la duong HA moc, khong duoc thanh duong im lang nang no."""
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    _bat_buoc_khong_con_rac(po)
    goc = po.read_text(encoding="utf-8")
    goc_byte = po.read_bytes()      # khoi phuc phai BYTE-EXACT — xem chu thich duoi
    goc_mtime = po.stat().st_mtime_ns   # ...VA phai tra lai ca DAU THOI GIAN
    moc_truoc = (GOC / "tools" / "check_dich_thieu.moc").read_bytes()
    moc_mtime = (GOC / "tools" / "check_dich_thieu.moc").stat().st_mtime_ns
    try:
        po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                            'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                      encoding="utf-8")
        r = _chay("check_dich_thieu.py", "--accept")
        assert r.returncode == 1, "--accept nang moc len duoc"
    finally:
        po.write_bytes(goc_byte)
        os.utime(po, ns=(goc_mtime, goc_mtime))
        moc_tep = GOC / "tools" / "check_dich_thieu.moc"
        moc_tep.write_bytes(moc_truoc)
        os.utime(moc_tep, ns=(moc_mtime, moc_mtime))


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


# ── 4. Lop thu BA: da boc `_()` ma khong co trong catalog ──────────────────

def test_dem_ca_ba_lop():
    """Mot chuoi phai qua ba cua moi toi duoc mat nguoi doc ban tieng Anh:

        1. duoc BOC `_()`          `check_i18n.py`
        2. co MAT trong catalog    loai `VANG`
        3. `msgstr` khong rong     loai `TRONG` / `FUZZY`

    Cua thu HAI khong ai canh cho toi 26/08 — va no da lot that: hai chuoi o
    chan trang dung chung (`Gia API`, `Huong dan API`) ra tieng Viet tren MOI
    trang cua ban EN. Chung da boc `_()` tu lau nen `check_i18n` bao dep; chung
    khong co mot dong nao trong `.po` nen phep dem muc rong cung khong thay.
    """
    r = _chay("check_dich_thieu.py")
    assert r.returncode == 0, r.stdout + r.stderr
    for tu in ("msgstr rong", "fuzzy", "vang khoi catalog"):
        assert tu in r.stdout, f"dong tom tat khong ke ra {tu!r}"


def test_chuoi_DA_BOC_ma_VANG_khoi_catalog_lam_do():
    """Bang chung cho lop thu ba. Khong co phep kiem nay thi no chi la mot y dinh."""
    mau = GOC / "server" / "templates" / "vps_dieu_khoan.html"
    _bat_buoc_khong_con_rac(mau)
    goc = mau.read_text(encoding="utf-8")
    goc_mtime = mau.stat().st_mtime_ns
    try:
        mau.write_text(
            goc.replace("{% block noi_dung %}",
                        '{% block noi_dung %}\n'
                        '<!-- {{ _("Chuoi thu banh coc VANG") }} -->', 1),
            encoding="utf-8", newline="\n")
        r = _chay("check_dich_thieu.py")
        assert r.returncode == 1, "chuoi boc `_()` ma vang khoi catalog van PASS"
        assert "VANG" in r.stdout
    finally:
        mau.write_text(goc, encoding="utf-8", newline="\n")
        os.utime(mau, ns=(goc_mtime, goc_mtime))


def test_khoi_tao_loai_KHONG_nuot_duoc_loai_khac():
    """`--khoi-tao-loai` la cua thoat duy nhat, va no phai bi chan hai phia.

    Mot cua thoat khong gioi han se thanh cach nguoi ta lam im lang moi thu
    khac — nen no chi nhan muc CUA DUNG MOT LOAI duoc goi ten.
    """
    po = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    moc_tep = GOC / "tools" / "check_dich_thieu.moc"
    goc = po.read_bytes()
    moc = moc_tep.read_bytes()
    goc_mtime = po.stat().st_mtime_ns
    moc_mtime = moc_tep.stat().st_mtime_ns
    try:
        po.write_bytes(goc.rstrip(b"\n") + b'\n\nmsgid "Chuoi thu loai TRONG"\n'
                                           b'msgstr ""\n')
        r = _chay("check_dich_thieu.py", "--khoi-tao-loai", "VANG")
        assert r.returncode == 1, (
            "khoi tao loai VANG da nuot mot muc TRONG moi")
        assert "ngoai loai VANG" in (r.stdout + r.stderr)
    finally:
        po.write_bytes(goc)
        os.utime(po, ns=(goc_mtime, goc_mtime))
        moc_tep.write_bytes(moc)
        os.utime(moc_tep, ns=(moc_mtime, moc_mtime))
