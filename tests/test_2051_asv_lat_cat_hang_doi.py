"""ASV lat cat qua HANG DOI THAT — `advance` nop luot noi tiep, run ve `done`.

`test_2050` chung minh ba menh de o muc giai doan voi 120 phut gia. Tep nay
chung minh phan con lai: CO CHE noi tiep qua hang doi that (claim, handler,
`advance`, dedupe, admission) cho cac giai doan dai chay trong chuoi mac dinh,
va ban ra cua ca chuoi GIONG lan chay mot mach.

🔴 **26/09/2026 — `edit_plan` thoi la mot giai doan NHIEU DON VI** (B1 §9b).
   Truoc do moi canh la mot loi goi VLM, tuc mot don vi lat cat tra tien. Nay
   ca giai doan la HAI buoc KHONG chia duoc — mot luot tach canh
   (PySceneDetect) va MOT luot ffmpeg `blackdetect`+`freezedetect` tren ca tep —
   nen no ⛔ khong con don vi nao de nhuong giua. Han cua hai buoc do duoc kep
   boi `lat_cat.han_tien_trinh_con`, cung khuon voi demucs/render.

⇒ Nen `edit_plan` ROI KHOI `TRAN_EP`, va do la mot menh de chu khong phai mot
  cho trong: no phai chay DUNG mot luot. `test_2050` chot phan han thoi gian.

Tran moi giai doan duoc ep nho (dong ho gia) de MOI don vi la mot luot.
"""
# ruff: noqa: F811 — fixture nhap tu `test_402` roi nhan lai lam tham so;
#   ca bo test ASV lam the, day khong phai dinh nghia trung.
from __future__ import annotations

import json
import re

import pytest

from tests.test_402_asv_mach_doc_gia import db, giong_gia, kho_tam  # noqa: F401
from tests.rao_chan_nang import demucs_gia_lap  # noqa: F401

SO_DOAN = 6

#: `do_hinh` = MOT luot ffmpeg giai ma ca tep (thay `doc_canh` cua ban VLM cu).
GIAY = {"chuyen_loi_thoai": 142.0, "do_hinh": 200.0, "tts": 100.0}


def _du_phong_giong() -> float:
    """Du phong MOT don vi cua `voice_synthesis` — MOT cho khai, ⛔ khong chep.

    🔴 **Vi sao ham nay ton tai (26/09).** `TRAN_EP["voice_synthesis"]` truoc day
       la hang `3600` go tay, va con so ay duoc chon cho `VONG_TOI_DA = 2`. Khi
       Task 4 ha `VONG_TOI_DA` xuong `1`, du phong mot don vi teo lai va bat dang
       thuc *"tran KHONG chua noi don vi thu hai"* vo — bai kiem do voi
       `assert (100.0 + 1980.0) > 3060.0`, ⛔ khong vi mot loi nao trong san pham.

    ⭐ Thuoc la **DOC thay vi CHEP**: cong thuc o day phai la cung mot bieu thuc
       ma `giai_doan_giong.chay` truyen cho `lat_cat.mo`, nen doi `VONG_TOI_DA`
       ⛔ khong bao gio lam do bai kiem nay nua.
    """
    from apps.auto_scan_video import (ai, giai_doan_giong as gg, lat_cat,
                                      nan_cho_vua)

    return ((nan_cho_vua.VONG_TOI_DA + 1) * gg._timeout_tts()
            + nan_cho_vua.VONG_TOI_DA
            * lat_cat.timeout_goi_ai(ai.RUT_NGAN_CHO_VUA)
            + lat_cat.DU_PHONG_NGOAI_GOI_S)


