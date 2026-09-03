"""Ngan sach loi cua `gate.py` la GIOI HAN TREN, khong phai mot phep gan.

## Loi that ma tep nay chot lai — do 2026-09-03

        os.cpu_count()            = 20   loi LOGIC
        psutil.cpu_count(False)   = 10   loi VAT LY   <- xdist `auto` dung so nay
        gate truyen  -n           = 11

`ngan_sach_loi()` tinh tren loi **logic**, xdist `auto` tinh tren loi **vat ly**,
va ca hai bi tru cung hang so `LOI_DE_DANH_CHO_MAY = 6`. Nen mot co che sinh ra
de **giam** tai lai dang **tang** no.

⭐ Tren may khong sieu phan luong, hai so trung nhau va loi nay khong ton tai.
   No chi lo ra o may co SMT. Nen phep kiem duoi day **gia lap nhieu hinh may**
   thay vi chi kiem may dang chay — mot phep kiem chi chay tren may nay se xanh
   o nua so may va khong ai biet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import gate  # noqa: E402


def _n_truyen_cho_pytest() -> int:
    """Goi CHINH ham gate dung. Khong chep phep tinh.

    ⭐ Tu 03/09 chi con MOT ham tra loi cau hoi nay, nen phep kiem goi thang no.
       Ban truoc cua tep nay chep lai phep `min(...)` ba ve — va mot ban chep la
       mot cho de hai ben lech nhau ma khong ai do.

    🔴 **`do_tai=False`, va do la mot lan sua that.** Khi ve DO DUOC duoc them
       vao (hop nhat voi `loi_dang_ban` cua phien lttchat), mac dinh thanh
       `True` — nen moi phep kiem SO HOC o day bat dau doc CPU that va **doi ket
       qua theo tai may**. Chung xanh khi chay mot minh va do duoi `-n 4`, do
       duoc ngay trong luot hoi quy dau tien cua pha 08.

    ⛔ Mot phep kiem cong chat luong chap chon con te hon khong co: no day nguoi
       ta vao thoi quen chay lai cho toi khi xanh, va tu do khong ai doc mau do
       nua. Nhung phep kiem CO chu dinh do ve DO DUOC thi tu `monkeypatch`
       `loi_dang_ban` — chung khong dung ham nay.
    """
    return gate.loi_cho_bo_test(phien="", do_tai=False)


def test_n_khong_bao_gio_vuot_so_xdist_tu_chon():
    """🔑 Bat bien chinh: ngan sach la TRAN, khong duoc thanh SAN."""
    assert _n_truyen_cho_pytest() <= gate.loi_cong_cu_tu_do()


@pytest.mark.parametrize("logic,vat_ly", [
    (20, 10),   # may nay — SMT, va la hinh may loi da song
    (16, 8),
    (8, 4),
    (4, 4),     # khong SMT: hai so trung nhau, loi khong the lo ra
    (2, 1),
    (64, 32),
])
def test_moi_hinh_may_deu_ton_trong_tran(monkeypatch, logic, vat_ly):
    """Gia lap nhieu may, vi loi nay chi lo ra o may co SMT.

    ⛔ Mot phep kiem chi chay tren may hien tai se xanh o nua so cau hinh va
       khong noi gi ve nua kia. `LOI_DE_DANH_CHO_MAY` cung bi keo theo — tren may
       4 loi, `20-6` va `4-6` cho hai the gioi khac han.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: logic)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: vat_ly)

    n = _n_truyen_cho_pytest()
    assert n <= vat_ly, f"may {logic}/{vat_ly}: truyen -n {n} > auto {vat_ly}"
    assert n >= 1, "khong duoc tra ve 0 worker"
    # ⭐ Va phai de lai cho cho may, tru khi may qua nho de con cho de lai.
    if vat_ly > gate.LOI_DE_DANH_VAT_LY + 1:
        assert n <= vat_ly - gate.LOI_DE_DANH_VAT_LY, (
            f"may {vat_ly} loi vat ly: -n {n} khong chua {gate.LOI_DE_DANH_VAT_LY} "
            f"loi cho OS + dich vu")


