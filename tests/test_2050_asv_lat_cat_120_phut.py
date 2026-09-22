"""ASV lat cat — video 120 phut o muc GIAI DOAN, dong ho gia + model gia.

Bai toan (docs/auto_scan_video_v6/CHAN_DOAN_TEST_448.md §10): 1.800 doan
(15 doan/phut x 120 phut) = 150 lo x 142 s = 21.300 s trong MOT job tran 3.600 s.

Ba menh de, moi menh de mot phep kiem (docs/auto_scan_video_final/L_VIDEO_DAI.md):
  (a) khong luot (job) nao vuot tran cua no;
  (b) giet giua chung roi chay tiep thi KHONG don vi nao da xong bi lam lai;
  (c) ban ra GIONG HET lan chay mot mach (khong lat cat).

⭐ Dong ho gia (`lat_cat.dong_ho`) cho moi lan goi model "ton" 142 s — so do
   p50 that ngay 10/09 — nen 21.300 s chay trong vai giay.
"""
# ruff: noqa: F811 — fixture nhap tu `test_402` roi nhan lai lam tham so;
#   ca bo test ASV lam the, day khong phai dinh nghia trung.
from __future__ import annotations

import json

import pytest

from tests.test_402_asv_mach_doc_gia import db, kho_tam  # noqa: F401

SO_DOAN_120_PHUT = 1800          # 15 doan/phut x 120 phut
GIAY_MOI_LO = 142.0              # p50 do 10/09 (CHAN_DOAN_TEST_448 §10)


@pytest.fixture(autouse=True)
def _xoa_moc_luot():
    """Phep kiem goi `bat_dau_luot` truc tiep — xoa moc de khong ro sang phep sau."""
    from apps.auto_scan_video import lat_cat

    yield
    lat_cat.ket_thuc_luot()


class DongHoGia:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _ban_ghi_dai(n: int = SO_DOAN_120_PHUT) -> dict:
    from apps.auto_scan_video import ban_ghi

    buoc = 7200.0 / n
    tho = {"segments": [{"start": k * buoc, "end": k * buoc + buoc * 0.8,
                         "text": f"cau so {k + 1}"} for k in range(n)],
           "language": "en", "engine": "gia", "alignment_status": "gia"}
    return ban_ghi.chuan_hoa(tho, thoi_luong_nguon=7200.0)


def _run(db, owner="uLat"):
    from apps.auto_scan_video import features
    from tests.conftest import bao_dam_user

    bao_dam_user(db, owner)
    run = features.tao_run(db, owner_id=owner, source_key="khong-dung",
                           settings={"giong_id": "Minh Đức",
                                     "timing_mode": "fit_original"},
                           uoc_luong_credit=0)
    db.commit()
    return run


