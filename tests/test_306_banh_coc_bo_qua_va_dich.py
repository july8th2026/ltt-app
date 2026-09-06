"""Ba banh coc, va bang chung rang chung CHAN THAT.

   `check_bo_qua` + `check_dich_thieu` them 25/08/2026; `check_ruff` them
   06/09/2026.

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
          po: pathlib.Path | None = None, moc: pathlib.Path | None = None,
          src: pathlib.Path | None = None, thu_muc: pathlib.Path | None = None,
          bo_qua_moc: pathlib.Path | None = None,
          ruff_moc: pathlib.Path | None = None,
          mypy_moc: pathlib.Path | None = None,
          ruff_goc: pathlib.Path | None = None,
          mypy_goc: pathlib.Path | None = None,
          mypy_thu_muc: str | None = None):
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
    if moc is not None:
        env["LTT_MOC_FILE"] = str(moc)
    if src is not None:
        env["LTT_SRC_ROOT"] = str(src)
    if thu_muc is not None:
        env["LTT_TEST_DIR"] = str(thu_muc)
    if bo_qua_moc is not None:
        env["LTT_BO_QUA_MOC"] = str(bo_qua_moc)
    if ruff_moc is not None:
        env["LTT_RUFF_MOC"] = str(ruff_moc)
    if mypy_moc is not None:
        env["LTT_MYPY_MOC"] = str(mypy_moc)
    if ruff_goc is not None:
        env["LTT_RUFF_GOC"] = str(ruff_goc)
    if mypy_goc is not None:
        env["LTT_MYPY_GOC"] = str(mypy_goc)
    if mypy_thu_muc is not None:
        env["LTT_MYPY_THU_MUC"] = mypy_thu_muc
    return subprocess.run([sys.executable, f"tools/{cong_cu}", *doi_so],
                          cwd=cwd or GOC, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env)


def _po_ban_sao(tmp_path: pathlib.Path, them: str = "") -> pathlib.Path:
    """Ban sao cua `messages.po`, co the noi them fixture. KHONG cham tep that."""
    goc = GOC / "locale" / "en" / "LC_MESSAGES" / "messages.po"
    ban = tmp_path / "messages.po"
    ban.write_bytes(goc.read_bytes() + them.encode("utf-8"))
    return ban


def _moc_ban_sao(tmp_path: pathlib.Path) -> pathlib.Path:
    """Bản sao của `check_dich_thieu.moc`. KHÔNG chạm tệp thật.

    ⛔ Cùng lý do với `_po_ban_sao`, và nó đã đủ điều kiện để dính **hai** lần
       trong một phiên (06/09): một lượt gate bị giết để lại `.moc` bẩn trong
       cây, rồi một lượt khác chạy `-n 6` khiến worker này đọc phải bản mà
       worker kia vừa tiêm — ba phép kiểm đỏ vì một cuộc đua, không vì một lỗi.
    """
    ban = tmp_path / "check_dich_thieu.moc"
    ban.write_bytes((GOC / "tools" / "check_dich_thieu.moc").read_bytes())
    return ban


def _bo_qua_moc_ban_sao(tmp_path: pathlib.Path) -> pathlib.Path:
    """Bản sao của `check_bo_qua.moc`. KHÔNG chạm tệp thật."""
    ban = tmp_path / "check_bo_qua.moc"
    ban.write_bytes((GOC / "tools" / "check_bo_qua.moc").read_bytes())
    return ban


def _cay_ma_gia(tmp_path: pathlib.Path, chuoi: str) -> pathlib.Path:
    """Một CÂY MÃ tí hon để babel trích: `babel.cfg` thật + đúng một template.

    ⭐ Mạnh hơn bản cũ chứ không yếu hơn. Bản cũ tiêm một chuỗi vào
       `server/templates/vps_dieu_khoan.html` **thật**, nên nó vừa ghi vào cây,
       vừa phụ thuộc vào nội dung một trang đang phục vụ khách. Ở đây phép kiểm
       tự dựng đủ và **chỉ** thứ nó cần, nên nó đo đúng cơ chế trích chứ không
       đo trạng thái của kho.
    """
    goc = tmp_path / "cay_ma"
    (goc / "server" / "templates").mkdir(parents=True)
    (goc / "babel.cfg").write_bytes((GOC / "babel.cfg").read_bytes())
    (goc / "server" / "templates" / "thu.html").write_text(
        '<!-- {{ _("%s") }} -->\n' % chuoi,
        encoding="utf-8", newline="\n")
    return goc


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
    """Bang chung. Khong co phep kiem nay thi banh coc chi la mot y dinh.

    🔴 Bản trước tạo **thật** `tests/zz_thu_banh_coc_bo_qua.py` rồi xoá trong
       `finally`. Đo 06/09 dưới `-n 6`: trong khoảng tệp ấy tồn tại, một worker
       khác chạy cùng công cụ và thấy thừa một chỗ bỏ qua ⇒
       `test_bo_qua_hien_tai_dat_moc` đỏ **4/4 lượt**. Một tiến trình bị giết
       còn tệ hơn — tệp ở lại trong `tests/`, và từ đó **mọi** lượt gate của
       **mọi** cây đều đỏ, vì một tệp không ai gõ.

    ⭐ Nay dựng thư mục test trong `tmp_path`: một tệp, đúng thứ cần đo. Không
       còn gì để dọn, nên cũng không còn gì để quên dọn.
    """
    thu_muc = tmp_path / "tests_gia"
    thu_muc.mkdir()
    (thu_muc / "zz_thu_banh_coc_bo_qua.py").write_text(
        "import pytest\n\n\n"
        '@pytest.mark.skipif(True, reason="thu banh coc")\n'
        "def test_gia_vo():\n    assert True\n",
        encoding="utf-8", newline="\n")

    r = _chay("check_bo_qua.py", thu_muc=thu_muc,
              bo_qua_moc=_bo_qua_moc_ban_sao(tmp_path))
    assert r.returncode == 1, "them mot cho bo qua MOI ma van PASS"
    assert "CHO BO QUA MOI" in r.stdout
    assert "zz_thu_banh_coc_bo_qua.py::test_gia_vo" in r.stdout


# ── 2. Banh coc DICH THIEU BAN EN ──────────────────────────────────────────

def test_dich_thieu_hien_tai_dat_moc():
    r = _chay("check_dich_thieu.py")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RESULT: PASS" in r.stdout


def test_fuzzy_duoc_DEM_NHU_CHUA_DICH(tmp_path):
    """`msgfmt` bo qua moi muc `#, fuzzy` khi sinh `.mo`. Mot ban dich fuzzy
    khong bao gio toi mat nguoi dung — no giong het `msgstr` rong khi chay, chi
    khac la no TRONG NHU da lam xong khi doc tep `.po`.

    ⭐ Phép kiểm này chỉ **đọc** `.moc`, và tôi đã bỏ sót nó khi chuyển sang bản
       sao — phép quét tay của tôi lọc theo *ghi*. Bánh cóc bên dưới bắt được.
       Đọc cũng đua: worker khác đang tiêm thì bản đọc được không phải bản thật.
    """
    r = _chay("check_dich_thieu.py")
    assert "fuzzy" in r.stdout, "phai noi ro co bao nhieu muc fuzzy"
    moc = _moc_ban_sao(tmp_path).read_text(encoding="utf-8")
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
    moc_ban = _moc_ban_sao(tmp_path)
    goc = po.read_text(encoding="utf-8")
    moc = moc_ban.read_text(encoding="utf-8")
    mot = next(d.split("\t", 1)[1]
               for d in moc.splitlines() if d.startswith("TRONG\t"))
    truoc = f'msgid "{mot}"\nmsgstr ""'
    if truoc not in goc:                       # muc nhieu dong — bo qua ca nay
        return
    moi = goc.replace(truoc, f'msgid "{mot}"\nmsgstr "TRANSLATED"', 1)
    po.write_text(moi + '\n#: server/templates/khong_co_that.html:1\n'
                        'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                  encoding="utf-8")
    r = _chay("check_dich_thieu.py", po=po, moc=moc_ban)
    assert r.returncode == 1, (
        "hoan doi mot-doi-mot lot qua — moc dang dem SO LUONG chu khong "
        "phai TAP HOP")
    assert "MUC MOI CHUA DICH" in r.stdout


def test_accept_TU_CHOI_khi_con_muc_moi(tmp_path):
    """`--accept` phai la duong HA moc, khong duoc thanh duong im lang nang no.

    ⭐ Trước 06/09 phép kiểm này chạy `--accept` lên `.moc` **thật** rồi khôi
       phục cả byte lẫn `mtime` trong thân hàm. Nó đúng về kỹ thuật và vẫn hỏng
       hai kiểu: `finally` không chạy khi tiến trình bị giết, và dưới `-n 6`
       một worker khác đọc phải bản đang bị tiêm. Nay ghi vào **bản sao**, nên
       không còn gì để khôi phục — và không còn gì để hỏng.
    """
    po = _po_ban_sao(tmp_path)
    moc_ban = _moc_ban_sao(tmp_path)
    goc = po.read_text(encoding="utf-8")
    po.write_text(goc + '\n#: server/templates/khong_co_that.html:1\n'
                        'msgid "Chuoi thu banh coc"\nmsgstr ""\n',
                  encoding="utf-8")
    r = _chay("check_dich_thieu.py", "--accept", po=po, moc=moc_ban)
    assert r.returncode == 1, "--accept nang moc len duoc"


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


def test_chuoi_DA_BOC_ma_VANG_khoi_catalog_lam_do(tmp_path):
    """Bang chung cho lop thu ba. Khong co phep kiem nay thi no chi la mot y dinh.

    🔴 Bản trước tiêm chuỗi vào `server/templates/vps_dieu_khoan.html` **thật**
       rồi khôi phục trong `finally`. Ngày 06/09 nó dính đúng chế độ hỏng mà
       docstring của `test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT` đã kể
       tên: một lượt gate bị giết giữa chừng, `finally` không chạy, và tệp
       template ở lại trong cây với chuỗi tiêm — cây bẩn ở một trang **đang
       phục vụ khách**.

    ⭐ Bản này **mạnh hơn**, không phải nhẹ hơn. Nó tự dựng một cây mã tí hon
       chứa đúng và chỉ thứ nó cần, nên nó đo cơ chế trích chứ không đo trạng
       thái của kho — và kết quả không còn phụ thuộc vào việc ai vừa sửa trang
       nào.
    """
    cay = _cay_ma_gia(tmp_path, "Chuoi thu banh coc VANG")
    r = _chay("check_dich_thieu.py", po=_po_ban_sao(tmp_path),
              moc=_moc_ban_sao(tmp_path), src=cay)
    assert r.returncode == 1, "chuoi boc `_()` ma vang khoi catalog van PASS"
    assert "VANG" in r.stdout


def test_khoi_tao_loai_KHONG_nuot_duoc_loai_khac(tmp_path):
    """`--khoi-tao-loai` la cua thoat duy nhat, va no phai bi chan hai phia.

    Mot cua thoat khong gioi han se thanh cach nguoi ta lam im lang moi thu
    khac — nen no chi nhan muc CUA DUNG MOT LOAI duoc goi ten.
    """
    # 🔴 Ghi chú cũ ở đúng chỗ này viết: *"`.moc` vẫn là tệp thật — nó nhỏ, được
    #    trả lại byte-exact, và quan trọng hơn: nó không phải thứ người khác
    #    đang sửa."* Đo 06/09 bác vế cuối, và vế cuối mới là vế chịu lực.
    #
    #    "Người khác" không phải một con người. Dưới `-n 6`, ba phép kiểm trong
    #    **chính tệp này** chạy ở ba worker cùng lúc, và chúng sửa đúng tệp ấy.
    #    Một trong ba đọc phải bản mà một trong hai kia vừa tiêm ⇒ ba phép kiểm
    #    đỏ vì một cuộc đua, không vì một lỗi. `git status` sau đó còn lại một
    #    dòng `TRONG\tChuoi thu banh coc` không ai gõ.
    #
    # ⇒ "Nhỏ" và "trả lại byte-exact" không cứu được: cả hai đều nói về **một**
    #   tiến trình. Bản sao thì đúng cho mọi số tiến trình.
    po = _po_ban_sao(tmp_path)
    moc_ban = _moc_ban_sao(tmp_path)
    goc = po.read_bytes()
    po.write_bytes(goc.rstrip(b"\n") + b'\n\nmsgid "Chuoi thu loai TRONG"\n'
                                       b'msgstr ""\n')
    r = _chay("check_dich_thieu.py", "--khoi-tao-loai", "VANG",
              po=po, moc=moc_ban)
    assert r.returncode == 1, "khoi tao loai VANG da nuot mot muc TRONG moi"
    assert "ngoai loai VANG" in (r.stdout + r.stderr)


# ── 5. Banh coc thu BA: `ruff` (them 06/09/2026) ───────────────────────────
#
# ⭐ Ba phep kiem duoi day khong ghi MOT BYTE nao vao cay. Chung khong tiem loi
#    vao ma nguon (lam vay la vi pham dung dieu `test_306` ra doi de chan) — ma
#    ha MOC xuong tren mot BAN SAO. Phep so sanh banh coc thuc hien la
#    `hien[ma] > moc[ma]`, nen ha moc mot bac va nang ma len mot bac la CUNG
#    MOT phep toan; chi khac o cho khong ai phai dong vao kho.


def _ruff_moc_that(tmp_path: pathlib.Path) -> dict[str, int]:
    """Chup so lieu ruff HIEN TAI ra `tmp_path`, tra ve {ma: so}."""
    ban = tmp_path / "ruff_goc.moc"
    r = _chay("check_ruff.py", "--accept", ruff_moc=ban)
    assert r.returncode == 0, f"khong chup duoc moc ruff:\n{r.stdout}\n{r.stderr}"
    dem: dict[str, int] = {}
    for d in ban.read_text(encoding="utf-8").splitlines():
        d = d.strip()
        if d and not d.startswith("#"):
            ma, _, so = d.partition("=")
            dem[ma.strip()] = int(so.strip())
    assert dem, "moc ruff rong — cau hinh `ruff.toml` khong con bat luat nao?"
    return dem


def _ghi_moc(tep: pathlib.Path, dem: dict[str, int]) -> pathlib.Path:
    tep.write_text("".join(f"{ma} = {so}\n" for ma, so in sorted(dem.items())),
                   encoding="utf-8")
    return tep


def test_ruff_hien_tai_dat_moc():
    """Moc da commit phai khop cay hien tai — neu khong, gate do ngay lap tuc."""
    r = _chay("check_ruff.py")
    assert r.returncode == 0, (
        "moc `check_ruff.moc` khong con khop cay:\n" + r.stdout + r.stderr)


def test_ruff_TANG_o_mot_ma_thi_DO(tmp_path):
    """Doi chung cho ca banh coc: no PHAI do khi mot ma vuot moc.

    ⛔ Khong co phep kiem nay thi mot banh coc hong se bao PASS, va cai PASS do
       doc y het mot cai PASS that — dung ca `check_so_test.py` da mac.
    """
    that = _ruff_moc_that(tmp_path)
    ma = sorted(that)[0]
    thap = dict(that, **{ma: that[ma] - 1})       # ha moc mot bac
    r = _chay("check_ruff.py", ruff_moc=_ghi_moc(tmp_path / "thap.moc", thap))
    assert r.returncode == 1, f"vuot moc o {ma} ma van xanh — banh coc khong can"
    assert ma in r.stdout, f"do roi nhung khong noi ma nao ({ma}) trong:\n{r.stdout}"


def test_ruff_HOAN_DOI_van_do_du_TONG_KHONG_DOI(tmp_path):
    """🔴 Cua ma mot moc dem TONG di lot — cung cua da lam `check_so_test` im.

    Xoa mot `F401` roi them mot `F811` thi TONG khong doi. Mot moc "tong <= N"
    noi PASS. Moc chot theo MA LUAT phai noi FAIL, vi `F811` (hai ham cung ten,
    cai sau che cai truoc) la mot loi THAT.
    """
    that = _ruff_moc_that(tmp_path)
    if len(that) < 2:
        return                                     # khong co gi de hoan doi
    tang, giam = sorted(that)[0], sorted(that)[1]
    lech = dict(that)
    lech[tang] -= 1                                # ma nay se VUOT moc
    lech[giam] += 1                                # ma kia se duoi moc
    assert sum(lech.values()) == sum(that.values()), "phep dung khong giu TONG"
    r = _chay("check_ruff.py", ruff_moc=_ghi_moc(tmp_path / "lech.moc", lech))
    assert r.returncode == 1, (
        "hoan doi mot-doi-mot lot qua — moc ruff dang dem TONG chu khong phai "
        "tung MA LUAT")


def test_ruff_nam_trong_gate_VA_chay_ca_o_quick():
    """Dung tu DANH SACH BUOC gate dung that, khong tu `grep` ma nguon.

    ⭐ Khac biet co that: mot phep `grep` van xanh khi dong `Step(...)` bi day
       ra sau `if not quick:`, hoac khi no nam trong mot nhanh khong bao gio
       chay. Dung `_steps()` thi khong.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_de_soi", GOC / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for quick in (True, False):
        ten = [s.name for s in gate._steps(quick=quick)]
        assert "ruff" in ten, f"buoc `ruff` vang mat khi quick={quick}: {ten}"