def test_chot_nay_THAT_SU_bat_duoc_ban_gan_thang(monkeypatch):
    """Chung minh phep kiem tren khong phai mot den xanh noi vao khong.

    Tai hien **ban truoc khi sua**: bo ve `loi_cong_cu_tu_do()` ra khoi `min`.
    Neu no van xanh thi phep kiem o tren dang do mot thu khac.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 20)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)

    # ⚠️ Tai hien bang CONG THUC CU tuong minh (20 loi LOGIC - 6 - so frontend),
    #    khong goi `ngan_sach_loi()` — ham do nay da sang don vi vat ly, nen goi
    #    no se do mot thu KHAC va phep kiem mat y nghia lich su cua no.
    #
    # 🔴 **`3` la mot HANG SO LICH SU, khong phai `len(gate.FRONTENDS)`.** Con so
    #    11 duoc do ngay 03/09 khi kho co BA frontend. Phien `lttchat` sau do
    #    them frontend thu tu (`chatltt`), va neu doan nay doc so frontend HIEN
    #    TAI thi phep kiem se tu doi cau chuyen lich su cua chinh no moi lan ai
    #    do them mot frontend.
    FRONTEND_LUC_DO = 3
    ban_cu = max(1, min(gate.LOI_TOI_DA_MOI_CONG_CU,
                        20 - 6 - FRONTEND_LUC_DO))
    assert ban_cu == 11, "ban cu phai tai hien dung con so 11 da do duoc"
    assert ban_cu > gate.loi_cong_cu_tu_do(), (
        "ban cu phai VUOT tran — neu khong thi khong co gi de sua")


def test_them_mot_frontend_da_CHE_khuyet_tat_chu_khong_sua_no():
    """🔴 Phat hien luc hop nhat hai nhanh, va no la mot bai hoc ve phep do.

    Cong thuc CU la `cpu_count() - 6 - len(FRONTENDS)`. Voi BA frontend no ra
    **11** — lon hon `auto` = 10, tuc thua tai. Phien `lttchat` them frontend
    thu tu vi mot ly do khong lien quan gi, va cong thuc do lien ra **10**.

    ⛔ Nhin qua thi "het loi". Thuc te khong co gi duoc sua: 10 worker pytest
       cong 4 frontend cong OS cong bon dich vu production van la **khong con
       cho nao de danh cho may**. Khuyet tat chi bi day tu "thua ro rang" sang
       "vua khit" — va mot con so vua khit thi lan sau ai them mot frontend nua
       la no lai tu "dung" thanh "sai" ma khong ai cham vao ngan sach.

    ⭐ Do la ly do ban sua that khong dieu chinh cong thuc do, ma thay bang HAI
       thu doc lap voi so frontend: mot phan DE DANH cho may
       (`LOI_DE_DANH_VAT_LY`) va mot TRAN cung (`TRAN_WORKER_BO_TEST`).
    """
    cu_ba_frontend = max(1, min(gate.LOI_TOI_DA_MOI_CONG_CU, 20 - 6 - 3))
    cu_hom_nay = max(1, min(gate.LOI_TOI_DA_MOI_CONG_CU,
                            20 - 6 - len(gate.FRONTENDS)))
    assert cu_ba_frontend == 11
    # Khong chot con so hom nay — no doi theo so frontend, va do chinh la van de.
    assert cu_hom_nay <= cu_ba_frontend, "them frontend chi lam so nay nho di"

    # ⛔ Cai duoc chot: cong thuc cu KHONG BAO GIO de lai cho cho may, du so
    #    frontend co la bao nhieu — no khong co khai niem "de danh".
    assert cu_hom_nay > gate.loi_cong_cu_tu_do() - gate.LOI_DE_DANH_VAT_LY, (
        "cong thuc cu phai luon vuot phan con lai sau khi de danh cho may")

    # Va ban moi thi co, bat ke so frontend.
    assert _n_truyen_cho_pytest() <= (gate.loi_cong_cu_tu_do()
                                      - gate.LOI_DE_DANH_VAT_LY)

    # Ban moi: bi tran cung keo xuong 6, va con chua 3 loi cho may.
    assert _n_truyen_cho_pytest() == gate.TRAN_WORKER_BO_TEST == 6


def test_loi_cong_cu_tu_do_doc_cung_nguon_voi_xdist():
    """Neu hai ben doc hai nguon khac nhau thi chung se lech lai, im lang.

    ⭐ `xdist/plugin.py:32` goi `psutil.cpu_count(logical=use_logical)`, va chi
       roi ve `os.cpu_count()` khi khong co psutil (`plugin.py:46`). Ham cua ta
       phai co dung hai nhanh do.
    """
    import inspect

    nguon = inspect.getsource(gate.loi_cong_cu_tu_do)
    assert "psutil" in nguon
    assert "logical=False" in nguon
    assert "os.cpu_count" in nguon, "thieu nhanh du phong khi khong co psutil"


def test_khong_tra_ve_0_khi_may_rat_nho(monkeypatch):
    """`max(1, ...)`: mot may 2 loi van phai chay duoc, chi la cham hon.

    Tu choi chay van la kieu hong te hon cham — cung luan cu voi
    `ngan_sach_loi()` giu `max(2, ...)`.
    """
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 2)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 1)
    # 1 - 3 de danh = -2 -> `max(1, ...)` cuu. Tu choi chay la kieu hong te hon cham.
    assert _n_truyen_cho_pytest() == 1


# ══════════════════════════════════════════════════════════════════════════════
#  B1/B2 — ngan sach per-MAY
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ghi_khoa_CU_lam_ngan_sach_GIAM_chu_khong_giu_nguyen():
    """🔴 Cho de sai nhat cua ca co che, va no hong ve phia MO.

    Mot ban ghi khoa ghi truoc 03/09 khong co khoa `so_loi`. Doc no thanh 0
    nghia la "luot do khong dung loi nao" ⇒ ngan sach khong bi tru ⇒ dung cai
    qua tai ta muon chan, chi khac la **im lang**.

    "Khong khai" va "khong dung" la hai dieu khac nhau.
    """
    import cua_so_yen as c

    assert c.loi_da_hua({"tai_nguyen": c.MAC_DINH}) == c.SO_LOI_KHI_KHONG_KHAI
    assert c.SO_LOI_KHI_KHONG_KHAI > 0, "fail-OPEN: ban ghi cu khong tru gi ca"


def test_khoa_treo_va_tai_nguyen_khac_KHONG_bi_tru():
    """Tru nham thi ngan sach teo lai vi mot khoa chet — cung te theo chieu kia."""
    import cua_so_yen as c

    assert c.loi_da_hua({"tai_nguyen": c.MAC_DINH, "so_loi": 9, "treo": "x"}) == 0
    assert c.loi_da_hua({"tai_nguyen": "postgres_test", "so_loi": 9}) == 0
    assert c.loi_da_hua({"tai_nguyen": c.MAC_DINH, "so_loi": 9}) == 9


def test_ngan_sach_per_MAY_tru_dung_tong_cua_phien_khac(monkeypatch):
    import cua_so_yen as c

    monkeypatch.setattr(c, "dang_giu", lambda: [
        {"phien": "a", "tai_nguyen": c.MAC_DINH, "so_loi": 4},
        {"phien": "b", "tai_nguyen": c.MAC_DINH},          # cu -> fail-closed
        {"phien": "c", "tai_nguyen": c.MAC_DINH, "so_loi": 5, "treo": "x"},
    ])
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 20)

    # 4 + SO_LOI_KHI_KHONG_KHAI, khoa treo khong tinh
    cho_doi = 4 + c.SO_LOI_KHI_KHONG_KHAI
    assert c.loi_phien_khac_dang_giu() == cho_doi
    assert (gate.ngan_sach_loi(tru_phien_khac=True)
            == max(2, 20 - gate.LOI_DE_DANH_CHO_MAY - cho_doi))


def test_KHONG_tru_chinh_minh(monkeypatch):
    """Mot luot khong duoc tru phan cua chinh no — no se tu bop co."""
    import cua_so_yen as c

    monkeypatch.setattr(c, "dang_giu", lambda: [
        {"phien": "toi", "tai_nguyen": c.MAC_DINH, "so_loi": 9}])
    assert c.loi_phien_khac_dang_giu("toi") == 0


def test_ap_ngan_sach_sua_CA_argv_chu_khong_chi_con_so(monkeypatch):
    """⛔ Diem dat nhat, `lttchat-...-49` chi ra.

    `_steps()` chay TRUOC khi giu khoa, nen `argv` da co dinh `-n <so>`. Tinh
    lai con so ma khong sua `argv` thi no tru dung va **van chay so worker cu**.
    """
    import cua_so_yen as c

    class St:
        def __init__(self):
            self.argv = [sys.executable, "tools/test_nhanh.py", "-n", "11"]
            self.so_loi = 11

    monkeypatch.setattr(c, "dang_giu", lambda: [
        {"phien": "khac", "tai_nguyen": c.MAC_DINH, "so_loi": 6}])
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 20)
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)

    st = St()
    gate._ap_ngan_sach_thuc([st], phien="toi")

    i = st.argv.index("-n")
    assert st.argv[i + 1] != "11", "argv KHONG duoc sua — van chay 11 worker"
    assert int(st.argv[i + 1]) == st.so_loi, "argv va so_loi lech nhau"
    assert int(st.argv[i + 1]) <= 10, "van vuot tran cua cong cu"


def test_khong_do_duoc_thi_GIU_NGUYEN_ngan_sach_chu_khong_doan(monkeypatch):
    """Mot cong cu do hong khong duoc bien thanh mot cai chan."""
    import builtins
    that = builtins.__import__

    def no(ten, *a, **k):
        if ten == "cua_so_yen":
            raise ImportError("gia lap")
        return that(ten, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no)
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 20)
    assert gate.ngan_sach_loi(tru_phien_khac=True) == gate.ngan_sach_loi()


# ══════════════════════════════════════════════════════════════════════════════
#  B3 — chen thi chay nho
# ══════════════════════════════════════════════════════════════════════════════

def test_chen_thi_ngan_sach_TU_TUT_XUONG(monkeypatch):
    """🔑 B3 roi ra tu B2, khong can mot nhanh rieng.

    Khi het `--cho` ma khoa van bi giu, `cua_so_yen` **van chay** (quyet dinh
    thiet ke co luan cu: tu choi chay la kieu hong te hon cham). Nhung luot kia
    VAN dang giu khoa, nen ban ghi cua no van nam do va phep tru per-MAY tu dong
    ap vao.

    ⇒ Khong viet mot nhanh "neu dang chen thi giam". Hai duong toi cung mot con
      so la hai cho de chung lech nhau.
    """
    import cua_so_yen as c

    monkeypatch.setattr(c, "dang_giu", lambda: [
        {"phien": "khac", "tai_nguyen": c.MAC_DINH, "so_loi": 4}])
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)

    day_du = gate.ngan_sach_loi()                                   # per-RUN
    khi_chen = gate.ngan_sach_loi(phien="toi", tru_phien_khac=True)  # per-MAY

    assert day_du == 10 - gate.LOI_DE_DANH_VAT_LY == 7
    assert khi_chen == max(2, 7 - 4) == 3, (
        "chen ma ngan sach khong tut => B3 khong hoat dong")
    assert khi_chen < day_du


def test_co_chay_khong_khoa_chi_de_NOI_RA_khong_tham_gia_phep_tinh():
    """Mot co bao trang thai khong duoc tro thanh mot nhanh logic thu hai."""
    import inspect

    import cua_so_yen as c

    nguon = inspect.getsource(c.CuaSoYen.chay_khong_khoa.fget)
    assert "self.da_giu" in nguon
    # ⛔ Neu no bat dau tinh toan ngan sach thi da co hai nguon su that.
    for cam in ("ngan_sach", "cpu_count", "so_loi"):
        assert cam not in nguon.split('"""')[-1], (
            f"`chay_khong_khoa` dang tinh {cam} — no chi duoc BAO trang thai")


