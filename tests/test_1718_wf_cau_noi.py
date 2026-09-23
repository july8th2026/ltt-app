"""Cầu nối: một attempt = một job, không hold riêng; kết thúc job → tín hiệu + wakeup."""
from __future__ import annotations
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.

import pytest

from tests.test_1711_wf_luoc_do_dong_co import db  # noqa: F401
from tests.test_1717_wf_tao_run import wf  # noqa: F401
from tests.test_1716_wf_xuat_ban_va_bao_gia_api import CC
# Bản GỐC (chưa bị `run` fixture monkeypatch) — tên cục bộ này trỏ thẳng vào
# đối tượng hàm thật, `monkeypatch.setattr(cong_cu, "tat_ca", ...)` chỉ đổi
# THUỘC TÍNH trên module `cong_cu`, không đổi được đối tượng đã bind ở đây.
# Dùng cho phép kiểm admission (Task 9 fix round 1) cần ToolSpec THẬT.
from platform_core.workflow.cong_cu import tat_ca as _tat_ca_that


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
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    dat = {"text.chat": replace(CC["text.chat"], tinh_gia=lambda p: 999)}
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=dat) is None
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.error.startswith("vuot_tran_bao_gia")


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


# ── Fix round 1 (review + controller rulings) ───────────────────────────────


def test_giai_tham_so_that_bai_ghi_ma_dau_vao_sai(db, run):
    """Node "b" tham chiếu output của "a" trước khi "a" từng chạy — cầu nối
    phải FAILED "b" ngay từ READY (chưa từng nộp job) với mã `dau_vao_sai`
    (đúng MỘT lần trong `error`, không lặp — review round 1)."""
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "b", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, _node(db, run, "b"), cong_cu=CC) is None
    assert mtt.trang_thai_node(db, run.id, "b") == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "b")
    assert anh.error.startswith("dau_vao_sai")
    assert anh.error.count("dau_vao_sai") == 1


def test_cancel_hook_bao_hieu_CANCELLED_ma_bi_huy(db, run):
    """`jobs.cancel` phải gọi hook (spec §3.1) và node phải CANCELLED với mã
    `bi_huy` — không phải `provider_loi` (review round 1, Important #1)."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    assert jobs.cancel(db, job) is True
    assert cau_noi.ap_ket_qua(db, run, "a") == "CANCELLED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.error.startswith("bi_huy")


def test_fail_thu_lai_KHONG_bao_hieu(db, run):
    """`retry=True` còn lượt ⇒ job về `queued` (`retry_scheduled` sự kiện),
    KHÔNG phải terminal — hook KHÔNG được gọi, node vẫn QUEUED chờ."""
    from platform_core import jobs
    from platform_core.models import JOB_QUEUED, Job, Wakeup, WaitpointSignal
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.fail(db, job, "gian doan tam thoi", retry=True)
    assert job.status == JOB_QUEUED
    assert db.query(WaitpointSignal).filter_by(
        waitpoint_id=job.parent_id).count() == 0
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="job").count() == 0
    assert mtt.trang_thai_node(db, run.id, "a") == "QUEUED"
    assert cau_noi.ap_ket_qua(db, run, "a") is None


def test_bao_ket_thuc_goi_lai_luy_dang_khong_nem_loi(db, run):
    """Gọi `bao_ket_thuc` hai lần cho cùng một job (job_runner gọi trùng,
    retry hạ tầng) chỉ được để lại ĐÚNG MỘT tín hiệu và MỘT wakeup, và lần gọi
    lại KHÔNG được ném lỗi (review round 1, Important #2: `except Exception`
    cũ nuốt luôn lỗi thật; giờ chỉ nuốt `IntegrityError` của khoá trùng)."""
    from platform_core import jobs
    from platform_core.models import Job, Wakeup, WaitpointSignal
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, {"text": "hello"})       # goi hook lan 1 (qua complete)
    cau_noi.bao_ket_thuc(db, job)                   # goi lai truc tiep lan 2
    assert db.query(WaitpointSignal).filter_by(
        waitpoint_id=job.parent_id).count() == 1
    assert db.query(Wakeup).filter_by(run_id=run.id, kind="job").count() == 1


def test_credit_cost_bao_cao_bi_ep_ve_gia_tran(db, run):
    """Handler báo `credit_cost` VƯỢT `gia_tran` đã chốt lúc publish — cầu
    nối không được thu quá trần đã báo giá cho khách (spec §5.8)."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.complete(db, job, {"text": "ok", "credit_cost": 999})
    assert cau_noi.ap_ket_qua(db, run, "a") == "SUCCEEDED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.cost_credit == 3          # gia_tran cua node "a" (CC: tinh_gia=3)
    assert run.actual_cost == 3