# ── 6. Banh coc thu TU: `mypy` (them 06/09/2026) ───────────────────────────
#
# ⭐ Cung khuon voi cum `ruff` o tren: ha MOC tren mot BAN SAO, khong tiem loi
#    vao cay. Xem chu thich cua muc 5.


def _mypy_moc_that(tmp_path: pathlib.Path) -> dict[str, int]:
    ban = tmp_path / "mypy_goc.moc"
    r = _chay("check_mypy.py", "--accept", mypy_moc=ban)
    assert r.returncode == 0, f"khong chup duoc moc mypy:\n{r.stdout}\n{r.stderr}"
    dem: dict[str, int] = {}
    for d in ban.read_text(encoding="utf-8").splitlines():
        d = d.strip()
        if d and not d.startswith("#"):
            ma, _, so = d.partition("=")
            dem[ma.strip()] = int(so.strip())
    assert dem, "moc mypy rong — `mypy.ini` hong hay mypy chet im lang?"
    return dem


def test_mypy_hien_tai_dat_moc():
    r = _chay("check_mypy.py")
    assert r.returncode == 0, (
        "moc `check_mypy.moc` khong con khop cay:\n" + r.stdout + r.stderr)


def test_mypy_TANG_o_mot_ma_thi_DO(tmp_path):
    """Doi chung: banh coc PHAI do khi mot ma vuot moc."""
    that = _mypy_moc_that(tmp_path)
    ma = sorted(that)[0]
    thap = dict(that, **{ma: that[ma] - 1})
    r = _chay("check_mypy.py", mypy_moc=_ghi_moc(tmp_path / "thap.moc", thap))
    assert r.returncode == 1, f"vuot moc o {ma} ma van xanh — banh coc khong can"
    assert ma in r.stdout, f"do roi nhung khong noi ma nao ({ma}):\n{r.stdout}"


