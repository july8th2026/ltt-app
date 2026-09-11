"""Pha 18 — QC la mot CONG that, va chan doan duoc tu du lieu ben.

Cong thoat cua pha nay co hai nua, va nua thu hai de bi bo qua: *QC la mot cong
phat hanh that* **va** *chan doan van hanh lam duoc tu du lieu ben cua app/nen
tang*. Mot bo QC do rat gioi ma khong chan gi thi truot nua dau; mot cong chan
tot ma chi ghi vao log tam thi truot nua sau.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import select

from apps.auto_scan_video import features, pipeline, qc, quan_sat
from apps.auto_scan_video.tables import (RUN_DONE, RUN_ERROR, STAGE_SUCCEEDED,
                                         AsvAsset)
from tests.fixtures import asv_media as fx
from tests.test_402_asv_mach_doc_gia import (  # noqa: F401
    _chay_het_hang_doi, _tao_run, asr_gia, db, dich_gia, giong_gia, kho_tam)

# 🔴 Pha 13: cac phep kiem trong tep nay chay HET chuoi, nen chung cham toi
#    `audio_prepare` — va truoc pha 13 dieu do co nghia la chung nap
#    **htdemucs THAT** moi luot gate, tren mot may dang phuc vu khach.
#    Fixture autouse duoi day thay dung mieng nang do; ffmpeg, kho, CSDL,
#    hang doi va worker van that.  (`LTT_TEST_NANG=1` de chay model that)
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

NANG_LUC = {"api", "ffmpeg", "gpu", "voice"}


def _dau_vao_dat(**ghi_de):
    """Mot bo dau vao ma MOI dung sai deu dat. Cac phep kiem duoi lam hong TUNG
    cai mot tu day, nen moi lan do chi ra dung mot nguyen nhan."""
    goc = dict(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 10.0},
        tt_nguon={"co_video": True, "co_tieng": True, "thoi_luong": 10.0},
        am_luong={"lufs": -14.0, "dinh_that": -2.0},
        ke_hoach={"doan": [
            {"ma": "1", "dat_tai_ms": 0, "dai_ms": 900,
             "ngan_sach_ms": 1000, "troi_sau_ms": 0},
            {"ma": "2", "dat_tai_ms": 1000, "dai_ms": 900,
             "ngan_sach_ms": 1000, "troi_sau_ms": 0},
        ], "so_doan_bi_cat": 0, "troi_toi_da_ms": 0},
        ban_ke_tieng={"doan": [{"ma": "1", "khoa": "a"}, {"ma": "2", "khoa": "b"}]},
        ban_dung_lop=[{"ma": "1", "dat_tai_ms": 0}, {"ma": "2", "dat_tai_ms": 1000}],
        bam_ra="abc", bam_nguon="abc",
    )
    goc.update(ghi_de)
    return goc


# ══════════════════════════════════════════════════════════════════════════════
#  §1  Bo do — moi dung sai phai NO duoc
# ══════════════════════════════════════════════════════════════════════════════

def test_dau_vao_tot_thi_moi_muc_deu_dat():
    """Chieu am. Mot bo QC do nham se lam MOI lan chay hong, va do la mot cach
    hong dat hon nhieu so voi mot bo QC de lot."""
    bc = qc.kiem(**_dau_vao_dat())
    assert bc["dat"], f"dau vao tot ma bao hong: {bc['muc_hong']}"


@pytest.mark.parametrize("ma,ghi_de", [
    ("T1", {"tt_ra": {"co_video": True, "co_tieng": False, "thoi_luong": 10.0}}),
    ("T2", {"tt_ra": {"co_video": True, "co_tieng": True, "thoi_luong": 12.0}}),
    ("T3", {"bam_ra": "khac", "bam_nguon": "abc"}),
    ("T4", {"am_luong": {"lufs": -10.0, "dinh_that": -2.0}}),
    ("T5", {"am_luong": {"lufs": -14.0, "dinh_that": -0.2}}),
    ("T6", {"ban_ke_tieng": {"doan": [{"ma": "1", "khoa": "a"}]}}),
    ("T7", {"ban_dung_lop": [{"ma": "1", "dat_tai_ms": 0},
                             {"ma": "2", "dat_tai_ms": 5000}]}),
])
def test_moi_dung_sai_deu_NO_duoc(ma, ghi_de):
    """⛔ Mot dung sai khong the no la mot dung sai khong canh gi ca.

    Day la phep kiem quan trong nhat cua tep: no chung minh cong **do that**,
    chu khong phai luon tra `dat`.
    """
    bc = qc.kiem(**_dau_vao_dat(**ghi_de))
    assert ma in bc["muc_hong"], f"{ma} khong no khi dang le phai no"
    assert not bc["dat"]


def test_ban_ra_DAI_HON_nguon_luon_hong_du_lech_nho():
    """§3 hua giu nguyen do dai. "Dai hon 0,3 giay" van la mot loi hua bi vi
    pham, khong phai mot sai so trong dung sai."""
    bc = qc.kiem(**_dau_vao_dat(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 10.3}))
    assert "T2" in bc["muc_hong"]


def test_ngan_hon_trong_dung_sai_thi_DAT():
    """Chieu nguoc lai: `-shortest` cat theo hinh nen ngan hon mot chut la binh
    thuong, va mot nguong hai chieu se danh hong moi lan chay dung."""
    bc = qc.kiem(**_dau_vao_dat(
        tt_ra={"co_video": True, "co_tieng": True, "thoi_luong": 9.8}))
    assert "T2" not in bc["muc_hong"]


def test_T11_no_khi_troi_vuot_ngan_sach_ba_doan():
    ke = _dau_vao_dat()["ke_hoach"]
    ke["doan"][0]["troi_sau_ms"] = 99_999
    bc = qc.kiem(**_dau_vao_dat(ke_hoach=ke))
    assert "T11" in bc["muc_hong"]


# ══════════════════════════════════════════════════════════════════════════════
#  §2  T8/T9/T10 — khong ap dung, va PHAI noi ra
# ══════════════════════════════════════════════════════════════════════════════

def test_T8_T9_T10_bao_la_khong_ap_dung_KEM_LY_DO():
    """⛔ Lang le bo chung khoi bao cao la sai: mot cong it muc hon ma khong noi
    gi trong y het mot cong day du."""
    bc = qc.kiem(**_dau_vao_dat())
    theo_ma = {m["ma"]: m for m in bc["muc"]}
    for ma in ("T8", "T9", "T10"):
        assert theo_ma[ma]["trang_thai"] == qc.KHONG_AP_DUNG
        assert len(theo_ma[ma]["mo_ta"]) > 40, f"{ma} khong ghi ly do"


def test_muc_KHONG_AP_DUNG_khong_bao_gio_duoc_tinh_la_dat():
    bc = qc.kiem(**_dau_vao_dat())
    for m in bc["muc"]:
        if m["trang_thai"] == qc.KHONG_AP_DUNG:
            assert m["trang_thai"] != qc.DAT


def test_bao_cao_liet_ke_DU_cac_dung_sai():
    """Chot theo TAP HOP. Bo sot mot dung sai la mot cong thung mot lo, va lo do
    khong the thay bang cach nhin bao cao.

    ⚠️ **Pha 18 mo tap hop tu T1-T12 thanh T1-T13, co chu dinh.**

       T13 bat mot truong hop khong chot nao truoc do bat duoc: mot tep **hop le,
       dung thoi luong, dung am luong, va toan mau den**. T1 chi hoi "co luong
       hinh khong", ma mot luong hinh toan den van la mot luong hinh.

    ⭐ Mo mot chot theo tap hop la mot hanh dong phai CO Y — do la ca ly do no
       chot tap hop thay vi chot so luong: doi so luong thi khong ai phai giai
       thich gi, doi tap hop thi phai noi ra them cai gi va vi sao.

    ⚠️ **Pha 27 mo tiep thanh T1-T16.** Ba dung sai duoc them, va moi cai bit
       mot cau hoi ma de bai pha 27 goi ten trong khi khong chot nao hoi:

         T14  preset giu hinh co THUC SU khong ma hoa lai khong. T3 da hoi dieu
              nay bang cach bam ca luong hinh — nhung T3 roi ve `KHONG_AP_DUNG`
              ngay khi khong bam duoc, va khi ay **khong ai** kiem loi hua cua
              preset. T14 la luoi thu hai, mien phi: bo ma hoa, kich thuoc va
              goc xoay da nam san trong ket qua ffprobe da chay.

         T15  moi dong phu de co NAM TRONG ban ra khong. Mot dong dat qua cuoi
              la mot dong khong ai thay: khach tra tien, tep `.ass` hop le,
              ffmpeg khong bao gi. Chot nay ra doi cung pha 14.

         T16  luong hinh va luong tieng co dai bang nhau khong. T2 do do dai
              CONTAINER — mot con so van dung khi hai luong ben trong lech
              nhau, tuc dung luc hong dung thu san pham nay ban.

    🔑 Va `PHIEN_BAN_QC` phai tang cung luc, neu khong mot lan chay lai se dung
       lai bao cao cu tu cache — bao cao do mot bo luat chua biet ba muc nay
       ton tai lam ra, va no se bao "dat".
    """
    bc = qc.kiem(**_dau_vao_dat())
    assert {m["ma"] for m in bc["muc"]} == {f"T{i}" for i in range(1, 17)}
    assert qc.PHIEN_BAN_QC >= 3, (
        "mo tap hop ma khong nang PHIEN_BAN_QC: lan chay lai se phuc vu bao "
        "cao cu tu cache")


def test_bao_cao_KHONG_nem_khi_co_muc_hong():
    """Mot bao cao liet ke MOI muc hong co ich hon mot ngoai le noi ve muc dau."""
    bc = qc.kiem(**_dau_vao_dat(
        tt_ra={"co_video": False, "co_tieng": False, "thoi_luong": 99.0}))
    assert len(bc["muc_hong"]) >= 2, "chi bao mot muc trong khi hong nhieu muc"


# ══════════════════════════════════════════════════════════════════════════════
#  §3  QC CHAN duoc — nua de quen nhat cua cong thoat
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def run_xong(db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia):
    fx.require_ffmpeg()
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    return run


def test_lan_chay_that_QUA_duoc_cong(run_xong, db):
    """Chieu am, tren du lieu that. Neu cong khong qua duoc thi no khong phai
    mot cong ma la mot buc tuong."""
    assert features.lay_run(db, run_xong.id, "uA").status == RUN_DONE
    s = features.giai_doan_theo_ten(db, run_xong.id, pipeline.QC)
    assert s.status == STAGE_SUCCEEDED
    assert (s.outputs or {}).get("qc_dat") is True


def test_QC_hong_thi_RUN_KHONG_ve_done(db, kho_tam, tmp_path, asr_gia,
                                       dich_gia, giong_gia, monkeypatch):
    """🔑 CHINH LA CONG THOAT, va ban dau toi lam SAI cho nay.

    Ban dau `thi_hanh` goi `danh_dau_xong` roi moi nem: dong `asv_stage` ghi
    `succeeded`, `_advance` dem du chin giai doan, va lan chay ve `done` **du
    bao cao QC noi `dat: False`**. Cong van do va van cho qua.

    ⛔ Mot cong khong chan thi khong phai cong — va no te hon khong co cong, vi
       no trong nhu co.
    """
    fx.require_ffmpeg()
    that = qc.kiem

    def _hong(**kw):
        bc = that(**kw)
        bc["dat"] = False
        bc["muc_hong"] = ["T4"]
        bc["so_muc_hong"] = 1
        return bc
    monkeypatch.setattr(qc, "kiem", _hong)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    run = features.lay_run(db, run.id, "uA")
    assert run.status == RUN_ERROR, "QC hong ma lan chay van ve done"


def test_QC_hong_van_LUU_bao_cao(db, kho_tam, tmp_path, asr_gia, dich_gia,
                                 giong_gia, monkeypatch):
    """⭐ Thu tu co y: artifact duoc promote TRUOC khi giai doan bao hong.

    Khac biet giua "lan chay cua ban hong" va "lan chay cua ban hong o muc T4,
    do duoc -10,0 LUFS so voi dich -14,0" — va nguoi can cau thu hai nhat la
    nguoi ho tro, khong phai khach.
    """
    fx.require_ffmpeg()
    that = qc.kiem

    def _hong(**kw):
        bc = that(**kw)
        bc["dat"] = False
        bc["muc_hong"] = ["T4"]
        return bc
    monkeypatch.setattr(qc, "kiem", _hong)

    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    bao = db.execute(select(AsvAsset).where(
        AsvAsset.run_id == run.id,
        AsvAsset.created_by_stage == pipeline.QC)).scalars().all()
    assert bao, "lan chay hong ma khong de lai bao cao QC nao"


def test_QC_hong_KHONG_duoc_thu_lai_ba_lan(db, kho_tam, tmp_path, asr_gia,
                                           dich_gia, giong_gia, monkeypatch):
    """Chay lai cung mot ban render cho cung mot phep do. Thu lai mot phep do
    tat dinh la ba lan cho vo ich."""
    from platform_core.models import Job

    fx.require_ffmpeg()
    that = qc.kiem
    monkeypatch.setattr(qc, "kiem", lambda **kw: {**that(**kw), "dat": False,
                                                  "muc_hong": ["T4"]})
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)

    j = db.execute(select(Job).where(
        Job.plan_id == run.id,
        Job.job_type == "asv_media.qc")).scalars().first()
    assert j is not None
    assert int(j.attempts or 0) <= 1, f"QC da thu {j.attempts} lan"


# ══════════════════════════════════════════════════════════════════════════════
#  §4  Chan doan tu du lieu BEN (muc 4-7)
# ══════════════════════════════════════════════════════════════════════════════

def test_dong_thoi_gian_dung_tu_du_lieu_ben_khong_tu_log(run_xong, db):
    dt = quan_sat.dong_thoi_gian(db, run_xong)
    assert dt["run_id"] == run_xong.id
    assert [m["giai_doan"] for m in dt["giai_doan"]] == list(pipeline.TEN_GIAI_DOAN)
    assert all(m["trang_thai"] == STAGE_SUCCEEDED for m in dt["giai_doan"])
    assert any(m["giay"] is not None for m in dt["giai_doan"])


def test_ky_su_ho_tro_dinh_vi_duoc_giai_doan_hong_MA_KHONG_doc_thu_muc_tam(
        db, kho_tam, tmp_path, asr_gia, dich_gia, giong_gia, monkeypatch):
    """Dung phep thu ma Prompt 18 dat ra."""
    from apps.auto_scan_video import ket_xuat

    fx.require_ffmpeg()
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do",
                        lambda *a, **k: (_ for _ in ()).throw(
                            ket_xuat.KetXuatError("ep hong")))
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    run = features.lay_run(db, run.id, "uA")

    dt = quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
    assert dt["giai_doan_hong"] == [pipeline.RENDER], (
        "khong chi ra duoc giai doan nao hong")
    muc = next(m for m in dt["giai_doan"] if m["giai_doan"] == pipeline.RENDER)
    assert muc["job_id"], "khong lan ra duoc job cua giai doan hong"
    assert muc["so_lan_thu"] >= 1
    assert "lan" in muc and muc["lan"] == "asv_media"


def test_ban_cho_KHACH_khong_lo_chi_tiet_van_hanh(db, kho_tam, tmp_path,
                                                  asr_gia, dich_gia, giong_gia,
                                                  monkeypatch):
    """Muc 6-7. Mac dinh la ban cho khach, va no khong duoc mang job id, ten
    worker, hay thong diep loi tho."""
    from apps.auto_scan_video import ket_xuat

    fx.require_ffmpeg()
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do",
                        lambda *a, **k: (_ for _ in ()).throw(
                            ket_xuat.KetXuatError("C:\\Users\\That\\tam\\x.mp4 hong")))
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    run = features.lay_run(db, run.id, "uA")

    goi = json.dumps(quan_sat.dong_thoi_gian(db, run), ensure_ascii=False)
    assert "C:\\\\Users" not in goi and "Users" not in goi
    assert "job_id" not in goi
    assert "worker" not in goi
    assert "chu_so_huu" not in goi

    # Nhung ban cho VAN HANH thi phai co — neu khong, no vo dung.
    goi_vh = json.dumps(quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True),
                        ensure_ascii=False)
    assert "job_id" in goi_vh and "chu_so_huu" in goi_vh


def test_mac_dinh_la_ban_CHO_KHACH():
    """⛔ Mot ham mac dinh tra ve ban day du roi doi nguoi goi nho tat di la mot
    ham se ro ri o lan quen dau tien."""
    import inspect

    sig = inspect.signature(quan_sat.dong_thoi_gian)
    assert sig.parameters["cho_van_hanh"].default is False


def test_tom_tat_loi_cho_khach_chi_noi_TEN_giai_doan(db, kho_tam, tmp_path,
                                                     asr_gia, dich_gia,
                                                     giong_gia, monkeypatch):
    from apps.auto_scan_video import ket_xuat

    fx.require_ffmpeg()
    monkeypatch.setattr(ket_xuat, "_chay_co_tien_do",
                        lambda *a, **k: (_ for _ in ()).throw(
                            ket_xuat.KetXuatError("bi mat: sk-abc123")))
    run = _tao_run(db, kho=kho_tam, tmp_path=tmp_path)
    _chay_het_hang_doi(db, nang_luc=NANG_LUC)
    run = features.lay_run(db, run.id, "uA")

    cau = quan_sat.tom_tat_loi_cho_khach(db, run)
    assert pipeline.RENDER in cau
    assert "sk-abc123" not in cau


def test_khong_hong_thi_tom_tat_loi_RONG(run_xong, db):
    assert quan_sat.tom_tat_loi_cho_khach(db, run_xong) == ""
