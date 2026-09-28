"""B17 §4.1, lan P0-a — `ho_so_dich.dung()` tinh + ghi `toc_doc_giong` (xem
`cai_dat.toc_doc_giong`/`cai_dat.voi_toc_doc_giong`) vao `run.settings` TRUOC
bat cu dieu gi khac, khong doi `voice_synthesis` (chay SAU trong chuoi) do
giong roi bao lai — do se la mot CHU TRINH trong DAG.

Dai 4960-4966 (da dem, dai trong). Xem `test_4960_...py` cho phan THUAN tren
`cai_dat.py`.
"""
from __future__ import annotations

import inspect
import json

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
# 3) RANH GIOI PHAM VI — chua duoc NOI vao loi nhac dich that su
# ============================================================================


def test_toc_doc_giong_CHUA_duoc_long_tieng_doc__ranh_gioi_pham_vi():
    """⚠️ Ghi lai RANH GIOI pham vi cua lan P0-a (B17 §4.1), CUNG mot hinh
    dang voi `test_4953::test_bang_sua_dong_am_CHUA_duoc_long_tieng_doc__
    ranh_gioi_pham_vi`: gia tri da duoc TINH + GHI (`run.settings` va dict
    tra ve khi thanh cong), nhung `long_tieng.loi_nhac`/`ngon_ngu.ngan_sach_
    do_dai` (ca hai ⛔ NGOAI pham vi so huu tep cua lan nay: `long_tieng.py`/
    `ngon_ngu.py` khong nam trong 'apps/auto_scan_video/cai_dat.py,
    ho_so_dich.py') CHUA doc no de neo do dai cau THEO GIONG cu the — chung
    van dung chung mot hang so CA-NGON-NGU (`ngon_ngu.NHIP[dich]`) cho MOI
    giong, dung hanh vi hom nay. Noi no vao phep tinh `do_dai_toi_da` moi
    dong (long_tieng.py so huu) la viec cua mot lan khac.

    Bai nay se DO (can sua lai dong chu thich nay) neu ai do noi truong nay
    vao ma khong cap nhat lai bao cao pham vi.
    """
    from apps.auto_scan_video import long_tieng

    nguon_loi_nhac = inspect.getsource(long_tieng.loi_nhac)
    assert "toc_doc_giong" not in nguon_loi_nhac, (
        "long_tieng.loi_nhac gio DA doc toc_doc_giong — cap nhat lai bao cao "
        "pham vi P0-a (khong con la viec con dang cua lan khac)")

    nguon_ngan_sach = inspect.getsource(ngon_ngu.ngan_sach_do_dai)
    assert "toc_doc_giong" not in nguon_ngan_sach, (
        "ngon_ngu.ngan_sach_do_dai gio DA doc toc_doc_giong — cap nhat lai "
        "bao cao pham vi P0-a")