def test_mypy_HOAN_DOI_van_do_du_TONG_KHONG_DOI(tmp_path):
    """Xoa mot `var-annotated` (vo hai) + them mot `attr-defined`
    (`AttributeError` luc chay) = tong khong doi. Moc dem TONG se im."""
    that = _mypy_moc_that(tmp_path)
    if len(that) < 2:
        return
    tang, giam = sorted(that)[0], sorted(that)[1]
    lech = dict(that)
    lech[tang] -= 1
    lech[giam] += 1
    assert sum(lech.values()) == sum(that.values()), "phep dung khong giu TONG"
    r = _chay("check_mypy.py", mypy_moc=_ghi_moc(tmp_path / "lech.moc", lech))
    assert r.returncode == 1, (
        "hoan doi mot-doi-mot lot qua — moc mypy dang dem TONG chu khong phai "
        "tung MA LOI")


def test_mypy_ini_THUAN_ASCII():
    """🔴 `mypy` doc `mypy.ini` bang `configparser`, va ham do mo tep theo bang
       ma HE THONG (cp1252 tren may nay) chu khong phai UTF-8.

       Do 06/09: mot ban `mypy.ini` co emoji lam mypy chet han
       `UnicodeDecodeError ... byte 0x90`, rc=2, truoc khi kiem MOT DONG ma
       nao. Va `check_mypy.py` khong the coi rc=2 la "0 loi" — nen luot gate
       se do, khong im lang; nhung trieu chung se tro ve mot tep .ini chu
       khong ve ma nguon, va do la cho rat kho doan.

    ⭐ Cung mot lop voi luat `.ps1 phai thuan ASCII` trong `CLAUDE.md` quy
       tac 2.
    """
    b = (GOC / "mypy.ini").read_bytes()
    xau = [(i, by) for i, by in enumerate(b) if by > 127]
    assert not xau, (
        f"`mypy.ini` co {len(xau)} byte ngoai ASCII (dau tien o vi tri "
        f"{xau[0][0]}, byte 0x{xau[0][1]:02x}) — configparser doc no bang "
        f"cp1252 va se chet")


