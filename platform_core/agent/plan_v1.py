"""Cau chuyen doi Canvas <-> **Plan v1** — goc cuoi cung con noi tieng Plan v1.

## Vi sao mo-dun nay ton tai thay vi bi xoa (spec §17.5 vs §17.6)

§17.5 giet runtime v1: `executor.py`, `agent.advance`, `AgentRun`. §17.6 thi
**GIU** `planner.py`, `validator.py`, `verifier.py`. Ma ca ba thu duoc giu chi
noi mot thu tieng: `plan_once()` SINH Plan v1 va `validate_plan()` DOC Plan v1.
Chung nao Tro ly AI (`apps/agent/routes/assistant.py`) con goi chung, van phai
co cho dich giua tai lieu Canvas va Plan v1.

Cho ay truoc day la `platform_core/agent/workflows.py` — mo-dun LUU TRU chuan.
Do moi la van de §17.5 chi ra: duong luu khong duoc phu thuoc vao Plan. Nen
cau chuyen doi don sang day, con `workflows.py` giu dung cua kiem cua no
(`kiem_canvas()`).

## ⛔ Day KHONG phai mot lop tuong thich, va day la dieu kien chet cua no

Khong co khach nao o lop Agent/Canvas (CLAUDE.md), nen mo-dun nay khong phuc vu
tuong thich nguoc — no phuc vu dung MOT tinh nang con song: kham Tro ly AI.

    Xoa mo-dun nay cung luc xoa `apps/agent/routes/assistant.py`
    (thiet ke lai Tro ly, phase 11 cua spec §19).

⚠️ Do 23/09/2026: tu Task 6, CanvasShell mo workflow qua `/agent/api/v3/...`
   nen `workflow.id` tren giao dien la id cua bang `workflow_draft`, KHONG phai
   `agent_workflows`. Moi cua v2 con lai (tro ly, ban chup, chia se, nhan ban,
   xuat/nhap) vi the tra 404 khi giao dien goi. Tuc la kham Tro ly **da khong
   voi toi duoc** — day la ly do manh nhat de phase 11 xoa ca cum, va la ly do
   khong dang bo them cong vao mo-dun nay.
"""
from __future__ import annotations

import copy

from platform_core.i18n import _ as _t
from platform_core.agent.workflows import (WorkflowError, kiem_canvas,
                                           page_graph)

__all__ = ["canvas_to_plan", "plan_to_canvas"]


def plan_to_canvas(plan: dict) -> dict:
    """Preserve every execution field; add layout only as editor metadata."""
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not isinstance(steps, list):
        raise WorkflowError(_t("Plan thiếu steps."))
    nodes, edges = [], []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise WorkflowError(_t("Step không hợp lệ."))
        sid = str(step.get("id", ""))
        execution = {key: copy.deepcopy(value) for key, value in step.items()
                     if key not in {"id", "after", "after_error"}}
        nodes.append({"id": sid, "type": "tool", "position": {"x": index * 280, "y": 0},
                      "data": execution})
        for source in step.get("after", []) or []:
            edges.append({"id": f"{source}--{sid}", "source": source, "target": sid,
                          "data": {"condition": "success"}})
        for source in step.get("after_error", []) or []:
            edges.append({"id": f"{source}--error--{sid}", "source": source, "target": sid,
                          "data": {"condition": "error"}})
    canvas = {"version": 1, "goal": str(plan.get("goal", "")),
              "budget_max_credit": int(plan.get("budget_max_credit", 0)),
              "nodes": nodes, "edges": edges,
              "viewport": {"x": 0, "y": 0, "zoom": 1}}
    kiem_canvas(canvas)
    return canvas


def canvas_to_plan(canvas: dict) -> dict:
    """Canvas -> Plan v1 cho `validate_plan()`/`plan_once()` cua Tro ly AI.

    ⭐ MOI phep kiem nam o `workflows.kiem_canvas()`, khong lap lai o day. Ban
       cu gop kiem va dich lam mot; tach ra roi thi ban sao thu hai cua cung
       mot luat la cho hai ban bat dau lech nhau.
    """
    meta = kiem_canvas(canvas)
    nodes, edges, _viewport = page_graph(canvas)
    deps: dict[str, list[str]] = {}
    error_deps: dict[str, list[str]] = {}
    for edge in edges:
        source, target = str(edge.get("source", "")), str(edge.get("target", ""))
        condition = str((edge.get("data") or {}).get("condition", "success"))
        bucket = error_deps if condition == "error" else deps
        if source not in bucket.setdefault(target, []):
            bucket[target].append(source)
    steps = []
    for node in nodes:
        sid = str(node.get("id", ""))
        data = copy.deepcopy(node["data"])
        step = {"id": sid, **data, "after": deps.get(sid, [])}
        if error_deps.get(sid):
            step["after_error"] = error_deps[sid]
        steps.append(step)
    return {"version": 1, "goal": meta["goal"],
            "budget_max_credit": meta["budget_max_credit"], "steps": steps}
