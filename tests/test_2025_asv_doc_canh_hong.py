"""R-05 — VLM doc canh HONG: nguyen nhan, va san pham phai lam gi khi no hong.

Luot nghiem thu nen v3 (23/09): 4/12 luot `doc_canh` hong ⇒ `so_cat = 0/6` ⇒
preset `smart_localize` giao mot ban **khong cat gi**, va giai doan bao
`succeeded`. Goi lai 18 canh cua chinh phim do bang model that: **8/18 hong**,
va moi luot hong deu la mot phan hoi HTTP thanh cong co hinh dang sai —
5 lan `"giữ"` (co dau), 2 lan tra ve mot MANG, 1 lan boc `{"objects": [...]}`.
So lieu day du: `docs/auto_scan_video_final/L_FIX_TOC_DO.md`.

  §1 `chuan_de_xuat`     — `"giữ"` la CUNG mot gia tri voi `giu`, khong phai rac
  §2 loi nhac            — mot KHUNG JSON, va `de_xuat` la MA chep y nguyen
  §3 thu lai             — phan hoi sai hinh dang duoc hoi lai MOT lan
  §4 do phu bang chung   — `smart_localize` khong duoc am tham thanh "giu het"

⛔ Khong phep kiem nao o day goi model that.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.auto_scan_video import (ai, canh as canh_mod,  # noqa: E402
                                  giai_doan_ban_bien_tap as gdbbt,
                                  hieu_canh as hc, hop_dong_v4)


# ══════════════════════════════════════════════════════════════════════════════
#  §1  `de_xuat` co dau van la `de_xuat`
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("tho,ra", [
    # 🔴 Nam luot THAT cua phim nghiem thu tra ve dung chuoi nay.
    ("giữ", "giu"), ("GIỮ", "giu"), (" Giữ ", "giu"),
    ("bỏ", "bo"), ("Không chắc", "khong_chac"), ("khong chac", "khong_chac"),
    ("khong-chac", "khong_chac"),
    ("giu", "giu"), ("bo", "bo"), ("khong_chac", "khong_chac"),
])
def test_de_xuat_co_dau_DUOC_nhan_dung_gia_tri(tho, ra):
    assert hc.chuan_de_xuat(tho) == ra


@pytest.mark.parametrize("tho", ["bu", "", None, "maybe", "đỏ", "giu_lai", 1])
def test_gia_tri_LA_van_bi_TU_CHOI(tho):
    """⛔ Chuan hoa nhan dien, khong doan. `"bu"` (1/18 luot that) van la loi."""
    assert hc.chuan_de_xuat(tho) == ""


def test_doc_hieu_canh_NHAN_phan_hoi_co_dau_va_TU_CHOI_gia_tri_la():
    goc = {"loai": "a", "chu_the": [], "hanh_dong": "", "cam_xuc": "",
           "quan_trong": 0.8, "de_xuat": "giữ", "do_tin": 0.9,
           "ly_do": "", "canh_bao": []}
    import json
    h = hc.doc_hieu_canh({"noi_dung": json.dumps(goc, ensure_ascii=False)}, "c1")
    assert h.de_xuat == hc.GIU

    goc["de_xuat"] = "bu"
    with pytest.raises(hc.HieuCanhError):
        hc.doc_hieu_canh({"noi_dung": json.dumps(goc, ensure_ascii=False)}, "c1")


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Loi nhac: mot KHUNG, khong phai mot cau ke ten khoa
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_canh_DUA_KHUNG_JSON_va_cam_MANG():
    van = hc.loi_nhac_canh("canh_0001", "xin chao", 2, {"a": 1})[0]["content"]
    assert '"de_xuat"' in van and '"do_tin"' in van and '"quan_trong"' in van
    assert "KHONG phai mang" in van
    for ma in hc.DE_XUAT:
        assert f'"{ma}"' in van


def test_loi_nhac_canh_NOI_RO_de_xuat_la_MA_khong_phai_chu_tieng_Viet():
    van = hc.loi_nhac_canh("canh_0001", "", 0, {})[0]["content"]
    assert "khong them dau tieng Viet" in van


def test_doi_loi_nhac_lam_DOI_van_tay_canh():
    """⛔ Giu van tay = lan chay sau dung lai ket qua sinh boi loi nhac CU."""
    assert hc.PHIEN_BAN_HIEU_CANH >= 4
    a = hc.van_tay_canh("c1", "x", 2, 0.65)
    truoc = hc.PHIEN_BAN_HIEU_CANH
    try:
        hc.PHIEN_BAN_HIEU_CANH = truoc + 1
        assert hc.van_tay_canh("c1", "x", 2, 0.65) != a
    finally:
        hc.PHIEN_BAN_HIEU_CANH = truoc


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Thu lai MOT lan, va chi voi loi HINH DANG
# ══════════════════════════════════════════════════════════════════════════════

def test_CHI_loi_HINH_DANG_duoc_hoi_lai():
    """⛔ Ranh gioi khong tuy y — va no la ly do `test_2051` van xanh.

    `LuocDoSai` / `HieuCanhError` = model DA tra loi, chi sai hinh dang ⇒ hoi
    lai. `AiMoHo` (khong biet da chay chua) va `AiError` tran (may ban, provider
    tu choi) ⇒ **khong** hoi lai: cai dau co the tra tien hai lan, cai sau la
    mot cau tra loi ve TINH TRANG chu khong phai mot phan hoi rac.
    """
    ma = inspect.getsource(gdbbt._doc_cac_canh)
    assert gdbbt.SO_LAN_DOC_CANH == 2 and "SO_LAN_DOC_CANH" in ma
    assert "except (ai.LuocDoSai, hc.HieuCanhError)" in ma
    for nhanh in ("except ai.AiMoHo", "except ai.AiError"):
        sau = ma[ma.index(nhanh) + len(nhanh):]
        # Nhanh khong-hoi-lai phai thoat vong `for lan in range(...)`.
        assert "break" in sau[:sau.index("except") if "except" in sau
                              else sau.index("if h is None")], nhanh


def test_luot_thu_lai_DUNG_ma_dispatch_KHAC():
    """`UNIQUE(run_id, ma_dispatch)` se nuot but toan cua luot thu hai neu hai
    luot dung chung `item_key` — tuc mot luot DA tra tien bien mat khoi so cai.

    ⚠️ Phep doc doi 23/09 (M-02), MENH DE thi khong: khoa chuyen tu mot chuoi
       f viet tai cho sang `_ma_don_vi_goi(...)` vi no nay mang THEM chieu thu
       hai — so VONG SUA. Chot bang hanh vi cua ham do thi manh hon chot bang
       mot chuoi con, va no chot duoc ca chieu moi.
    """
    f = gdbbt._ma_don_vi_goi
    # Luot binh thuong = DUNG ma canh, khong hau to (so cai cu doc duoc).
    assert f("canh_0003", vong_sua=0, lan_lai=0) == "canh_0003"
    # Ba chieu deu phai cho khoa KHAC nhau, va khong chieu nao trung chieu kia.
    khoa = {f("canh_0003", vong_sua=v, lan_lai=l)
            for v in (0, 1, 2) for l in (0, 1)}
    assert len(khoa) == 6, khoa
    # Hai canh khac nhau khong bao gio dung chung khoa.
    assert f("canh_0003", vong_sua=1, lan_lai=1) != f("canh_0004", vong_sua=1,
                                                      lan_lai=1)
    # Va nguoi goi that phai di qua no, khong go lai chuoi.
    assert "_ma_don_vi_goi(" in inspect.getsource(gdbbt._doc_cac_canh)


def test_nhat_ky_GHI_THONG_DIEP_chu_khong_chi_ten_lop():
    """🔴 Nhat ky luot nen v3 chi co `(LuocDoSai)`, nen phai goi lai 18 luot
    that moi biet vi sao. Mot dong log day du thi khong."""
    ma = inspect.getsource(gdbbt._doc_cac_canh)
    assert "str(exc)[:200]" in ma


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Do phu bang chung — `smart_localize` khong duoc am tham thanh "giu het"
# ══════════════════════════════════════════════════════════════════════════════

def _chi_muc(n: int):
    return canh_mod.ChiMucCanh(
        tuple(canh_mod.Canh(f"canh_{i + 1:04d}", float(i), float(i + 1))
              for i in range(n)), float(n))


class _Hieu:
    def __init__(self, ma):
        self.ma_canh = ma


def test_SMART_LOCALIZE_tu_choi_khi_con_canh_KHONG_co_bang_chung():
    ci = _chi_muc(6)
    hieu = tuple(_Hieu(c.ma) for c in ci.canh[:4])
    hong = [{"ma_canh": "canh_0005", "loai": "LuocDoSai", "ly_do": "x"},
            {"ma_canh": "canh_0006", "loai": "HieuCanhError", "ly_do": "y"}]
    with pytest.raises(gdbbt.ThieuBangChungCanh) as e:
        gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci, hieu, hong)
    # Thong diep phai NOI RA bao nhieu canh, de khach biet minh dang doc cai gi.
    assert "2" in str(e.value) and "6" in str(e.value)


def test_SMART_LOCALIZE_DI_TIEP_khi_doc_du_moi_canh():
    """Doi chung cua bai tren: neu cua chan MOI luot thi bai tren van xanh."""
    ci = _chi_muc(6)
    gdbbt._chot_do_phu(hop_dong_v4.PRESET_CAT_THONG_MINH, ci,
                       tuple(_Hieu(c.ma) for c in ci.canh), [])


def test_GIU_HINH_KHONG_bi_cua_nay_chan():
    """⛔ Preset giu hinh khong doc canh nao ca — do phu 0 o do la dung hop dong."""
    ci = _chi_muc(6)
    gdbbt._chot_do_phu(hop_dong_v4.PRESET_GIU_HINH, ci, (), [])


def test_loi_thieu_bang_chung_KHONG_duoc_nen_tang_tu_dong_thu_lai():
    """⚠️ Lan hoi lai da xay ra TRONG giai doan (`SO_LAN_DOC_CANH`). Mot vong
    thu lai thu hai o tang job la cung mot phep goi tren cung mot khung hinh,
    cong them mot hoa don. Nguoi quyet dinh chay lai la KHACH."""
    from apps.auto_scan_video import loi as _loi
    from apps.auto_scan_video.giai_doan_media import ThieuNguon
    assert issubclass(gdbbt.ThieuBangChungCanh, ThieuNguon)
    assert _loi.phan_loai(gdbbt.ThieuBangChungCanh("x")) == \
        _loi.THIEU_THUONG_NGUON


def test_tom_tat_giai_doan_MANG_so_canh_hong_va_do_phu():
    """Bang chung cua luot chay phai tra loi duoc *"co lo hong nao khong"*."""
    ma = inspect.getsource(gdbbt.chay)
    for khoa in ('"so_canh_hong"', '"canh_hong"', '"do_phu_bang_chung"'):
        assert khoa in ma


def test_nguong_do_phu_la_BAT_BIEN_khong_phai_tham_so_hieu_chinh():
    assert gdbbt.PHU_BANG_CHUNG_TOI_THIEU == 1.0


def test_DOC_CANH_van_doi_dung_hai_truong_quyet_dinh():
    """Bo do doi `de_xuat`/`do_tin` — hai truong `_quyet_dinh_mot_canh` that su doc."""
    assert ai.DOC_CANH.truong_bat_buoc == ("de_xuat", "do_tin")