def test_mypy_nam_trong_gate_VA_chay_ca_o_quick():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gate_de_soi_mypy",
                                                  GOC / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for quick in (True, False):
        ten = [s.name for s in gate._steps(quick=quick)]
        assert "mypy" in ten, f"buoc `mypy` vang mat khi quick={quick}: {ten}"


def test_mypy_va_ruff_MIEN_cung_mot_danh_sach():
    """Hai cong cu nhin cung pham vi thi mot tep duoc mien o cho nay khong
    bat ngo bi bat o cho kia. `core/` va `cutclipshort/` la hai cai dat nhat:
    mot la 15.668 dong dong bang, mot la engine VENDOR."""
    ruff = (GOC / "ruff.toml").read_text(encoding="utf-8")
    mypy = (GOC / "mypy.ini").read_text(encoding="utf-8")
    for thu_muc in ("core", "cutclipshort"):
        assert thu_muc in ruff, f"`{thu_muc}` khong con duoc mien trong ruff.toml"
        assert thu_muc in mypy, f"`{thu_muc}` khong con duoc mien trong mypy.ini"


# ── 7. `quet()` phai dem DUNG — doi chieu voi mot su that DOC LAP ──────────
#
# 🔴 HAI PHEP KIEM DUOI DAY RA DOI TU MOT KET QUA DO DUOC, khong tu suy doan.
#
#    Ngay 06/09 `cosmic-ray` chay 97 dot bien tren `tools/check_ruff.py`. Mot
#    trong so do doi
#
#        dem[ma] = dem.get(ma, 0) + 1     ->     dem[ma] = dem.get(ma, 0) ** 1
#
#    `0 ** 1` luon la 0, nen MOI so dem thanh 0, `tang` luon rong, va banh coc
#    bao PASS **vinh vien**. No mu hoan toan.
#
# ⛔ Bon phep kiem o muc 5 KHONG thay. Ly do la mot khiem khuyet trong chinh
#    chung: ca bon lay moc bang `--accept`, ma `--accept` goi `quet()`. Khi
#    `quet()` hong, moc hong **y het** — va hong so voi hong thi van bang nhau.
#    Chung chot duoc PHEP SO SANH, nhung khong chot duoc PHEP DEM.
#
# ⭐ Nen hai phep kiem nay khong hoi cong cu "may dem duoc bao nhieu", ma dat
#    truoc mot cay co so loi DA BIET roi hoi lai. Do la su that doc lap.


