"""B17 §4.1, lan P0-a — `ho_so_dich.dung()` tinh + ghi `toc_doc_giong` (xem
`cai_dat.toc_doc_giong`/`cai_dat.voi_toc_doc_giong`) vao `run.settings` TRUOC
bat cu dieu gi khac, khong doi `voice_synthesis` (chay SAU trong chuoi) do
giong roi bao lai — do se la mot CHU TRINH trong DAG.

Dai 4960-4966 (da dem, dai trong). Xem `test_4960_...py` cho phan THUAN tren
`cai_dat.py`.
"""
from __future__ import annotations

import ast
import inspect
import json
import textwrap

from apps.auto_scan_video import ngon_ngu


class _RunGia:
    """`run` gia CO `.settings` (mutable) — khac `_RunGia` cua test_408/4953
    (chi id/owner_id/credit_held) vi day dung phai thu ghi vao settings."""

    def __init__(self, *, credit_held: int = 0, settings: dict | None = None) -> None:
        self.id = 1
        self.owner_id = 1
        self.credit_held = credit_held
        self.settings = dict(settings or {})


def _ban_gia_thanh_cong(db, run, thao_tac, tin, *, stage, item_key, ctx=None,
                        temperature=None):
    return {"noi_dung": json.dumps({
        "the_loai": "x", "so_nguoi_noi": 1, "bang_dai_tu": {},
        "bang_ten_rieng": {}, "giong_van": "", "bang_sua_dong_am": {},
    }, ensure_ascii=False), "su_dung": None}


# ============================================================================
# 1) Ghi vao `run.settings` — noi DOC DUOC o MOI nhanh (thanh cong lan hong)
# ============================================================================


