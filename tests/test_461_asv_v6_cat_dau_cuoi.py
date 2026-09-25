"""V6 pha 10 — cat dau/cuoi: hinh hoc, ba tang cuong che, VA duong toi khach.

## Vi sao tep nay co §3 va §4 chu khong dung o §1

§1 chot **quy tac hinh hoc**. Mot tep chi co §1 se xanh hoan toan trong khi
khong mot khach nao cat duoc gi — dung hinh dang loi da xay ra **bon lan trong
mot ngay o bon phien khac nhau** va da co ten trong kho nay:

    nang luc dung  ·  phep kiem xanh  ·  khong ai di tren duong toi no

Va tep nay duoc viet vi mot ca **dang song** cua chinh hinh dang do, tim thay
khi trace `vung_che`: `tu_giay`/`den_giay` duoc nhan, duoc kiem, duoc luu — roi
`che_do_render._loc_lam_mo` khong doc chung lan nao. Ba phep kiem o `test_456`
deu xanh, vi ca ba chot rang gia tri **duoc giu**, khong chot rang no **co tac
dung**.

⇒ Nen o day hai cau hoi duoc hoi tach nhau:
     §1–§2  luat co dung khong
     §3     co duong tu giao dien toi giai doan khong
     §4     tren duong do co ai DANG di khong  (HTTP that, CSDL that)
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from apps.auto_scan_video import cat_dau_cuoi as cdc
from apps.auto_scan_video import hop_dong_v4

# ⚠️ Nhap MODULE roi lay thuoc tinh, khong `from ... import _nop`. Dang nhap
#    truc tiep lam `ruff` bao F811 o moi ham nhan fixture cung ten — mot bao
#    dong gia cho mot thanh ngu pytest binh thuong, va banh coc `ruff` dem chung.
from tests import test_423_asv_giao_dien as _gd
from tests import test_447_asv_v4_giao_dien_san_pham as _sp
from tests import asv_js

# ⛔ Gan qua THUOC TINH, khong `from ... import moi_truong`. Dang nhap truc tiep
#    lam `ruff` bao F811 o **moi** ham nhan fixture cung ten — bon ham o §4 la
#    +4 F811, va banh coc `ruff` dem chung roi do. Do la mot bao dong gia cho
#    mot thanh ngu pytest hoan toan binh thuong; `test_455` da tra gia va ghi
#    lai, va tep nay quen mat mot lan nua.
moi_truong = _gd.moi_truong
_nop = _sp._nop
_settings = _sp._settings

GOC = Path(__file__).resolve().parents[1]
#: 🔴 **b4 hai giai doan (25/09): cua so cat chuyen sang GIAI DOAN 2.**
#:    Truoc do no duoc GIAO voi `ban_do.giu` trong `giai_doan_ban_dung` (COMPOSE).
#:    Nay giai doan 1 ⛔ khong cat gi — no giao MP4 tieng Viet **toan bo do dai
#:    goc** — nen moi phep cat, ke ca cua so cua khach, nam o `giai_doan_hinh_anh`.
#:
#: ⭐ Ba tang o §3 ⛔ khong bi noi long, chi doi cho: luat L3 (*"CHI o preset
#:    cat"*) van duoc cuong che bang mot `if` so `cach` voi che do cat.
DUONG_GIAI_DOAN = GOC / "apps" / "auto_scan_video" / "giai_doan_hinh_anh.py"
DUONG_ROUTES = GOC / "apps" / "auto_scan_video" / "routes.py"
DUONG_MAU = GOC / "apps" / "auto_scan_video" / "templates" / "asv_trang_chinh.html"


# ══════════════════════════════════════════════════════════════════════════════
#  §1  chuan_hoa — bon luat
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tho", [None, "", (), []])
def test_vang_mat_la_ca_video(tho):
    assert cdc.chuan_hoa(tho) is None


def test_L4_toan_bo_video_KHONG_duoc_ghi_thanh_mot_cua_so():
    """⛔ `(0.0, 1.0)` phai tra `None`, y het khi vang mat.

    Neu no tra `(0.0, 1.0)` thi moi lan chay khong cat cung mang mot cua so, va
    `giao()` se dung lai tung khoang bang mot phep nhan dau cham dong — du de
    doi con so o thap phan thu muoi lam, du de doi **van tay**, va khong du de
    doi mot khung hinh nao. Tuc phuc vu lai toan bo cache cho khong viec gi.
    """
    assert cdc.chuan_hoa((0.0, 1.0)) is None
    assert cdc.chuan_hoa([0.0, 1.0]) is None


def test_cua_so_hop_le_duoc_giu_nguyen():
    assert cdc.chuan_hoa((0.25, 0.75)) == (0.25, 0.75)


def test_L2_cua_so_NGUOC_bi_tu_choi_chu_KHONG_bi_dao_lai():
    """🔑 Day la phep kiem quan trong nhat cua §1.

    Mot ban "tien tay" se viet `a, b = sorted((a, b))` va moi bai kiem khac van
    xanh. Nhung mot cua so bi dao lai la mot cua so khach **khong ve**: ho go
    nham hai o cho nhau, ta cat mot doan ho khong chon, va ho chi biet khi xem
    video da giao. Nen o day khang dinh CA HAI ve: nem, va khong tra ve ban da
    sap xep.
    """
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa((0.8, 0.2))
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa((0.5, 0.5))          # rong cung la nguoc


@pytest.mark.parametrize("tho", [(-0.1, 0.5), (0.1, 1.4), (-2.0, 3.0)])
def test_ngoai_khoang_0_1_bi_tu_choi(tho):
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa(tho)


def test_qua_ngan_bi_tu_choi():
    assert cdc.chuan_hoa((0.10, 0.10 + cdc.TOI_THIEU)) == (0.10, 0.10 + cdc.TOI_THIEU)
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa((0.10, 0.10 + cdc.TOI_THIEU / 2))


@pytest.mark.parametrize("xau", [float("nan"), float("inf"), float("-inf")])
def test_NaN_va_vo_cuc_bi_chan_RIENG(xau):
    """⛔ `float("nan")` doc duoc, va MOI phep so sanh voi no deu `False` — nen
    no lot qua `0.0 <= a < b <= 1.0` neu khong co nhanh chan rieng. Doi ffmpeg
    moi phat hien la doi qua muon: luc do no la mot bo loc hong o giua chuoi."""
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa((0.1, xau))
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa((xau, 0.9))


@pytest.mark.parametrize("tho", ["0.1,0.9", (0.1,), (0.1, 0.2, 0.3),
                                 ("a", "b"), {"tu": 0.1}, 42])
def test_dang_khong_doc_duoc_bi_tu_choi(tho):
    with pytest.raises(cdc.CatLoi):
        cdc.chuan_hoa(tho)


def test_thong_bao_loi_LA_cau_tieng_Viet_cho_khach():
    """Khong ma loi, khong ten truong, khong ten ham."""
    with pytest.raises(cdc.CatLoi) as e:
        cdc.chuan_hoa((0.8, 0.2))
    van = str(e.value)
    assert van.endswith((".", "!"))
    for cam in ("Traceback", "cat_dau_cuoi", "ValueError", "None", "0.8"):
        assert cam not in van, f"thong bao ro ri {cam!r}: {van}"


# ══════════════════════════════════════════════════════════════════════════════
#  §2  giao — don vi la GIAY
# ══════════════════════════════════════════════════════════════════════════════

def test_khong_co_cua_so_thi_khoang_di_qua_NGUYEN_VEN():
    khoang = [(0.0, 5.0), (10.0, 12.0)]
    assert cdc.giao(khoang, None, 20.0) == [(0.0, 5.0), (10.0, 12.0)]


def test_thoi_luong_khong_do_duoc_thi_khong_cat_gi():
    """⛔ Thoi luong 0 nghia la ta KHONG BIET video dai bao nhieu. Nhan mot cua
    so phan so voi mot thoi luong khong biet cho ra mot khoang bang 0 — tuc cat
    sach ca video. Duong lui phai la **khong cat**, khong phai **cat het**."""
    assert cdc.giao([(0.0, 5.0)], (0.25, 0.75), 0.0) == [(0.0, 5.0)]


def test_cat_hai_dau_cua_mot_khoang():
    assert cdc.giao([(0.0, 100.0)], (0.25, 0.75), 100.0) == [(25.0, 75.0)]


def test_khoang_nam_HOAN_TOAN_ngoai_cua_so_bi_LOAI_chu_khong_bi_kep():
    """🔴 L3 cua `vung_che` phat bieu tren truc thoi gian: kep ve bien tao ra
    mot khoang do dai 0 — mot canh "duoc giu" ma khong co khung hinh nao. Loai
    han thi ban dung noi dung su that: canh do khong con."""
    ra = cdc.giao([(0.0, 10.0), (50.0, 60.0), (90.0, 100.0)],
                  (0.4, 0.7), 100.0)
    assert ra == [(50.0, 60.0)]


def test_cua_so_khong_cham_khoang_nao_thi_NEM_va_noi_ve_DOAN_CAT():
    """⛔ `ban_dung.dung` cung nem cho ca nay, nhung cau cua no noi ve *"ban dung
    khong co khoang nao"*. Mot khach vua go hai o so khong co cach nao noi cau
    do voi viec ho vua lam."""
    with pytest.raises(cdc.CatLoi) as e:
        cdc.giao([(0.0, 10.0)], (0.5, 0.9), 100.0)
    assert "cắt" in str(e.value).lower()


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Co DUONG khong — tu giao dien xuong giai doan
# ══════════════════════════════════════════════════════════════════════════════

def _goi_ten(cay: ast.AST) -> set[str]:
    """Moi `x.y(...)` trong cay, tra ve dang `"x.y"`."""
    ra = set()
    for nut in ast.walk(cay):
        if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Attribute):
            g = nut.func.value
            if isinstance(g, ast.Name):
                ra.add(f"{g.id}.{nut.func.attr}")
    return ra


def test_giai_doan_hinh_anh_THUC_SU_goi_giao():
    """⛔ Day la phep kiem bat "nang luc dung, khong ai di tren duong".

    Khong dem chuoi: doc AST. Mot chu thich nhac ten `cat_dau_cuoi` khong lam
    bai nay xanh, va do la ca diem — `vung_che` co du ca chu thich lan truong
    `tu_giay`, va khong dong ma nao doc chung.
    """
    cay = ast.parse(DUONG_GIAI_DOAN.read_bytes().decode("utf-8"))
    assert "cat_dau_cuoi.giao" in _goi_ten(cay)


def test_giai_doan_chi_giao_o_duong_CAT_va_KHONG_tin_giao_dien():
    """🔑 Tang thu ba. Loi goi phai nam trong mot `if` so `cach` voi che do cat.

    Neu no nam o cap ngoai thi mot yeu cau dung tay se cat duoc o preset giu
    hinh — va preset ay **hua** do dai ra bang do dai vao.
    """
    cay = ast.parse(DUONG_GIAI_DOAN.read_bytes().decode("utf-8"))
    trong_if = False
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.If):
            continue
        dk = ast.unparse(nut.test)
        if "CAT_MA_HOA_LAI" not in dk:
            continue
        for than in nut.body:
            if "cat_dau_cuoi.giao" in _goi_ten(than):
                trong_if = True
    assert trong_if, ("`cat_dau_cuoi.giao` phai nam trong nhanh `cach == "
                      "cdr.CAT_MA_HOA_LAI` — o cap ngoai thi preset giu hinh "
                      "cung cat duoc")


def test_route_tao_NHAN_truong_cat_va_goi_chuan_hoa():
    """Tang thu nhat: kiem o CUA, truoc khi giu credit."""
    cay = ast.parse(DUONG_ROUTES.read_bytes().decode("utf-8"))
    tao = next(n for n in ast.walk(cay)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name == "tao")
    ten_tham_so = {a.arg for a in tao.args.args + tao.args.kwonlyargs}
    assert "cat" in ten_tham_so, "route `tao` khong nhan truong `cat`"
    # 22/09 (asv-final cong-noi-bo): phep duyet ha xuong `dich_vu_tao` — MOT
    # duong cho route lan cong noi bo. Route phai goi no; no phai goi chuan_hoa.
    assert "dich_vu_tao.dung_cai_dat" in _goi_ten(tao)
    dv = ast.parse((DUONG_ROUTES.parent / "dich_vu_tao.py").read_bytes().decode("utf-8"))
    dung = next(n for n in ast.walk(dv)
                if isinstance(n, ast.FunctionDef) and n.name == "dung_cai_dat")
    assert "cat_dau_cuoi.chuan_hoa" in _goi_ten(dung)


def test_giao_dien_co_o_nhap_VA_neo_preset():
    """Tang thu hai. Thieu `data-preset-can` thi hai o hien ca o preset giu
    hinh, va khach ve xong moi bi may chu tu choi."""
    van = DUONG_MAU.read_bytes().decode("utf-8")
    assert 'name="cat"' in van, "form khong co truong `cat` nao de gui"
    assert 'id="asv-nhom-cat"' in van
    assert 'data-preset-can' in van.split('id="asv-nhom-cat"')[1][:400]


def test_client_gui_PHAN_SO_chu_khong_gui_GIAY():
    """🔑 L1. Neu client gui giay thi may chu — noi chia cho `thoi_luong` — se
    hieu "12 giay" thanh "1200% video", va `chuan_hoa` tu choi ca lo. Khach thay
    mot loi khong lien quan gi toi thu ho vua go.

    Neo theo **hanh vi**: phai co mot phep chia cho thoi luong truoc khi dong
    goi. Dem chuoi `"cat"` thi mot dong chu thich cung lam bai nay xanh.
    """
    js = asv_js.doc("asv/cat.js")
    # ⚠️ Ten bien doi o pha 12b (`thoiLuongCat` -> `thoiLuongVideo`) khi danh
    #    sach vung bat dau doc chung no. Bai nay DO khi doi ten, va do la
    #    dung viec no phai lam: mot cai neo theo ten thi phai duoc nhin lai
    #    moi lan ten doi, chu khong duoc noi long thanh mot phep tim mo ho.
    assert "thoiLuongVideo" in js
    assert "/ thoiLuongVideo" in js, "khong thay phep doi giay -> phan so"
    assert "JSON.stringify([fa, fb])" in js


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Co ai DANG di tren duong do khong — HTTP that
# ══════════════════════════════════════════════════════════════════════════════

def test_preset_giu_hinh_TU_CHOI_cua_so_cat(moi_truong, tmp_path):
    """⛔ Va tu choi **truoc khi giu credit**, khong phai o `ban_dung.kiem` sau
    chin giai doan."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_GIU_HINH,
             cat=json.dumps([0.1, 0.6]))
    # ⭐ 400 chu khong 200: `_lai_voi_loi` dung lai chinh trang Studio kem cau
    #    loi va tra `status_code=400`. Ban dau bai nay khang dinh 200 — va no
    #    do vi **bai kiem** sai, khong vi ma sai. Ghi lai de bai sau khong "sua"
    #    ma nguon cho khop mot ky vong go tu tri nho.
    assert r.status_code == 400, "phai tra ve trang co loi, khong phai 303"
    assert "/run/" not in str(r.url), "khong duoc tao lan chay nao"
    assert "không cắt bớt được" in r.text