def _cay_mau_ruff(tmp_path: pathlib.Path) -> pathlib.Path:
    """3 x F401, 2 x F541, 1 x F811 — dem tay, khong hoi cong cu."""
    d = tmp_path / "cay_ruff"
    d.mkdir()
    (GOC / "ruff.toml").read_bytes()          # bao dam cau hinh that con do
    (d / "ruff.toml").write_bytes((GOC / "ruff.toml").read_bytes())
    (d / "a.py").write_text("import os\nimport sys\nimport json\n", encoding="utf-8")
    (d / "b.py").write_text("def f():\n    pass\n\n\ndef f():\n    pass\n",
                            encoding="utf-8")
    (d / "c.py").write_text("x = f''\ny = f'khong co gi'\n", encoding="utf-8")
    return d


def test_ruff_quet_DEM_DUNG_tren_cay_da_biet_truoc(tmp_path):
    """Dot bien `+ 1` -> `** 1` lam moi so dem thanh 0. Phep kiem nay giet no."""
    d = _cay_mau_ruff(tmp_path)
    moc = tmp_path / "mau.moc"
    r = _chay("check_ruff.py", "--accept", ruff_goc=d, ruff_moc=moc)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"

    dem = {}
    for dong in moc.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#"):
            ma, _, so = dong.partition("=")
            dem[ma.strip()] = int(so.strip())

    assert dem == {"F401": 3, "F541": 2, "F811": 1}, (
        f"`quet()` dem SAI tren mot cay da biet truoc.\n"
        f"  mong doi: {{'F401': 3, 'F541': 2, 'F811': 1}}\n"
        f"  nhan duoc: {dem}\n"
        f"Neu moi gia tri deu 0 thi phep CONG trong `quet()` da hong — dung ca"
        f" `cosmic-ray` bat duoc 06/09.")