@pytest.fixture()
def noi_dung_gia(monkeypatch):
    """Cat dau vao cua CONTENT_PROCESS ve ban ghi 120 phut; model gia + dong ho gia.

    Tra ve `(dong_ho, nhat_ky)`; `nhat_ky` ghi moi lan goi model:
    `(item_key, [ma...])`.
    """
    from apps.auto_scan_video import (ai, ban_bien_tap, canh as canh_mod,
                                      giai_doan_noi_dung as gd, hop_dong_v4,
                                      lat_cat, long_tieng)

    goc = _ban_ghi_dai()
    ci = canh_mod.ChiMucCanh((canh_mod.Canh("canh_0001", 0.0, 7200.0),), 7200.0)
    ban = ban_bien_tap.lap_ban(preset=hop_dong_v4.PRESET_GIU_HINH, chi_muc=ci,
                               hieu_canh=(), ban_ghi=goc)
    monkeypatch.setattr(gd, "_doc_ban_ghi", lambda db, kho, run: (goc, "ck-120"))
    monkeypatch.setattr(gd, "_doc_ban_bien_tap", lambda db, kho, run: (ban, ci))
    monkeypatch.setattr(gd, "_giong_da_chot",
                        lambda db, run: ("Minh Đức", {"nguon": "gia"}))

    dh = DongHoGia()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)
    nhat_ky: list = []
    hong = {"o_lan": 0}          # >0: lan goi thu N "giet" worker

    class WorkerChet(BaseException):
        """Mo phong tien trinh bi giet: KHONG phai Exception de khong nhanh
        `except` nao cua giai doan nuot duoc."""

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None):
        mas = [str(d["ma"]) for d in json.loads(messages[-1]["content"])["doan"]]
        if hong["o_lan"] and len(nhat_ky) + 1 == hong["o_lan"]:
            hong["o_lan"] = 0
            dh.t += GIAY_MOI_LO / 2
            raise WorkerChet()
        dh.t += GIAY_MOI_LO
        nhat_ky.append((item_key, mas))
        than = {"doan": {m: {"chu": "loi viet cua " + m,
                             "cam_xuc": long_tieng.CAM_XUC[0],
                             "kieu_noi": long_tieng.KIEU_NOI[0],
                             "nhan_manh": []} for m in mas}}
        return {"noi_dung": json.dumps(than, ensure_ascii=False), "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    return dh, nhat_ky, hong, WorkerChet


def _chay_theo_luot(db, run, ham, dh, *, toi_da=100):
    """Dong vai hang doi: moi vong = MOT job. Tra `(ket_qua, [giay moi luot])`."""
    from apps.auto_scan_video import features, lat_cat
    from apps.auto_scan_video.tables import AsvRun

    ten = ham.__module__
    luot_giay: list[float] = []
    for _ in range(toi_da):
        lat_cat.bat_dau_luot()
        t0 = dh.t
        try:
            db.expire_all()
            ra = ham(db, _kho(), run=db.get(AsvRun, run.id), ctx=None)
            luot_giay.append(dh.t - t0)
            return ra, luot_giay
        except lat_cat.TiepNoi as tn:
            luot_giay.append(dh.t - t0)
            db.rollback()
            st = features.giai_doan_theo_ten(db, run.id, _giai_doan_cua(ten))
            lat_cat.ghi_tiep_noi(db, st, tn)
            db.commit()
    raise AssertionError("khong xong sau %d luot" % toi_da)


def _giai_doan_cua(ten_module: str) -> str:
    from apps.auto_scan_video import pipeline

    return {"apps.auto_scan_video.giai_doan_noi_dung": pipeline.CONTENT_PROCESS,
            "apps.auto_scan_video.giai_doan_qc_ai": pipeline.QC_AI}[ten_module]


def _kho():
    from platform_core.storage import get_storage

    return get_storage()


def _doc(khoa: str) -> bytes:
    with _kho().open(khoa) as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════════

def test_tran_that_KHONG_chua_noi_120_phut_neu_chay_mot_mach():
    """Doi chung cho (a): khong co lat cat thi bai toan la that — 150 lo x 142 s
    vuot tran 3.600 s gan 6 lan. Neu so nay khong vuot thi phep kiem (a) ben
    duoi khong chung minh gi."""
    from apps.auto_scan_video import lat_cat, long_tieng, pipeline

    tran = lat_cat.tran_giai_doan(pipeline.CONTENT_PROCESS)
    so_lo = -(-SO_DOAN_120_PHUT // long_tieng.DOAN_MOI_LO)
    assert tran == 3600
    assert so_lo * GIAY_MOI_LO > 5 * tran


def test_a_KHONG_luot_nao_vuot_tran_va_c_ban_ra_GIONG_lan_mot_mach(
        db, kho_tam, noi_dung_gia, monkeypatch):
    from apps.auto_scan_video import giai_doan_noi_dung as gd, lat_cat, pipeline

    dh, nhat_ky, _hong, _chet = noi_dung_gia
    tran = lat_cat.tran_giai_doan(pipeline.CONTENT_PROCESS)

    # ── Lan chay LAT CAT ──
    run = _run(db, "uLat1")
    ra, luot = _chay_theo_luot(db, run, gd.chay, dh)
    goi_lat = list(nhat_ky)
    ban_ra_lat = _doc(ra["phan"][0]["staging_key"])

    # (a) moi luot nam trong ngan sach (khong chi trong tran)
    assert len(luot) >= 6, luot
    assert max(luot) <= lat_cat.HE_SO_TRAN * tran, luot
    assert sum(luot) == pytest.approx(150 * GIAY_MOI_LO)
    # Khoa so cai cua lo la DUY NHAT tren ca giai doan (khong `lo_000` lan hai)
    khoa = [k for k, _ in goi_lat]
    assert len(khoa) == len(set(khoa)) == 150
    assert khoa == [f"lo_{i:03d}" for i in range(150)]

    # ── Lan chay MOT MACH (khong lat cat) tren run khac ──
    monkeypatch.setattr(lat_cat, "tran_giai_doan", lambda ten: 10 ** 9)
    monkeypatch.setattr(lat_cat, "LUOT_MUC_TIEU_S", 10 ** 9)
    nhat_ky.clear()
    run2 = _run(db, "uLat2")
    ra2, luot2 = _chay_theo_luot(db, run2, gd.chay, dh)
    assert len(luot2) == 1 and luot2[0] > tran, (
        "doi chung: mot mach PHAI vuot tran that — %s" % luot2)

    # (c) cung loi nhac gui di, cung ban ra tung byte
    assert nhat_ky == goi_lat
    assert ra["phan"][0]["staging_key"] != ra2["phan"][0]["staging_key"]
    assert ban_ra_lat == _doc(ra2["phan"][0]["staging_key"])
    assert ra["tom_tat"] == ra2["tom_tat"]


def test_b_GIET_giua_chung_roi_chay_tiep_KHONG_lam_lai_don_vi_nao(
        db, kho_tam, noi_dung_gia):
    from apps.auto_scan_video import (features, giai_doan_noi_dung as gd,
                                      lat_cat, pipeline)

    dh, nhat_ky, hong, WorkerChet = noi_dung_gia
    run = _run(db, "uLat3")

    # Giet o lan goi thu 50 — giua mot luot noi tiep.
    hong["o_lan"] = 50
    with pytest.raises(WorkerChet):
        _chay_theo_luot(db, run, gd.chay, dh)
    db.rollback()
    st = features.giai_doan_theo_ten(db, run.id, pipeline.CONTENT_PROCESS)
    assert lat_cat.con_tro(st), "phai con con tro cua luot da nhuong truoc do"
    da_xong_truoc = {m for _, mas in nhat_ky for m in mas}
    assert len(da_xong_truoc) == 49 * 12

    ra, _luot = _chay_theo_luot(db, run, gd.chay, dh)

    # Moi doan duoc gui DUNG MOT lan qua ca hai lan chay (lo bi giet chua giao)
    dem: dict = {}
    for _, mas in nhat_ky:
        for m in mas:
            dem[m] = dem.get(m, 0) + 1
    assert len(dem) == SO_DOAN_120_PHUT
    assert max(dem.values()) == 1, "lam lai doan da xong"

    tai_lieu = json.loads(_doc(ra["phan"][0]["staging_key"]))
    assert len(tai_lieu["muc"]) == SO_DOAN_120_PHUT


# ══════════════════════════════════════════════════════════════════════════════
#  QC_AI — cung hinh dang, TRUOC 22/09 khong co diem chot nao
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def qc_gia(monkeypatch):
    from apps.auto_scan_video import ai, giai_doan_qc_ai as gq, lat_cat

    monkeypatch.setenv(gq.BIEN_BAT, "1")
    muc = [{"ma": f"seg_{k:05d}", "goc": f"cau {k}", "chu": f"loi {k}"}
           for k in range(SO_DOAN_120_PHUT)]
    monkeypatch.setattr(gq, "_khoa_theo_duoi", lambda db, run, st, duoi: "k/x.json")
    monkeypatch.setattr(gq, "_doc_json", lambda kho, khoa: {})
    monkeypatch.setattr(gq, "_cac_muc", lambda ban: list(muc))
    dh = DongHoGia()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)
    nhat_ky: list = []

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None):
        dh.t += GIAY_MOI_LO
        nhat_ky.append(item_key)
        so = int(item_key.split("_")[1])
        if so % 7 == 3:                     # vai lo hong -> bi bo, KHONG thu lai
            raise ai.AiError("gia lap hong")
        lo = json.loads(messages[-1]["content"])
        mas = [str(d["ma"]) for d in (lo.get("doan") or [])]
        than = {"doan": {m: {"dat": int(m[-1]) % 2 == 0, "ly_do": "gia",
                             "do_tin": 0.9} for m in mas}}
        return {"noi_dung": json.dumps(than), "su_dung": None}

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)
    return dh, nhat_ky


