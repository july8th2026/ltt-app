"""ASV lat cat qua HANG DOI THAT — `advance` nop luot noi tiep, run ve `done`.

`test_2050` chung minh ba menh de o muc giai doan voi 120 phut gia. Tep nay
chung minh phan con lai: CO CHE noi tiep qua hang doi that (claim, handler,
`advance`, dedupe, admission) cho ca ba giai doan dai chay trong chuoi mac
dinh — `edit_plan`, `content_process`, `voice_synthesis` — va ban ra cua ca
chuoi GIONG lan chay mot mach.

Tran moi giai doan duoc ep nho (dong ho gia) de MOI don vi la mot luot.
"""
# ruff: noqa: F811 — fixture nhap tu `test_402` roi nhan lai lam tham so;
#   ca bo test ASV lam the, day khong phai dinh nghia trung.
from __future__ import annotations

import json
import re

import pytest

from tests.fixtures import asv_media as fx_media
from tests.test_402_asv_mach_doc_gia import db, giong_gia, kho_tam  # noqa: F401
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

SO_DOAN = 6

#: Tran ep nho: moi giai doan nhuong sau DUNG mot don vi (xem so hoc trong
#: `test_so_hoc_tran_ep_la_MOT_don_vi_moi_luot`).
TRAN_EP = {"content_process": 500, "edit_plan": 500, "voice_synthesis": 3600}
GIAY = {"chuyen_loi_thoai": 142.0, "doc_canh": 200.0, "tts": 100.0}


class DongHoGia:
    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture()
def chuoi_gia(monkeypatch, giong_gia):
    from apps.auto_scan_video import (ai, canh as canh_mod, giai_doan_ban_bien_tap,
                                      giai_doan_chep_loi, giong_noi, lat_cat,
                                      long_tieng, thi_hanh)

    # ASR: 6 doan trong video 3 giay.
    tho = {"segments": [{"start": k * 0.5, "end": k * 0.5 + 0.4,
                         "text": f"cau thu {k + 1}"} for k in range(SO_DOAN)],
           "language": "en", "engine": "gia", "alignment_status": "gia"}
    monkeypatch.setattr(giai_doan_chep_loi, "chep_loi",
                        lambda duong_tieng, **kw: json.loads(json.dumps(tho)))

    # Ba canh 1 giay, moi canh mot khung.
    def phan_tich(duong, *, thoi_luong, hoi_huy=None, **kw):
        return canh_mod.ChiMucCanh(
            tuple(canh_mod.Canh("canh_%04d" % (i + 1), float(i), float(i + 1),
                                (float(i) + 0.5,)) for i in range(3)), 3.0)

    monkeypatch.setattr(canh_mod, "phan_tich", phan_tich)
    monkeypatch.setattr(giai_doan_ban_bien_tap.canh_mod, "phan_tich", phan_tich,
                        raising=False)
    monkeypatch.setattr(long_tieng, "DOAN_MOI_LO", 1)

    dh = DongHoGia()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)
    goi: list = []

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        goi.append((run_.id, thao_tac.ma, item_key))
        if thao_tac.ma == ai.DOC_CANH.ma:
            dh.t += GIAY["doc_canh"]
            if item_key == "canh_0002":
                raise ai.AiError("gia lap: model tu choi canh 2")
            return fx_media.phan_hoi_ngoai_dich(thao_tac, messages)
        if thao_tac.ma == ai.CHUYEN_LOI_THOAI.ma:
            dh.t += GIAY["chuyen_loi_thoai"]
            mas = [str(d["ma"]) for d in json.loads(messages[-1]["content"])["doan"]]
            than = {"doan": {m: {"chu": "loi viet " + m,
                                 "cam_xuc": long_tieng.CAM_XUC[0],
                                 "kieu_noi": long_tieng.KIEU_NOI[0],
                                 "nhan_manh": []} for m in mas}}
            return {"noi_dung": json.dumps(than), "su_dung": None}
        raise ai.AiError("gia lap: thao tac %s khong dung o day" % thao_tac.ma)

    monkeypatch.setattr(ai, "goi_tinh_tien", gia)

    doc_that = giong_noi.doc_mot_doan

    def doc(chu, **kw):
        dh.t += GIAY["tts"]
        return doc_that(chu, **kw)

    monkeypatch.setattr(giong_noi, "doc_mot_doan", doc)

    # Do thoi gian (dong ho gia) cua MOI job giai doan.
    luot: list = []
    chay_that = thi_hanh.chay_giai_doan

    def chay_do(ten, params, ctx=None):
        t0 = dh.t
        try:
            return chay_that(ten, params, ctx)
        finally:
            luot.append((ten, dh.t - t0))

    monkeypatch.setattr(thi_hanh, "chay_giai_doan", chay_do)
    return dh, goi, luot