def test_khong_giu_duoc_khoa_thi_chay_khong_khoa_la_True():
    import cua_so_yen as c

    k = c.CuaSoYen("toi", "lenh", bat=True, tai_nguyen=(c.MAC_DINH,))
    k.da_giu = []
    assert k.chay_khong_khoa is True
    k.da_giu = [c.MAC_DINH]
    assert k.chay_khong_khoa is False
    # Tat xep hang thi khong phai "chen", chi la khong xep hang.
    k2 = c.CuaSoYen("toi", "lenh", bat=False, tai_nguyen=(c.MAC_DINH,))
    assert k2.chay_khong_khoa is False


# ══════════════════════════════════════════════════════════════════════════════
#  Logic THONG NHAT — mot cau hoi, mot cau tra loi
# ══════════════════════════════════════════════════════════════════════════════

def test_chi_MOT_ham_quyet_dinh_so_worker_cua_bo_test():
    """⛔ Truoc 03/09 co SAU cho cung tra loi "duoc bao nhieu loi", tren HAI don vi.

    Chong cheo nhieu tang thi khong ai doc noi ca duong, va cho lech nam GIUA hai
    tang la cho khong ai soi — dung kieu loi da song tu `03845cb`: mot ve tinh
    tren loi logic (20), mot ve tren loi vat ly (10).

    ⭐ Chot bang AST: duong dung `argv` cua buoc `bo test` chi duoc goi
       `loi_cho_bo_test`, khong duoc tu ghep `min(...)` mot lan nua.
    """
    import ast
    import inspect

    import textwrap
    nguon = textwrap.dedent(inspect.getsource(gate._steps))
    cay = ast.parse(nguon)
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "loi_cho_bo_test" in goi, "`_steps` khong dung ham thong nhat"
    # Cac ten cu khong duoc quay lai o duong nay.
    nguon_ap = inspect.getsource(gate._ap_ngan_sach_thuc)
    assert "loi_cho_bo_test" in nguon_ap
    assert "LOI_TOI_DA_MOI_CONG_CU" not in nguon_ap, (
        "tran cua VITEST khong duoc dung cho pytest — do la muon hang so qua "
        "bien don vi lan thu hai")


