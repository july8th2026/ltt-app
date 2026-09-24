"""Cong noi bo Auto Scan Video — vong doi day du qua NAM ham cua cong.

submit -> tien do chay -> ket qua; huy; thu lai mot giai doan hong.

Hang doi, dinh tuyen job, dieu phoi `_advance`, tien, quyen so huu la THAT.
Chi than cua tung giai doan la gia (`thi_hanh.chay_giai_doan`), vi cau hoi o
day la *"cong co di dung duong dich vu khong"*, khong phai *"engine co dung
khong"* — cai do la viec cua `test_402` va cac tep engine.
"""
from __future__ import annotations

import io

import pytest

from tests.conftest import bao_dam_user

CHU = "u-cong-a"
KHAC = "u-cong-b"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'cong.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    monkeypatch.setenv("LTT_AUTO_SCAN_VIDEO", "1")
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core.storage import LocalStorage, set_storage
    set_storage(LocalStorage(str(tmp_path / "kho")))
    gen = dbmod.get_session()
    s = next(gen)
    from platform_core import credit
    for u in (CHU, KHAC):
        bao_dam_user(s, u)
        credit.nap(s, u, 1000)
    s.commit()
    try:
        yield s
    finally:
        s.close()
        set_storage(None)
        dbmod.reset_engine()


def ve_tai_len(db, tmp_path, owner=CHU) -> str:
    """Mot phien tai len DA XONG cua `owner`, dung hop dong `upload_sessions`."""
    from platform_core import upload_sessions
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features
    from tests.fixtures.asv_media import require_ffmpeg, tiny_mp4

    require_ffmpeg()
    tep = tiny_mp4(tmp_path / f"{owner}.mp4", duration_s=1.0)
    phien = upload_sessions.stage_bytes(
        db, get_storage(), user_id=owner, app_slug=features.SLUG,
        filename="a.mp4", content_type="video/mp4", data=tep.read_bytes(),
        max_size=features.TRAN_BEN_VUNG,
        allowed_types=features.KIEU_VIDEO_HOP_LE)
    db.commit()
    return phien.id


#: Cai dat toi thieu hop le. AUTO_MATCH de khong phai dung mot giong LTT Voice.
CAI_DAT = {"timing_mode": "fit_original", "che_do_giong": "AUTO_MATCH",
           "ngon_ngu_nguon": "en", "ngon_ngu_dich": "vi"}


@pytest.fixture()
def giai_doan_gia(monkeypatch):
    """Thay than MOI giai doan. `hong` = tap giai doan se hong o lan thu dau."""
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    from apps.auto_scan_video import features, pipeline, thi_hanh

    trang = {"hong": set(), "da_hong": set()}

    def chay(ten, params, ctx=None):
        gen = get_session()
        s = next(gen)
        try:
            run = features.lay_run(s, params["run_id"], params["owner_id"])
            st = features.giai_doan_theo_ten(s, run.id, ten)
            if ten in trang["hong"] and ten not in trang["da_hong"]:
                trang["da_hong"].add(ten)
                features.danh_dau_hong(s, st, "hong gia", cuoi_cung=True)
                s.commit()
                raise RuntimeError("hong gia")
            khoa = []
            if ten == pipeline.RENDER:
                k = f"asv/{run.owner_id[:16]}/ra/{run.id}.mp4"
                get_storage().put(k, io.BytesIO(b"\x00" * 64), content_type="video/mp4")
                khoa = [k]
            features.danh_dau_xong(s, st, outputs={"stage": ten, "khoa_asset": khoa},
                                   # Van tay THAT: `_advance` doi chieu no.
                                   fingerprint=thi_hanh.van_tay(
                                       ten, run, thi_hanh._gom_dau_vao(s, run.id, ten)),
                                   credit_actual=1)
            s.commit()
            return {"stage": ten, "credit_cost": 1}
        finally:
            s.close()

    monkeypatch.setattr(thi_hanh, "chay_giai_doan", chay)
    return trang


def chay_hang_doi(db, *, dung_khi=None, toi_da=300) -> int:
    """Nhat + chay job nhu worker that. `dung_khi(db)` True -> dung som."""
    from platform_core import jobs
    from platform_core.job_runner import JobContext

    dem = 0
    for _ in range(toi_da):
        job = jobs.claim(db, worker_id="w-cong",
                         capabilities={"api", "ffmpeg", "gpu", "voice"})
        if job is None:
            break
        db.commit()
        ctx = JobContext(job.id)
        ctx.job_type = job.job_type
        try:
            jobs.complete(db, job, jobs.resolve_handler(job.job_type)(dict(job.params), ctx) or {})
        except Exception as exc:        # noqa: BLE001
            jobs.fail(db, job, str(exc), retry=False)
        db.commit()
        dem += 1
        db.expire_all()
        if dung_khi is not None and dung_khi(db):
            break
    db.expire_all()
    return dem


# ══════════════════════════════════════════════════════════════════════════════

