"""Canonical Canvas persistence and lossless Plan v1 conversion."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from platform_core.agent.normalizer import MAX_JSON_DEPTH, MAX_PLAN_BYTES, _depth
from platform_core.agent.validator import ValidationResult, validate_plan
from platform_core.models import (WORKFLOW_APPROVED, WORKFLOW_ARCHIVED,
                                  WORKFLOW_DRAFT, WORKFLOW_VALIDATED,
                                  AgentWorkflow)

STATUSES = {WORKFLOW_DRAFT, WORKFLOW_VALIDATED, WORKFLOW_APPROVED, WORKFLOW_ARCHIVED}
_CLIENT_FORBIDDEN = {"owner_id", "user_id", "estimated", "price", "credit_cost",
                     "credential", "secret", "csrf_token", "callback_url",
                     "webhook_url", "storage_key"}


class WorkflowError(ValueError):
    pass


class WorkflowConflict(WorkflowError):
    pass


class WorkflowNotFound(WorkflowError):
    pass


def _has_forbidden(value) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _CLIENT_FORBIDDEN or _has_forbidden(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_has_forbidden(item) for item in value)
    return False


def _safe_json(value) -> None:
    try:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise WorkflowError("Canvas JSON không hợp lệ.") from exc
    if len(raw) > MAX_PLAN_BYTES:
        raise WorkflowError("Canvas vượt giới hạn 64 KiB.")
    if _depth(value) > MAX_JSON_DEPTH:
        raise WorkflowError("Canvas JSON lồng quá sâu.")


def plan_to_canvas(plan: dict) -> dict:
    """Preserve every execution field; add layout only as editor metadata."""
    steps = plan.get("steps") if isinstance(plan, dict) else None
    if not isinstance(steps, list):
        raise WorkflowError("Plan thiếu steps.")
    nodes, edges = [], []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise WorkflowError("Step không hợp lệ.")
        sid = str(step.get("id", ""))
        execution = {key: copy.deepcopy(value) for key, value in step.items()
                     if key not in {"id", "after"}}
        nodes.append({"id": sid, "type": "tool", "position": {"x": index * 280, "y": 0},
                      "data": execution})
        for source in step.get("after", []) or []:
            edges.append({"id": f"{source}--{sid}", "source": source, "target": sid})
    canvas = {"version": 1, "goal": str(plan.get("goal", "")),
              "budget_max_credit": int(plan.get("budget_max_credit", 0)),
              "nodes": nodes, "edges": edges,
              "viewport": {"x": 0, "y": 0, "zoom": 1}}
    _safe_json(canvas)
    return canvas


def canvas_to_plan(canvas: dict) -> dict:
    _safe_json(canvas)
    if not isinstance(canvas, dict) or canvas.get("version") != 1:
        raise WorkflowError("Chỉ hỗ trợ Canvas version 1.")
    nodes, edges = canvas.get("nodes"), canvas.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise WorkflowError("Canvas cần nodes và edges dạng danh sách.")
    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("data"), dict):
            raise WorkflowError("Node không hợp lệ.")
        sid = str(node.get("id", ""))
        if not sid or sid in ids or node.get("type", "tool") != "tool":
            raise WorkflowError("Node id/type thiếu hoặc trùng.")
        ids.add(sid)
    deps: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            raise WorkflowError("Edge không hợp lệ.")
        source, target = str(edge.get("source", "")), str(edge.get("target", ""))
        if not source or not target:
            raise WorkflowError("Edge thiếu source/target.")
        if source not in ids or target not in ids:
            raise WorkflowError("Edge tham chiếu node không tồn tại.")
        if source not in deps.setdefault(target, []):
            deps[target].append(source)
    steps = []
    for node in nodes:
        sid = str(node.get("id", ""))
        data = copy.deepcopy(node["data"])
        if {"id", "after"}.intersection(str(key).lower() for key in data) or _has_forbidden(data):
            raise WorkflowError("Node chứa trường chỉ server được đặt.")
        steps.append({"id": sid, **data, "after": deps.get(sid, [])})
    return {"version": 1, "goal": str(canvas.get("goal", "")),
            "budget_max_credit": int(canvas.get("budget_max_credit", 0)),
            "steps": steps}


def get_owned(db: Session, workflow_id: str, user_id: str) -> AgentWorkflow:
    row = db.get(AgentWorkflow, workflow_id)
    if row is None or row.user_id != user_id:
        raise WorkflowNotFound("Không tìm thấy workflow.")
    return row


def create(db: Session, *, user_id: str, name: str, canvas: dict,
           source_workflow_id: str = "") -> AgentWorkflow:
    plan = canvas_to_plan(canvas)
    row = AgentWorkflow(user_id=user_id, name=(name.strip() or "Workflow mới")[:160],
                        goal=plan["goal"], plan_version=1,
                        nodes=copy.deepcopy(canvas["nodes"]), edges=copy.deepcopy(canvas["edges"]),
                        viewport=copy.deepcopy(canvas.get("viewport") or {}),
                        budget_max=plan["budget_max_credit"], source_workflow_id=source_workflow_id)
    db.add(row); db.flush()
    return row


def as_canvas(row: AgentWorkflow) -> dict:
    return {"version": row.plan_version, "goal": row.goal,
            "budget_max_credit": row.budget_max, "nodes": copy.deepcopy(row.nodes),
            "edges": copy.deepcopy(row.edges), "viewport": copy.deepcopy(row.viewport)}


def save(db: Session, *, workflow_id: str, user_id: str, revision: int,
         name: str, canvas: dict) -> AgentWorkflow:
    row = get_owned(db, workflow_id, user_id)
    if row.status == WORKFLOW_ARCHIVED:
        raise WorkflowError("Workflow đã lưu trữ.")
    plan = canvas_to_plan(canvas)
    now = datetime.now(timezone.utc)
    result = db.execute(update(AgentWorkflow).where(
        AgentWorkflow.id == workflow_id, AgentWorkflow.user_id == user_id,
        AgentWorkflow.revision == revision).values(
            name=(name.strip() or "Workflow mới")[:160], goal=plan["goal"],
            nodes=copy.deepcopy(canvas["nodes"]), edges=copy.deepcopy(canvas["edges"]),
            viewport=copy.deepcopy(canvas.get("viewport") or {}),
            budget_max=plan["budget_max_credit"], estimated=0,
            status=WORKFLOW_DRAFT, revision=revision + 1, updated_at=now))
    if result.rowcount != 1:
        raise WorkflowConflict("Workflow đã được sửa ở phiên khác.")
    db.flush(); db.expire(row); return row


def validate(db: Session, row: AgentWorkflow, *, user) -> ValidationResult:
    result = validate_plan(canvas_to_plan(as_canvas(row)), db=db, user=user)
    row.estimated = result.estimated_max_credit
    row.status = WORKFLOW_VALIDATED if result.valid else WORKFLOW_DRAFT
    row.revision += 1
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return result