def test_moi_ve_deu_tinh_tren_LOI_VAT_LY(monkeypatch):
    """Mot don vi duy nhat. Lech don vi la loi da song 5 thang o kho nay."""
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    # Khong phu thuoc `os.cpu_count()` (logic) nua.
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 999)

    # 🔴 `do_tai=False`, cung ly do voi `_n_truyen_cho_pytest` — va day la cho
    #    thu HAI cua cung mot loi, tim ra o luot hoi quy cua pha 12.
    #
    #    Phep kiem nay do SO HOC cua don vi. De `do_tai` mac dinh (`True`) thi no
    #    doc CPU that va doi ket qua theo tai may: xanh khi chay mot minh, do
    #    duoi `-n 4`. Mot phep kiem cong chat luong chap chon day nguoi ta vao
    #    thoi quen chay lai cho toi khi xanh, va tu do khong ai doc mau do nua.
    assert gate.loi_cho_bo_test(phien="", do_tai=False) == gate.TRAN_WORKER_BO_TEST

    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 8)
    assert gate.loi_cho_bo_test(phien="", do_tai=False) == min(
        gate.TRAN_WORKER_BO_TEST, 8 - gate.LOI_DE_DANH_VAT_LY)


def test_phien_khac_giu_thi_tu_tut_xuong(monkeypatch):
    import cua_so_yen as c
    monkeypatch.setattr(c, "dang_giu", lambda: [
        {"phien": "khac", "tai_nguyen": c.MAC_DINH, "so_loi": 4}])
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    # 10 - 3 - 4 = 3, nho hon tran 6 -> 3 thang
    assert gate.loi_cho_bo_test(phien="toi") == 3