def _chay_run(db, kho_tam, owner):
    from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run
    from apps.auto_scan_video import hop_dong_v4

    run = _tao_run(db, owner=owner)
    run.settings = {**dict(run.settings or {}),
                    "preset": hop_dong_v4.PRESET_CAT_THONG_MINH}
    db.commit()
    _chay_het_hang_doi(db, nang_luc={"api", "ffmpeg", "gpu", "voice"}, toi_da=800)
    return run


def _ban_ra(db, run) -> dict:
    """Artifact JSON cua ba giai doan dai, da thay run_id/owner bang nhan co dinh."""
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features, pipeline

    ra = {}
    for ten in (pipeline.EDIT_PLAN, pipeline.CONTENT_PROCESS,
                pipeline.VOICE_SYNTHESIS):
        s = features.giai_doan_theo_ten(db, run.id, ten)
        for k in (s.outputs or {}).get("khoa_asset") or []:
            if k.endswith(".json"):
                with get_storage().open(k) as f:
                    # Khoa kho mang run_id (co khi rut gon) va owner — bo di.
                    ra[ten] = re.sub(r"asvr_[0-9a-f]+", "RUN",
                                     f.read().decode("utf-8")
                                     .replace(run.id, "RUN")
                                     .replace(run.owner_id, "OWN"))
    return ra


def test_so_hoc_tran_ep_la_MOT_don_vi_moi_luot():
    """Tu kiem cau hinh phep kiem: moi tran ep phai (1) chua vua mot don vi te
    nhat — neu khong `lat_cat.mo` hong — va (2) KHONG chua noi don vi thu hai."""
    from apps.auto_scan_video import (ai, giai_doan_giong as gg, lat_cat,
                                      nan_cho_vua)

    du = {
        "content_process": lat_cat.timeout_goi_ai(ai.CHUYEN_LOI_THOAI),
        "edit_plan": 1 * 120 + lat_cat.timeout_goi_ai(ai.DOC_CANH),
        "voice_synthesis": ((nan_cho_vua.VONG_TOI_DA + 1) * gg._timeout_tts()
                            + nan_cho_vua.VONG_TOI_DA
                            * lat_cat.timeout_goi_ai(ai.RUT_NGAN_CHO_VUA)),
    }
    mot = {"content_process": GIAY["chuyen_loi_thoai"], "edit_plan": GIAY["doc_canh"],
           "voice_synthesis": GIAY["tts"]}
    for ten, tran in TRAN_EP.items():
        ngan = lat_cat.HE_SO_TRAN * tran
        d = du[ten] + lat_cat.DU_PHONG_NGOAI_GOI_S
        assert d < ngan, ten
        assert mot[ten] + d > ngan, ten