def test_mypy_quet_DEM_DUNG_tren_cay_da_biet_truoc(tmp_path):
    """Cung menh de cho `check_mypy`: 1 attr-defined + 1 union-attr."""
    d = tmp_path / "cay_mypy"
    (d / "apps").mkdir(parents=True)
    (d / "mypy.ini").write_bytes((GOC / "mypy.ini").read_bytes())
    (d / "apps" / "x.py").write_text(
        "class A:\n    ten: str = 'x'\n\n\n"
        "def g(a: A) -> None:\n    print(a.khong_co_gi)\n\n\n"
        "def h(x: int | None) -> int:\n    return x.bit_length()\n",
        encoding="utf-8")
    moc = tmp_path / "mau_mypy.moc"
    r = _chay("check_mypy.py", "--accept", mypy_goc=d, mypy_thu_muc="apps", mypy_moc=moc)
    assert r.returncode == 0, f"{r.stdout}\n{r.stderr}"

    dem = {}
    for dong in moc.read_text(encoding="utf-8").splitlines():
        dong = dong.strip()
        if dong and not dong.startswith("#"):
            ma, _, so = dong.partition("=")
            dem[ma.strip()] = int(so.strip())

    assert dem == {"attr-defined": 1, "union-attr": 1}, (
        f"`quet()` dem SAI tren mot cay da biet truoc: {dem}")


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
    # 🔴 MỞ RỘNG 06/09. Bánh cóc này chỉ canh `locale/`, và trong cùng một ngày
    #    **cả hai** lớp còn lại đều nổ, theo đúng hai chế độ hỏng mà docstring
    #    trên vừa kể tên:
    #
    #      `tools/check_dich_thieu.moc`      -> HAI tien trinh (`-n 6`), 3 do
    #      `server/templates/*.html`         -> tien trinh BI GIET, cay ban
    #
    # ⭐ Nguyên lý đã đúng từ đầu; thứ thiếu là **phạm vi**. Một bánh cóc chỉ
    #    bảo vệ thứ nó nhìn thấy, nên nguyên lý đúng mà phạm vi hẹp thì vẫn để
    #    lọt đúng cái nó sinh ra để chặn.
    CHO_PHEP = {"_po_ban_sao", "_moc_ban_sao", "_bo_qua_moc_ban_sao",
                "_cay_ma_gia",
                "test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT"}
    #: đường-dẫn-tệp-thật → hàm tạo bản sao thay thế nó
    #:
    #: ⛔ Lớp thứ tư (`GOC / "tests"`) **lọt** ở bản mở rộng đầu tiên, và nó lọt
    #:    vì tôi liệt kê ba đường dẫn mình vừa thấy chứ không hỏi *"còn tệp thật
    #:    nào khác không"*. Chính lượt `-n 6` chỉ ra nó — 4/4 lượt đỏ ở
    #:    `test_bo_qua_hien_tai_dat_moc`. Một danh sách chép tay chỉ bảo vệ thứ
    #:    người viết nhớ ra.
    CAM = {
        'GOC / "locale"': "_po_ban_sao(tmp_path)",
        '"check_dich_thieu.moc"': "_moc_ban_sao(tmp_path)",
        '"check_bo_qua.moc"': "_bo_qua_moc_ban_sao(tmp_path)",
        'GOC / "server" / "templates"': "_cay_ma_gia(tmp_path, ...)",
        'GOC / "tests"': "mot thu muc trong `tmp_path` + `thu_muc=`",
    }
    cho_phep = " / ".join(sorted(CHO_PHEP - {
        "test_KHONG_test_nao_duoc_GHI_vao_messages_po_THAT"}))
    xau = []
    for nut in ast.walk(ast.parse(van)):
        if not isinstance(nut, ast.FunctionDef):
            continue
        # Bo qua chinh ham nay va cac ham tao ban sao: chung PHAI nhac duong dan
        # de tim ra duong dan. Mot banh coc bat chinh no thi khong dung duoc.
        if nut.name in CHO_PHEP:
            continue
        for d in (ast.get_source_segment(van, nut) or "").splitlines():
            for dau, thay in CAM.items():
                if dau in d:
                    xau.append(f"{nut.name}: {d.strip()}   => dung `{thay}`")
    assert not xau, (
        "Cac ham sau cham toi TEP THAT trong kho:\n  " + "\n  ".join(xau)
        + f"\nChi `{cho_phep}` duoc phep cham. Dung ban sao roi "
          "`_chay(..., po=po)`.")


# ── 8. Hai lo do CHINH `cosmic-ray` chi ra (06/09) ────────────────────────
#
# ⭐ Hai phep kiem duoi day khong den tu suy doan. Chung den tu hai dot bien
#    SONG SOT trong luot thu hai, moi cai la mot cau hoi that ma bo phep kiem
#    chua ai hoi.