def test_bo_dem_LICH_cung_dung_don_vi_VAT_LY(monkeypatch):
    """⛔ Tang cuoi cua viec thong nhat, va no suyt bi bo sot.

    `loi_cho_bo_test` da sang don vi vat ly, nhung **bo dem lich**
    (`_chay_theo_lich`) van dung `ngan_sach_loi()`. Neu ham do con tinh tren loi
    LOGIC (20-6=14) thi no cho tong <= 14: `bo test` khai 6, con **8 suat** cho
    buoc tinh chay cung — tam buoc tinh ~4 loi vat ly + 6 = 10/10, cham tran tro
    lai.

    ⭐ Mot don vi cho CA LUOT chay, khong phai mot don vi cho moi tang. Cho lech
       nam giua hai tang la cho khong ai soi.
    """
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr(gate.os, "cpu_count", lambda: 999)   # logic khong duoc anh huong

    ns = gate.ngan_sach_loi()
    assert ns == 10 - gate.LOI_DE_DANH_VAT_LY == 7
    assert ns < 14, "van dang tinh tren loi logic"

    bt = gate.loi_cho_bo_test(phien="")
    assert bt <= ns, "bo test mot minh da vuot ngan sach cua ca luot"
    assert ns - bt >= 0, "khong con suat nao cho buoc tinh"


