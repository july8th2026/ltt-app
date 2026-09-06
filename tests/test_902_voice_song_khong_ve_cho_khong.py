"""702 — `veSong` khong duoc tai + giai ma cho mot canvas khong ai nhin thay.

## Phep do dung sau tep nay (05/09, `docs/MOBILE/02_BASELINE.md`)

Man Studio co NAM trinh phat. O MOI khung nhin do duoc, chi MOT canvas that su
hien; bon cai con lai `display:none` (danh sach "Gan day" thu gon). Nhung
`veSong` chay cho ca nam.

Do bang mang, bam ▶ mot dong "Gan day" o 390px:

    206  bytes=0-        401.324 byte   <- the <audio>, hop le
    200  (khong Range)   401.324 byte   <- fetch cua veSong, VE VAO display:none

Chi phi tuyen tinh, do duoc: **~275 KB moi giay tieng** (tai + PCM float32).
O tran 600 giay do la 55 MB tai + 110 MB PCM = **165 MB cho mot lan ve**.

## Vi sao kiem bang CAU TRUC chu khong bang chuoi

Mot phep kiem `assert "soCotVe" in js` xanh ngay ca khi ai do de lai ten ham roi
xoa cho goi. Nen tep nay **doi ngoac** de lay dung than ham, **boc chu thich
truoc** (neu khong thi chinh doan giai thich o tren se lam phep kiem xanh gia),
roi chot mot menh de ve THU TU: cong kiem phai dung TRUOC luot tai.

Khong cham CSDL, khong cham kho, khong mo trinh duyet.
"""
from __future__ import annotations

import pathlib
import re

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent
JS = GOC / "server" / "static" / "voice.js"


def boc_chu_thich(s: str) -> str:
    """Bo `/* ... */` va `// ...`, GIU nguyen do dai bang khoang trang.

    Giu do dai de moi chi so tim duoc van tro dung vi tri trong ban goc — va de
    so sanh THU TU giua hai moc khong bi lech.

    ⚠️ Khong dung ke chuoi/regex literal cua JS. `voice.js` khong co chuoi nao
       chua `/*`, va mot bo boc chu thich day du la mot bo phan tich JS — thu ma
       neu can thi ta nen dung `node` chu khong tu viet.
    """
    ra = list(s)
    i, n = 0, len(s)
    while i < n:
        if s.startswith("/*", i):
            j = s.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if ra[k] != "\n":
                    ra[k] = " "
            i = j
        elif s.startswith("//", i):
            j = s.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                ra[k] = " "
            i = j
        else:
            i += 1
    return "".join(ra)


def than_ham(s: str, ten: str) -> str:
    """Than cua `function <ten>(` lay bang DOI NGOAC, khong bang regex."""
    m = re.search(r"function\s+" + re.escape(ten) + r"\s*\(", s)
    assert m, f"khong tim thay `function {ten}(` trong voice.js"
    i = s.index("{", m.end())
    sau = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            sau += 1
        elif s[j] == "}":
            sau -= 1
            if sau == 0:
                return s[i:j + 1]
    pytest.fail(f"ngoac cua `{ten}` khong dong")


@pytest.fixture(scope="module")
def js_sach() -> str:
    return boc_chu_thich(JS.read_text(encoding="utf-8"))


# ── Bo boc chu thich phai that su hoat dong ────────────────────────────────
#
# Neu no khong boc, moi phep kiem duoi day xanh vi doan chu thich dai o dau tep
# nay va o `voice.js` deu nhac toi `fetch` lan `soCotVe`.

def test_bo_boc_chu_thich_that_su_boc():
    vao = "a /* fetch( */ b // fetch(\nc"
    ra = boc_chu_thich(vao)
    assert "fetch(" not in ra
    assert len(ra) == len(vao), "phai giu do dai de chi so khong lech"
    assert ra.strip().startswith("a")
    assert ra.rstrip().endswith("c")


def test_than_ham_lay_dung_bang_doi_ngoac():
    s = "function a(){ if (x) { y(); } } function b(){ z(); }"
    assert than_ham(s, "a") == "{ if (x) { y(); } }"
    assert "z()" not in than_ham(s, "a")


def test_phep_kiem_thu_tu_that_su_DO_khi_cong_dat_sai_cho():
    """Mot phep kiem khong bao gio do duoc thi khong chung minh gi.

    Chung minh o day tren mot chuoi TU DUNG, khong sua tep trong kho: mot phep
    kiem sua tam mot tep that se lam `gate.py` bao "CAY DA DOI TRONG LUC CHAY"
    va vut bo ca luot do cua chinh no.
    """
    xau = boc_chu_thich(
        "function veSong(c, u, a){ fetch(u); if (soCotVe(c) === 0) return; }")
    than = than_ham(xau, "veSong")
    assert than.find("soCotVe(") > than.find("fetch("), "chuoi mau phai la ban SAI"

    tot = boc_chu_thich(
        "function veSong(c, u, a){ if (soCotVe(c) === 0) return; fetch(u); }")
    than_tot = than_ham(tot, "veSong")
    assert than_tot.find("soCotVe(") < than_tot.find("fetch(")


