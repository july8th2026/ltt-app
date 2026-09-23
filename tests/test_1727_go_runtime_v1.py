"""Runtime Agent v1 đã biến mất khỏi mã (spec §3.1 luật 1, §17.5).

## Vì sao một `import` thử là phép đo đúng, còn `grep` thì không

`grep "executor"` khớp cả chữ "executor" trong một docstring lịch sử — và
docstring lịch sử là thứ NÊN ở lại. Thứ phải chết là **mô-đun có thể import
được**: chừng nào `import platform_core.agent.executor` còn chạy, người sau còn
gọi được nó, và "một runtime" chỉ là một câu trong tài liệu.

## Vế đối chứng bắt buộc

`validator`, `verifier`, `planner` **phải còn import được** (spec §17.6). Không
có vế này thì một bản vá xoá cả `platform_core/agent/` cũng làm bài trên xanh.

## ⚠️ Phạm vi thật của bài `canvas_to_plan`/`plan_to_canvas`

Bài dưới đo **mô-đun lưu trữ chuẩn** (`platform_core.agent.workflows`) không
còn nói tiếng Plan v1 — chứ không đo "Plan v1 đã chết trong cả kho". Nó chưa
chết: spec §17.6 GIỮ `planner.py` + `validator.py`, mà cả hai chỉ nói Plan v1,
và Trợ lý AI (`apps/agent/routes/assistant.py`) còn gọi chúng. Cầu chuyển đổi
vì thế dọn sang `platform_core/agent/plan_v1.py` — một góc cách ly có điều kiện
chết ghi sẵn trong docstring của nó, không phải một lớp tương thích mới.
"""
from __future__ import annotations

import importlib

import pytest


@pytest.mark.parametrize("ten", ["platform_core.agent.executor"])
def test_mo_dun_v1_khong_con_import_duoc(ten):
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(ten)


@pytest.mark.parametrize("ten", ["canvas_to_plan", "plan_to_canvas"])
def test_cau_chuyen_doi_canvas_plan_da_go(ten):
    wf = importlib.import_module("platform_core.agent.workflows")
    assert not hasattr(wf, ten), f"{ten} van con — spec §17.5"


def test_luu_workflow_VAN_tu_choi_truong_chi_may_chu_dat():
    """🔑 Vế đối chứng của bài ngay trên.

    `canvas_to_plan()` không chỉ dựng Plan — nó còn là **cửa kiểm** của đường
    lưu: nó ném khi Canvas của khách chứa `owner_id`/`estimated`/`credit_cost`…
    Xoá nó mà quên mang theo mệnh đề ấy thì bài trên vẫn xanh trong khi một
    khách vừa được quyền tự đặt giá cho workflow của mình.
    """
    from platform_core.agent import workflows
    canvas = {"version": 1, "goal": "g", "budget_max_credit": 10,
              "nodes": [{"id": "n1", "type": "tool", "position": {"x": 0, "y": 0},
                         "data": {"tool": "text.script", "credit_cost": 0}}],
              "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}
    with pytest.raises(workflows.WorkflowError):
        workflows.kiem_canvas(canvas)


@pytest.mark.parametrize("ten", ["platform_core.agent.validator",
                                 "platform_core.agent.verifier",
                                 "platform_core.agent.planner"])
def test_ba_mo_dun_O_LAI_van_import_duoc(ten):
    """🔑 Vế đối chứng (spec §17.6)."""
    assert importlib.import_module(ten) is not None


def test_agent_khong_con_khai_job_type_nao():
    from apps.agent.manifest import MANIFEST
    assert MANIFEST.job_types == (), (
        "`agent.advance` da chet; app `agent` gio la UI thuan")


def test_workflow_dong_co_VAN_co_chu_so_huu():
    """⛔ Nếu không app nào khai `workflow.dong_co`, `jobs.resolve_handler`
    không tra được chủ và **worker không chạy động cơ** — toàn bộ 01a chết
    im lặng. Đây là bài đắt nhất của task này."""
    from platform_core.registry import job_type_owners
    assert job_type_owners().get("workflow.dong_co") == "agent_dong_co"


def test_handle_tu_choi_job_type_la_thay_vi_chay_nhanh_advance_cu():
    """`handle` phân nhánh theo `ctx.job_type`. Không có ctx ⇒ job_type rỗng
    ⇒ phải NÉM, chứ không được rơi xuống nhánh `agent.advance` cũ (nhánh đó
    đọc `params["run_id"]` và sẽ ném một lỗi KHÁC, nói về v1)."""
    from apps.agent import jobs
    with pytest.raises(ValueError, match="khong thuoc app agent"):
        jobs.handle({"run_id": "r1", "user_id": "u1"})


# ─────────────────────────────────────────────────────────────────────────────
# Task 9 (plan 01b) — `AgentRun` và hai mô-đun sống nhờ nó đã đi theo runtime v1
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("ten", ["platform_core.agent.runs",
                                 "platform_core.agent.budget"])
def test_mo_dun_song_nho_AgentRun_khong_con_import_duoc(ten):
    """`runs.py` là dịch vụ trạng thái của `AgentRun`; `budget.py` là ranh giới
    tiền của chính nó. Không còn bảng thì không còn hai mô-đun này."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(ten)


@pytest.mark.parametrize("ten", ["AgentRun", "AGENT_PLANNING",
                                 "AGENT_AWAITING_APPROVAL", "AGENT_RUNNING",
                                 "AGENT_DONE", "AGENT_ERROR",
                                 "AGENT_CANCELLED"])
def test_models_khong_con_AgentRun_va_hang_trang_thai(ten):
    models = importlib.import_module("platform_core.models")
    assert not hasattr(models, ten), f"{ten} van con trong models — spec §17.5"


@pytest.mark.parametrize("ten", ["AgentWorkflow", "Job", "CreditEntry"])
def test_cac_model_O_LAI_van_con(ten):
    """🔑 Vế đối chứng: một bản vá xoá nhầm nửa `models.py` cũng làm bài trên
    xanh. Ba model này KHÔNG thuộc runtime v1 và phải còn nguyên."""
    models = importlib.import_module("platform_core.models")
    assert hasattr(models, ten)


def test_cua_quan_tri_cua_run_v1_da_dong_nhung_so_lieu_worker_O_LAI():
    """Hai cửa `/api/admin/runs*` chỉ đọc bảng `agent_runs` ⇒ chết cùng bảng.

    ⚠️ `/api/admin/metrics` thì KHÁC: nửa `AgentRun` của nó chết, nhưng
    `worker_wait_by_capability` đo **job con** — và job con vẫn được sinh ra
    bởi động cơ v2 (`platform_core/workflow/cau_noi.py` đặt `parent_id`). Đó
    là một tính chất còn sống, nên nó được CHUYỂN chứ không bị xoá.
    """
    from apps.agent.routes import router
    duong = {getattr(r, "path", "") for r in router.routes}
    assert "/api/admin/runs" not in duong
    assert "/api/admin/runs/{run_id}/cancel" not in duong
    assert "/api/admin/metrics" in duong
