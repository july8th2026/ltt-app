"""Nen tang nhieu phien: so dang ky thanh phan, ho so gate, khoa tai nguyen.

## Vi sao bo kiem nay ton tai

Phase -1 them mot phep LOC vao cong chat luong: tu "chay tat ca" sang "chay
nhung gi lien quan". Mot phep loc sai **khong bao gio keu** — no chi im lang bo
qua, va dong ket qua van xanh. Do la lop loi dat nhat co the them vao mot cong
chat luong, nen no phai duoc chot chat hon phan con lai.

⛔ Chot quan trong nhat khong phai chot nao do do dung. La
   `test_moi_buoc_gate_cu_van_con` — no cam viec **mat che phu** khi doi cau
   truc gate. Xem `PURIFICATION_GATES`: "Prove new gate coverage >= old".
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "tools"))

import cua_so_yen  # noqa: E402
import thanh_phan as tp  # noqa: E402


# ---------------------------------------------------------------------------
# So dang ky thanh phan
# ---------------------------------------------------------------------------

def test_moi_app_deu_thanh_mot_thanh_phan():
    """App suy tu thu muc, khong tu ban khai — nen khong the quen mot app.

    Day la ly do `_cac_app` doc `apps/*/manifest.py` thay vi doc TOML: mot app
    moi tu dong co mat, khong cho ai nho cap nhat mot danh sach.
    """
    tp_all = tp.cac_thanh_phan(GOC)
    tren_dia = {d.name for d in (GOC / "apps").iterdir()
                if d.is_dir() and (d / "manifest.py").is_file()}
    trong_do_thi = {t.split(":", 1)[1] for t in tp_all if t.startswith("app:")}
    assert tren_dia == trong_do_thi, (
        f"lech giua apps/ va do thi: chi tren dia {tren_dia - trong_do_thi}, "
        f"chi trong do thi {trong_do_thi - tren_dia}")


def test_khop_tien_to_dai_nhat_thang():
    """`platform_core/credit.py` phai ve `core:tien`, khong ve `core:nen`."""
    assert tp.thanh_phan_cua("platform_core/credit.py") == "core:tien"
    assert tp.thanh_phan_cua("platform_core/models.py") == "core:nen"
    assert tp.thanh_phan_cua("apps/vps/routes.py") == "app:vps"
    assert tp.thanh_phan_cua("server/auth/session.py") == "server:auth"


def test_duong_windows_va_posix_cho_cung_ket_qua():
    """Kho nay chay tren Windows; `git` tra `/`, `Path` tra `\\`."""
    assert (tp.thanh_phan_cua(r"platform_core\credit.py")
            == tp.thanh_phan_cua("platform_core/credit.py") == "core:tien")


def test_duong_khong_ai_so_huu_thi_KHONG_doan():
    """Tra `None`, va `bi_anh_huong` phai bien no thanh 'chay tat ca'."""
    assert tp.thanh_phan_cua("mot/duong/khong/ton/tai.py") is None
    assert tp.bi_anh_huong({"mot/duong/khong/ton/tai.py"}, GOC) is None


def test_cham_tep_dung_chung_thi_chay_TAT_CA():
    """⛔ Fail-open. `conftest.py` cham moi thu, nen no khong duoc thu hep."""
    assert tp.bi_anh_huong({"tests/conftest.py"}, GOC) is None
    assert tp.bi_anh_huong({"tools/gate.py"}, GOC) is None


def test_anh_xa_test_suy_tu_IMPORT_chu_khong_tu_TEN_TEP():
    """🔴 Chot trung tam. Xem docstring `thanh_phan.py`.

    `thumbnail` co 2 tep test mang ten no nhung ~19 tep IMPORT no. Chon theo
    ten se bo qua 17 phep kiem — im lang, va o dung cho nguy hiem nhat.
    """
    bang = tp.test_cua_thanh_phan(GOC)
    theo_ten = {t for t in bang["app:thumbnail"] if "thumbnail" in t}
    assert len(bang["app:thumbnail"]) > 3 * max(len(theo_ten), 1), (
        f"chi thay {len(bang['app:thumbnail'])} tep cho thumbnail "
        f"({len(theo_ten)} khop ten) - phep suy theo import co ve da hong")


def test_chi_lay_module_test_that():
    """⛔ `tests/__init__.py` lot vao lam ca luot chet bang INTERNALERROR.

    Va INTERNALERROR khong phai mot test do — no la ca bo test KHONG CHAY,
    trong khi dong ket qua trong y het mot that bai binh thuong.
    """
    moi_tep = set()
    for ds in tp.test_cua_thanh_phan(GOC).values():
        moi_tep |= ds
    xau = {t for t in moi_tep if not Path(t).name.startswith("test_")}
    assert not xau, f"khong phai module test ma van duoc chon: {sorted(xau)}"


def test_canh_dong_lam_sdk_het_mo_coi():
    """`sdk/` khong module nao import — chi `GOI_TAI` tra bang chuoi.

    Neu chot nay do, `sdk/` da tro lai thanh mo coi voi phep do tinh, va lan
    don dep sau se cham no la CHET. No khong chet: no la duong DUY NHAT cho
    khach macOS/Linux.
    """
    _, tieu_thu = tp.do_thi_phu_thuoc(GOC)
    assert tieu_thu["sdk"], (
        "sdk/ khong con nguoi tieu thu nao - canh dong GOI_TAI da mat khoi "
        "tools/thanh_phan.toml")


def test_moi_canh_dong_deu_co_bang_chung():
    """Mot canh khong chi duoc ra dong ma la mot canh khong ai kiem lai duoc."""
    for canh in tp.nap_khai().get("canh_dong", []):
        assert canh.get("bang_chung"), f"canh thieu bang chung: {canh}"
        assert canh.get("co_che"), f"canh thieu co che: {canh}"


def test_mo_rong_nguoi_tieu_thu_khong_bo_sot_chieu_nguoc():
    """Doi `core:tien` phai keo theo nguoi DUNG no, khong chi ban than no."""
    phan = tp.bi_anh_huong({"platform_core/credit.py"}, GOC)
    assert phan is not None and "core:tien" in phan
    assert len(phan) > 1, "khong mo rong sang nguoi tieu thu"


# ---------------------------------------------------------------------------
# Khoa tai nguyen
# ---------------------------------------------------------------------------

@pytest.fixture
def khoa_sach():
    """Don moi khoa truoc va sau — bo kiem nay khong duoc de lai rac."""
    def don():
        for bg in cua_so_yen.dang_giu():
            cua_so_yen.nha(ep=True, tai_nguyen=bg.get("tai_nguyen",
                                                      cua_so_yen.MAC_DINH))
    don()
    yield
    don()


def test_hai_tai_nguyen_khac_nhau_KHONG_doi_nhau(khoa_sach):
    """⭐ Chinh la ly do Phase -1 doi khoa don thanh khoa theo ten.

    Truoc do hai luot khong dung chung gi van phai xep hang sau nhau.
    """
    assert cua_so_yen.thu_giu("A", "lenh-A", "postgres_test")
    assert cua_so_yen.thu_giu("B", "lenh-B", "gpu0")
    assert {b["tai_nguyen"] for b in cua_so_yen.dang_giu()} >= {
        "postgres_test", "gpu0"}


def test_cung_mot_tai_nguyen_thi_nguoi_thu_hai_TRUOT(khoa_sach):
    assert cua_so_yen.thu_giu("A", "lenh-A", "postgres_test")
    assert cua_so_yen.thu_giu("B", "lenh-B", "postgres_test") is False


def test_khoa_treo_bi_doat_chu_khong_treo_mai(khoa_sach):
    """PID chet => khoa phai bi doat, neu khong mot lan Ctrl-C khoa ca may."""
    tep = cua_so_yen._tep("postgres_test")
    tep.write_text(json.dumps({
        "phien": "ma", "pid": 999_999_999, "lenh": "x",
        "bat_dau_epoch": 0.0}), encoding="utf-8")
    assert cua_so_yen.thu_giu("moi", "lenh", "postgres_test") is True


def test_xin_nhieu_tai_nguyen_la_TAT_CA_hoac_KHONG(khoa_sach):
    """⛔ Giu mot phan roi doi phan con lai la cong thuc khoa chet."""
    assert cua_so_yen.thu_giu("nguoi-giu", "lenh", "gpu0")
    k = cua_so_yen.CuaSoYen("toi", "lenh", bat=False,
                            tai_nguyen=("gpu0", "postgres_test"))
    assert k._thu_giu_het() is False
    assert k.da_giu == [], "giu mot phan roi that bai - se khoa chet"
    assert cua_so_yen._doc("postgres_test") is None, "chua nha phan da giu"


def test_xin_theo_thu_tu_SAP_XEP(khoa_sach):
    """Hai luot xin cung tap theo hai thu tu khac nhau la khoa chet."""
    k = cua_so_yen.CuaSoYen("x", "y", bat=False,
                            tai_nguyen=("gpu0", "cpu_nhieu", "postgres_test"))
    assert list(k.tai_nguyen) == sorted(k.tai_nguyen)


def test_sau_khi_thoat_van_bao_duoc_da_giu_gi(khoa_sach):
    """🔴 Chot nay lap dung khoang trong ma bo kiem nay tung bo lot.

    Kho ket qua cua gate goi `_ghi_ket_qua` **sau** khoi `with`, ma `__exit__`
    thi xoa `da_giu` (bat buoc — neu khong, mot lan thoat thu hai se nha khoa
    cua nguoi khac). Ket qua: ban ghi cua mot luot CO giu `cpu_nhieu` lai viet
    `tai_nguyen_da_giu: []`.

    ⛔ Va chot cu **khong bat duoc**, vi no dung mot doi tuong khoa gia chua he
       duoc `__exit__`. Do la kieu khoang trong dien hinh: kiem dung tung manh
       thay vi kiem doan noi giua chung.
    """
    with cua_so_yen.CuaSoYen("toi", "gate", tai_nguyen=("postgres_test",)) as k:
        assert k.da_giu == ["postgres_test"]
    assert k.da_giu == [], "phai rong sau khi thoat, neu khong se nha khoa hai lan"
    assert k.da_giu_xong == ["postgres_test"], (
        "sau khi thoat phai van bao duoc luot nay da giu gi")


def test_tai_nguyen_mac_dinh_giu_DUNG_ten_tep_cu():
    """Doi ten la mo cua so cho hai ban gate cung tuong minh doc quyen."""
    assert cua_so_yen._tep(cua_so_yen.MAC_DINH) == cua_so_yen.TEP_KHOA


# ---------------------------------------------------------------------------
# Gate: ho so va che phu
# ---------------------------------------------------------------------------

def _nap_gate():
    import importlib
    return importlib.import_module("gate")


def test_moi_ho_so_deu_khai_no_KHONG_chung_minh_gi():
    """🔴 Cai gia cua mot ho so khong tu khai da duoc tra roi.

    Ngay 25/08 hai phien doc dong `PASS` cua `--quick` thanh "moi thu xanh",
    trong khi moi loi that hom do nam o dung buoc no bo qua. Them ho so ma
    khong them cau tu khai la lam song lai chuyen do duoi ten moi.
    """
    gate = _nap_gate()
    for ten, hs in gate.HO_SO.items():
        assert hs.get("khong_chung_minh"), f"ho so {ten} khong khai gioi han"
        assert hs.get("chung_minh"), f"ho so {ten} khong khai no chung minh gi"


def test_moi_buoc_gate_cu_van_con():
    """⛔ CHE PHU MOI PHAI >= CHE PHU CU. Chot nay chan viec mat buoc lang le.

    `PURIFICATION_GATES`: "Prove new gate coverage >= old critical coverage."
    Doi cau truc gate ma lam roi mot buoc thi chot nay do — chu khong phai
    doi mot su co tren production moi biet.
    """
    gate = _nap_gate()
    ten = {s.name for s in gate._steps(quick=False)}
    bat_buoc = {
        "bien dich duoc", "secret scan", "app contract lint", "kieu xuong dong",
        "kich thuoc route server", "chuong chua treo", "ten chua dinh nghia",
        "nuot loi lang le", "bien .ps1 trung tham so", "trung so test",
        "bo qua im lang", "ky tu dieu khien", "chuoi chua dich",
        # ⛔ "system profile" GO 2026-09-04 cung voi ca tinh nang (chu du an
        #    quyet). Chot nay canh viec MAT BUOC LANG LE, va lan nay viec mat
        #    la CO Y — nen phai go khoi ban chuan, khong phai nen chot.
        #    Ly do + toan bo pham vi: docs/HO_SO_HE_THONG.md (nay la bia mo).
        "dich thieu ban EN", "hop dong API",
        "anh chup hop dong", "tai lieu sinh ra", "SDK khop hop dong",
        "tai san GUI", "postman", "bo test (song song)",
    }
    assert bat_buoc <= ten, f"buoc da BIEN MAT khoi gate: {sorted(bat_buoc - ten)}"


def test_chi_buoc_that_su_doc_quyen_moi_khai_tai_nguyen():
    """Chi buoc THAT SU dung doc quyen mot thu moi duoc khai no.

    🔴 SUA 06/09/2026 — ban truoc chot `== {"bo test (song song)"}`, tuc chot
       mot GIA TRI. No do khi bon buoc khac duoc khai `postgres_test`, va cai
       do la mot ban va CAN THIET chu khong phai khai thua:

           tools/check_multiproc.py:19   "cac test nay goi `drop_all()`"
           => hai luot gate o hai worktree cung do trong mot dem:
              relation "api_metric_samples" does not exist   (mot phien)
              assert 0 == 9  (9 job bien mat)                (phien kia)

    ⚠️ Lo ngai cua ban cu VAN DUNG va van duoc chot o day: khai thua lam moi
       thu xep hang tro lai. Nhung pham vi cua no hep hon ban cu gia dinh, va
       dieu do DO DUOC:

           `Step.tai_nguyen` chi duoc doc o DUNG MOT cho trong gate.py — de
           gop thanh tap `can` cho khoa CA LUOT. Bo lap lich (`_chay_theo_lich`)
           dung `so_loi`, KHONG dung `tai_nguyen`.

       => Khai them KHONG lam cac buoc xep hang **trong** mot luot. No chi doi
          thu luot ay giu so voi **luot khac**. Phep kiem thu hai duoi day chot
          chinh tinh chat do, nen neu ai lam `tai_nguyen` anh huong lap lich
          thi no do.

    ⭐ Chot TAP HOP, khong chot so luong — va moi ten trong tap phai co ly do
       doc duoc ngay canh no.
    """
    gate = _nap_gate()
    co_tn = {s.name for s in gate._steps(quick=False) if s.tai_nguyen}
    du_kien = {
        # Chay pytest `-n` => an gan het loi, VA cham CSDL test dung chung.
        "bo test (song song)",
        "bo test (noi tiep)",
        "bo test (pham vi)",
        # `check_multiproc.py` goi `drop_all()` tren CSDL test dung chung.
        "bat bien da tien trinh",
        # `do_migration_tren_postgres.py` DUNG roi XOA mot CSDL nhap canh CSDL
        # chinh (`..._test`), va chay ca chuoi alembic tren do. Hai luot gate
        # cung luc se giam nhau dung o buoc `CREATE DATABASE` / `DROP DATABASE`
        # — cung ho voi `drop_all()` o dong tren, chi khac cap: mot ben xoa
        # BANG, ben nay xoa ca CSDL.
        "migration tren postgres",
        # `dien_tap_m1_tren_postgres.py` dung CUNG mot CSDL nhap (`..._test`)
        # va cung goi `create_all`/`drop_all` tren do. Hai luot gate cung luc
        # se giam nhau y het buoc tren — cung tai nguyen, cung lop va cham.
        #
        # ⛔ No PHAI khai `tai_nguyen`, khong duoc bo di cho qua phep kiem nay:
        #    bo di se mo lai dung lop loi `drop_all()` vao nhau ma
        #    `postgres_test` sinh ra de chan.
        "M-1 tren postgres",
    }
    thua = co_tn - du_kien
    assert not thua, f"buoc khai tai nguyen ngoai du kien: {sorted(thua)}"


def test_tai_nguyen_KHONG_duoc_anh_huong_lich_chay_trong_mot_luot():
    """Menh de lam cho phep kiem tren an toan: khai them chi ton kem GIUA cac luot.

    ⛔ Neu mot ban sua nao do cho `tai_nguyen` tham gia `_chay_theo_lich` thi
       moi lan khai them mot tai nguyen se **noi tiep hoa** cac buoc trong cung
       mot luot — dung cai lo ngai ma ban cu cua phep kiem tren dinh chan, va
       luc do tap `du_kien` o tren tro nen nguy hiem.

    ⭐ Nen thay vi cam khai them, ta chot **ly do khai them la re**: `tai_nguyen`
       chi duoc doc de gop thanh khoa ca luot.
    """
    import ast as _ast

    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cay = _ast.parse(ma)
    doc_o = []
    for n in _ast.walk(cay):
        if isinstance(n, _ast.Attribute) and n.attr == "tai_nguyen":
            doc_o.append(n.lineno)

    lich = next(f for f in _ast.walk(cay)
                if isinstance(f, _ast.FunctionDef) and f.name == "_chay_theo_lich")
    trong_lich = [l for l in doc_o if lich.lineno <= l <= lich.end_lineno]
    assert not trong_lich, (
        f"`_chay_theo_lich` doc `tai_nguyen` o dong {trong_lich} - khai them "
        "gio se noi tiep hoa cac buoc trong CUNG mot luot")


def test_chot_bien_dich_KHONG_di_vao_cay_cua_phien_khac():
    """⛔ `.claude/worktrees/<ten>/` la cay lam viec cua PHIEN KHAC.

    Do 2026-09-02: cay chinh do o `bien dich duoc` vi mot tep dang viet do cua
    phien khac chua null byte — mot loi ma phien doc thong bao **khong so huu
    va khong sua duoc**.

    ⛔ `bien dich duoc` la CONG GAC: chay mot minh, truoc het, va khi no do thi
       ca luot dung lai. Nen mot phien khac go phim la du de chan luot do cua ta.

    ⭐ Cai gia that khong phai thoi gian. Mot chot do vi ly do khong lien quan
       se day nguoi ta bo qua chinh no — roi toi luc no do vi ly do that thi
       phan xa da thanh "chac lai chuyen cay rieng".

    Do duoc: 2.647 tep quet -> 1.035. Phan chenh la hai cay long ben trong.
    """
    import check_bien_dich as cbd

    assert cbd.bo_qua(cbd.GOC / ".claude" / "worktrees" / "x" / "t.py") is True
    # Va khong duoc loai tru qua tay: tep that trong kho van phai duoc kiem.
    assert cbd.bo_qua(cbd.GOC / "tools" / "gate.py") is False
    assert cbd.bo_qua(cbd.GOC / "apps" / "vps" / "routes.py") is False


def test_gate_khong_duoc_dat_qua_NGAN_SACH_LOI():
    """🔴 HAI lan may treo phai reset cung, 2026-09-02. Day la chot chan lan ba.

    Lich cu dem TIEN TRINH CON va suy "10 la vua tren 20 loi". Phep suy do dung
    cho nhom `tinh` — moi buoc do that su la MOT tien trinh. No sai cho hai loai
    khac, va sai rat lon:

        `bo test`     -> pytest `-n auto`               = 20 worker
        `frontend` x3 -> vitest `min(12, numCpus - 1)`  = 36 worker

    ⇒ "10 tien trinh" thuc te la ~61 luong tren 20 loi — canh BON dich vu
      production dang phuc vu khach that tren cung may.

    ⛔ Chot nay do **phep tinh**, khong chay gate: mot chot ve qua tai ma tu no
       lam qua tai la mot chot khong ai dam chay.
    """
    gate = _nap_gate()

    ns = gate.ngan_sach_loi()
    assert ns >= 2, "ngan sach phai chay duoc ca tren may hai loi"
    assert ns <= (os.cpu_count() or 4) - gate.LOI_DE_DANH_CHO_MAY, (
        "ngan sach an vao phan de danh cho dich vu production")

    steps = gate._steps(quick=False)

    # ⛔ Khong buoc nao duoc tu do minh theo CA MAY.
    for s in steps:
        assert s.so_loi <= gate.LOI_TOI_DA_MOI_CONG_CU, (
            f"{s.name} xin {s.so_loi} loi, vuot tran mot cong cu")
        assert s.so_loi <= ns, f"{s.name} xin nhieu hon ca ngan sach"

    # ⛔ Va han muc phai duoc TRUYEN XUONG, khong chi tinh ra roi bo do.
    bo_test = [s for s in steps if s.name.startswith("bo test")]
    assert bo_test, "khong con buoc `bo test` — chot nay dang canh nham cho"
    argv = " ".join(bo_test[0].argv)
    assert "-n" in bo_test[0].argv, (
        "`bo test` khong duoc truyen `-n` tuong minh — pytest se lay `auto` "
        "tuc MOI loi cua may, va no khong biet gi ve vitest hay production")
    assert "auto" not in argv, "`-n auto` da quay lai"

    # Frontend: chi kiem khi nhanh THAT duoc chon (cay rieng thieu node_modules
    # thi buoc do la mot dong tu khai BO QUA, khong phai `npm test`).
    for s in steps:
        if s.nhom == "frontend" and any("npm" in a.lower() for a in s.argv[:1]):
            assert any("--maxWorkers=" in a for a in s.argv), (
                f"{s.name} khong chan worker — vitest se tu lay min(12, n-1)")


def test_tien_trinh_con_chay_o_uu_tien_THAP():
    """⭐ Lop bao ve THU HAI, va no can vi lop thu nhat la mot PHEP TINH.

    Ngan sach loi co the tinh sai; uu tien thi khong. Du gate co nham bao nhieu,
    he dieu hanh van cho `LTTStudioWeb` chay truoc mot tien trinh uu tien thap.

    Va no gan nhu mien phi: tren may ranh, tien trinh uu tien thap van dung
    100% CPU — no chi nhuong khi co ai do CAN.
    """
    import inspect

    gate = _nap_gate()
    if os.name == "nt":
        assert gate.UU_TIEN_THAP == 0x00004000, "BELOW_NORMAL_PRIORITY_CLASS"
    than = inspect.getsource(gate._run)
    assert "creationflags" in than, (
        "`_run` khong con ha uu tien tien trinh con — production se phai tranh "
        "CPU ngang hang voi mot luot do")


def test_ho_so_mac_dinh_van_la_day_du():
    """⛔ Tuong thich nguoc: `python tools/gate.py` tran phai khong doi nghia."""
    gate = _nap_gate()
    assert gate.HO_SO["day-du"]["xep_hang"] is True
    assert gate.HO_SO["vong-lap"]["xep_hang"] is False


def test_pham_vi_rong_thi_HA_CAP_chu_khong_bao_PASS():
    """Mot pham vi khong test nao phai keo ve day du, khong duoc in mot dong xanh."""
    gate = _nap_gate()
    assert gate._steps_pham_vi([]) == []


# ---------------------------------------------------------------------------
# Kho ket qua
# ---------------------------------------------------------------------------

def test_kho_ket_qua_nam_ngoai_git_va_ngoai_deploy():
    """⛔ Du lieu mot lan chay khong duoc len production.

    `test-results/` phai vua o `.gitignore` vua o danh sach `/XD` cua robocopy
    trong `setup/2-cai-dat.ps1`. Deploy chep CA CAY ke ca tep untracked, nen
    `.gitignore` mot minh **khong** du.
    """
    assert "/test-results/" in (GOC / ".gitignore").read_text(encoding="utf-8")
    cai_dat = (GOC / "setup" / "2-cai-dat.ps1").read_text(encoding="utf-8",
                                                          errors="replace")
    assert "test-results" in cai_dat, (
        "test-results khong con trong /XD - ket qua gate se len production")


def test_kho_ket_qua_ghi_du_danh_tinh(tmp_path, monkeypatch):
    """Phien sau phai biet 'gate nao da chay tren ma nao'.

    ⛔ Ghi vao `tmp_path`, KHONG vao kho that. Ban dau chot nay goi thang
       `_ghi_ket_qua` va de lai ba ban ghi `day-du PASS` GIA trong
       `test-results/gates/` — mot phien sau doc chung se tin rang gate day du
       da xanh. Do dung la cai bay `AGENTS.md` §10.4 goi ten: rac test lot vao
       tep that. Mot chot ve tinh trung thuc cua kho ket qua ma tu lam ban kho
       ket qua thi no dang chung minh dieu nguoc lai.
    """
    gate = _nap_gate()
    monkeypatch.setattr(gate, "ROOT", tmp_path)

    class _KhoaGia:
        da_cho_s = 1.5
        da_giu = ["cpu_nhieu"]

    gate._ghi_ket_qua("day-du", [], "PASS", 12.3, _KhoaGia(), False)
    ra = list((tmp_path / "test-results" / "gates").glob("*.json"))
    assert ra, "khong ghi duoc ban ghi nao"
    d = json.loads(ra[0].read_text(encoding="utf-8"))
    for khoa in ("id", "luc", "ho_so", "ket_qua", "sha", "nhanh", "cay",
                 "la_cay_chinh", "cho_khoa_giay", "tai_nguyen_da_giu"):
        assert khoa in d, f"ban ghi thieu {khoa}"
    assert (GOC / "test-results" / "gates" / f"{d['id']}.json").exists() is False, (
        "chot da ghi vao kho ket qua THAT")


def test_kho_ket_qua_KHONG_ghi_bien_moi_truong():
    """⚠️ Bien moi truong chua bi mat. Mot kho ket qua khong duoc cham vao do."""
    ma = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    khuc = ma[ma.index("def _ghi_ket_qua"):ma.index("def _git_gon")]
    assert "environ" not in khuc, "kho ket qua dang ghi bien moi truong"
    assert ".tail" not in khuc, "kho ket qua dang ghi dau ra cua buoc"


# ---------------------------------------------------------------------------
# Cay rieng
# ---------------------------------------------------------------------------

def test_cap_dai_so_test_dem_tren_MOI_cay():
    """⛔ Đếm một cây là lặp lại đúng cái lỗi mục này sinh ra để sửa.

    `tools/check_so_test.py` đã ghi đúng gốc từ 23/08: *"mỗi phiên chọn số tiếp
    theo dựa trên thứ nó nhìn thấy lúc bắt đầu — nên hai phiên bắt đầu cùng buổi
    chiều sẽ chọn trùng nhau, đều đúng theo cách họ nhìn."*

    Chốt đó **chặn tương lai** (một mốc, không cho tăng) nhưng **không đóng
    gốc**: hai phiên vẫn chọn trùng, hậu quả chỉ dời sang lúc merge — gate đỏ,
    rồi một người phải đi đổi tên tệp của người khác. Đo 2026-09-02: đã có
    **22 số trùng**, và `test_394` va chạm ngay giữa hai phiên đang sống.

    ⭐ Cấp dải lúc TẠO CÂY thì va chạm không xảy ra được. Nhưng chỉ khi phép đếm
       nhìn **mọi cây** — nếu nó chỉ đếm cây chính thì hai phiên tạo cây cùng
       lúc lại nhận cùng một dải, và ta quay về đúng chỗ cũ.
    """
    import inspect

    from tools import cay_rieng

    than = inspect.getsource(cay_rieng._cap_dai_so_test)
    assert "_moi_cay_tren_dia()" in than, (
        "phep dem chi nhin mot cay — do dung la loi 'chon theo tam nhin rieng'")

    # Va `_moi_cay_tren_dia` phai hoi git, khong duoc doan theo duong dan.
    than2 = inspect.getsource(cay_rieng._moi_cay_tren_dia)
    assert "worktree" in than2 and "list" in than2


def test_tai_lieu_cay_rieng_khong_tro_toi_tep_khong_ton_tai():
    """Mot tham chieu chet trong tai lieu an toan la mot lop bao ve TUONG TUONG.

    `cay_rieng.py` tung ghi rang `tools/check_cay_chinh.py` chan viec deploy tu
    cay rieng "va no chay trong gate". Tep do KHONG TON TAI. Chot chan that nam
    trong `setup/2-cai-dat.ps1` va duoc `test_362` bao ve.
    """
    import re
    ma = (GOC / "tools" / "cay_rieng.py").read_text(encoding="utf-8")
    thieu = [t for t in set(re.findall(r"tools/([a-z0-9_]+\.py)", ma))
             if not (GOC / "tools" / t).is_file()]
    assert not thieu, (
        f"cay_rieng.py tro toi tools/{{{', '.join(sorted(thieu))}}} "
        "nhung tep do khong ton tai")