def test_tong_toi_da_luon_chua_cho_cho_may(monkeypatch):
    """Bat bien cuoi: ngan sach + de danh khong duoc vuot loi that co."""
    for vl in (4, 8, 10, 16, 32):
        monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda v=vl: v)
        ns = gate.ngan_sach_loi()
        assert ns <= vl, f"may {vl} loi: ngan sach {ns} vuot"
        if vl > gate.LOI_DE_DANH_VAT_LY + 2:
            assert vl - ns >= gate.LOI_DE_DANH_VAT_LY, (
                f"may {vl} loi: chi de lai {vl-ns}, can {gate.LOI_DE_DANH_VAT_LY}")


# ══════════════════════════════════════════════════════════════════════════════
#  Hop nhat KHAI BAO + DO DUOC — mot so, hai nguon
# ══════════════════════════════════════════════════════════════════════════════
#
# `loi_dang_ban()` den tu phien `lttchat` (4420b56); `loi_cho_bo_test()` tu phien
# nay. Hai nhanh, hai nua cua cung mot bai toan, va **khong nhanh nao co ca hai**
# cho toi 03/09. Cac phep kiem duoi day chot cach chung ghep lai.

def test_hai_nguon_CHONG_len_nhau_thi_dem_MOT_lan(monkeypatch):
    """🔴 Cho de sai nhat cua ban hop nhat: `+` thay vi `max`.

    Mot phien khac vua KHAI 6 loi vua DANG DUNG 6 loi thi no xuat hien o ca hai
    nguon. Cong lai la tru 12 cho mot viec chiem 6, ngan sach tut ve 1, va co
    che giam tai tu lam minh vo dung.
    """
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr(gate, "LOI_DE_DANH_VAT_LY", 3)
    monkeypatch.setattr(gate, "TRAN_WORKER_BO_TEST", 6)
    # do duoc: 3 (nen) + 2 (phien kia) = 5 loi vat ly dang ban
    monkeypatch.setattr(gate, "loi_dang_ban", lambda *a, **k: 5.0)
    import cua_so_yen
    monkeypatch.setattr(cua_so_yen, "loi_phien_khac_dang_giu", lambda *a, **k: 2)

    # ⛔ Con so phai nam TREN san `max(1, ...)`, neu khong phep kiem vo hieu.
    #
    # 🔴 Ban dau cho nay dat khai_bao=6, do_duoc=6. Voi `max` ra 10-3-6=1; voi
    #    `+` ra 10-3-12=-5, roi `max(1, ...)` keo ve 1. **Ca hai deu ra 1**, nen
    #    phep kiem xanh ca khi thuat toan sai — do bang mot lan dot bien that,
    #    khong phai bang suy luan.
    #
    # ⇒ 2 va 2: `max` -> 10-3-2 = 5; `+` -> 10-3-4 = 3. Hai so khac nhau, va ca
    #   hai deu duoi tran 6 nen tran khong che mat khac biet.
    n = gate.loi_cho_bo_test(phien="toi")
    assert n == 5, f"phai la 10-3-max(2,2)=5, khong phai 10-3-4=3 -> {n}"


