"""Bounded 100-node Canvas/Plan release contract."""
from __future__ import annotations

import json
from time import perf_counter

from platform_core.agent import plan_v1, workflows
from platform_core.agent.validator import MAX_STEPS, validate_plan


def _canvas(count: int) -> dict:
    nodes = [{
        "id": f"n{index}",
        "type": "tool",
        "position": {"x": (index % 10) * 280, "y": (index // 10) * 190},
        "data": {"tool": "text.script", "params": {"topic": f"Muc {index}"},
                 "fanout": 1, "max_retry": 0, "on_fail": "retry_same",
                 "verify": None},
    } for index in range(count)]
    edges = [{"id": f"e{index}", "source": f"n{index - 1}",
              "target": f"n{index}"} for index in range(1, count)]
    return {"version": 2, "goal": "scale", "budget_max_credit": 1000,
            "active_page_id": "page-1", "pages": [{"id": "page-1",
            "name": "Scale", "nodes": nodes, "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1}, "frames": [],
            "notes": [], "comments": [], "view": {"grid": True,
            "connections": True, "minimap": True}}]}


def test_canvas_100_nodes_round_trips_within_bounded_document_limit():
    canvas = _canvas(100)
    encoded = json.dumps(canvas, ensure_ascii=False).encode("utf-8")
    assert 64 * 1024 < workflows.MAX_CANVAS_BYTES == 512 * 1024
    assert len(encoded) < workflows.MAX_CANVAS_BYTES
    started = perf_counter()
    plan = plan_v1.canvas_to_plan(canvas)
    assert len(plan["steps"]) == MAX_STEPS == 100
    assert perf_counter() - started < 0.5


def test_plan_step_limit_rejects_101_before_provider_or_credit_access():
    plan = plan_v1.canvas_to_plan(_canvas(100))
    plan["steps"].append(dict(plan["steps"][-1], id="n100", after=["n99"]))
    result = validate_plan(plan)
    assert result.valid is False
    assert result.issues[0].code == "steps"
    assert "100" in result.issues[0].message


def test_canvas_document_limit_stays_bounded():
    canvas = _canvas(100)
    canvas["pages"][0]["notes"] = [{"id": "oversize", "text": "x" *
                                      workflows.MAX_CANVAS_BYTES,
                                      "x": 0, "y": 0}]
    try:
        # ⭐ Do o `kiem_canvas` — cua ma duong LUU that su di qua. Truoc 23/09
        #    bai nay goi `canvas_to_plan`; tu khi Plan v1 roi mo-dun luu tru,
        #    goi lai o do se do mot cua ma `PUT /api/workflows` khong di qua.
        workflows.kiem_canvas(canvas)
    except workflows.WorkflowError as exc:
        assert "512 KiB" in str(exc)
    else:  # pragma: no cover - explicit release guard
        raise AssertionError("Oversized Canvas was accepted")
