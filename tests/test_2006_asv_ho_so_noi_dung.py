"""R-01 §1 — `ho_so_noi_dung`: nguoi SINH RA thu `AUTO_MATCH` van doi mai.

Bang chung mo lo hong: `docs/auto_scan_video_final/bang_chung/NEN_V3.md` luot A —
mot lan chay that chet o `content_process` voi `ChuaRangError` sau 133 giay
demucs + ASR **da tra tien**, vi khong giai doan nao sinh `HoSoNoiDung`.

Tep nay do PHAN DUNG HO SO. Phan rang giong o `test_2007`, phan chay het chuoi
o `test_2008`, phan phep do F0 o `test_2009`.
"""
from __future__ import annotations

import json

import pytest

from apps.auto_scan_video import ai, cao_do, hieu_canh as hc
from apps.auto_scan_video import ho_so_noi_dung as hs


def _ban_ghi(ngon_ngu="zh"):
    return {"ngon_ngu": ngon_ngu, "doan": [
        {"ma": "d0001", "bat": 0.0, "ket": 2.0, "chu": "mot hai ba"},
        {"ma": "d0002", "bat": 2.0, "ket": 6.0, "chu": "bon nam sau bay"},
    ]}


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Tu vung — lay tu CATALOG, va gia tri la thi BO chu khong doi
# ══════════════════════════════════════════════════════════════════════════════

def test_tu_vung_lay_tu_CATALOG_chu_khong_go_tay():
    """⛔ Mot ban sao go tay cua ba mat se lech ngay ngay catalog them mot
    phong cach — va lech theo huong im lang."""
    from apps.ltt_voice import giong_mau

    tv = hs.tu_vung()
    assert tv["gioi"] == frozenset(giong_mau.NHAN_GIOI)
    assert tv["vung"] == frozenset(giong_mau.NHAN_VUNG)
    assert tv["phong_cach"] == frozenset(giong_mau.NHAN_PHONG_CACH)


def test_gia_tri_NGOAI_catalog_bi_BO_chu_khong_bi_doi_sang_gia_tri_gan_giong():
    """🔴 Day la cho lo hong suyt tai sinh.

    Model rat hay tra ve `phong_cach: "thuyet minh"` — mot chu dung tieng Viet,
    hop ly voi con nguoi, va **khong co trong catalog**. `giong_mau.loc` se tra
    ve rong, tuc ho so co ma van khong rang duoc giong nao.

    ⛔ Va cach chua KHONG duoc la doi no sang mot gia tri gan giong: doi la bia
       ra mot rang buoc khach khong he co. Bo di = khong rang buoc mat do.
    """
    ra = hs.loc_dac_diem({"gioi": "nam", "vung": "bac",
                          "phong_cach": "thuyet minh"})
    assert ra == {"gioi": "nam", "vung": "bac"}
    assert "phong_cach" not in ra


def test_mat_la_hoan_toan_thi_bi_bo_het():
    assert hs.loc_dac_diem({"tuoi": "30", "mau_toc": "den"}) == {}
    assert hs.loc_dac_diem({}) == {}
    assert hs.loc_dac_diem({"gioi": "NAM "}) == {"gioi": "nam"}


# ══════════════════════════════════════════════════════════════════════════════
#  §2  Bang chung TAT DINH — khong goi ai, khong ton gi
# ══════════════════════════════════════════════════════════════════════════════

def test_bang_chung_doc_tu_ban_ghi_va_phep_do_F0():
    bc = hs.bang_chung(_ban_ghi(), f0=118.0)
    assert bc["ngon_ngu_goc"] == "zh"
    assert bc["so_doan"] == 2
    assert bc["giay_co_thoai"] == 6.0
    assert bc["f0_trung_vi"] == 118.0
    # 10 + 15 ky tu tren 6 giay
    assert bc["ky_tu_moi_giay"] == pytest.approx(25 / 6, abs=0.01)


def test_ban_ghi_rong_KHONG_chia_cho_khong():
    bc = hs.bang_chung({"ngon_ngu": "en", "doan": []})
    assert bc["so_doan"] == 0 and bc["ky_tu_moi_giay"] == 0.0


def test_tom_tat_cat_o_ranh_DOAN_chu_khong_giua_cau():
    """⚠️ Mot cau cut moi model doan tiep phan thieu, va no doan bang token cua
    khach. (Ban sinh doi `hieu_canh.ngu_canh_cho_canh` — cat theo CANH — da bi
    xoa 26/09 cung duong VLM cua `edit_plan`, Task 22; nen tu hom nay bai nay la
    NGUOI DO DUY NHAT cua luat "cat o ranh doan, dung cat giua cau".)"""
    van = hs.tom_tat_ban_ghi(_ban_ghi(), toi_da=14)
    assert van == "mot hai ba"        # doan thu hai khong lot, KHONG bi cat doi


# ══════════════════════════════════════════════════════════════════════════════
#  §3  Dung ho so — phep DO thang phep DOAN
# ══════════════════════════════════════════════════════════════════════════════

class _Run:
    id = "r1"
    owner_id = "uA"
    settings: dict = {}


def _thay_model(monkeypatch, than: dict | None, *, no=None):
    """Thay `ai.goi_tinh_tien` — cua tra tien duy nhat cua app."""
    def gia(db, run, thao_tac, messages, **kw):
        assert thao_tac.ma == ai.HO_SO_NOI_DUNG.ma
        if no is not None:
            raise no
        return {"noi_dung": json.dumps(than, ensure_ascii=False)}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)