def test_nop_job_ghi_admission_tu_toolspec_that(db, run):
    """`nop_job` phải đi đúng con đường nộp canonical
    (`public_api/invocation.py:submit`, dòng ~500-560): `Job.admission_resource`
    /`admission_slots` phải khớp `ToolSpec` THẬT của registry khi tool đó khai
    admission — thiếu bước này `jobs.claim()` coi mọi job GPU là miễn phí và có
    thể nhận quá số thẻ (review round 1, controller-found, load-bearing cho
    GPU). Dùng `audio_pause.run` (bộ ba tĩnh `admission_resource="gpu_stt"`,
    `admission_slots=1`) — không cần tham số `model` như `text.chat`."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt

    cc_that = _tat_ca_that()
    assert cc_that["audio_pause.run"].spec is not None
    node = {"id": "audio_test", "type": "app.audio_pause.run",
            "params": {"audio": "x", "pause_plan": {}}, "gia_tran": 10}
    mtt.chuyen_node(db, run.id, "audio_test", sang="READY", mo_ta="t")
    jid = cau_noi.nop_job(db, run, node, cong_cu=cc_that)
    assert jid is not None
    job = db.get(Job, jid)
    assert job.admission_resource == "gpu_stt"
    assert job.admission_slots > 0


def test_nop_job_cong_cu_bien_mat_thi_FAILED_khong_KeyError(db, run):
    """F5 (final-review.md): tool bị gỡ khỏi registry sau khi version đã
    publish (app tắt cờ, tool đổi tên) — `cc_all[...]` tra tay ném `KeyError`
    thẳng vào `mot_vong`, nuốt theo lượt (`except Exception`), node kẹt QUEUED
    tới khi hết `TRAN_RUN` 20h. Phải FAILED có mã rõ ngay trong lượt này."""
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    assert cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu={}) is None
    assert mtt.trang_thai_node(db, run.id, "a") == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.error.startswith("cong_cu_khong_con")


def test_ap_ket_qua_cong_cu_bien_mat_thi_FAILED_khong_KeyError(db, run):
    """F5 — cùng bẫy, cửa vào thứ hai: job ĐÃ nộp xong (tool còn khi nộp) rồi
    mới bị gỡ khỏi registry trước khi job kết thúc. `ap_ket_qua` tra
    `side_effect` bằng tay ở nhánh không-SUCCEEDED cũng ném `KeyError`."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    jobs.fail(db, job, "hong", retry=False)
    assert cau_noi.ap_ket_qua(db, run, "a", cong_cu={}) == "FAILED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.error.startswith("cong_cu_khong_con")


def test_ap_ket_qua_thieu_gia_tran_fail_closed(db, run, monkeypatch):
    """M2 (final-review.md): thiếu `gia_tran` (không nên xảy ra — bộ biên
    dịch luôn ghi, `_ban_publish` từ chối version chưa biên dịch) phải
    FAIL CLOSED (trần = 0), khớp mặc định của `nop_job` — trước fix,
    `ap_ket_qua` mặc định fail-OPEN (thu hết `credit_cost` báo cáo, không
    trần) khi thiếu khoá này, hai bản sao của MỘT luật trôi khỏi nhau."""
    from platform_core import jobs
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt, thi_hanh

    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))

    goc = cau_noi._node_cua

    def _thieu_tran(db_, run_, node_id):
        n = dict(goc(db_, run_, node_id))
        n.pop("gia_tran", None)
        return n
    monkeypatch.setattr(cau_noi, "_node_cua", _thieu_tran)

    jobs.complete(db, job, {"text": "ok", "credit_cost": 999})
    assert cau_noi.ap_ket_qua(db, run, "a") == "SUCCEEDED"
    anh = thi_hanh.anh_chup_hien_tai(db, run.id, "a")
    assert anh.cost_credit == 0, (
        "thieu gia_tran phai fail CLOSED (tran=0), khong duoc fail-open")


def test_nop_job_khong_admission_khi_CongCu_gia_khong_co_spec(db, run):
    """`CongCu` giả (không đi qua `cong_cu.tat_ca()`, `spec is None`, như mọi
    fixture `CC` khác trong tệp này) phải giữ hành vi CŨ nguyên vẹn: không
    admission, không lỗi — đối chứng cho phép kiểm trên."""
    from platform_core.models import Job
    from platform_core.workflow import cau_noi, may_trang_thai as mtt
    assert CC["text.chat"].spec is None
    mtt.chuyen_node(db, run.id, "a", sang="READY", mo_ta="t")
    job = db.get(Job, cau_noi.nop_job(db, run, _node(db, run, "a"), cong_cu=CC))
    assert job.admission_resource == "" and job.admission_slots == 0
