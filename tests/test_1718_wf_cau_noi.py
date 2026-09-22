"""Cầu nối: một attempt = một job, không hold riêng; kết thúc job → tín hiệu + wakeup."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

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


def _node(db, run, nid):
    from platform_core.models import WorkflowVersion
    g = db.get(WorkflowVersion, run.version_id).graph
    return next(n for n in g["nodes"] if n["id"] == nid)


def test_nop_job_khong_giu_tien_rieng(db, run):
    from platform_core import credit
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC)
    job = db.get(Job, jid)
    assert job.origin == "workflow" and job.plan_id == run.id
    assert job.params["owner_id"] == "u1"
    assert credit.so_da_giu(db, job.id) == 0
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"


def test_ket_thuc_job_sinh_tin_hieu_wakeup_va_chi_phi(db, run):
    from platform_core import jobs
    from platform_core.models import Job, Wakeup
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, {"text": "xin chao"})
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="job").count() == 1
    assert cau_noi.ap_ket_qua(db, run, "a") == "SUCCEEDED"
    from platform_core.workflow import thi_hanh
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.output_ref == {"text": "xin chao"} and anh.cost_credit == 3
    assert run.actual_cost == 3


def test_tham_so_giai_tu_output_nguon(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    ja = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, ja, {"text": "noi dung"})
    cau_noi.ap_ket_qua(db, run, "a")
    mtt.chuyen_node(db, run.id, "b", sang="READY", mo_ta="t")
    jb = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "b"), cong_cu=CC))
    assert jb.params["q"] == "noi dung"


def test_vuot_tran_bao_gia_thi_node_FAILED_khong_nop(db, run):
    from dataclasses import replace
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    dat = {"text.chat": replace(CC["text.chat"], tinh_gia=lambda p: 999)}
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=dat) is None
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"


def test_job_loi_khong_tinh_tien(db, run):
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.fail(db, job, "hong", retry=False)
    assert cau_noi.ap_ket_qua(db, run, "a") == "FAILED"
    assert run.actual_cost == 0


def test_mo_ho_irreversible_la_ABANDONED(db, run):
    from dataclasses import replace
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    cc = {"text.chat": replace(CC["text.chat"], side_effect="irreversible")}
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=cc))
    job.provider_state = jobs.PROVIDER_AMBIGUOUS
    jobs.fail(db, job, "mat ket noi sau khi gui", retry=False)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu=cc) == "ABANDONED"