def test_chi_DO_DUOC_thi_van_tut_xuong(monkeypatch):
    """Kich ban 03/09: 12 tien trinh `demucs` ngoai moi khoa.

    ⛔ Khong cai nao xin khoa va khong cai nao nam trong `-n`. Khoa khong thay
       chung; hang so khong thay chung. Chi phep DO thay.
    """
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr(gate, "LOI_DE_DANH_VAT_LY", 3)
    monkeypatch.setattr(gate, "TRAN_WORKER_BO_TEST", 6)
    monkeypatch.setattr(gate, "loi_dang_ban", lambda *a, **k: 9.5)
    import cua_so_yen
    monkeypatch.setattr(cua_so_yen, "loi_phien_khac_dang_giu", lambda *a, **k: 0)

    assert gate.loi_cho_bo_test(phien="toi") == 1


def test_chi_KHAI_BAO_thi_van_tut_xuong(monkeypatch):
    """Chieu con lai: phien khac vua giu khoa, chua kip dot CPU nao."""
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr(gate, "LOI_DE_DANH_VAT_LY", 3)
    monkeypatch.setattr(gate, "TRAN_WORKER_BO_TEST", 6)
    monkeypatch.setattr(gate, "loi_dang_ban", lambda *a, **k: 0.5)
    import cua_so_yen
    monkeypatch.setattr(cua_so_yen, "loi_phien_khac_dang_giu", lambda *a, **k: 5)

    assert gate.loi_cho_bo_test(phien="toi") == 2


def test_may_RANH_thi_phep_do_KHONG_lam_tut_ngan_sach(monkeypatch):
    """Nen may khong duoc tru hai lan.

    `LOI_DE_DANH_VAT_LY` da tru nen roi. Neu ve DO DUOC tru ca nen mot lan nua
    thi tren mot may khong co ai chay, ngan sach van tut — va khong ai hieu vi
    sao.
    """
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr(gate, "LOI_DE_DANH_VAT_LY", 3)
    monkeypatch.setattr(gate, "TRAN_WORKER_BO_TEST", 6)
    monkeypatch.setattr(gate, "loi_dang_ban", lambda *a, **k: 3.0)  # dung bang nen
    import cua_so_yen
    monkeypatch.setattr(cua_so_yen, "loi_phien_khac_dang_giu", lambda *a, **k: 0)

    assert gate.loi_cho_bo_test(phien="toi") == 6


def test_loi_dang_ban_tra_ve_don_vi_VAT_LY(monkeypatch):
    """⛔ Ban goc nhan voi `os.cpu_count()` = 20 (LOGIC).

    Tron don vi la **dung cai loi da khoi dau ca chuyen nay** (`-n 11` lon hon
    `auto` = 10). Doi don vi khi NHAP, khong phai khi dung.
    """
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)

    class _Gia:
        @staticmethod
        def cpu_percent(interval=None):
            return 50.0
    monkeypatch.setitem(sys.modules, "psutil", _Gia)

    # 50% cua 10 loi VAT LY = 5.0. Neu tinh tren 20 loi logic se ra 10.0.
    assert gate.loi_dang_ban(0.01) == 5.0