def _tran_ep_giong() -> float:
    """Tran thoi gian ep cho MOT luot `voice_synthesis`.

    Hai bat dang thuc phai dong thoi dung (xem
    `test_so_hoc_tran_ep_la_MOT_don_vi_moi_luot`):

        d < HE_SO_TRAN * tran        (mot don vi te nhat con VUA)
        HE_SO_TRAN * tran < mot + d  (don vi THU HAI thi KHONG vua)

    ⇒ `tran` nam trong khoang mo `(d / HE_SO_TRAN, (mot + d) / HE_SO_TRAN)`. Lay
      **diem giua** de khong bam vao hai dau — mot gia tri sat bien la mot bai
      kiem se do vi mot thay doi lam tron.
    """
    from apps.auto_scan_video import lat_cat

    return (_du_phong_giong() + GIAY["tts"] / 2) / lat_cat.HE_SO_TRAN


#: Tran ep nho: moi giai doan nhuong sau DUNG mot don vi (xem so hoc trong
#: `test_so_hoc_tran_ep_la_MOT_don_vi_moi_luot`).
#:
#: ⚠️ `voice_synthesis` TINH RA tu cac hang so cua san pham, ⛔ khong go tay —
#:    xem `_du_phong_giong`. Hai so con lai van go tay vi du phong cua chung
#:    ⛔ khong phu thuoc hang so nao dang doi.
#:
#: ⛔ `edit_plan` ⛔ KHONG co trong bang — xem docstring dau tep (26/09).
TRAN_EP = {"content_process": 500, "voice_synthesis": _tran_ep_giong()}

