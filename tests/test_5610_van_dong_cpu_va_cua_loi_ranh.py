r"""Ngan sach CPU: van DONG trong gate + cua LOI RANH o `tai_may`.

## 🔴 Bon lo do duoc 28/09/2026, sau mot lan treo may vi `--ho-so day-du`

| # | Lo | Vi sao khong ai bat duoc |
|---|---|---|
| 1 | `_chay_theo_lich` goi `ngan_sach_loi()` **khong** `tru_phien_khac` | tham so ay ton tai tu 03/09 va **khong noi nao truyen `True`** — ma chet, nen khong phep kiem nao that bai |
| 2 | `loi_dang_ban()` chi lay mau luc KHOI DONG | tai **den sau** (Defender, 5,45 loi) khong ai tru; bo dem la mot hang so suot luot |
| 3 | `tai_may.do()` phan quyet **chi theo RAM** | `chay_nang.py` cho theo ham nay, nen may bi chiem 9,5/10 loi van tra `RANH` |
| 4 | `conftest` xin `cpu_nhieu` ma khong khai `so_loi` | `loi_da_hua` roi ve mac dinh **8**, nen mot `pytest -n 2` lam moi phien khac tut ngan sach ve san |

⭐ Ca bon deu **khong sai mot con so nao**. Chung sai o cho **ai doc con so ay**:
   mot ham do dung tai roi khong ai goi, mot phep do dung roi khong lay mau lai,
   mot phan quyet dung ve RAM roi bi hoi ve CPU, mot so biet ro roi khong khai.

## ⭐ Ve con thieu, tu `docs/auto_scan_video_final/B12_...md` (phien khac, cung ngay)

Ho do duoc mat xich ma phep do cua toi **khong** thay: `RapidOCR` an **15,2 loi**
tu trong mot worker pytest. Toi da do tung buoc `tinh` cua gate va thay **moi
buoc <= 0,97 loi** — dung, nhung ⛔ khong tra loi gi ve treo may, vi thu phuong
nam SAU mot buoc: `bo test` -> worker -> `test_4301` -> model OCR.

🔑 ⇒ Hai lop phong thu KHAC nhau, khong the thay nhau:
   · **tai hộ tieu thu** (`chan_loi()` cua ho) — dung cho hộ ta BIET ten;
   · **van DONG o day** — do CPU **toan may**, nen no bat ca hộ ta ⛔ chua biet,
     ke ca tien trinh CHAU khong xin khoa va khong nam trong `-n`.

⚠️ Nen moi phep kiem duoi day co **doi chung**: mot lan may RANH (phai khong
   chan gi) va mot lan may DAY (phai chan). Khong co ve thu hai, mot cua da khoa
   cung va mot cua khong ton tai doc y het nhau.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parent.parent
if str(GOC / "tools") not in sys.path:
    sys.path.insert(0, str(GOC / "tools"))

import gate  # noqa: E402
import tai_may  # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
#  LO 3 — cua LOI RANH o `tai_may.do()`
# ══════════════════════════════════════════════════════════════════════════════

class _BoNho:
    def __init__(self, gib: float):
        self.available = int(gib * 1024 ** 3)


def _tiem(monkeypatch, *, cpu: float, ram_gib: float = 32.0,
          vat_ly: int = 10, logic: int = 20):
    import psutil
    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: cpu)
    monkeypatch.setattr(psutil, "virtual_memory", lambda: _BoNho(ram_gib))
    monkeypatch.setattr(
        psutil, "cpu_count",
        lambda logical=True: logic if logical else vat_ly)


def test_may_DAY_CPU_thi_QUA_TAI_du_RAM_con_nhieu(monkeypatch):
    """🔴 Ca that 28/09: RAM 46 GiB trong, CPU 95% — ban cu tra `RANH`, va
    `chay_nang.py` doc dung ham nay de quyet dinh co cho hay khong."""
    _tiem(monkeypatch, cpu=95.0, ram_gib=46.0)
    k = tai_may.do()
    assert k["phan_quyet"] == tai_may.QUA_TAI, k
    assert "loi vat ly ranh" in k["ly_do"], k["ly_do"]


def test_DOI_CHUNG_may_ranh_thi_van_RANH(monkeypatch):
    """⛔ Khong co ve nay, mot cua khoa cung cung lam bai tren xanh."""
    _tiem(monkeypatch, cpu=5.0, ram_gib=46.0)
    assert tai_may.do()["phan_quyet"] == tai_may.RANH


def test_muc_GIUA_thi_BAN_chu_khong_phai_hai_trang_thai(monkeypatch):
    """75% tren 10 loi = 2,5 loi ranh: chua QUA TAI nhung khong con la RANH.

    ⭐ Ba muc chu khong hai: gop `BAN` vao `RANH` thi `chay_nang` lao vao, gop no
       vao `QUA TAI` thi moi lenh nang doi oan nua ngay.
    """
    _tiem(monkeypatch, cpu=75.0, ram_gib=46.0)
    assert tai_may.do()["phan_quyet"] == tai_may.BAN


def test_Defender_MOT_MINH_khong_duoc_chan_lenh_nang(monkeypatch):
    """🔴 Ve bao ve nguoc, va no la ve quyet dinh CON SO 3,0 thay vi 4,0.

    Defender an 5,45 loi (do 25/09, ngoai moi khoa) ⇒ con 4,55 ranh. Neu cua nay
    bat o day thi MOI lan Defender quet se huy mot lenh nang cua MOI phien
    (`chay_nang.py` cho 30 phut roi thoat 3).

    ⚠️ Cung ho `bao dong gia lam nguoi ta TAT cong`: mot canh bao luon bat thi
       nguoi ta hoc cach di vong, va luc ay ta mat ca cai canh that.
    """
    _tiem(monkeypatch, cpu=54.5, ram_gib=46.0)          # 5,45/10 loi
    assert tai_may.do()["phan_quyet"] == tai_may.RANH


def test_ve_RAM_mot_minh_van_tuyen_duoc_QUA_TAI(monkeypatch):
    """Cua moi chi HA xuong, ⛔ khong bao gio nang len — RAM giu nguyen quyen."""
    _tiem(monkeypatch, cpu=1.0, ram_gib=2.0)
    assert tai_may.do()["phan_quyet"] == tai_may.QUA_TAI


def test_cua_moi_dem_loi_VAT_LY_chu_khong_LOGIC(monkeypatch):
    """🔴 Tron don vi la chinh con bo da lam treo may 03/09 (`-n 11` > `auto` 10).

    85% tren **10 loi vat ly** = 1,5 loi ranh -> QUA TAI.
    Neu ham doc 20 loi LOGIC thi ra 3,0 -> chi `BAN`. Hai ket luan khac nhau tu
    cung mot phep do, va cho lech nam giua hai don vi.

    ⚠️ Lan dau toi chon 80% (= dung **2,0** loi ranh) va bai do vi `ranh < 2.0`
       la `False`. Loi o **phep kiem**, khong o san pham: mot bai do dat ngay
       TREN diem ranh gioi thi no do cach viet `<` hay `<=`, ⛔ khong do dieu no
       muon noi. Chon mot diem cach ranh gioi ra.
    """
    _tiem(monkeypatch, cpu=85.0, ram_gib=46.0, vat_ly=10, logic=20)
    k = tai_may.do()
    assert k["loi_vat_ly"] == 10, "doc cpu_count(logical=True) - sai don vi"
    assert k["phan_quyet"] == tai_may.QUA_TAI, k


# ══════════════════════════════════════════════════════════════════════════════
#  LO 1 — bo dem lich phai TRU phien khac
# ══════════════════════════════════════════════════════════════════════════════

def _than_ham(ten: str) -> ast.FunctionDef:
    cay = ast.parse((GOC / "tools" / "gate.py").read_text(encoding="utf-8"))
    ds = [n for n in ast.walk(cay)
          if isinstance(n, ast.FunctionDef) and n.name == ten]
    assert ds, "mat moc " + ten
    return ds[0]


def test_bo_dem_LICH_tru_phien_khac():
    """⛔ Chot bang AST, ⛔ khong chay gate: mot chot ve qua tai ma tu no lam qua
    tai la mot chot khong ai dam chay (cung ly le `test_394`).

    🔴 `tru_phien_khac` la ma chet tu 03/09 den 28/09. Mot tham so co tai lieu,
       co phep kiem rieng (`test_431::test_ngan_sach_per_MAY_...`), va **khong ai
       goi** — nen phep kiem kia xanh trong khi san pham khong dung no.
    """
    goi = [c for c in ast.walk(_than_ham("_chay_theo_lich"))
           if isinstance(c, ast.Call)
           and isinstance(c.func, ast.Name) and c.func.id == "ngan_sach_loi"]
    assert goi, "lich chay khong con hoi `ngan_sach_loi` - ai chot tran bay gio?"
    for c in goi:
        kw = {k.arg for k in c.keywords}
        assert "tru_phien_khac" in kw, (
            "bo dem lich lay ngan sach per-RUN: hai luot gate song song se cung "
            "lay 8 loi tren mot may 10 loi. Truyen tru_phien_khac=True.")
        assert "phien" in kw, (
            "tru phien khac ma khong noi MINH la phien nao ⇒ tru ca khoa cua "
            "chinh minh, ngan sach tut ve san mot cach vo co")


def test_ngan_sach_per_MAY_that_su_nho_hon_khi_co_phien_khac(monkeypatch):
    """Doi chung cho bai tren: phep tinh phai DOI, khong chi doi chu ky."""
    monkeypatch.setattr(gate, "loi_cong_cu_tu_do", lambda: 10)
    monkeypatch.setattr("cua_so_yen.loi_phien_khac_dang_giu", lambda *a, **k: 4)
    assert (gate.ngan_sach_loi(phien="toi", tru_phien_khac=True)
            < gate.ngan_sach_loi())


# ══════════════════════════════════════════════════════════════════════════════
#  LO 2 — van DONG: lay mau LAI trong luc chay
# ══════════════════════════════════════════════════════════════════════════════

def test_co_san_va_san_du_de_tien():
    """⛔ Mot van khong san se ha tran ve 0 khi Defender quet ⇒ gate DUNG HAN.

    ⚠️ Mot co che sinh ra de tranh treo may ⛔ khong duoc phep tu thanh cai treo.
    """
    assert gate.SAN_LOI_DONG >= 2, (
        "san < 2: hai buoc nhe khong con nap duoc vao nhau, va mot buoc khai 1 "
        "co the phai cho mot cach khong can thiet")
    assert gate.SAN_LOI_DONG <= gate.ngan_sach_loi()


def test_van_dong_KHONG_treo_khi_may_bao_DAY(monkeypatch, tmp_path):
    """🔴 Bai dat nhat tep nay, va no do HANH VI chu khong do van ban.

    Tiem `loi_dang_ban` = toan bo may bi chiem. Van se ha tran ve `SAN_LOI_DONG`.
    Mot buoc khai **nhieu hon san** van phai chay xong — nho ve
    `con_lai == ngan_sach` (chay MOT MINH).

    ⛔ Khong co ve ay, `bo test` (khai 7) treo vinh vien moi lan Defender quet —
      va trieu chung se la *"gate dung im, khong dong log nao"*, dung thu kho
      chan doan nhat.
    """
    monkeypatch.setattr(gate, "loi_dang_ban", lambda mau_s=1.0: 99.0)
    buoc = gate.Step("buoc nang gia", [sys.executable, "-c", "pass"],
                     tmp_path, nhom="nang", so_loi=7)
    gate._chay_theo_lich([buoc], j=2, tuan_tu=False, phien="thu")
    assert buoc.ok is True, "buoc khai > tran dong da bi bo lai, hoac treo"


def test_van_dong_KHONG_tru_hai_lan_tai_cua_CHINH_minh():
    """⚠️ `ngoai = loi_dang_ban() - da_phat` — tru phan cua CHINH luot nay ra.

    🔴 Thieu phep tru ay thi van tu bop co minh: gate cang chay cang do thay may
       cang ban (vi chinh no lam ban), tran cang tut, toi khi ve san. Mot vong
       phan hoi duong, va no ⛔ khong bao gio bao loi — chi cham dan.

    ⭐ Chot bang AST vi day la mot **quan he** giua hai bien, khong phai mot gia
       tri do duoc tu ngoai.

    🔴 **Ban dau bai nay do SAI DAI LUONG, va mot phep tiem loi da bat duoc.**
       No hoi *"chu `da_phat` co xuat hien trong ham khong?"* — chu ay van xuat
       hien nguyen ven o dong `da_phat = ...` ngay khi phep tru da bi bo. Tuc bai
       do **su co mat cua mot CAI TEN**, khong do **quan he** giua hai bien.
       Cung ho `banh-coc-do-cach-go-thay-vi-do-tinh-chat`.

    ⇒ Nay no lay dung node gan `ngoai` va doi `da_phat` nam TRONG bieu thuc ay.
    """
    than = _than_ham("_chay_theo_lich")
    ds = [n for n in ast.walk(than)
          if isinstance(n, ast.FunctionDef) and n.name == "_do_lai_tran"]
    assert ds, "mat luong nen `_do_lai_tran`"
    gan = [n for n in ast.walk(ds[0]) if isinstance(n, ast.Assign)
           and any(isinstance(t, ast.Name) and t.id == "ngoai" for t in n.targets)]
    assert gan, "van dong khong con tinh `ngoai` - tran lay tu dau?"
    ten = {x.id for g in gan for x in ast.walk(g.value) if isinstance(x, ast.Name)}
    assert "da_phat" in ten, (
        "`ngoai` khong tru `da_phat` ⇒ vong phan hoi duong: gate tu lam may ban "
        "roi tu ha tran cua minh ve san, va no ⛔ khong bao gio bao loi - chi "
        f"cham dan. Ten doc ra duoc trong bieu thuc: {sorted(ten)}")


# ══════════════════════════════════════════════════════════════════════════════
#  LO 4 — `conftest` phai KHAI `so_loi` khi giu `cpu_nhieu`
# ══════════════════════════════════════════════════════════════════════════════

def test_conftest_khai_so_loi_khi_xin_khoa():
    """🔴 Khong khai ⇒ `loi_da_hua` roi ve `SO_LOI_KHI_KHONG_KHAI = 8`, tuc mot
    `pytest -n 2` go tay lam **moi phien khac** tut ngan sach ve san.

    ⚠️ Fail-closed o `loi_da_hua` la dung cho cho no dung — khi ⛔ khong ai khai
       thi doan ve phia de dat. Nhung o day ta **biet** so that, va mot cho biet
       ma khong khai la mot cho bat co che kia phai doan.
    """
    src = (GOC / "tests" / "conftest.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay) if isinstance(n, ast.FunctionDef)
           and n.name == "pytest_collection_modifyitems"]
    assert ham, "mat moc `pytest_collection_modifyitems`"
    goi = [c for c in ast.walk(ham[0])
           if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
           and c.func.id == "CuaSoYen"]
    assert goi, "conftest khong con xin khoa `cpu_nhieu`?"
    for c in goi:
        assert "so_loi" in {k.arg for k in c.keywords}, (
            "xin `cpu_nhieu` ma khong khai `so_loi` ⇒ cua_so_yen dem 8 loi cho "
            "luot nay, va moi phien khac cho oan")


def test_so_loi_mac_dinh_KHONG_nho_hon_tran_bo_test():
    """Doi chung huong nguoc: mot mac dinh qua NHO cung la mot kieu sai.

    ⭐ `SO_LOI_KHI_KHONG_KHAI` phai >= tran that, neu khong fail-closed lai thanh
       fail-OPEN: **quen khai** tro nen RE hon khai dung, va moi cho quen se im
       lang di qua.
    """
    import cua_so_yen
    assert cua_so_yen.SO_LOI_KHI_KHONG_KHAI >= gate.TRAN_WORKER_BO_TEST, (
        "mac dinh khi khong khai NHO hon tran that ⇒ khong khai thanh co loi")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# ══════════════════════════════════════════════════════════════════════════════
#  LO 5 — giu mutex CA MAY ma tu han che (`-j` nho)
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Ca that 28/09/2026, mot phien THU BA: `gate.py --pham-vi <35 pham vi> -j 2`
#    giu `cpu_nhieu` + `postgres_test` **25 phut**, va giay CPU ca cay tien trinh
#    do duoc **28 giay** = 0,02 loi. Hai lan cua mot phien khac dung sau no.
#
# ⭐ `cpu_nhieu` la mutex TOAN MAY (chu du an chot 23/09 sau mot su co do duoc).
#    Nen khi mot luot DA giu no, no doc quyen may — va `-j 2` la **tu han che vo
#    co**: cai gia ⛔ khong do len MAY, no do len **KHOA**, tuc len nguoi xep hang.
#
# ⛔ Ban va la mot CANH BAO, ⛔ khong phai tu ghi de `-j`. Doi mutex thanh semaphore
#    co trong so se **dao** quyet dinh 23/09 cua chu du an — viec do chi chu du an
#    quyet, va `cua_so_yen.py` phuc vu moi phien cua ca hai kho.

def test_canh_bao_khi_giu_mutex_ca_may_ma_j_nho():
    """⭐ Chot bang AST: dieu kien phai so `args.j` voi **ngan sach loi**, ⛔ khong
    voi mot hang so go tay — mot nguong go tay se lech voi may khac.

    ⚠️ Va no phai co ve `can` (dang giu tai nguyen): mot luot `--khong-khoa` ⛔
       khong giu mutex nao, nen canh bao o do la bao dong gia.
    """
    src = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "dang giu mutex CA MAY" in src, "mat canh bao"
    cay = ast.parse(src)
    dk = [n for n in ast.walk(cay) if isinstance(n, ast.If)
          and "mutex CA MAY" in ast.dump(n)]
    assert dk, "khong tim duoc khoi `if` cua canh bao"
    ten = {x.id for x in ast.walk(dk[0].test) if isinstance(x, ast.Name)}
    goi = {x.func.id for x in ast.walk(dk[0].test)
           if isinstance(x, ast.Call) and isinstance(x.func, ast.Name)}
    assert "can" in ten, (
        "canh bao khong hoi `can` (co dang giu tai nguyen khong) ⇒ mot luot "
        "`--khong-khoa` cung bi canh bao: bao dong gia")
    assert "ngan_sach_loi" in goi, (
        "canh bao so `-j` voi mot hang so go tay thay vi voi ngan sach loi — "
        "nguong go tay se lech tren may khac")


# ══════════════════════════════════════════════════════════════════════════════
#  LO 6 — `gate.py` in `PASS` roi CHET truoc khi ghi so
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 Ca that 28/09/2026, mot phien khac do va bao lai:
#
#      RESULT: PASS  [--ho-so doi: bo test THU HEP theo pham vi]   <- DA IN
#      UnicodeEncodeError: 'charmap' codec can't encode character '⛔'
#      ls -t .gate/*.json  ->  ban ghi moi nhat la cua luot TRUOC
#
#    Man hinh noi `PASS`; `.gate/` khong co ban ghi nao cho luot ay. Ban ghi la
#    thu `deploy` doc ⇒ ai tin man hinh se deploy tren mot phan quyet KHONG TON TAI.
#
# ⚠️ **Cai co la cua toi**: chinh toi them `⛔` vao `HO_SO["doi"]
#    ["khong_chung_minh"]` sang cung ngay (ban va noi dung ay DUNG — no sua mot
#    cau that su sai — no chi mang mot emoji vao mot duong in chua bao gio duoc
#    bao ve).
#
# ⭐ Hai tang phong thu, va chung KHAC nhau:
#    · ep UTF-8 dau tep (phien khac da va)  -> go CAI CO
#    · ghi so TRUOC khi in (bai duoi day)    -> go CAI SUNG
#   Tang hai khong phu thuoc vao viec ai do co nho ep UTF-8 hay khong.

def test_ghi_so_dat_TRUOC_moi_dong_in_giai_thich():
    """⭐ Chot **THU TU** bang AST — cung ky thuat `test_5611` dung cho
    `credit_cost`, va cung ly le: day la mot quan he VI TRI, thu de bi mot ban
    refactor "don dep" dao lai ma khong ai thay gi khac la.

    🔴 Ve phan biet duoc: mot bai chi kiem *"co ep UTF-8 khong"* van XANH khi thu
       tu bi dao lai — va luc ay mot `print` co dau o bat ky dong nao trong ~150
       dong con lai se lam mat ban ghi. Nen bai nay do THU TU, khong do ep UTF-8.
    """
    src = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert ham, "mat moc `main`"

    dong_ghi = None
    for n in ast.walk(ham[0]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "_ghi_ket_qua":
            dong_ghi = n.lineno if dong_ghi is None else min(dong_ghi, n.lineno)
    assert dong_ghi is not None, "`main` khong con goi `_ghi_ket_qua`"

    # Moi `print` co mot chuoi f/literal chua `RESULT:` — day la moc dau cua
    # phan in ket qua.
    dong_result = None
    for n in ast.walk(ham[0]):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "print"):
            continue
        if "RESULT:" in ast.dump(n):
            dong_result = n.lineno if dong_result is None \
                else min(dong_result, n.lineno)
    assert dong_result is not None, "khong tim duoc dong in `RESULT:`"

    assert dong_ghi < dong_result, (
        f"`_ghi_ket_qua` o dong {dong_ghi}, dong in `RESULT:` dau tien o "
        f"{dong_result}: ghi so phai di TRUOC. Neu khong, mot `UnicodeEncodeError` "
        "o bat ky `print` nao giua hai diem se cho ra `PASS` tren man hinh ma "
        "`.gate/` rong — va `deploy` doc `.gate/`, khong doc man hinh.")


def test_ghi_ket_qua_TRA_VE_chu_khong_IN():
    """⛔ Ve con lai cua cung ban va: neu `_ghi_ket_qua` **tu in**, thi de dong
    `[ket qua]` nam dung cho nguoi doc tim no, ca viec GHI phai doi toi cuoi.

    ⇒ Hai viec phai roi nhau: ghi (khong the that lac) di truoc, in (co the nem)
      di sau. Bai nay chot rang ham ay ⛔ khong con `print` nao.
    """
    src = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "_ghi_ket_qua"]
    assert ham, "mat moc `_ghi_ket_qua`"
    in_ra = [n for n in ast.walk(ham[0])
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "print"]
    assert not in_ra, (
        f"`_ghi_ket_qua` con {len(in_ra)} loi goi `print` — ghi va in lai bi buoc "
        "vao nhau, va do la ly do goc cua su co 28/09")


def test_moi_chuoi_khong_chung_minh_IN_DUOC_tren_cp1252():
    """⭐ Hinh dang phien khac de nghi, va no do mot thu KHAC hai bai tren: noi
    dung cac chuoi, ⛔ khong phai thu tu cac buoc.

    ⚠️ `cp1252` la ma trang PowerShell 5.1 thuong dung. Mot chuoi co `⛔`/`⭐` in
       tren do se nem — va o duong `khong_chung_minh` thi cai nem ay tung lam mat
       ca mot phan quyet.
    """
    import io as _io

    hong = []
    for ten, ho in gate.HO_SO.items():
        cau = str(ho.get("khong_chung_minh") or "")
        try:
            _io.StringIO().write(cau.encode("cp1252").decode("cp1252"))
        except (UnicodeEncodeError, UnicodeDecodeError) as loi:
            hong.append(f"{ten}: {loi}")
    assert not hong, (
        "chuoi `khong_chung_minh` KHONG in duoc tren cp1252: " + " | ".join(hong)
        + ". Hoac bo ky tu ngoai cp1252, hoac dam bao gate ep UTF-8 TRUOC moi "
          "duong in nay — va nho rang ghi so da di truoc (xem bai tren).")


def test_MOI_chuoi_di_vao_print_deu_IN_DUOC_tren_cp1252():
    """🔴 Bai nay thay mot LUAT bang mot CO CHE, va ly do rat cu the: toi vi pham
    chinh luat ay **hai lan trong mot ngay**, lan thu hai ngay trong khi dang sua
    lan thu nhat.

        ca 1  `⛔` trong `HO_SO["doi"]["khong_chung_minh"]`   (sang 28/09)
        ca 2  `⚠️` trong dong canh bao `[khoa]` mutex          (chieu 28/09)

    ⚠️ Ca 2 quan trong hon ca 1, vi no o dong ~2152 — **truoc khi mot buoc nao
       chay xong** — nen phep va *"ghi so TRUOC khi in"* ⛔ KHONG cuu duoc no:
       khoi ghi so nam sau phan chay. Toi tung viet rang phep va do "go cai sung";
       sai, no **thu hep cua so** chu khong dong.

    ⭐ Nen bai nay quet **MOI** chuoi di vao `print(...)` trong ca tep, ⛔ khong chi
       cac chuoi `khong_chung_minh`. Mot luat ma nguoi viet no vi pham hai lan
       trong mot ngay thi ⛔ khong phai mot luat — no la mot loi nhac.

    ⛔ Va bai nay ⛔ KHONG thay the viec ep UTF-8 trong `main()`: no chan mot chuoi
       MOI di vao, con ep UTF-8 phu ca nhung gi doi thu vien in ra (`subprocess`
       chuyen tiep, thong diep loi cua pytest) — thu bai nay ⛔ khong nhin thay.
    """
    src = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    hong = []
    for n in ast.walk(cay):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "print"):
            continue
        for x in ast.walk(n):
            if not (isinstance(x, ast.Constant) and isinstance(x.value, str)):
                continue
            try:
                x.value.encode("cp1252")
            except UnicodeEncodeError:
                la = []
                for c in x.value:
                    try:
                        c.encode("cp1252")
                    except UnicodeEncodeError:
                        if c not in la:
                            la.append(c)
                hong.append(f"dong {n.lineno}: {''.join(la)!r} trong "
                            f"{x.value.strip()[:40]!r}")
    assert not hong, (
        "chuoi di vao `print` co ky tu NGOAI cp1252 — mot console PowerShell 5.1 "
        "se nem `UnicodeEncodeError` tai dung dong do:\n  " + "\n  ".join(hong)
        + "\n⇒ Thay ky tu ay bang chu (`CANH BAO:`, `KHONG`, `->`). Emoji trong "
          "CHU THICH thi vo hai — chi chuoi IN RA moi di qua bo ma hoa console.")


def test_main_EP_UTF8_truoc_khi_in():
    """⛔ Ve con lai: bai tren chan chuoi cua CHINH ta, ⛔ khong chan thu thu vien
    khac in ra qua duong nay. Ep UTF-8 la tang phu duoc ca do.

    ⭐ Chot rang `reconfigure` duoc goi TRONG `main`, va truoc `_parser()` — dong
       dau tien co the in bat cu gi la `parser.parse_args()` (thong diep loi cua
       argparse, co the chua duong dan tieng Viet).
    """
    src = (GOC / "tools" / "gate.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = [n for n in ast.walk(cay)
           if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert ham, "mat moc `main`"
    dong_ep = dong_parser = None
    for n in ast.walk(ham[0]):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "reconfigure":
            dong_ep = n.lineno if dong_ep is None else min(dong_ep, n.lineno)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "_parser":
            dong_parser = n.lineno if dong_parser is None \
                else min(dong_parser, n.lineno)
    assert dong_ep is not None, (
        "`main` khong ep UTF-8 ⇒ mot dong in co dau se giet ca luot gate tren "
        "console cp1252, va lam mat phan quyet neu no chet truoc khoi ghi so")
    if dong_parser is not None:
        assert dong_ep < dong_parser, (
            f"ep UTF-8 o dong {dong_ep} SAU `_parser()` o {dong_parser}: thong "
            "diep loi cua argparse in ra truoc khi stdout duoc ep")
