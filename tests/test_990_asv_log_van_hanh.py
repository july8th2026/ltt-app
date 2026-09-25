"""Log van hanh ASV (25/09) — nguoi GHI da noi vao `job_events`.

Chan doan da chot truoc khi sua: kien truc dung (asv_stage.started_at/
finished_at duoc ghi that, `job_events` co san `append`/`timeline`/visibility),
nhung khong noi nao trong `apps/auto_scan_video/` goi `job_events.append`.
Bon phep kiem duoi day chot bon manh vua noi:

  1. `job_events.append_progress_counter` la BAT BIEN O BIEN — NEM neu thieu
     bo dem, NEM neu bo dem lui.
  2. `JobContext.progress_counter` nen tran dong theo N giay HOAC K don vi.
  3. `run_id` di vao process log (JSONL) qua `_JsonFormatter`.
  4. Tich hop that: `thi_hanh.chay_giai_doan` ghi duoc `stage_enter`/
     `stage_exit` cho MOT giai doan that (`media_prepare`, ffmpeg that).
"""
from __future__ import annotations

import pytest

from tests.test_402_asv_mach_doc_gia import _chay_het_hang_doi, _tao_run, db, kho_tam  # noqa: F401


# ══════════════════════════════════════════════════════════════════════════════
#  1. Bat bien o bien cua job_events.append_progress_counter
# ══════════════════════════════════════════════════════════════════════════════

def _job_that(db):
    from tests.conftest import bao_dam_user
    from platform_core import jobs as jobq

    bao_dam_user(db, "u_nhip")
    job = jobq.submit(db, user_id="u_nhip", app_slug="auto_scan_video",
                      job_type="auto_scan_video.voice_synthesis",
                      params={"run_id": "r1", "owner_id": "u_nhip",
                              "stage": "voice_synthesis"})
    db.commit()
    return job


def test_progress_counter_NEM_khi_thieu_bo_dem(db):
    """Doi chung TRUC TIEP: ham ghi tien do that su NEM neu thieu da_xong/tong."""
    from platform_core import job_events

    job = _job_that(db)
    with pytest.raises(ValueError):
        job_events.append_progress_counter(db, job, da_xong=None, tong=10, don_vi="doan")
    with pytest.raises(ValueError):
        job_events.append_progress_counter(db, job, da_xong=5, tong=None, don_vi="doan")
    # Sau hai lan nem, khong co dong `progress_counter` nao ca — nem KHONG
    # duoc ghi mot ban nua roi moi bao loi. (`submit()` da tu ghi "submitted";
    # chi loc dung ma dang xet.)
    dong = job_events.timeline(db, job.id, include_internal=True)
    assert [e.event_code for e in dong if e.event_code == "progress_counter"] == []


def test_progress_counter_NEM_khi_am(db):
    from platform_core import job_events

    job = _job_that(db)
    with pytest.raises(ValueError):
        job_events.append_progress_counter(db, job, da_xong=-1, tong=10, don_vi="doan")
    dong = job_events.timeline(db, job.id, include_internal=True)
    assert [e.event_code for e in dong if e.event_code == "progress_counter"] == []


def test_progress_counter_NEM_khi_lui(db):
    """Bat bien thu hai: da_xong khong duoc giat lui trong CUNG mot job."""
    from platform_core import job_events

    job = _job_that(db)
    job_events.append_progress_counter(db, job, da_xong=20, tong=100, don_vi="doan")
    db.commit()
    with pytest.raises(ValueError):
        job_events.append_progress_counter(db, job, da_xong=10, tong=100, don_vi="doan")
    # Tien len thi khong sao.
    job_events.append_progress_counter(db, job, da_xong=25, tong=100, don_vi="doan")
    db.commit()
    dong = job_events.timeline(db, job.id, include_internal=True)
    da_xong = [e.details["da_xong"] for e in dong if e.event_code == "progress_counter"]
    assert da_xong == [20, 25]


def test_progress_counter_ghi_dung_noi_dung_va_INTERNAL(db):
    from platform_core import job_events

    job = _job_that(db)
    ev = job_events.append_progress_counter(db, job, da_xong=3, tong=9, don_vi="lo")
    db.commit()
    assert ev.event_code == "progress_counter"
    assert ev.visibility == job_events.INTERNAL
    assert ev.details == {"da_xong": 3, "tong": 9, "don_vi": "lo"}


# ══════════════════════════════════════════════════════════════════════════════
#  2. Tran dong cua JobContext.progress_counter (N giay HOAC K don vi)
# ══════════════════════════════════════════════════════════════════════════════