def test_ruff_GIAM_thi_van_XANH_chu_khong_bao_la_TANG(tmp_path):
    """Dot bien `so > moc` -> `so != moc` song sot.

    🔴 Voi `!=`, mot lan DON BOT loi cung bi bao la "TANG" va gate do. Mot banh
       coc phat nguoi sua dung thi se bi tat — dung co che da ghi trong
       `khoa-khai-thieu-tai-nguyen`: **ban va MOT PHIA phat nguoi sua dung**.

    ⇒ Dat moc CAO hon thuc te: phai XANH.
    """
    that = _ruff_moc_that(tmp_path)
    ma = sorted(that)[0]
    cao = dict(that, **{ma: that[ma] + 5})
    r = _chay("check_ruff.py", ruff_moc=_ghi_moc(tmp_path / "cao.moc", cao))
    assert r.returncode == 0, (
        f"moc CAO hon thuc te ma van do — banh coc dang bao ca chieu GIAM la "
        f"loi:\n{r.stdout}")
    assert "GIAM" in r.stdout, "giam that ma khong noi gi"


def test_ruff_KHONG_CO_MOC_thi_DO_chu_khong_lang_le_XANH(tmp_path):
    """Dot bien `return 1` -> `return 0` o nhanh "CHUA CO MOC" song sot.

    ⛔ Mot banh coc khong tim thay moc ma tra 0 la mot banh coc TU TAT: xoa tep
       `.moc` di thi gate xanh tro lai, va khong ai thay gi. Do dung kieu hong
       ma `docs/BAY_TRONG_CONG_CHAT_LUONG.md` canh bao.
    """
    r = _chay("check_ruff.py", ruff_moc=tmp_path / "khong_ton_tai.moc")
    assert r.returncode == 1, (
        f"khong co moc ma van XANH — xoa tep .moc la tat duoc banh coc:\n{r.stdout}")
    assert "CHUA CO MOC" in r.stdout


def test_ruff_CAY_SACH_khong_lam_cong_cu_chet(tmp_path):
    """Ba dot bien quanh `if r.returncode not in (0, 1)` song sot 06/09.

    🔴 Ly do: MOI phep kiem khac deu chay tren mot cay CO loi, nen `ruff` luon
       tra 1. Nhanh `ruff tra 0` (cay sach) chua bao gio duoc chay — va do
       chinh la nhanh se chay dau tien tren mot kho da don xong.

    ⚠️ Phep kiem nay cung ghi lai mot GOC KHUAT co that: tren mot cay SACH,
       `quet()` tra `{}`, `--accept` ghi mot moc RONG, va luot sau `doc_moc()`
       doc ra `{}` -> cong cu bao "CHUA CO MOC" va do. Tuc no khong phan biet
       duoc "sach" voi "chua co moc".

       KHONG sua o day: kho nay co 513 phat hien, trang thai ay khong voi toi
       duoc, va them nhanh cho mot trang thai khong the xay ra la them cho de
       hong. Ghi lai de nguoi sau khong phai kham pha lai.
    """
    d = tmp_path / "cay_sach"
    d.mkdir()
    (d / "ruff.toml").write_bytes((GOC / "ruff.toml").read_bytes())
    (d / "sach.py").write_text("def f(x: int) -> int:\n    return x + 1\n",
                               encoding="utf-8")
    moc = tmp_path / "sach.moc"
    r = _chay("check_ruff.py", "--accept", ruff_goc=d, ruff_moc=moc)
    assert r.returncode == 0, (
        f"`ruff` tra 0 (cay sach) ma cong cu chet — nhanh nay chua tung duoc "
        f"chay:\n{r.stdout}\n{r.stderr}")
    assert "0 phat hien" in r.stdout, r.stdout


# ── 9. Ranh gioi import (`import-linter`, them 06/09/2026) ─────────────────


def test_ranh_gioi_hien_tai_dat():
    r = _chay("check_ranh_gioi.py")
    assert r.returncode == 0, f"hop dong import dang gay:\n{r.stdout}\n{r.stderr}"