def test_qc_ai_lat_cat_KHONG_hoi_lai_lo_nao_va_bao_cao_GIONG_mot_mach(
        db, kho_tam, qc_gia, monkeypatch):
    from apps.auto_scan_video import giai_doan_qc_ai as gq, lat_cat, pipeline, qc_ai

    dh, nhat_ky = qc_gia
    tran = lat_cat.tran_giai_doan(pipeline.QC_AI)
    so_lo = -(-SO_DOAN_120_PHUT // qc_ai.DOAN_MOI_LO)

    run = _run(db, "uQc1")
    ra, luot = _chay_theo_luot(db, run, gq.chay, dh)
    assert len(luot) > 1 and max(luot) <= lat_cat.HE_SO_TRAN * tran, luot
    bao_cao_lat = _doc(ra["phan"][0]["staging_key"])
    assert nhat_ky == [f"lo_{i:03d}" for i in range(so_lo)], (
        "moi lo hoi DUNG mot lan, ke ca lo hong (khong thu lai o luot sau)")
    lat_goi = list(nhat_ky)

    monkeypatch.setattr(lat_cat, "tran_giai_doan", lambda ten: 10 ** 9)
    monkeypatch.setattr(lat_cat, "LUOT_MUC_TIEU_S", 10 ** 9)
    nhat_ky.clear()
    run2 = _run(db, "uQc2")
    ra2, luot2 = _chay_theo_luot(db, run2, gq.chay, dh)
    assert len(luot2) == 1 and luot2[0] > tran
    assert nhat_ky == lat_goi
    assert bao_cao_lat == _doc(ra2["phan"][0]["staging_key"])
    assert ra["tom_tat"] == ra2["tom_tat"]


def test_du_phong_lon_hon_ngan_sach_thi_HONG_NGAY_khong_de_job_bi_giet(db, monkeypatch):
    from apps.auto_scan_video import lat_cat, pipeline

    run = _run(db, "uLat9")
    monkeypatch.setattr(lat_cat, "tran_giai_doan", lambda ten: 100)
    with pytest.raises(ValueError):
        lat_cat.mo(db, run, pipeline.CONTENT_PROCESS, van_tay="v",
                   du_phong_s=90.0)


def test_du_phong_moi_giai_doan_VUA_trong_tran_manifest():
    """Cau hinh that: don vi te nhat cua moi giai doan lat cat phai vua MOT job,
    neu khong `lat_cat.mo` hong ngay luc chay that."""
    from apps.auto_scan_video import (ai, canh, giai_doan_ban_bien_tap as gbt,
                                      giai_doan_giong as gg, lat_cat,
                                      nan_cho_vua, pipeline)

    du = {
        pipeline.CONTENT_PROCESS: lat_cat.timeout_goi_ai(ai.CHUYEN_LOI_THOAI),
        pipeline.QC_AI: lat_cat.timeout_goi_ai(ai.QC_NGU_NGHIA),
        pipeline.EDIT_PLAN: (canh.KHUNG_MOI_CANH * gbt.CHO_RUT_KHUNG_S
                             + lat_cat.timeout_goi_ai(ai.DOC_CANH)),
        pipeline.VOICE_SYNTHESIS: ((nan_cho_vua.VONG_TOI_DA + 1) * gg._timeout_tts()
                                   + nan_cho_vua.VONG_TOI_DA
                                   * lat_cat.timeout_goi_ai(ai.RUT_NGAN_CHO_VUA)),
    }
    for ten, giay in du.items():
        ngan_sach = lat_cat.HE_SO_TRAN * lat_cat.tran_giai_doan(ten)
        assert giay + lat_cat.DU_PHONG_NGOAI_GOI_S < ngan_sach, (ten, giay, ngan_sach)


def test_tien_trinh_con_KHONG_song_lau_hon_tran_job(monkeypatch):
    """Demucs (5.400 s) va render (3.600 s) co timeout >= tran job cua chung:
    job bi `_het_gio` giet truoc, tien trinh con mo coi giu GPU. Timeout thuc
    dung phai nam trong ngan sach con lai cua job."""
    from apps.auto_scan_video import (giai_doan_ket_xuat, lat_cat, pipeline,
                                      tach_tieng)

    dh = DongHoGia()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)
    for ten, mac_dinh in ((pipeline.AUDIO_PREPARE, tach_tieng.TIMEOUT_TACH_S),
                          (pipeline.RENDER, giai_doan_ket_xuat.TIMEOUT_RENDER)):
        tran = lat_cat.tran_giai_doan(ten)
        assert mac_dinh >= tran, "doi chung: mac dinh cu PHAI cham tran"
        lat_cat.bat_dau_luot()
        dh.t += 600                                   # da troi 10 phut
        han = lat_cat.han_tien_trinh_con(ten, mac_dinh)
        assert 600 + han <= lat_cat.HE_SO_TRAN * tran, (ten, han)