def test_ctx_progress_counter_nen_dong_khi_chua_du_nguong(db, monkeypatch):
    from platform_core.job_runner import JobContext

    job = _job_that(db)
    ctx = JobContext(job.id)
    # Lan dau LUON ghi (la_dau), bat ke nguong.
    assert ctx.progress_counter(1, 100, don_vi="doan",
                                nhip_giay=30.0, nhip_don_vi=5) is True
    # Chua du CA HAI nguong (0 giay troi qua, 1 don vi < 5) -> nen (khong ghi).
    assert ctx.progress_counter(2, 100, don_vi="doan",
                                nhip_giay=30.0, nhip_don_vi=5) is False
    # Du don vi (>=5) nhung KHONG du giay -> van nen, vi la AND (thua hon).
    assert ctx.progress_counter(6, 100, don_vi="doan",
                                nhip_giay=30.0, nhip_don_vi=5) is False
    # Lan cuoi (da_xong >= tong) LUON ghi, bat ke nguong.
    assert ctx.progress_counter(100, 100, don_vi="doan",
                                nhip_giay=30.0, nhip_don_vi=5) is True

    from platform_core import job_events
    dong = job_events.timeline(db, job.id, include_internal=True)
    ghi = [e.details["da_xong"] for e in dong if e.event_code == "progress_counter"]
    assert ghi == [1, 100]


def test_ctx_progress_counter_ghi_khi_du_ca_hai_nguong(db, monkeypatch):
    import time as _time
    from platform_core import job_runner as jr

    job = _job_that(db)
    ctx = jr.JobContext(job.id)
    assert ctx.progress_counter(1, 100, don_vi="doan",
                                nhip_giay=0.05, nhip_don_vi=3) is True
    _time.sleep(0.06)
    # Du giay (0.06 > 0.05) VA du don vi (4-1=3 >= 3) -> ghi.
    assert ctx.progress_counter(4, 100, don_vi="doan",
                                nhip_giay=0.05, nhip_don_vi=3) is True


# ══════════════════════════════════════════════════════════════════════════════
#  3. run_id di vao process log (_JsonFormatter)
# ══════════════════════════════════════════════════════════════════════════════

def test_run_id_vao_process_log():
    import json
    import logging

    from platform_core.observability import _JsonFormatter, job_logging_context

    fmt = _JsonFormatter()
    rec = logging.LogRecord("apps.auto_scan_video.thi_hanh", logging.INFO,
                            __file__, 1, "test", None, None)
    # Ngoai context: khong co run_id (khong bia dat khoa rong).
    payload = json.loads(fmt.format(rec))
    assert "run_id" not in payload

    with job_logging_context(run_id="asvr_demo123", app_slug="auto_scan_video"):
        rec2 = logging.LogRecord("apps.auto_scan_video.thi_hanh", logging.INFO,
                                 __file__, 1, "test", None, None)
        payload2 = json.loads(fmt.format(rec2))
    assert payload2["run_id"] == "asvr_demo123"
    assert payload2["app_slug"] == "auto_scan_video"


# ══════════════════════════════════════════════════════════════════════════════
#  4. Tich hop THAT: mot giai doan that ghi stage_enter/stage_exit
# ══════════════════════════════════════════════════════════════════════════════

def test_media_prepare_that_ghi_stage_enter_va_stage_exit(db, kho_tam, tmp_path):
    from platform_core import job_events
    from platform_core.models import Job
    from apps.auto_scan_video import features, pipeline

    run = _tao_run(db, owner="u_bien", giu=10, kho=kho_tam, tmp_path=tmp_path,
                   duration_s=3.0)
    # advance (nop media_prepare) + media_prepare that (ffmpeg that).
    dem = _chay_het_hang_doi(db, toi_da=2)
    assert dem == 2

    stage = features.giai_doan_theo_ten(db, run.id, pipeline.MEDIA_PREPARE)
    assert stage.status == "succeeded"
    assert stage.job_id

    job = db.get(Job, stage.job_id)
    dong = job_events.timeline(db, job.id, include_internal=True)
    ma = [e.event_code for e in dong]
    assert "stage_enter" in ma, ma
    assert "stage_exit" in ma, ma

    ra = next(e for e in dong if e.event_code == "stage_exit")
    assert ra.details["trang_thai"] == "succeeded"
    assert ra.details["stage"] == pipeline.MEDIA_PREPARE
    assert ra.details["wall_s"] >= 0
    assert "cpu_s_can_duoi" in ra.details
    assert ra.details["attempt"] == 1
