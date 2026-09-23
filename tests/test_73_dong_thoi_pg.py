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

from tests.conftest import bao_dam_user
import threading
from types import SimpleNamespace

import pytest

# Không đọc thẳng biến môi trường: `pg_scratch` từ chối một URL không chứng
# minh được nó là CSDL vứt đi. Các test này gọi `drop_all()`, và trên máy chủ
# thì PostgreSQL của nền tảng đang chạy ngay cạnh.
from tests.pg_scratch import scratch_url

PG_URL = scratch_url()

# 🔴 MOT BO KIEM BI BO QUA LA MOT BO KIEM DANG MUC RUONG, va tep nay da chung
#    minh dieu do bang chinh no.
#
#    Ngay 2026-09-02, lan dau bo kiem nay duoc chay tren mot PostgreSQL vut di:
#    6/7 xanh, 1 do. Cai do KHONG phai mot cuoc dua — no la
#    `ExecutorError: Tool khong con kha dung: text.script`.
#
#    `text.script` la tool cua app `kichban`, **da go tu 2026-08-25 (Q109)**.
#    Nghia la hai phep kiem o day tro toi mot thu khong con ton tai suot mot
#    tuan, va khong ai biet — vi thieu `LTT_TEST_DATABASE_URL` thi chung khong
#    chay, va mot phep kiem khong chay thi khong bao gio do.
#
# ⭐ Cai giá that: `tests/test_94_agent_app.py:51` da SUA DUNG loi nay ngay
#    26/08, kem mot chu thich giai thich day du. Nguoi sua khong the biet o day
#    con hai cho nua — vi o day khong co gi keu len.
#
# ⇒ Bai hoc khong phai "nho sua het moi cho". La: mot phep kiem chi bao ve duoc
#   thu gi khi no CHAY. Xem `docs/system_purification/reports/07_*.md`.


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


def test_global_queue_cap_dem_va_insert_nguyen_tu(Sess):
    """Tám request cùng thấy queue trống vẫn chỉ đúng ba request được commit."""
    from platform_core import jobs
    from platform_core.public_api import limits
    from platform_core.public_api.config import load_public_api_config
    from platform_core.public_api.errors import ApiError

    config = load_public_api_config({
        "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT": "3",
        "LTT_PUBLIC_API_MAX_ACTIVE_JOBS": "0",
    })
    n = 8
    start = threading.Barrier(n)
    results: list[str] = []
    guard = threading.Lock()

    def worker(index: int) -> None:
        ss = Sess()
        result = ""
        try:
            start.wait()
            limits.enforce_job_admission(
                ss, principal=SimpleNamespace(user_id=f"queue-user-{index}"),
                config=config, resource="llm_remote", class_slugs=())
            jobs.submit(
                ss, user_id=f"queue-user-{index}", app_slug="sample",
                job_type="sample.run", params={},
                admission_resource="llm_remote", admission_slots=1)
            ss.commit()
            result = "ok"
        except ApiError:
            ss.rollback()
            result = "full"
        except Exception as exc:  # noqa: BLE001 - preserve race diagnostics
            ss.rollback()
            result = f"err:{type(exc).__name__}:{exc}"
        finally:
            ss.close()
            with guard:
                results.append(result)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(n)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results.count("ok") == 3, results
    assert results.count("full") == n - 3, results
    assert not [value for value in results if value.startswith("err:")], results

    check = Sess()
    try:
        from platform_core.models import Job
        assert check.query(Job).filter_by(admission_resource="llm_remote").count() == 3
    finally:
        check.close()


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
        jobs.submit(s, user_id=uid, app_slug="appthu", job_type="appthu.dao_nguoc",
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


def test_hai_worker_dong_thoi_deu_chon_internal_khi_con_du_ung_vien(Sess):
    """P1+P2 trên PostgreSQL thật: strict priority không làm hỏng SKIP LOCKED."""
    from platform_core import jobs

    seed = Sess()
    try:
        for index in range(20):
            jobs.submit(
                seed, user_id=f"external-{index}", app_slug="appthu",
                job_type="appthu.dao_nguoc", params={"i": index},
                admission_resource="shared-gpu", priority_class="external",
                origin="public_api")
        internal_ids = set()
        for index in range(2):
            row = jobs.submit(
                seed, user_id=f"internal-{index}", app_slug="appthu",
                job_type="appthu.dao_nguoc", params={"i": index},
                admission_resource="shared-gpu", priority_class="internal",
                origin="internal_runtime")
            internal_ids.add(row.id)
        seed.commit()
    finally:
        seed.close()

    start = threading.Barrier(2)
    claimed: list[tuple[str, str]] = []
    guard = threading.Lock()

    def worker(name: str) -> None:
        session = Sess()
        try:
            start.wait()
            row = jobs.claim(session, worker_id=name)
            assert row is not None
            session.commit()
            with guard:
                claimed.append((row.id, row.priority_class))
        finally:
            session.close()

    threads = [threading.Thread(target=worker, args=(name,))
               for name in ("priority-w1", "priority-w2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(claimed) == 2
    assert {job_id for job_id, _priority in claimed} == internal_ids
    assert {priority for _job_id, priority in claimed} == {"internal"}


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
        runs.submit_child(s, run, step_id="s1", app_slug="appthu",
                          job_type="appthu.dao_nguoc", params={"text": str(i)},
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
    bao_dam_user(s, "approval-user"); credit.cap_tay(s, "approval-user", 100, by="test")
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


# ⏭️ `test_agent_executor_hai_scheduler_khong_submit_trung` DA GO 23/09/2026.
#
#    No do: hai scheduler cung `executor.tick()` mot run chi tao MOT job con.
#    Runtime v1 (`platform_core/agent/executor.py` + job `agent.advance`) da bi
#    go cung spec §17.5 ⇒ khong con hai scheduler nao de dua.
#
# ⚠️ Menh de "hai worker khong nhac trung mot viec" KHONG chet theo: no chuyen
#    sang dong co Workflow V2 (`workflow.dong_co`, mot vong duy nhat), va o do
#    `tests/test_1720_wf_dong_co_pg.py` la cho canh no tren PostgreSQL.


def test_agent_workflow_hai_save_cung_revision_chi_mot_thanh_cong(Sess):
    """Optimistic locking P10: hai editor không được ghi đè mất dữ liệu."""
    from platform_core.agent import workflows

    # Canvas viet thang, khong di vong qua `plan_to_canvas`: tu §17.5 tai lieu
    # Canvas la NGUON CHAN LY, Plan v1 chi con la tieng cua Tro ly AI.
    canvas = {"version": 1, "goal": "PostgreSQL workflow", "budget_max_credit": 20,
              "nodes": [{"id": "s1", "type": "tool",
                         "position": {"x": 0, "y": 0},
                         "data": {"tool": "text.prompt_package", "fanout": 1,
                                  "max_retry": 0, "on_fail": "retry_same",
                                  "verify": None,
                                  "params": {"title": "PostgreSQL race",
                                             "story": "Mot cau chuyen thu."}}}],
              "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    s = Sess()
    row = workflows.create(s, user_id="workflow-user", name="Gốc",
                           canvas=canvas)
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