def test_preset_cat_NHAN_cua_so_va_LUU_vao_settings(moi_truong, tmp_path):
    """Neu bai nay xanh ma `test_giai_doan_ban_dung_THUC_SU_goi_giao` do thi ta
    dang o dung ca `vung_che` da mac: luu duoc, khong thi hanh duoc."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             cat=json.dumps([0.2, 0.8]))
    assert "/run/" in str(r.url), r.text[:400]
    run_id = str(r.url).rsplit("/run/", 1)[1].split("/")[0]
    assert _settings(run_id)["cat"] == [0.2, 0.8]


def test_KHONG_cat_thi_settings_KHONG_mang_khoa_cat(moi_truong, tmp_path):
    """L4 do o tang HTTP: mot lan chay binh thuong khong duoc mang them mot
    truong ma khong lan nao dung toi."""
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH)
    run_id = str(r.url).rsplit("/run/", 1)[1].split("/")[0]
    assert "cat" not in _settings(run_id)


def test_cua_so_SAI_bi_tu_choi_o_CUA_bang_cau_tieng_Viet(moi_truong, tmp_path):
    _app, a, csrf, _b, _cb = moi_truong
    r = _nop(a, csrf, tmp_path, preset=hop_dong_v4.PRESET_CAT_THONG_MINH,
             cat=json.dumps([0.9, 0.1]))
    assert r.status_code == 400
    assert "/run/" not in str(r.url), "cua so nguoc van tao duoc lan chay"
    assert "Đoạn cắt phải nằm trong video" in r.text