def test_dung_GHI_toc_doc_giong_vao_run_settings_khi_THANH_CONG(monkeypatch):
    from apps.auto_scan_video import ai, ho_so_dich

    monkeypatch.setattr(ai, "goi_tinh_tien", _ban_gia_thanh_cong)
    run = _RunGia(settings={"giong_id": "Minh Duc"})
    ho_so_dich.dung(None, run, {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    assert run.settings.get("toc_doc_giong") == ngon_ngu.NHIP["vi"]


def test_dung_GHI_toc_doc_giong_vao_run_settings_KE_CA_MODEL_TRA_RAC(monkeypatch):
    """Nhanh 'model tra rac' (⛔ khong nem) van phai ghi settings — gia tri
    la ham THUAN, khong phu thuoc model co tra loi duoc hay khong."""
    from apps.auto_scan_video import ai, ho_so_dich

    monkeypatch.setattr(ai, "goi_tinh_tien",
                        lambda *a, **k: {"noi_dung": "khong phai JSON", "su_dung": None})
    run = _RunGia(settings={"giong_id": "x", "ngon_ngu_dich": "en"})
    ra = ho_so_dich.dung(None, run, {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    assert run.settings.get("toc_doc_giong") == ngon_ngu.NHIP["en"]
    # Hop dong CU van dung nguyen — xem test_408::test_ho_so_dich_model_tra_
    # RAC_van_tra_ho_so_RONG. Dict TRA VE khong mang khoa moi.
    from apps.auto_scan_video import ho_so_dich as hsd
    assert set(ra) == set(hsd.KHOA)


def test_dung_GHI_truoc_khi_NEM_AsvError(monkeypatch):
    """Cua chan ngan sach (`AsvError`) nem TRUOC khi model duoc goi — nhung
    `toc_doc_giong` van phai co mat trong `run.settings` (ghi VO DIEU KIEN o
    dau ham, truoc ca loi goi model)."""
    import pytest

    from apps.auto_scan_video import ai, features, ho_so_dich

    def nem(*a, **k):
        raise features.AsvError("het ngan sach")

    monkeypatch.setattr(ai, "goi_tinh_tien", nem)
    run = _RunGia(settings={"giong_id": "x"})
    with pytest.raises(features.AsvError):
        ho_so_dich.dung(None, run, {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    assert run.settings.get("toc_doc_giong") == ngon_ngu.NHIP["vi"]


def test_dung_THANH_CONG_mang_toc_doc_giong_trong_dict_tra_ve(monkeypatch):
    from apps.auto_scan_video import ai, ho_so_dich

    monkeypatch.setattr(ai, "goi_tinh_tien", _ban_gia_thanh_cong)
    run = _RunGia(settings={"ngon_ngu_dich": "en"})
    ra = ho_so_dich.dung(None, run, {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    assert ra["toc_doc_giong"] == ngon_ngu.NHIP["en"]


def test_dung_KHONG_co_thuoc_tinh_settings_VAN_CHAY_DUOC(monkeypatch):
    """`run` khong co `.settings` san (giong stub cua test_408/test_418/
    test_4953) khong duoc lam ham nay nem — no phai TU tao thuoc tinh do,
    dung cach `cai_dat.doc()` da phong thu."""
    from apps.auto_scan_video import ai, ho_so_dich

    class _RunKhongSettings:
        def __init__(self):
            self.id = 1
            self.owner_id = 1
            self.credit_held = 0

    monkeypatch.setattr(ai, "goi_tinh_tien", _ban_gia_thanh_cong)
    run = _RunKhongSettings()
    ho_so_dich.dung(None, run, {"doan": [{"ma": "seg_0001", "chu": "x"}]})

    assert run.settings["toc_doc_giong"] == ngon_ngu.NHIP["vi"]


# ============================================================================
# 2) Khop voi `cai_dat.toc_doc_giong` — khong tinh mot cong thuc rieng o day
# ============================================================================


def test_dung_dung_DUNG_cai_dat_toc_doc_giong_khong_tu_tinh_rieng(monkeypatch):
    """Neo CHO GOI: `ho_so_dich.dung` goi qua `cai_dat.voi_toc_doc_giong`,
    khong tu viet lai cong thuc — mot cong thuc thu hai se tach doi song
    song hai noi phai luon khop nhau."""
    from apps.auto_scan_video import ho_so_dich

    nguon = inspect.getsource(ho_so_dich.dung)
    assert "cai_dat" in nguon or "cd." in nguon, (
        "ho_so_dich.dung khong thay goi qua module cai_dat")
    assert "voi_toc_doc_giong" in nguon


# ============================================================================
# 3) DA NOI DAY — chieu NGUOC cua bai ranh gioi cu (lan P0-a2, 28/09/2026)
# ============================================================================
#
# 🔴 **Bai o day TRUOC la mot bai ranh gioi**: no chot rang `long_tieng.loi_nhac`
#    va `ngon_ngu.ngan_sach_do_dai` **CHUA** doc `toc_doc_giong`, vi hai tep ay
#    ⛔ ngoai pham vi so huu cua lan P0-a. Lan P0-a2 noi day, nen bai ay DA DO
#    dung nhu no tu khai — va cho dung cua no bay gio la **chieu nguoc**:
#    gia tri ay duoc doc O DAU, va co dung MOT lan moi cau khong.
#
# ⚠️ **Vi sao AST chu ⛔ khong `"toc_doc_giong" in nguon`.** Bai cu do bang phep
#    dem chuoi, va khi P0-a2 chay lai no thi no do vi **mot dong DOCSTRING** —
#    tuc mot bai chi dem chuoi ⛔ **khong phan biet duoc "da noi day" voi "da
#    viet mot cau chu thich ve viec noi day"**. Cung ho
#    [[phep-kiem-xanh-tren-thu-da-hong]]: doc thu DAI DIEN thay vi doc thu THAT.


def _cay_loi_nhac() -> ast.AST:
    from apps.auto_scan_video import long_tieng
    return ast.parse(textwrap.dedent(inspect.getsource(long_tieng.loi_nhac)))


def _cac_goi_ngan_sach(cay: ast.AST) -> list[ast.Call]:
    """Moi loi goi `*.ngan_sach_do_dai(...)` trong cay."""
    ra = []
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if ten == "ngan_sach_do_dai":
            ra.append(n)
    return ra


def test_ngan_sach_do_dai_NHAN_toc_doc_giong_la_tham_so_CHI_TU_KHOA():
    """Hop dong cua ben NHAN: mot tham so chi-tu-khoa, mac dinh `None`.

    ⛔ `None` ⛔ khong duoc la `0`: hai thu do la hai trang thai khac nhau
    (*"ben goi khong biet giong"* vs *"so do hong"*), xem docstring cua ham.
    """
    tham = inspect.signature(ngon_ngu.ngan_sach_do_dai).parameters
    assert "toc_doc_giong" in tham, (
        "ngon_ngu.ngan_sach_do_dai KHONG con nhan toc_doc_giong — day la mot "
        "BUOC LUI ve trang thai 'can gat khong ai doc' cua P0-a")
    p = tham["toc_doc_giong"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default is None


def test_loi_nhac_DOC_toc_doc_giong_tu_HO_SO__mot_kenh_mot_chu():
    """Neo CHO DOC: gia tri vao qua `ho_so` (`ho_so_dich.dung()` tra ve no), ⛔
    khong qua mot tham so thu hai cua `loi_nhac`.

    🔑 Mot kenh, mot chu. Hai duong vao cung mot dai luong la hinh dang
       [[hai-cho-khai-cung-mot-dieu-khong-ai-bat-khop]] — va o day duong `ho_so`
       DA co that o CA HAI cho goi cua `giai_doan_noi_dung`, nen mot tham so
       moi chi them mot duong co the LECH.
    """
    from apps.auto_scan_video import long_tieng

    cay = _cay_loi_nhac()
    doc_tu_ho_so = [
        n for n in ast.walk(cay)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute) and n.func.attr == "get"
        and isinstance(n.func.value, ast.Name) and n.func.value.id == "ho_so"
        and n.args and isinstance(n.args[0], ast.Constant)
        and n.args[0].value == "toc_doc_giong"
    ]
    assert len(doc_tu_ho_so) == 1, (
        f"mong DUNG mot cho `ho_so.get('toc_doc_giong')`, thay {len(doc_tu_ho_so)}")
    assert "toc_doc_giong" not in inspect.signature(long_tieng.loi_nhac).parameters, (
        "toc_doc_giong tro thanh tham so cua loi_nhac — gio co HAI duong vao "
        "cung mot dai luong (ho_so + tham so); chot MOT duong")


def test_do_dai_toi_da_neo_theo_toc_doc_giong__DUNG_MOT_lan_MOI_CAU():
    """⭐ *"Doc dung mot lan cho moi cau"* — do bang AST, hai ve:

    1. trong `loi_nhac` co **DUNG MOT** loi goi `ngan_sach_do_dai`, va no
       **nam trong vong `for` chay tung doan** ⇒ moi cau tinh lai tran cua no;
    2. loi goi ay truyen `toc_doc_giong=` ⇒ tran ay neo theo GIONG.

    ⛔ Hai ve phai di CUNG NHAU. Mot loi goi ngoai vong `for` (tinh mot lan roi
       dung lai cho ca lo) van thoa ve 2 nhung **sai dai luong**: cac doan trong
       mot lo co `thoi_luong_giay` KHAC nhau.
    """
    cay = _cay_loi_nhac()
    goi = _cac_goi_ngan_sach(cay)
    assert len(goi) == 1, (
        f"mong DUNG mot loi goi ngan_sach_do_dai trong loi_nhac, thay {len(goi)}")
    (g,) = goi
    kw = {k.arg for k in g.keywords}
    assert "toc_doc_giong" in kw, (
        "loi goi ngan_sach_do_dai KHONG truyen toc_doc_giong — tran do dai "
        "van dung hang so ca-ngon-ngu cho MOI giong (trang thai truoc P0-a2)")

    trong_vong = [
        v for v in ast.walk(cay)
        if isinstance(v, ast.For) and any(x is g for x in ast.walk(v))
    ]
    assert trong_vong, (
        "loi goi ngan_sach_do_dai nam NGOAI moi vong `for` — mot tran tinh mot "
        "lan roi dung lai cho ca lo la SAI DAI LUONG: cac doan khac thoi luong")
