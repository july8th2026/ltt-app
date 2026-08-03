"""Canonical Canvas persistence and lossless Plan v1 conversion."""
from __future__ import annotations

import copy
import json
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from platform_core.agent.normalizer import MAX_JSON_DEPTH, _depth
from platform_core.agent.validator import ValidationResult, validate_plan
from platform_core.models import (WORKFLOW_APPROVED, WORKFLOW_ARCHIVED,
                                  WORKFLOW_DRAFT, WORKFLOW_VALIDATED,
                                  AgentWorkflow, AgentWorkflowSnapshot)

STATUSES = {WORKFLOW_DRAFT, WORKFLOW_VALIDATED, WORKFLOW_APPROVED, WORKFLOW_ARCHIVED}
MAX_PAGES = 20
MAX_FRAMES_PER_PAGE = 50
MAX_ANNOTATIONS_PER_PAGE = 200
MAX_CANVAS_BYTES = 512 * 1024
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
    if len(raw) > MAX_CANVAS_BYTES:
        raise WorkflowError("Canvas vượt giới hạn 512 KiB.")
    if _depth(value) > MAX_JSON_DEPTH:
        raise WorkflowError("Canvas JSON lồng quá sâu.")


def _page_graph(canvas: dict) -> tuple[list, list, dict]:
    """Return the executable graph while preserving the full editor document."""
    version = canvas.get("version") if isinstance(canvas, dict) else None
    if version == 1:
        return canvas.get("nodes"), canvas.get("edges"), canvas.get("viewport") or {}
    if version != 2:
        raise WorkflowError("Chỉ hỗ trợ Canvas version 1 hoặc 2.")
    pages = canvas.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise WorkflowError("Canvas v2 cần 1–20 pages.")
    page_ids: set[str] = set()
    active = None
    active_id = str(canvas.get("active_page_id", ""))
    for page in pages:
        if not isinstance(page, dict):
            raise WorkflowError("Page không hợp lệ.")
        page_id = str(page.get("id", ""))
        if not page_id or page_id in page_ids or len(page_id) > 64:
            raise WorkflowError("Page id thiếu, quá dài hoặc trùng.")
        page_ids.add(page_id)
        if len(str(page.get("name", ""))) > 80:
            raise WorkflowError("Tên page vượt 80 ký tự.")
        frames = page.get("frames", [])
        notes = page.get("notes", [])
        comments = page.get("comments", [])
        if (not isinstance(frames, list) or len(frames) > MAX_FRAMES_PER_PAGE
                or not isinstance(notes, list) or not isinstance(comments, list)
                or len(notes) + len(comments) > MAX_ANNOTATIONS_PER_PAGE):
            raise WorkflowError("Frame/annotation của page không hợp lệ hoặc vượt giới hạn.")
        if page_id == active_id:
            active = page
    if active is None:
        raise WorkflowError("active_page_id không tồn tại.")
    return active.get("nodes"), active.get("edges"), active.get("viewport") or {}


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
    _safe_json(canvas)
    return canvas


