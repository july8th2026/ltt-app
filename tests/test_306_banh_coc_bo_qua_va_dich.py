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


def _chay(cong_cu: str, *doi_so: str, cwd: pathlib.Path | None = None,
          po: pathlib.Path | None = None):
    """Chay CHINH cong do. `po` tro no sang mot BAN SAO cua `messages.po`.

    🔴 VI SAO CAN `po` — VA VI SAO BA LAN VA TRUOC DEU KHONG DU.

       Bon phep kiem duoi day tung ghi de `locale/en/LC_MESSAGES/messages.po`
       THAT roi tra ve trong `finally`. Cho do da va **ba lan**, moi lan mot
       trieu chung khac:

         26/08  `write_text` doi LF -> CRLF. Ban "khoi phuc" khac ban goc
                **10.465 dong**, va `git status` cua bat ky ai chay pytest bong
                co mot tep .po sua doi khong hieu tu dau. Sua: `write_bytes`.
         sau do Phai tra lai ca `st_mtime` (`os.utime`) — dau van tay cua gate
                doc mtime, nen mot lan ghi-lai-y-het van lam no in
                "CAY DA DOI TRONG LUC CHAY", tu vo hieu hoa ca luot gate.
         30/08  **Mat du lieu.** Hai luot gate chay song song:
                  A chup `goc` = ban day du, ghi fixture
                  B chup `goc` = **ban fixture cua A**, ghi tiep
                  A khoi phuc ban day du
                  B khoi phuc **ban fixture** de len  ->  con 81 byte
                Lan do xoa 78 muc dich cua mot phien khac, va `git status` VAN
                SACH — nen no khong nhin nhu mot su co, no nhin nhu chua ai lam
                gi ca.

    ⛔ Ba lan va deu dung ve ky thuat va deu la va TRIEU CHUNG. Goc chi co mot:
       **mot test ghi vao tep that thi khong the an toan** — khong voi hai tien
       trinh, khong voi mot tien trinh bi giet, khong voi mot nguoi khac dang
       sua cung tep do.
    """
    env = dict(os.environ)
    if po is not None:
        env["LTT_PO_FILE"] = str(po)
    return subprocess.run([sys.executable, f"tools/{cong_cu}", *doi_so],
                          cwd=cwd or GOC, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


def _po_ban_sao(tmp_path: pathlib.Path, them: str = "") -> pathlib.Path:
    """Ban sao cua `messages.po`, co the noi them fixture. KHONG cham tep that."""
    goc = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    ban = tmp_path / "messages.po"
    ban.write_bytes(goc.read_bytes() + them.encode("utf-8"))
    return ban


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


# ⛔ BA TEST DUOI DAY TUNG GHI DE `locale/en/LC_MESSAGES/messages.po`
#    THAT. **KHONG CON NUA tu 30/08** — chung chay tren ban sao qua
#    `_po_ban_sao()` + `LTT_PO_FILE`. Giu nguyen ca doan duoi vi no ghi
#    lai BA LAN VA truoc do, va ba lan ay deu dung ky thuat ma deu vá
#    TRIEU CHUNG — do moi la thu dang doc.
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


def test_chuoi_MOI_chua_dich_lam_do(tmp_path):
    # Ban sao. KHONG cham tep that.
    po = _po_ban_sao(tmp_path)
    goc = po.read_text(encoding="utf-8")
    po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                        'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                  encoding="utf-8")
    r = _chay("check_dich_thieu.py", po=po)
    assert r.returncode == 1, "them mot chuoi chua dich MOI ma van PASS"
    assert "MUC MOI CHUA DICH" in r.stdout


def test_HOAN_DOI_van_lam_do_du_TONG_KHONG_DOI(tmp_path):
    """🔴 Chinh la ca lam `check_so_test.py` bao PASS tren mot va cham that.

    Dich mot muc cu VA them mot muc moi trong cung mot luot: tong van dung 279.
    Mot moc dem SO LUONG se noi PASS. Moc dem TAP HOP phai noi FAIL.
    """
    # Ban sao. KHONG cham tep that.
    po = _po_ban_sao(tmp_path)
    goc = po.read_text(encoding="utf-8")
    moc = (GOC / "tools" / "check_dich_thieu.moc").read_text(encoding="utf-8")
    mot = next(d.split("\t", 1)[1]
               for d in moc.splitlines() if d.startswith("TRONG\t"))
    truoc = f'msgid "{mot}"\nmsgstr ""'
    if truoc not in goc:                       # muc nhieu dong — bo qua ca nay
        return
    moi = goc.replace(truoc, f'msgid "{mot}"\nmsgstr "TRANSLATED"', 1)
    po.write_text(moi + '\n#: server/templates/khong_co_that.html:1\n'
                        'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                  encoding="utf-8")
    r = _chay("check_dich_thieu.py", po=po)
    assert r.returncode == 1, (
        "hoan doi mot-doi-mot lot qua — moc dang dem SO LUONG chu khong "
        "phai TAP HOP")
    assert "MUC MOI CHUA DICH" in r.stdout


def test_accept_TU_CHOI_khi_con_muc_moi(tmp_path):
    """`--accept` phai la duong HA moc, khong duoc thanh duong im lang nang no."""
    # Ban sao. KHONG cham tep that.
    po = _po_ban_sao(tmp_path)
    goc = po.read_text(encoding="utf-8")
    moc_truoc = (GOC / "tools" / "check_dich_thieu.moc").read_bytes()
    moc_mtime = (GOC / "tools" / "check_dich_thieu.moc").stat().st_mtime_ns
    po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                        'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                  encoding="utf-8")
    r = _chay("check_dich_thieu.py", "--accept", po=po)
    assert r.returncode == 1, "--accept nang moc len duoc"
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


def test_khoi_tao_loai_KHONG_nuot_duoc_loai_khac(tmp_path):
    """`--khoi-tao-loai` la cua thoat duy nhat, va no phai bi chan hai phia.

    Mot cua thoat khong gioi han se thanh cach nguoi ta lam im lang moi thu
    khac — nen no chi nhan muc CUA DUNG MOT LOAI duoc goi ten.
    """
    # Bản sao cho `.po`. `.moc` vẫn là tệp thật — nó nhỏ, được trả lại
    # byte-exact, và quan trọng hơn: nó không phải thứ người khác đang sửa.
    po = _po_ban_sao(tmp_path)
    moc_tep = GOC / "tools" / "check_dich_thieu.moc"
    goc = po.read_bytes()
    moc = moc_tep.read_bytes()
    moc_mtime = moc_tep.stat().st_mtime_ns
    try:
        po.write_bytes(goc.rstrip(b"\n") + b'\n\nmsgid "Chuoi thu loai TRONG"\n'
                                           b'msgstr ""\n')
        r = _chay("check_dich_thieu.py", "--khoi-tao-loai", "VANG", po=po)
        assert r.returncode == 1, (
            "khoi tao loai VANG da nuot mot muc TRONG moi")
        assert "ngoai loai VANG" in (r.stdout + r.stderr)
    finally:
        moc_tep.write_bytes(moc)
        os.utime(moc_tep, ns=(moc_mtime, moc_mtime))


def test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT():
    """Bánh cóc — và nó đóng lại một chỗ đã vá **ba lần** mà chưa lần nào tới gốc.

    Bốn phép kiểm trong tệp này từng ghi đè `locale/en/LC_MESSAGES/messages.po`
    thật rồi trả về trong `finally`. Ba lần vá, ba triệu chứng khác nhau:

      26/08  `write_text` đổi LF → CRLF; bản "khôi phục" khác bản gốc **10.465
             dòng**, và `git status` của bất kỳ ai chạy pytest bỗng bẩn.
      sau đó Phải trả lại cả `st_mtime` — dấu vân tay của gate đọc mtime, nên
             một lần ghi-lại-y-hệt vẫn làm nó in *"CAY DA DOI TRONG LUC CHAY"*,
             tức một lượt gate tự vô hiệu hoá chính nó.
      30/08  **Mất dữ liệu.** 78 mục dịch của một phiên khác biến mất, và
             `git status` vẫn **sạch** — nên nó không nhìn như một sự cố, nó
             nhìn như chưa ai làm gì cả.

    ⚠️ Ở lần thứ ba có **ít nhất hai cơ chế** cùng cho ra đúng triệu chứng đó:
       hai lượt gate chạy song song (lượt B chụp `goc` = bản fixture của A rồi
       "khôi phục" đè lên), **và** một lần `git checkout` khôi phục tệp bẩn mà
       không tách được rác test khỏi công người khác. Không có bằng chứng tách
       được hai cái. ⇒ Đừng ghi nguyên nhân là một trong hai.

    ⭐ Điều đáng ghi là: **cả hai đều biến mất khi test thôi ghi vào tệp thật.**
       Đó là lý do bản vá này đúng cho cả hai mà không cần biết cái nào đã xảy
       ra. Ba lần vá trước đều đúng về kỹ thuật và đều vá **triệu chứng**.

    ⇒ Một test ghi vào tệp thật thì **không thể an toàn** — không với hai tiến
      trình, không với một tiến trình bị giết, không với một người khác đang
      sửa cùng tệp đó.
    """
    import ast

    van = pathlib.Path(__file__).read_text(encoding="utf-8")

    # ⭐ Chốt ĐƯỜNG DẪN, không chốt tên hàm ghi. `po.write_text(...)` bây giờ là
    #    hợp lệ — `po` là bản sao. Thứ không được phép là **chạm tới tệp thật**,
    #    và tệp thật chỉ được xuất hiện ở đúng một chỗ: hàm tạo bản sao.
    cho_phep = "_po_ban_sao"
    xau = []
    for nut in ast.walk(ast.parse(van)):
        if not isinstance(nut, ast.FunctionDef):
            continue
        # Bo qua chinh ham nay: no PHAI nhac duong dan de tim ra duong dan.
        # Mot banh coc bat chinh no thi khong dung duoc.
        if nut.name in (cho_phep,
                        "test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT"):
            continue
        for d in (ast.get_source_segment(van, nut) or "").splitlines():
            if 'GOC / "locale"' in d:
                xau.append(f"{nut.name}: {d.strip()}")
    assert not xau, (
        "Cac ham sau cham toi `messages.po` THAT:\n  " + "\n  ".join(xau)
        + f"\nChi `{cho_phep}()` duoc phep. Dung `_po_ban_sao(tmp_path)` roi "
          "`_chay(..., po=po)`.")
