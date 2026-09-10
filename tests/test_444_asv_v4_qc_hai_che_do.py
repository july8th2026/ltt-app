"""Pha 18 — QC biet hai che do render.

Bon nhom:

  A. T3 theo che do  — bam luong hinh chi co nghia o preset GIU HINH
  B. T2 theo che do  — thoi luong so voi MONG DOI, khong phai voi nguon
  C. T13             — ban ra hop le nhung TOAN DEN van la mot lan giao hong
  D. Bang chung      — bao cao noi no da do theo luat nao, va song sot khi hong
"""
from __future__ import annotations

import pytest

from apps.auto_scan_video import che_do_render as cdr, qc


def _dau_vao(**doi):
    """Mot bo dau vao DAT, de tung phep kiem chi doi dung thu no muon do."""
    goc = {
        "tt_ra": {"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        "tt_nguon": {"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        "am_luong": {"lufs": qc.LUFS_DICH, "dinh_that": -2.0},
        "ke_hoach": {"doan": [], "so_doan_bi_cat": 0, "troi_toi_da_ms": 0},
        "ban_ke_tieng": {"doan": []},
        "ban_dung_lop": [],
        "do_sang": 40.0,
    }
    goc.update(doi)
    return goc


def _muc(bc, ma):
    return next(m for m in bc["muc"] if m["ma"] == ma)


# ══════════════════════════════════════════════════════════════════════════════
#  A. T3 theo che do
# ══════════════════════════════════════════════════════════════════════════════

def test_che_do_CAT_thi_T3_KHONG_AP_DUNG_du_co_bam():
    """🔴 Menh de trung tam cua pha 18, va cong thoat goi dich danh no.

    Preset cat **ma hoa lai** luong hinh — bat buoc, vi cat bang stream copy chi
    cat duoc tai keyframe (GOP do duoc: 8,333 giay). Nen bam KHONG BAO GIO khop.

    ⛔ De T3 so bam o che do nay la chot mot dieu ta **co y khong lam**, va no lam
       QC chan dung cai no phai cho qua: moi lan chay preset cat deu hong.
    """
    bc = qc.kiem(**_dau_vao(bam_ra="aaa", bam_nguon="bbb",
                            che_do_render=cdr.CAT_MA_HOA_LAI))
    assert _muc(bc, "T3")["trang_thai"] == qc.KHONG_AP_DUNG
    assert bc["dat"], "che do cat bi QC chan vi mot phep so vo nghia"


def test_che_do_SAO_CHEP_thi_T3_VAN_so_bam():
    """Va chieu nguoc lai: preset giu hinh **sao chep** luong hinh, nen bam phai
    khop — do la loi hua D-ASV-03, va no van duoc canh giu."""
    dat = qc.kiem(**_dau_vao(bam_ra="aaa", bam_nguon="aaa",
                             che_do_render=cdr.SAO_CHEP))
    assert _muc(dat, "T3")["trang_thai"] == qc.DAT

    hong = qc.kiem(**_dau_vao(bam_ra="aaa", bam_nguon="bbb",
                              che_do_render=cdr.SAO_CHEP))
    assert _muc(hong, "T3")["trang_thai"] == qc.HONG
    assert not hong["dat"]


def test_khong_khai_che_do_thi_GIU_HANH_VI_CU():
    """⭐ Mot ho so QC cu (chua co truong che do) van phai doc duoc va van phai
    so bam — khong duoc am tham tro thanh de dai voi du lieu cu."""
    bc = qc.kiem(**_dau_vao(bam_ra="aaa", bam_nguon="bbb"))
    assert _muc(bc, "T3")["trang_thai"] == qc.HONG


# ══════════════════════════════════════════════════════════════════════════════
#  B. T2 theo che do
# ══════════════════════════════════════════════════════════════════════════════

def test_che_do_CAT_so_thoi_luong_voi_MONG_DOI_khong_phai_voi_nguon():
    """🔴 Ban ra ngan hon nguon dung bang phan da cat — do la **muc dich cua san
    pham**, khong phai mot khiem khuyet.

    So voi nguon o day se lam T2 hong o MOI lan chay preset cat.
    """
    bc = qc.kiem(**_dau_vao(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 60.0},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        che_do_render=cdr.CAT_MA_HOA_LAI, thoi_luong_mong_doi=60.0))
    assert _muc(bc, "T2")["trang_thai"] == qc.DAT
    assert bc["dat"]