def test_vong_doi_submit_tien_do_ket_qua(db, tmp_path, giai_doan_gia):
    from apps.auto_scan_video import cong_noi_bo as cong, pipeline

    phieu = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat=CAI_DAT, upload_id=ve_tai_len(db, tmp_path)))
    assert phieu.trang_thai == "queued" and phieu.credit_giu > 0
    assert phieu.cai_dat["ngon_ngu_nguon"] == "en"

    dau = cong.get_status(db, CHU, phieu.run_id)
    assert dau.phan_tram == 0 and not dau.ket_thuc and not dau.co_ket_qua
    assert [g.ten for g in dau.giai_doan] == [g.ten for g in pipeline.CHUOI]
    with pytest.raises(cong.LoiXungDot):
        cong.get_result(db, CHU, phieu.run_id)

    # Dung giua chung: tien do phai TANG, chua ket thuc.
    chay_hang_doi(db, dung_khi=lambda s: sum(
        g.trang_thai == "succeeded"
        for g in cong.get_status(s, CHU, phieu.run_id).giai_doan) >= 3)
    giua = cong.get_status(db, CHU, phieu.run_id)
    assert 0 < giua.phan_tram < 100 and giua.trang_thai == "running"

    chay_hang_doi(db)
    cuoi = cong.get_status(db, CHU, phieu.run_id)
    assert cuoi.trang_thai == "done" and cuoi.ket_thuc and cuoi.phan_tram == 100
    assert cuoi.co_ket_qua and cuoi.loi == ""
    kq = cong.get_result(db, CHU, phieu.run_id)
    assert kq.khoa_video.endswith(".mp4")
    from platform_core.storage import get_storage
    assert get_storage().exists(kq.khoa_video)


def test_huy_run_dang_cho(db, tmp_path, giai_doan_gia):
    from apps.auto_scan_video import cong_noi_bo as cong

    phieu = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat=CAI_DAT, upload_id=ve_tai_len(db, tmp_path)))
    tt = cong.cancel_run(db, CHU, phieu.run_id)
    assert tt.trang_thai == "cancelled" and tt.ket_thuc
    # Luy dang: huy lan hai khong nem, khong doi gi.
    assert cong.cancel_run(db, CHU, phieu.run_id).trang_thai == "cancelled"
    # Worker nhat job con sau khi huy -> khong lam song lai run.
    chay_hang_doi(db)
    assert cong.get_status(db, CHU, phieu.run_id).trang_thai == "cancelled"
    with pytest.raises(cong.LoiXungDot):
        cong.retry_run(db, CHU, phieu.run_id, "render")


def test_thu_lai_mot_giai_doan_hong_roi_chay_toi_done(db, tmp_path, giai_doan_gia):
    from apps.auto_scan_video import cong_noi_bo as cong, pipeline

    ten = pipeline.TRANSCRIBE
    giai_doan_gia["hong"].add(ten)
    phieu = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat=CAI_DAT, upload_id=ve_tai_len(db, tmp_path)))

    # Dung NGAY sau khi giai doan hong, truoc luot advance quyet toan run.
    chay_hang_doi(db, dung_khi=lambda s: ten in cong.get_status(
        s, CHU, phieu.run_id).giai_doan_hong)
    tt = cong.get_status(db, CHU, phieu.run_id)
    assert ten in tt.giai_doan_hong and not tt.ket_thuc
    assert tt.loi.startswith(ten)

    kq = cong.retry_run(db, CHU, phieu.run_id, ten)
    assert kq.da_dat_lai[0] == ten
    assert ten not in cong.get_status(db, CHU, phieu.run_id).giai_doan_hong

    chay_hang_doi(db)
    assert cong.get_status(db, CHU, phieu.run_id).trang_thai == "done"
    assert cong.get_result(db, CHU, phieu.run_id).khoa_video


def test_hong_roi_advance_quyet_toan_thi_thu_lai_la_XUNG_DOT(db, tmp_path, giai_doan_gia):
    """Hanh vi cua dich vu, khong phai cua cong: run da quyet toan thi nop run moi."""
    from apps.auto_scan_video import cong_noi_bo as cong, pipeline

    giai_doan_gia["hong"].add(pipeline.MEDIA_PREPARE)
    phieu = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat=CAI_DAT, upload_id=ve_tai_len(db, tmp_path)))
    chay_hang_doi(db)
    tt = cong.get_status(db, CHU, phieu.run_id)
    assert tt.trang_thai == "error" and tt.ket_thuc
    with pytest.raises(cong.LoiXungDot) as e:
        cong.retry_run(db, CHU, phieu.run_id, pipeline.MEDIA_PREPARE)
    assert e.value.ma == "xung_dot"


def test_nop_lai_tren_nguon_cua_run_cu(db, tmp_path, giai_doan_gia):
    """`nguon_run_id`: tai dung tep nguon, doi cap ngon ngu — khong tai len lai."""
    from apps.auto_scan_video import cong_noi_bo as cong

    p1 = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat=CAI_DAT, upload_id=ve_tai_len(db, tmp_path)))
    p2 = cong.submit_run(db, CHU, cong.YeuCauChay(
        cai_dat={**CAI_DAT, "ngon_ngu_dich": "en", "ngon_ngu_nguon": "zh"},
        nguon_run_id=p1.run_id))
    assert p2.run_id != p1.run_id and p2.cai_dat["ngon_ngu_dich"] == "en"
    # Nguoi khac khong muon duoc nguon cua CHU.
    with pytest.raises(cong.LoiKhongTimThay):
        cong.submit_run(db, KHAC, cong.YeuCauChay(cai_dat=CAI_DAT,
                                                 nguon_run_id=p1.run_id))