def test_bo_boc_khong_bi_lua_boi_chinh_doan_giai_thich():
    """Chu thich noi ve `fetch(` phai KHONG duoc tinh la mot luot tai that.

    Day la cai bay da tung lam mot bo do quet van ban bao dong tren chinh doan
    van giai thich no. Neu bo boc hong, phep kiem thu tu o tren se xanh gia cho
    moi ban ma — ke ca ban da bo cong di.
    """
    xau = boc_chu_thich(
        "function veSong(c, u, a){ /* goi fetch(u) o day */ "
        "if (soCotVe(c) === 0) return; fetch(u); }")
    than = than_ham(xau, "veSong")
    assert than.count("fetch(") == 1, "chu thich van bi dem la mot luot tai"


# ── Menh de that ───────────────────────────────────────────────────────────

def test_veSong_kiem_canvas_TRUOC_khi_tai(js_sach):
    """Cong phai dung truoc luot tai — khong phai chi "co mat o dau do"."""
    than = than_ham(js_sach, "veSong")
    i_cong = than.find("soCotVe(")
    i_tai = than.find("fetch(")
    assert i_cong >= 0, (
        "`veSong` khong con hoi canvas ve duoc bao nhieu cot. Bo cong nay lai la "
        "quay ve trang thai 05/09: bon trong nam trinh phat tai + giai ma toan bo "
        "tep de ve vao mot canvas `display:none`.")
    assert i_tai >= 0, "`veSong` khong con `fetch(` — doc lai tep, phep kiem nay da cu"
    assert i_cong < i_tai, (
        "cong kiem canvas nam SAU luot tai — tuc tep van bi tai ve roi moi bi vut di")


def test_soCotVe_khong_co_mac_dinh_bia(js_sach):
    """`clientWidth || 300` o day bien "khong ve duoc" thanh "ve duoc 100 cot"."""
    than = than_ham(js_sach, "soCotVe")
    assert "300" not in than, (
        "`soCotVe` co mot mac dinh. Ham nay tra loi *co dang giai ma khong*, va "
        "o do mot mac dinh la mot cau tra loi bia — `songGia`/`songDeu` duoc phep "
        "dung `|| 300` vi chung chi VE, khong QUYET DINH.")
    assert "clientWidth" in than


def test_songDeu_khong_tu_goi_lai_chinh_no(js_sach):
    """Ban cu: `if (!canvas) { songDeu(canvas); return; }` — de quy vo han.

    Nhanh duy nhat kich hoat no lai chinh la nhanh phong thu trong `veSong`, nen
    mot `RangeError: Maximum call stack size exceeded` se giet ca handler dung
    luc ta dang co gang xu ly mot truong hop bien.
    """
    than = than_ham(js_sach, "songDeu")
    assert "songDeu(" not in than, (
        "`songDeu` goi lai chinh no — de quy vo han, xem chu thich trong ham")


def test_tran_cam_ung_dung_hinh_hoc_canvas_chu_khong_dung_hang_so_moi(js_sach):
    """Tran tren cam ung phai suy tu so cot ve duoc, khong tu mot so go tay.

    ⭐ Menh de that o day: **khong duoc de mot hang so giay thu hai** ra doi
       canh `TRAN_GIAY_SONG`. Mot hang so thu hai la mot con so se troi doc lap
       voi cai thu nhat, va khong ai biet cai nao dang co hieu luc.
    """
    than = than_ham(js_sach, "veSong")
    assert "matChamThuc()" in than, "khong con nhanh rieng cho man cam ung"
    # Nhanh cam ung phai so `duration` voi `soCotVe(...)`, khong voi mot so.
    m = re.search(r"matChamThuc\(\)\s*&&\s*au\.duration\s*>\s*([A-Za-z_(][^)]*\))", than)
    assert m, "nhanh cam ung khong con so `au.duration` voi mot bieu thuc"
    assert "soCotVe" in m.group(1), (
        f"tran cam ung dang so voi `{m.group(1)}` — phai la `soCotVe(canvas)` de "
        "no suy tu be ngang that cua canvas thay vi tu mot hang so moi")


def test_tran_desktop_van_la_quyet_dinh_cua_phien_voice(js_sach):
    """Lượt soat mobile KHONG duoc doi `TRAN_GIAY_SONG`.

    Do la quyet dinh cua phien Voice dua tren chi phi bo nho. Phep do mat do
    thong tin (mot cot gánh bao nhieu giay) la mot lap luan MOI — no da duoc bao
    cho ho, va viec doi hay khong la cua ho.
    """
    m = re.search(r"TRAN_GIAY_SONG\s*=\s*(\d+)", js_sach)
    assert m, "`TRAN_GIAY_SONG` bien mat"
    assert m.group(1) == "600", (
        f"`TRAN_GIAY_SONG` doi thanh {m.group(1)}. Neu day la co y thi phai di "
        "kem mot quyet dinh cua chu he con Voice, khong phai mot luot sua mobile.")