def test_ban_ra_LECH_so_voi_mong_doi_van_bi_bat():
    """Va chot khong bi noi long: lech qua nguong van hong, chi la so voi mot
    con so DUNG."""
    bc = qc.kiem(**_dau_vao(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 55.0},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        che_do_render=cdr.CAT_MA_HOA_LAI, thoi_luong_mong_doi=60.0))
    assert _muc(bc, "T2")["trang_thai"] == qc.HONG


def test_ban_ra_DAI_HON_mong_doi_luon_hong_du_trong_dung_sai():
    """⛔ "Khong bao gio dai hon" la mot chot RIENG, khong phai he qua cua
    `abs(lech) <= 0,5`: mot ban ra dai hon 0,3 giay van vi pham loi hua §3 —
    khach dua vao mot video, khong dua vao mot khoang thoi gian de dien vao."""
    bc = qc.kiem(**_dau_vao(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 60.3},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 100.0},
        che_do_render=cdr.CAT_MA_HOA_LAI, thoi_luong_mong_doi=60.0))
    assert _muc(bc, "T2")["trang_thai"] == qc.HONG


def test_khong_khai_mong_doi_thi_lui_ve_thoi_luong_NGUON():
    bc = qc.kiem(**_dau_vao())
    assert _muc(bc, "T2")["mong_doi"] == 100.0


# ══════════════════════════════════════════════════════════════════════════════
#  C. T13 — ban ra rong / toan den
# ══════════════════════════════════════════════════════════════════════════════

def test_ban_ra_TOAN_DEN_bi_CHAN():
    """🔴 Mot tep **hop le, dung thoi luong, dung am luong, va toan mau den** van
    la mot lan giao hong — va truoc pha 18 khong chot nao bat duoc no.

    T1 chi hoi "co luong hinh khong", ma mot luong hinh toan den van la mot luong
    hinh.
    """
    bc = qc.kiem(**_dau_vao(do_sang=0.4))
    assert _muc(bc, "T13")["trang_thai"] == qc.HONG
    assert not bc["dat"]


def test_canh_TOI_THAT_van_qua_duoc():
    """⚠️ Nguong RAT thap co y: mot canh dem that co the trung binh duoi 10. Ta
    khong doan chat luong nghe thuat — ta bat truong hop **khong co gi ca**."""
    bc = qc.kiem(**_dau_vao(do_sang=8.0))
    assert _muc(bc, "T13")["trang_thai"] == qc.DAT


def test_khong_do_duoc_do_sang_thi_KHONG_AP_DUNG_chu_khong_HONG():
    """⛔ Khong do duoc khac han do ra sai. Bien mot phep do that bai thanh mot
    ket luan "hong" la tu tao ra bao dong gia — va bao dong gia lam nguoi ta
    ngung doc bao cao."""
    assert _muc(qc.kiem(**_dau_vao(do_sang=None)), "T13")["trang_thai"] == qc.KHONG_AP_DUNG
    assert _muc(qc.kiem(**_dau_vao(do_sang=-1.0)), "T13")["trang_thai"] == qc.KHONG_AP_DUNG


def test_do_sang_KHONG_duyet_het_khung():
    """🔑 Mot video 2 gio co 216.000 khung, va cau hoi "co phai toan den khong"
    khong can 216.000 phep do. Chot rang so mau la HUU HAN va nho."""
    assert 0 < qc.SO_KHUNG_DO_SANG <= 32


# ══════════════════════════════════════════════════════════════════════════════
#  D. Bao cao noi no da do theo LUAT NAO
# ══════════════════════════════════════════════════════════════════════════════

def test_bao_cao_GHI_che_do_da_do():
    """🔑 "T3 khong ap dung" co nghia hoan toan khac giua hai preset. Mot bao cao
    khong ghi che do la mot bao cao khong doc lai duoc."""
    bc = qc.kiem(**_dau_vao(che_do_render=cdr.CAT_MA_HOA_LAI,
                            thoi_luong_mong_doi=60.0))
    assert bc["che_do_render"] == cdr.CAT_MA_HOA_LAI
    assert bc["thoi_luong_mong_doi"] == 60.0


def test_PHIEN_BAN_QC_da_duoc_nang():
    """⛔ Khong nang thi mot lan chay lai se dung lai bao cao QC cu tu cache —
    bao cao duoc lam boi mot bo luat khong biet preset cat ton tai."""
    assert qc.PHIEN_BAN_QC >= 2