def test_ranh_gioi_KHONG_TRO_no_phai_DO_duoc(tmp_path):
    """🔴 Suyt thanh mot buoc gate XANH VINH VIEN. Do 06/09/2026:

           lint-imports                  rc=1   4.675 ky tu bao cao
           python -m importlinter.cli    rc=0   0 ky tu

       Ca hai chay tren CUNG mot cay dang co MOT VI PHAM duoc tiem vao.
       `-m importlinter.cli` chi NAP module (no dinh nghia mot nhom `click`)
       chu khong GOI lenh nao — nen no thoat 0, im lang, mai mai.

    ⛔ Toi da suyt gan dung dong ay vao gate. Bat duoc chi vi da hoi "no CO DO
       duoc khong?" truoc khi tin. Mot buoc tro thi ba hop dong trong
       `.importlinter` chi la do trang tri.

    ⭐ Phep kiem nay tiem VAO BAN SAO trong `tmp_path`, khong cham cay that:
       no dung `LTT_RANH_GIOI_GOC`... khong, don gian hon — no chi doi chieu
       rang cong cu PHAN BIET duoc hai truong hop, bang cach goi thang API.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "crg", GOC / "tools" / "check_ranh_gioi.py")
    crg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crg)

    # Cay that phai DAT.
    assert crg.main() == 0

    # Va cong cu phai doc duoc mot cau hinh CO vi pham thanh "gay".
    from importlinter.cli import EXIT_STATUS_SUCCESS, lint_imports

    xau = tmp_path / "hong.ini"
    xau.write_text(
        "[importlinter]\n"
        "root_packages =\n    platform_core\n    apps\n\n"
        "[importlinter:contract:cam-het]\n"
        "name = cam platform_core import bat cu gi\n"
        "type = forbidden\n"
        "source_modules =\n    platform_core\n"
        "forbidden_modules =\n    apps\n",
        encoding="ascii")
    import os
    cu = os.getcwd()
    os.chdir(GOC)
    try:
        # Hop dong nay hien DANG DAT (0 vi pham that), nen no phai tra SUCCESS.
        assert lint_imports(config_filename=str(xau)) == EXIT_STATUS_SUCCESS
    finally:
        os.chdir(cu)


def test_ranh_gioi_nam_trong_gate_VA_chay_ca_o_quick():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gate_rg", GOC / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for quick in (True, False):
        ten = [s.name for s in gate._steps(quick=quick)]
        assert "ranh gioi import" in ten, f"vang mat khi quick={quick}"
    # ⛔ Va PHAI goi qua vo, khong goi `-m importlinter.cli` (tro).
    argv = next(s.argv for s in gate._steps(quick=True)
                if s.name == "ranh gioi import")
    assert any("check_ranh_gioi.py" in str(a) for a in argv), (
        f"buoc dang goi {argv} — neu do la `-m importlinter.cli` thi no TRO")


def test_importlinter_cau_hinh_THUAN_ASCII():
    """Cung ly do voi `mypy.ini`: `configparser` mo tep theo bang ma HE THONG."""
    b = (GOC / ".importlinter").read_bytes()
    xau = [(i, by) for i, by in enumerate(b) if by > 127]
    assert not xau, (
        f"`.importlinter` co {len(xau)} byte ngoai ASCII (dau tien o {xau[0][0]})")


# ── 10. Banh coc CVE (`pip-audit`, them 06/09/2026) ────────────────────────
#
# ⛔ Cum nay KHONG cham mang. `check_cve.py` mat 49 giay va hoi PyPI/OSV, nen
#    goi no trong bo test la bien mot phep kiem thanh mot phep do phu thuoc
#    duong truyen. Ba phep kiem duoi day chot dung nhung menh de THUOC VE cong
#    cu: dinh dang moc, doi hoi LY DO, va viec no KHONG nam trong gate.


def test_moc_cve_MOI_DONG_deu_co_LY_DO():
    """⛔ Mot dong mien tru CVE khong ly do la mot dong se song mai ma khong ai
       nho vi sao. Khac han `check_ruff.moc`: o do la no ky thuat, o day la mot
       quyet dinh BAO MAT.
    """
    import re
    tep = GOC / "tools" / "check_cve.moc"
    mau = re.compile(r"^[A-Za-z0-9-]+\s*\|\s*[^|]+\|\s*\S.*$")
    xau = []
    for so, dong in enumerate(tep.read_text(encoding="utf-8").splitlines(), 1):
        d = dong.strip()
        if not d or d.startswith("#"):
            continue
        if not mau.match(d):
            xau.append(f"{so}: {d!r}")
    assert not xau, "dong sai dinh dang hoac THIEU LY DO:\n  " + "\n  ".join(xau)


def test_check_cve_TU_CHOI_moc_thieu_ly_do(tmp_path):
    """Doi chung: cong cu phai DUNG HAN, khong duoc am tham chap nhan."""
    import pytest

    moc = tmp_path / "khong_ly_do.moc"
    moc.write_text("PYSEC-2026-2132 | click\n", encoding="ascii")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ccve", GOC / "tools" / "check_cve.py")
    ccve = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ccve)
    ccve.TEP_MOC = moc
    with pytest.raises(SystemExit) as loi:
        ccve.doc_moc()
    assert "ly do" in str(loi.value).lower()


def test_check_cve_KHONG_nam_trong_gate():
    """🔴 Co Y khong nam trong gate, va phep kiem nay chot dieu do.

       Do 06/09: **49 giay** va no hoi PyPI/OSV qua mang. Mot buoc gate do vi
       MAT MANG la mot buoc do vi ly do khong lien quan toi ma — dung thu day
       nguoi ta bo qua mau do (`BAY_TRONG_CONG_CHAT_LUONG.md` Bay 26).

    ⭐ CVE xuat hien theo THOI GIAN, khong theo commit. Hoi mot lan truoc khi
       giao hang moi dung nhip — xem `docs/16_CAP_NHAT_VA_DEPLOY.md` muc 2b.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gate_cve", GOC / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    for quick in (True, False):
        for s in gate._steps(quick=quick):
            assert not any("check_cve" in str(a) for a in s.argv), (
                f"`check_cve.py` da lot vao gate o buoc `{s.name}` — no ton 49 "
                f"giay va phu thuoc mang")
    # Va no phai duoc nhac o tai lieu deploy, neu khong khong ai chay no.
    dl = (GOC / "docs" / "16_CAP_NHAT_VA_DEPLOY.md").read_text(encoding="utf-8")
    assert "check_cve.py" in dl, (
        "cong cu khong nam trong gate VA khong duoc nhac o quy trinh deploy "
        "= mot cong cu khong ai chay")