def test_chuoi_lat_cat_qua_hang_doi_ve_done_va_GIONG_mot_mach(
        db, kho_tam, chuoi_gia, monkeypatch):
    from platform_core.models import Job
    from apps.auto_scan_video import features, lat_cat, pipeline
    from apps.auto_scan_video.tables import RUN_DONE

    from apps.auto_scan_video import giai_doan_ban_bien_tap as gdbbt

    dh, goi, luot = chuoi_gia
    that = lat_cat.tran_giai_doan
    monkeypatch.setattr(lat_cat, "tran_giai_doan",
                        lambda ten: TRAN_EP.get(ten) or that(ten))
    # 🔑 **Phep kiem nay noi ve LAT CAT, khong ve chinh sach do phu bang chung.**
    #
    #    Kich ban co chu y de `canh_0002` hong (de chung minh luot 3 KHONG hoi
    #    lai no). Tu 23/09 `smart_localize` tu choi lap ban khi con canh khong
    #    co bang chung (`gdbbt.PHU_BANG_CHUNG_TOI_THIEU = 1.0`, R-05) — dung
    #    theo san pham, nhung no se lam lan chay dung o `edit_plan` va moi menh
    #    de ve hang doi phia duoi khong bao gio duoc chay.
    #
    # ⛔ Ha nguong o day la ha cho RIENG phep kiem nay, khong ha o san pham.
    #    `tests/test_2025_asv_doc_canh_hong.py` moi la noi chot nguong do.
    monkeypatch.setattr(gdbbt, "PHU_BANG_CHUNG_TOI_THIEU", 0.0)

    # ── Lan chay LAT CAT ──
    run = _chay_run(db, kho_tam, "uHd1")
    run = features.lay_run(db, run.id, "uHd1")
    assert run.status == RUN_DONE, run.error

    # (a) moi job giai doan nam trong ngan sach cua tran EP
    for ten, giay in luot:
        if ten in TRAN_EP:
            assert giay <= lat_cat.HE_SO_TRAN * TRAN_EP[ten], (ten, giay)
    so_luot = {t: sum(1 for x, _ in luot if x == t) for t in TRAN_EP}
    # ⭐ `edit_plan` nhuong sau mot LO, khong mot canh (25/09, lan `asv-toc-do`).
    #    `LO_DOC_CANH` canh duoc hoi CUNG LUC, nen mot luot lat cat mang tron mot
    #    lo: 3 canh / lo 2 = 2 luot. ⛔ Con so 2 o day KHONG duoc go tay — no
    #    phai doc tu chinh hang so, neu khong no se troi khoi san pham.
    #
    # ⚠️ Va dung doc dong nay thanh "lat cat da noi ngan sach": tran thoi gian
    #    cua mot luot KHONG doi (phep kiem (a) ngay tren van chot no). Mot lo hai
    #    loi goi SONG SONG het xap xi thoi gian cua MOT loi goi, nen phan du
    #    phong mot-don-vi cua `lat_cat` van du.
    import math

    from apps.auto_scan_video.giai_doan_ban_bien_tap import LO_DOC_CANH
    assert so_luot == {"content_process": SO_DOAN,
                       "edit_plan": math.ceil(3 / LO_DOC_CANH),
                       "voice_synthesis": SO_DOAN}, so_luot

    # Co che: moi luot mot job RIENG (dedupe `:nK`), `attempt` KHONG tang.
    for ten in TRAN_EP:
        g = pipeline.THEO_TEN[ten]
        jobs = db.query(Job).filter(Job.plan_id == run.id,
                                    Job.job_type == g.job_type).all()
        assert len(jobs) == so_luot[ten], ten
        assert {j.status for j in jobs} == {"done"}, ten
        assert len({j.dedupe_key for j in jobs}) == len(jobs), ten
        s = features.giai_doan_theo_ten(db, run.id, ten)
        assert int(s.attempt) == 1, (ten, s.attempt)
        assert "tiep_noi" not in (s.outputs or {}), ten

    # (b) KHONG lam lai: moi canh / moi lo hoi DUNG mot lan — ke ca canh 2
    #     (hong o luot 2, khong duoc hoi lai o luot 3).
    cua_run = [(m, k) for r, m, k in goi if r == run.id]
    assert sorted(k for m, k in cua_run if m == "doc_canh") == [
        "canh_0001", "canh_0002", "canh_0003"]
    lo = [k for m, k in cua_run if m == "chuyen_loi_thoai"]
    assert len(lo) == len(set(lo)) == SO_DOAN
    ban_lat = _ban_ra(db, run)

    # ── Lan chay MOT MACH ──
    monkeypatch.setattr(lat_cat, "tran_giai_doan", lambda ten: 10 ** 9)
    monkeypatch.setattr(lat_cat, "LUOT_MUC_TIEU_S", 10 ** 9)
    luot.clear()
    run2 = _chay_run(db, kho_tam, "uHd2")
    run2 = features.lay_run(db, run2.id, "uHd2")
    assert run2.status == RUN_DONE, run2.error
    assert all(sum(1 for x, _ in luot if x == t) == 1 for t in TRAN_EP)

    # (c) ban ra cua ba giai doan giong het (sau khi bo run_id/owner)
    ban_mach = _ban_ra(db, run2)
    assert set(ban_lat) == set(TRAN_EP)
    assert ban_lat == ban_mach
