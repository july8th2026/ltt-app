"""Động cơ: đồ thị thẳng a→b chạy tới SUCCEEDED; lỗi rẽ nhánh ERROR; huỷ; hạn."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixtures are intentionally requested below.

import ast
import pathlib

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1717_wf_tao_run import wf  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC


@pytest.fixture()
def run(db, wf, monkeypatch):
    from platform_core.workflow import cong_cu, tao_run
    monkeypatch.setattr(cong_cu, "tat_ca", lambda: CC)
    r, _ = tao_run.tao_run(db, workflow=wf, owner_id="u1",
                           trigger_kind="manual", idempotency_key="k")
    return r


def _job_cua(db, run, nid):
    from platform_core.models import Job
    from platform_core.workflow import thi_hanh
    return db.get(Job, thi_hanh.anh_chup_hien_tai(db, run.id, nid).job_id)


def test_do_thi_thang_chay_het(db, run):
    from platform_core import jobs
    from platform_core.workflow import dong_co, may_trang_thai as mtt
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "RUNNING"
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"
    assert mtt.trang_thai_node(db, run.id, "b") == "PENDING"
    jobs.complete(db, _job_cua(db, run, "a"), {"text": "x"})
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert mtt.trang_thai_node(db, run.id, "b") == "QUEUED"
    assert _job_cua(db, run, "b").params["q"] == "x"
    jobs.complete(db, _job_cua(db, run, "b"), {"text": "y"})
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "SUCCEEDED"
    assert run.actual_cost == 6 and run.ket_so_luc is not None


def test_nguon_hong_thi_dich_SKIPPED_va_run_FAILED(db, run):
    from platform_core import jobs
    from platform_core.workflow import dong_co, may_trang_thai as mtt, su_kien
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    jobs.fail(db, _job_cua(db, run, "a"), "hong", retry=False)
    assert dong_co.xu_ly_run(db, run.id, cong_cu=CC) == "FAILED"
    assert mtt.trang_thai_node(db, run.id, "b") == "SKIPPED"
    assert su_kien.doc(db, run.id)[-1].loai == "WorkflowFailed"


def test_xu_ly_hai_lan_khong_nop_doi(db, run):
    from platform_core.models import Job
    from platform_core.workflow import dong_co
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert db.query(Job).filter_by(plan_id=run.id).count() == 1


def test_huy_run_huy_job(db, run):
    """⚠️ Tra job bằng `Job.plan_id == run.id` trực tiếp — KHÔNG qua ảnh chụp
    mới nhất: `huy_run` chuyển node sang CANCELLED bằng `chuyen_node(...)`
    không kèm `job_id`, nên ảnh chụp CANCELLED mới nhất mang `job_id == ""`
    (mặc định của `thi_hanh.ghi_chuyen`) — tra qua `anh_chup_hien_tai` sẽ vỡ."""
    from platform_core.models import JOB_CANCELLED, Job
    from platform_core.workflow import dong_co
    dong_co.xu_ly_run(db, run.id, cong_cu=CC)
    assert dong_co.huy_run(db, run.id, "nguoi dung huy") is True
    assert run.status == "CANCELLED"
    job = db.query(Job).filter_by(plan_id=run.id).one()
    assert job.status == JOB_CANCELLED


def test_dong_co_khong_import_io():
    """Kế thừa bất biến `test_962`: động cơ không gọi ra ngoài (G23)."""
    cay = ast.parse(pathlib.Path("platform_core/workflow/dong_co.py")
                    .read_text(encoding="utf-8"))
    cam = {"requests", "httpx", "urllib", "socket", "subprocess", "aiohttp"}
    for nut in ast.walk(cay):
        if isinstance(nut, (ast.Import, ast.ImportFrom)):
            ten = {a.name.split(".")[0] for a in nut.names} | {
                (getattr(nut, "module", "") or "").split(".")[0]}
            assert not (ten & cam), ten
