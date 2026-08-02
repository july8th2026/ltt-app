"""
W0.1/W0.2 — kiểm ĐỒNG THỜI trên PostgreSQL thật (SQLite bỏ qua FOR UPDATE và
pg_advisory_lock nên KHÔNG chứng minh được gì về race). Các test này là bằng
chứng cho hai bất biến tiền/hàng-đợi mà audit 2026-07-31 nêu là chưa được test:

1. `credit.giu_cho` không double-spend khi nhiều request song song của cùng user;
2. `jobs.claim` (FOR UPDATE SKIP LOCKED) không để hai worker nhặt trùng một job.

Chạy: đặt `LTT_TEST_DATABASE_URL` trỏ tới một database PostgreSQL DÙNG RIÊNG cho
test (test này DROP/CREATE mọi bảng). Không đặt → cả file tự bỏ qua, nên
`pytest` trên máy phát triển không có PostgreSQL vẫn xanh.
"""
from __future__ import annotations

import os
import threading

import pytest

PG_URL = os.environ.get("LTT_TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not PG_URL,
    reason="Can LTT_TEST_DATABASE_URL (PostgreSQL rieng) de kiem dong thoi.",
)


@pytest.fixture()
def Sess():
    """Sessionmaker trỏ tới DB test PostgreSQL, bảng dựng sạch mỗi test."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import platform_core.models  # noqa: F401 — đăng ký bảng vào Base
    from platform_core.db import Base

    engine = create_engine(PG_URL, future=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield maker
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_giu_cho_khong_double_spend_dong_thoi(Sess):
    """Số dư 10, tám request song song mỗi cái giữ 10: đúng MỘT thành công,
    số dư cuối = 0 (không âm). Không có advisory lock thì nhiều cái cùng qua và
    số dư âm — đây chính là lỗ hổng P0-1."""
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    s = Sess()
    u = tao_nguoi_dung(s, email="race@x.com", password="matkhau-tot-12")
    s.commit()
    uid = u.id
    credit.cap_tay(s, uid, 10, by="test")
    s.commit()
    s.close()

    N = 8
    ket_qua: list[str] = []
    barrier = threading.Barrier(N)

    def worker(i: int) -> None:
        ss = Sess()
        try:
            barrier.wait()  # ép tất cả vào giu_cho gần như cùng lúc
            credit.giu_cho(ss, uid, 10, job_id=f"job-{i}")
            ss.commit()
            ket_qua.append("ok")
        except credit.ThieuCreditError:
            ss.rollback()
            ket_qua.append("thieu")
        except Exception as e:  # noqa: BLE001 — ghi lại để chẩn đoán nếu vỡ
            ss.rollback()
            ket_qua.append(f"err:{type(e).__name__}:{e}")
        finally:
            ss.close()

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    assert ket_qua.count("ok") == 1, ket_qua        # đúng một lần giữ được
    s2 = Sess()
    try:
        assert credit.so_du(s2, uid) == 0            # không âm, không mất tiền
    finally:
        s2.close()


def test_claim_khong_nhac_trung_hai_worker(Sess):
    """Hàng đợi 20 job, hai worker nhặt song song: mỗi job đúng một worker lấy,
    tổng đúng 20, không trùng. Chứng minh FOR UPDATE SKIP LOCKED (P0 hàng đợi)."""
    from platform_core import jobs
    from platform_core.users import tao_nguoi_dung

    s = Sess()
    u = tao_nguoi_dung(s, email="q@x.com", password="matkhau-tot-12")
    s.commit()
    uid = u.id
    N = 20
    for i in range(N):
        jobs.submit(s, user_id=uid, app_slug="demo", job_type="demo.reverse",
                    params={"i": i})
    s.commit()
    s.close()

    lay: dict[str, list[str]] = {"w1": [], "w2": []}
    start = threading.Barrier(2)

    def worker(name: str) -> None:
        start.wait()
        while True:
            ss = Sess()
            try:
                job = jobs.claim(ss, worker_id=name)
                if job is None:
                    ss.commit()
                    ss.close()
                    break
                lay[name].append(job.id)
                ss.commit()      # giữ trạng thái running -> không bị nhặt lại
            finally:
                ss.close()

    ts = [threading.Thread(target=worker, args=(n,)) for n in ("w1", "w2")]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    tat_ca = lay["w1"] + lay["w2"]
    assert len(tat_ca) == N                 # nhặt hết
    assert len(set(tat_ca)) == N            # không job nào bị nhặt hai lần


def test_claim_bon_child_agent_khong_trung(Sess):
    """Fan-out Agent dùng cùng queue Q26: hai worker phải chia đúng 4 child."""
    from platform_core import jobs
    from platform_core.agent import runs
    from platform_core.models import AGENT_AWAITING_APPROVAL, AGENT_RUNNING

    s = Sess()
    run = runs.create_run(s, user_id="agent-user", goal="fanout")
    runs.transition(s, run, AGENT_AWAITING_APPROVAL)
    run.status = AGENT_RUNNING  # structural P3 fixture; P5 approval is tested below
    for i in range(4):
        runs.submit_child(s, run, step_id="s1", app_slug="demo",
                          job_type="demo.reverse", params={"text": str(i)},
                          dedupe_key=f"{run.id}:s1:{i}")
    s.commit(); s.close()

    claimed: list[str] = []
    lock = threading.Lock()
    start = threading.Barrier(2)

    def worker(name: str) -> None:
        start.wait()
        while True:
            ss = Sess()
            try:
                job = jobs.claim(ss, worker_id=name)
                if job is None:
                    ss.commit()
                    return
                with lock:
                    claimed.append(job.id)
                ss.commit()
            finally:
                ss.close()

    threads = [threading.Thread(target=worker, args=(name,)) for name in ("aw1", "aw2")]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert len(claimed) == 4
    assert len(set(claimed)) == 4


def test_agent_approve_dong_thoi_chi_mot_hold(Sess):
    """Hai request approve cùng version chỉ tạo đúng một hold."""
    from platform_core import credit
    from platform_core.agent import budget, runs
    from platform_core.agent.validator import ValidationResult

    s = Sess()
    credit.cap_tay(s, "approval-user", 100, by="test")
    run = runs.create_run(s, user_id="approval-user", goal="approve race")
    plan = {"version": 1, "budget_max_credit": 30, "steps": [{"id": "s1"}]}
    validation = ValidationResult(True, (), 16, ({"step_id": "s1", "maximum": 16},))
    budget.set_quote(s, run, plan=plan, validation=validation)
    run_id, version = run.id, run.version
    s.commit(); s.close()

    results: list[str] = []
    start = threading.Barrier(2)

    def worker() -> None:
        ss = Sess()
        try:
            start.wait()
            budget.approve(ss, run_id=run_id, user_id="approval-user",
                           approved_by="approval-user", expected_version=version)
            ss.commit()
            results.append("ok")
        except Exception as exc:  # noqa: BLE001 - preserve race diagnostics
            ss.rollback()
            results.append(f"err:{type(exc).__name__}:{exc}")
        finally:
            ss.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()

    assert results.count("ok") == 2, results
    check = Sess()
    try:
        assert credit.so_da_giu(check, run_id) == 20
        assert credit.so_du(check, "approval-user") == 80
    finally:
        check.close()


def test_agent_executor_hai_scheduler_khong_submit_trung(Sess):
    """Hai scheduler tick cùng run chỉ tạo một child cho step ready."""
    from platform_core import credit
    from platform_core.agent import budget, executor, runs
    from platform_core.agent.validator import ValidationResult

    s = Sess()
    credit.cap_tay(s, "executor-user", 100, by="test")
    plan = {
        "version": 1, "budget_max_credit": 20,
        "steps": [{"id": "s1", "tool": "text.script", "after": [],
                   "params": {"topic": "PostgreSQL race"}}],
    }
    run = runs.create_run(s, user_id="executor-user", goal="scheduler race")
    budget.set_quote(s, run, plan=plan, validation=ValidationResult(True, (), 3, ()))
    budget.approve(s, run_id=run.id, user_id="executor-user",
                   approved_by="executor-user", expected_version=run.version)
    run_id = run.id
    s.commit(); s.close()

    results: list[str] = []
    start = threading.Barrier(2)

    def worker() -> None:
        ss = Sess()
        try:
            start.wait()
            executor.tick(ss, run_id=run_id, user_id="executor-user")
            ss.commit()
            results.append("ok")
        except Exception as exc:  # noqa: BLE001 - preserve race diagnostics
            ss.rollback()
            results.append(f"err:{type(exc).__name__}:{exc}")
        finally:
            ss.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert results.count("ok") == 2, results
    check = Sess()
    try:
        assert len(runs.children(check, runs.get_owned(
            check, run_id, "executor-user"))) == 1
    finally:
        check.close()


def test_agent_workflow_hai_save_cung_revision_chi_mot_thanh_cong(Sess):
    """Optimistic locking P10: hai editor không được ghi đè mất dữ liệu."""
    from platform_core.agent import workflows

    plan = {"version": 1, "goal": "PostgreSQL workflow", "budget_max_credit": 20,
            "steps": [{"id": "s1", "tool": "text.script", "after": [],
                       "params": {"topic": "PostgreSQL race"}}]}
    s = Sess()
    row = workflows.create(s, user_id="workflow-user", name="Gốc",
                           canvas=workflows.plan_to_canvas(plan))
    workflow_id = row.id
    s.commit(); s.close()

    results: list[str] = []
    start = threading.Barrier(2)

    def worker(name: str) -> None:
        ss = Sess()
        try:
            canvas = workflows.as_canvas(
                workflows.get_owned(ss, workflow_id, "workflow-user"))
            canvas["goal"] = name
            start.wait()
            workflows.save(ss, workflow_id=workflow_id, user_id="workflow-user",
                           revision=1, name=name, canvas=canvas)
            ss.commit(); results.append("ok")
        except workflows.WorkflowConflict:
            ss.rollback(); results.append("conflict")
        except Exception as exc:  # noqa: BLE001
            ss.rollback(); results.append(f"err:{type(exc).__name__}:{exc}")
        finally:
            ss.close()

    threads = [threading.Thread(target=worker, args=(name,))
               for name in ("Editor A", "Editor B")]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(results) == ["conflict", "ok"], results
    check = Sess()
    try:
        saved = workflows.get_owned(check, workflow_id, "workflow-user")
        assert saved.revision == 2
        assert saved.name in {"Editor A", "Editor B"}
        assert saved.goal == saved.name
    finally:
        check.close()