def test_khong_do_duoc_CPU_thi_FAIL_OPEN(monkeypatch):
    """⚠️ Mot cong chat luong tu choi chay vi khong doc noi CPU la mot cong
    khong ai dung — no se bi go bang mot co `--bo-qua`."""
    def _no(*a, **k):
        raise OSError("khong doc duoc")

    class _Gia:
        cpu_percent = staticmethod(_no)
    monkeypatch.setitem(sys.modules, "psutil", _Gia)
    assert gate.loi_dang_ban(0.01) == 0.0


def test_do_tai_TAT_duoc_de_khong_cham_them_mot_giay(monkeypatch):
    """`loi_dang_ban` chan 1 giay. Duong goi phai tat duoc no khi khong can."""
    goi = []
    monkeypatch.setattr(gate, "loi_dang_ban",
                        lambda *a, **k: goi.append(1) or 9.0)
    import cua_so_yen
    monkeypatch.setattr(cua_so_yen, "loi_phien_khac_dang_giu", lambda *a, **k: 0)

    gate.loi_cho_bo_test(phien="toi", do_tai=False)
    assert goi == [], "do_tai=False ma van do"


# ══════════════════════════════════════════════════════════════════════════════
#  Tang thu BA: `-n auto` go tay ngoai gate
# ══════════════════════════════════════════════════════════════════════════════

def test_conftest_hoi_CHINH_gate_chu_khong_tu_tinh():
    """⛔ Duong `pytest -n auto` **go tay, ngoai gate** phai chung tran voi gate.

    🔴 Truoc 03/09 `conftest.pytest_xdist_auto_num_workers` co phep tinh RIENG,
       va no ra 10 — toan bo loi vat ly, khong chua mot loi nao cho OS lan bon
       dich vu production. Docstring cua chinh no ghi lai rang phien viet no da
       go `pytest -n auto` ngoai gate **ba lan trong mot ngay** 03/09.

    ⇒ Mot lenh go tay khong duoc di duong khac. Chot bang AST: ham do phai goi
      `loi_cho_bo_test`.
    """
    import ast as _ast

    tep = Path(__file__).resolve().parent / "conftest.py"
    cay = _ast.parse(tep.read_text(encoding="utf-8"))
    ham = [n for n in _ast.walk(cay)
           if isinstance(n, _ast.FunctionDef)
           and n.name == "pytest_xdist_auto_num_workers"]
    assert ham, "mat moc `pytest_xdist_auto_num_workers`"

    goi = {c.func.attr for c in _ast.walk(ham[0])
           if isinstance(c, _ast.Call) and isinstance(c.func, _ast.Attribute)}
    goi |= {c.func.id for c in _ast.walk(ham[0])
            if isinstance(c, _ast.Call) and isinstance(c.func, _ast.Name)}
    assert "loi_cho_bo_test" in goi, (
        "conftest tu tinh so worker cho `-n auto` thay vi hoi gate - "
        "xem test_431 muc 'Tang thu BA'")


def test_conftest_van_LAY_MIN_chu_khong_dat_de(monkeypatch):
    """Neu gate tra ve mot so LON hon phep tinh cuc bo thi van lay so nho.

    ⭐ Cung bai hoc voi `loi_cong_cu_tu_do`: mot tran la GIOI HAN TREN, khong
       phai mot phep gan. Dat de thi khi ben kia rong rai hon, cai "tran" thanh
       SAN.
    """
    import ast as _ast

    tep = Path(__file__).resolve().parent / "conftest.py"
    src = tep.read_text(encoding="utf-8")
    cay = _ast.parse(src)
    ham = [n for n in _ast.walk(cay)
           if isinstance(n, _ast.FunctionDef)
           and n.name == "pytest_xdist_auto_num_workers"][0]
    doan = _ast.get_source_segment(src, ham) or ""
    assert "min(n, " in doan or "min(n," in doan, (
        "phai LAY MIN voi phep tinh cuc bo, khong duoc gan thang so cua gate")