def test_bao_cao_van_LIET_KE_MOI_muc_hong_chu_khong_nem():
    """Mot bao cao liet ke moi muc hong co ich hon mot ngoai le noi ve muc dau."""
    bc = qc.kiem(**_dau_vao(
        tt_ra={"co_video": False, "co_tieng": False, "thoi_luong": 999.0},
        do_sang=0.0))
    assert len(bc["muc_hong"]) >= 3
    assert not bc["dat"]


# ══════════════════════════════════════════════════════════════════════════════
#  E. CHO NOI — giai doan co truyen dung thu vao `kiem` khong
# ══════════════════════════════════════════════════════════════════════════════
#
# 🔴 **Bon nhom tren do CHINH SACH, va kiem dot bien chi ra chung khong do CHO
#    NOI.** Moi phep kiem o tren goi thang `qc.kiem` voi tham so tuong minh, nen
#    hai dot bien lam `giai_doan_qc` truyen SAI gia tri vao van xanh:
#
#      * doc che do tu `settings` thay vi tu ban dung
#      * khong truyen `thoi_luong_mong_doi`
#
# ⭐ Va do dung la cho mot lan chay preset cat se hong trong thuc te: chinh sach
#    dung, day du, va khong bao gio duoc goi voi dung tham so.

from tests.test_402_asv_mach_doc_gia import (asr_gia, db, dich_gia,  # noqa: E402,F401
                                             giong_gia, kho_tam)
from tests.test_440_asv_v4_long_tieng import _nhieu_canh, _run_cat  # noqa: E402
from tests.rao_chan_nang import demucs_gia_lap  # noqa: E402,F401


def test_CHO_NOI_giai_doan_QC_doc_che_do_tu_BAN_DUNG(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """🔑 Doc tu BAN DUNG, khong suy lai tu `settings`.

    Ban dung la thu da **thuc su duoc render**. Neu hai nguon lech nhau thi cai
    dung la cai da chay — suy lai o day se cho QC do mot lan chay khac voi lan
    chay that.
    """
    from apps.auto_scan_video import che_do_render as cdr, features, pipeline
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi

    _nhieu_canh(monkeypatch)
    run = _run_cat(db, kho_tam, tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.QC)
    assert gd is not None and gd.status == "succeeded", (
        "QC: %s %s" % (getattr(gd, "status", None), getattr(gd, "error", "")))

    import json

    from platform_core.storage import get_storage

    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        bc = json.loads(f.read().decode("utf-8"))

    assert bc["che_do_render"] == cdr.CAT_MA_HOA_LAI, (
        "QC khong doc che do tu ban dung — no dang do mot lan chay khac")
    assert bc["thoi_luong_mong_doi"] > 0, (
        "QC khong duoc truyen thoi luong mong doi, nen T2 dang so voi NGUON")

    t3 = next(m for m in bc["muc"] if m["ma"] == "T3")
    assert t3["trang_thai"] == qc.KHONG_AP_DUNG, (
        "T3 van so bam o mot lan chay DA MA HOA LAI")
    t2 = next(m for m in bc["muc"] if m["ma"] == "T2")
    assert t2["mong_doi"] == bc["thoi_luong_mong_doi"]


def test_CHO_NOI_preset_GIU_HINH_van_so_bam(
        tmp_path, monkeypatch, db, kho_tam, asr_gia, dich_gia, giong_gia):
    """Va chieu nguoc lai o chinh cho noi: preset mac dinh van phai so bam, tuc
    loi hua D-ASV-03 van duoc canh giu qua ca duong day."""
    import json

    from apps.auto_scan_video import che_do_render as cdr, features, pipeline
    from platform_core.storage import get_storage
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db)
    db.expire_all()

    gd = features.giai_doan_theo_ten(db, run.id, pipeline.QC)
    assert gd is not None and gd.status == "succeeded"
    khoa = next(k for k in (gd.outputs or {}).get("khoa_asset") or []
                if k.endswith(".json"))
    with get_storage().open(khoa) as f:
        bc = json.loads(f.read().decode("utf-8"))

    assert bc["che_do_render"] == cdr.SAO_CHEP
    t3 = next(m for m in bc["muc"] if m["ma"] == "T3")
    assert t3["trang_thai"] in (qc.DAT, qc.HONG), (
        "preset giu hinh ma T3 khong ap dung — loi hua sao chep luong hinh dang "
        "khong duoc canh giu boi thu gi ca")