def canvas_to_plan(canvas: dict) -> dict:
    _safe_json(canvas)
    if not isinstance(canvas, dict) or _has_forbidden(canvas):
        raise WorkflowError("Canvas chứa trường chỉ server được đặt.")
    nodes, edges, _viewport = _page_graph(canvas)
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
    error_deps: dict[str, list[str]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            raise WorkflowError("Edge không hợp lệ.")
        source, target = str(edge.get("source", "")), str(edge.get("target", ""))
        if not source or not target:
            raise WorkflowError("Edge thiếu source/target.")
        if source not in ids or target not in ids:
            raise WorkflowError("Edge tham chiếu node không tồn tại.")
        condition = str((edge.get("data") or {}).get("condition", "success"))
        if condition not in {"success", "error"}:
            raise WorkflowError("Edge condition không hợp lệ.")
        bucket = error_deps if condition == "error" else deps
        if source not in bucket.setdefault(target, []):
            bucket[target].append(source)
    steps = []
    for node in nodes:
        sid = str(node.get("id", ""))
        data = copy.deepcopy(node["data"])
        if {"id", "after", "after_error"}.intersection(
                str(key).lower() for key in data) or _has_forbidden(data):
            raise WorkflowError("Node chứa trường chỉ server được đặt.")
        step = {"id": sid, **data, "after": deps.get(sid, [])}
        if error_deps.get(sid):
            step["after_error"] = error_deps[sid]
        steps.append(step)
    return {"version": 1, "goal": str(canvas.get("goal", "")),
            "budget_max_credit": int(canvas.get("budget_max_credit", 0)),
            "steps": steps}


def scope_plan(plan: dict, target_ids: list[str]) -> dict:
    """Return targets plus their transitive success/error prerequisites."""
    steps = list((plan or {}).get("steps") or [])
    by_id = {str(step.get("id", "")): step for step in steps}
    targets = {str(value) for value in target_ids if str(value)}
    if not targets or not targets.issubset(by_id):
        raise WorkflowError("Scope tham chiếu node không tồn tại.")
    included: set[str] = set()
    pending = list(targets)
    while pending:
        step_id = pending.pop()
        if step_id in included:
            continue
        included.add(step_id)
        step = by_id[step_id]
        pending.extend(str(dep) for dep in (step.get("after") or []))
        pending.extend(str(dep) for dep in (step.get("after_error") or []))
    scoped = copy.deepcopy(plan)
    scoped["steps"] = []
    for step in steps:
        if str(step.get("id")) not in included:
            continue
        clone = copy.deepcopy(step)
        clone["after"] = [dep for dep in clone.get("after", []) if dep in included]
        if "after_error" in clone:
            clone["after_error"] = [dep for dep in clone.get("after_error", []) if dep in included]
        scoped["steps"].append(clone)
    return scoped


def scope_targets(canvas: dict, scope: dict) -> tuple[list[str], dict]:
    """Resolve a client scope against server-owned Canvas metadata."""
    mode = str((scope or {}).get("mode") or "full")
    nodes, _edges, _viewport = _page_graph(canvas)
    node_ids = [str(node.get("id")) for node in nodes or []]
    if mode == "full":
        return node_ids, {"mode": "full", "node_ids": node_ids}
    if mode in {"node", "selection"}:
        requested = ((scope or {}).get("node_ids") or
                     [str((scope or {}).get("node_id") or "")])
        targets = [str(value) for value in requested if str(value)]
        if not targets or not set(targets).issubset(node_ids):
            raise WorkflowError("Scope node/lựa chọn không hợp lệ.")
        return targets, {"mode": mode, "node_ids": targets}
    if mode == "frame":
        frame_id = str((scope or {}).get("frame_id") or "")
        version = canvas.get("version")
        page = next((item for item in canvas.get("pages", [])
                     if item.get("id") == canvas.get("active_page_id")), {}) if version == 2 else {}
        frame = next((item for item in page.get("frames", []) if item.get("id") == frame_id), None)
        targets = [str(value) for value in (frame or {}).get("node_ids", [])]
        if frame is None or not targets or not set(targets).issubset(node_ids):
            raise WorkflowError("Frame không tồn tại hoặc không có node hợp lệ.")
        return targets, {"mode": "frame", "frame_id": frame_id,
                         "frame_name": str(frame.get("name") or "Frame"), "node_ids": targets}
    raise WorkflowError("Chế độ chạy không được hỗ trợ.")


def get_owned(db: Session, workflow_id: str, user_id: str) -> AgentWorkflow:
    row = db.get(AgentWorkflow, workflow_id)
    if row is None or row.user_id != user_id:
        raise WorkflowNotFound("Không tìm thấy workflow.")
    return row


def create(db: Session, *, user_id: str, name: str, canvas: dict,
           source_workflow_id: str = "") -> AgentWorkflow:
    plan = canvas_to_plan(canvas)
    nodes, edges, viewport = _page_graph(canvas)
    row = AgentWorkflow(user_id=user_id, name=(name.strip() or "Workflow mới")[:160],
                        goal=plan["goal"], plan_version=1,
                        nodes=copy.deepcopy(nodes), edges=copy.deepcopy(edges),
                        viewport=copy.deepcopy(viewport), document=copy.deepcopy(canvas),
                        budget_max=plan["budget_max_credit"], source_workflow_id=source_workflow_id)
    db.add(row); db.flush(); _snapshot(db, row, "create")
    return row


def _snapshot(db: Session, row: AgentWorkflow, reason: str) -> AgentWorkflowSnapshot:
    existing = db.query(AgentWorkflowSnapshot).filter_by(
        workflow_id=row.id, revision=row.revision).first()
    if existing is not None:
        return existing
    item = AgentWorkflowSnapshot(workflow_id=row.id, user_id=row.user_id,
                                 revision=row.revision, name=row.name,
                                 document=as_canvas(row), reason=reason[:32])
    db.add(item); db.flush(); return item


def snapshots(db: Session, workflow_id: str, user_id: str) -> list[AgentWorkflowSnapshot]:
    get_owned(db, workflow_id, user_id)
    return db.query(AgentWorkflowSnapshot).filter_by(
        workflow_id=workflow_id, user_id=user_id).order_by(
        AgentWorkflowSnapshot.revision.desc()).limit(100).all()


def restore_snapshot(db: Session, *, workflow_id: str, user_id: str,
                     revision: int, expected_revision: int) -> AgentWorkflow:
    row = get_owned(db, workflow_id, user_id)
    item = db.query(AgentWorkflowSnapshot).filter_by(
        workflow_id=workflow_id, user_id=user_id, revision=revision).first()
    if item is None:
        raise WorkflowNotFound("Không tìm thấy snapshot.")
    return save(db, workflow_id=row.id, user_id=user_id, revision=expected_revision,
                name=item.name, canvas=copy.deepcopy(item.document), reason="restore")


def as_canvas(row: AgentWorkflow) -> dict:
    if isinstance(row.document, dict) and row.document.get("version") in {1, 2}:
        return copy.deepcopy(row.document)
    return {"version": row.plan_version, "goal": row.goal,
            "budget_max_credit": row.budget_max, "nodes": copy.deepcopy(row.nodes),
            "edges": copy.deepcopy(row.edges), "viewport": copy.deepcopy(row.viewport)}


def save(db: Session, *, workflow_id: str, user_id: str, revision: int,
         name: str, canvas: dict, reason: str = "save") -> AgentWorkflow:
    row = get_owned(db, workflow_id, user_id)
    if row.status == WORKFLOW_ARCHIVED:
        raise WorkflowError("Workflow đã lưu trữ.")
    plan = canvas_to_plan(canvas)
    nodes, edges, viewport = _page_graph(canvas)
    now = datetime.now(timezone.utc)
    result = db.execute(update(AgentWorkflow).where(
        AgentWorkflow.id == workflow_id, AgentWorkflow.user_id == user_id,
        AgentWorkflow.revision == revision).values(
            name=(name.strip() or "Workflow mới")[:160], goal=plan["goal"],
            nodes=copy.deepcopy(nodes), edges=copy.deepcopy(edges),
            viewport=copy.deepcopy(viewport), document=copy.deepcopy(canvas),
            budget_max=plan["budget_max_credit"], estimated=0,
            status=WORKFLOW_DRAFT, revision=revision + 1, updated_at=now))
    if result.rowcount != 1:
        raise WorkflowConflict("Workflow đã được sửa ở phiên khác.")
    db.flush(); db.expire(row); _snapshot(db, row, reason); return row


def validate(db: Session, row: AgentWorkflow, *, user) -> ValidationResult:
    result = validate_plan(canvas_to_plan(as_canvas(row)), db=db, user=user)
    row.estimated = result.estimated_max_credit
    row.status = WORKFLOW_VALIDATED if result.valid else WORKFLOW_DRAFT
    row.revision += 1
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return result