def test_GIOI_do_duoc_THANG_gioi_model_doan(monkeypatch):
    """🔑 Mot phep do tren chinh giong dang noi manh hon mot phan doan tu van
    ban da dich, va khi hai cai lech nhau thi cai lech la cai doan."""
    _thay_model(monkeypatch, {"the_loai": "tai lieu", "nhip": "cham",
                              "dac_diem_giong": {"gioi": "nu",
                                                 "phong_cach": "tu_nhien"}})
    ho_so = hs.dung(object(), _Run(), ban_ghi=_ban_ghi(), f0=110.0)
    assert ho_so.dac_diem_giong["gioi"] == "nam"        # 110 Hz -> nam (DO)
    assert ho_so.dac_diem_giong["phong_cach"] == "tu_nhien"   # model dien not


def test_khong_do_duoc_thi_lay_gioi_cua_model(monkeypatch):
    _thay_model(monkeypatch, {"the_loai": "tai lieu", "nhip": "cham",
                              "dac_diem_giong": {"gioi": "nu"}})
    ho_so = hs.dung(object(), _Run(), ban_ghi=_ban_ghi(), f0=0.0)
    assert ho_so.dac_diem_giong == {"gioi": "nu"}


def test_model_HONG_khong_lam_mat_phan_DO_DUOC(monkeypatch):
    """⚠️ May B chet / het ngan sach / sai luoc do: ho so NGHEO di, lan chay
    khong chet. Phan do duoc van con, va mot mat la du de rang giong."""
    _thay_model(monkeypatch, None, no=ai.AiError("may B khong tra loi"))
    ho_so = hs.dung(object(), _Run(), ban_ghi=_ban_ghi(), f0=205.0)
    assert ho_so.dac_diem_giong == {"gioi": "nu"}


def test_model_hong_VA_khong_do_duoc_thi_ho_so_RONG_chu_khong_bia(monkeypatch):
    """⛔ `ADR-V4-001` D-V4-04: khong duoc thoai hoa thanh "giong mac dinh".

    Khong do duoc + model khong tra loi duoc = **khong co can cu**, va ho so
    phai noi dung the. `rang_giong` se bien no thanh `CHUA_RANG`.
    """
    _thay_model(monkeypatch, None, no=ai.AiError("may B khong tra loi"))
    ho_so = hs.dung(object(), _Run(), ban_ghi=_ban_ghi(), f0=0.0)
    assert ho_so.dac_diem_giong == {}


def test_phong_cach_NGOAI_catalog_cua_model_bi_chan_o_day(monkeypatch):
    """Cua thu hai cho cung mot loi — `loi_nhac_ho_so` da khai tu vung, nhung
    mot model khong nghe loi van phai bi chan."""
    _thay_model(monkeypatch, {"the_loai": "tai lieu", "nhip": "cham",
                              "dac_diem_giong": {"phong_cach": "thuyet minh"}})
    ho_so = hs.dung(object(), _Run(), ban_ghi=_ban_ghi(), f0=0.0)
    assert ho_so.dac_diem_giong == {}


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Loi nhac — chay duoc KHI KHONG CO CANH NAO
# ══════════════════════════════════════════════════════════════════════════════

def test_loi_nhac_khong_co_canh_van_mang_bang_chung():
    """🔑 `localize_preserve_picture` khong doc canh nao (0,0 giay `edit_plan`
    trong luot that). Loi nhac vi the phai dung duoc khi `cac_canh` rong — neu
    khong, preset giu hinh vinh vien khong co ho so."""
    bc = hs.bang_chung(_ban_ghi(), f0=118.0)
    van = hc.loi_nhac_ho_so((), "mot hai ba", bang_chung=bc)[0]["content"]
    assert "Cac canh" not in van
    assert "f0_trung_vi" in van and "118" in van


def test_loi_nhac_KHAI_tu_vung_phong_cach_cua_catalog():
    from apps.ltt_voice.giong_mau import NHAN_PHONG_CACH

    van = hc.loi_nhac_ho_so((), "x")[0]["content"]
    for ma in NHAN_PHONG_CACH:
        assert ma in van, f"loi nhac khong khai `{ma}`"


def test_thao_tac_ho_so_KHONG_doi_model_thi_giac():
    """🔴 `loi_nhac_ho_so` khong gui mot khung hinh nao. Khai `can_thi_giac`
    lam lan chay doi mot model dat hon va hiem hon — va lam thao tac nay khong
    bao gio dung duoc o preset khong doc canh."""
    assert ai.HO_SO_NOI_DUNG.can_thi_giac is False


# ══════════════════════════════════════════════════════════════════════════════
#  §5  Nguon cua tung mat duoc GHI RA — de man ho tro noi "vi sao giong nay"
# ══════════════════════════════════════════════════════════════════════════════

def test_nguon_gioi_phan_biet_DO_voi_DOAN():
    assert cao_do.gioi_tu_f0(110.0) == "nam"
    assert cao_do.gioi_tu_f0(210.0) == "nu"
    assert cao_do.gioi_tu_f0(168.0) == "", "vung xam phai tra ve KHONG KHAI"
    assert cao_do.gioi_tu_f0(0.0) == ""