#: Ba giai doan co artifact JSON duoc doi soat giua hai lan chay.
BA_GIAI_DOAN = ("edit_plan", "content_process", "voice_synthesis")


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

    # ⭐ 26/09: `edit_plan` do hinh bang MOT luot ffmpeg cho ca tep. Ba canh deu
    #    co loi thoai (ASR gia phu kin 0-2,9 s) nen ⛔ khong canh nao bi cat, va
    #    do phu bang chung la 1,0 — tuc ⛔ khong can ha `PHU_BANG_CHUNG_TOI_THIEU`
    #    nhu ban VLM cu phai lam.
    def do_hinh_gia(duong, *, thoi_luong, timeout=None):
        dh.t += GIAY["do_hinh"]
        return {"khoang_den": [], "khoang_dong": [],
                "den_s": 0.0, "dong_s": 0.0, "so_loi_giai_ma": 0}

    monkeypatch.setattr(giai_doan_ban_bien_tap.qc, "do_hinh", do_hinh_gia)

    dh = DongHoGia()
    monkeypatch.setattr(lat_cat, "dong_ho", dh)
    goi: list = []

    def gia(db_, run_, thao_tac, messages, *, stage, item_key, uoc_credit=0,
            ctx=None, temperature=None, luoc_do=None):
        goi.append((run_.id, thao_tac.ma, item_key))
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
    nhat — neu khong `lat_cat.mo` hong — va (2) KHONG chua noi don vi thu hai.

    ⚠️ **Tu 26/09 con so cua `voice_synthesis` duoc TINH RA, ⛔ khong chep.** Ban
       cu go `3600` — mot gia tri dan xuat tu `VONG_TOI_DA = 2` — nen Task 4 (ha
       xuong `1`) lam bai nay do o `assert (100.0 + 1980.0) > 3060.0` ma san pham
       ⛔ khong he sai. Xem `_du_phong_giong` / `_tran_ep_giong`.
    """
    from apps.auto_scan_video import ai, lat_cat

    du = {
        "content_process": (lat_cat.timeout_goi_ai(ai.CHUYEN_LOI_THOAI)
                            + lat_cat.DU_PHONG_NGOAI_GOI_S),
        # ⭐ CUNG bieu thuc ma `TRAN_EP` dung — mot cho khai, nen hai ben ⛔ khong
        #    the lech nhau.
        "voice_synthesis": _du_phong_giong(),
    }
    mot = {"content_process": GIAY["chuyen_loi_thoai"],
           "voice_synthesis": GIAY["tts"]}
    for ten, tran in TRAN_EP.items():
        ngan = lat_cat.HE_SO_TRAN * tran
        d = du[ten]
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
    # ⭐ **26/09: KHONG con phai ha nguong do phu bang chung.**
    #
    #    Ban VLM cu de `canh_0002` hong co chu y, nen `smart_localize` tu choi lap
    #    ban (`PHU_BANG_CHUNG_TOI_THIEU = 1,0`, R-05) va lan chay dung o
    #    `edit_plan` truoc khi moi menh de ve hang doi duoc chay ⇒ phep kiem phai
    #    ha nguong CHO RIENG no.
    #
    # 🔑 Phep do tat dinh phu MOI canh, nen do phu la 1,0 that su. Cai ha nguong
    #    do bien mat, va do la mot CHENH LECH DO DUOC giua hai bo do: bo cu co
    #    mot ti le hong khong dieu khien duoc (8/18 luot that, 23/09), bo moi
    #    ⛔ khong co.
    assert gdbbt.PHU_BANG_CHUNG_TOI_THIEU == 1.0, (
        "nguong do phu phai la gia tri SAN PHAM — phep kiem nay khong con "
        "phai ha no")

    # ── Lan chay LAT CAT ──
    run = _chay_run(db, kho_tam, "uHd1")
    run = features.lay_run(db, run.id, "uHd1")
    assert run.status == RUN_DONE, run.error

    # (a) moi job giai doan nam trong ngan sach cua tran EP
    for ten, giay in luot:
        if ten in TRAN_EP:
            assert giay <= lat_cat.HE_SO_TRAN * TRAN_EP[ten], (ten, giay)
    so_luot = {t: sum(1 for x, _ in luot if x == t) for t in TRAN_EP}
    # ⭐ **`edit_plan` chay DUNG MOT luot (26/09)** — no ⛔ khong con don vi nao de
    #    nhuong giua. Day la mot menh de, nen no duoc chot tuong minh:
    assert sum(1 for x, _ in luot if x == pipeline.EDIT_PLAN) == 1, (
        "edit_plan phai chay dung MOT luot — no khong con la giai doan nhieu "
        "don vi (B1 §9b)")

    # 🔴 **`voice_synthesis` nhuong sau mot KHE DOC, ⛔ khong sau mot DOAN** (25/09,
    #    lan `b2-gop-khe`). `nan_thoi_luong.gop_khe` da dieu khien that: 2-4 doan
    #    lien ke chua vua duoc doc trong MOT luot, nen so lat cat = so KHE DOC,
    #    nho hon hoac bang `SO_DOAN`.
    #
    # ⛔ Con so nay KHONG duoc go tay: doc tu chinh bao cao cua giai doan
    #    (`tom_tat.so_khe_doc`), neu khong no troi khoi luat gop ngay lan ai do
    #    doi `TRAN_GOP_KHE`. Va `ban_ke` van co mot dong cho MOI `ma` goc — phan
    #    ay do o `tests/test_4700_asv_gop_khe_that.py`.
    gd_giong = features.giai_doan_theo_ten(db, run.id, pipeline.VOICE_SYNTHESIS)
    so_khe_doc = int((gd_giong.outputs or {}).get("so_doan") or 0)
    assert 0 < so_khe_doc <= SO_DOAN, (so_khe_doc, SO_DOAN)
    assert int((gd_giong.outputs or {}).get("so_ma_noi_dung") or 0) == SO_DOAN, (
        "`so_ma_noi_dung` phai la so `ma` cua content.json")
    assert so_luot == {"content_process": SO_DOAN,
                       "voice_synthesis": so_khe_doc}, so_luot

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
    # ⭐ 26/09: `edit_plan` ⛔ khong goi model nao, nen so cai cua no PHAI rong.
    assert [k for m, k in cua_run if m == "doc_canh"] == [], (
        "edit_plan lai goi VLM — xem test_3912 §1")
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
    assert all(sum(1 for x, _ in luot if x == t) == 1 for t in BA_GIAI_DOAN)

    # (c) ban ra cua ba giai doan giong het (sau khi bo run_id/owner)
    ban_mach = _ban_ra(db, run2)
    assert set(ban_lat) == set(BA_GIAI_DOAN)
    assert ban_lat == ban_mach
