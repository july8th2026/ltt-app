"""P10 regression: Canvas model, lossless Plan conversion and locking."""
from __future__ import annotations

import copy

import pytest

from platform_core.agent import workflows


def _plan():
    return {"version": 1, "goal": "Tạo và nâng cấp video",
            "budget_max_credit": 10000, "steps": [
        {"id": "source", "tool": "video.generate", "after": [], "fanout": 2,
         "max_retry": 1, "on_fail": "regenerate", "verify": None,
         "params": {"prompt": "Rừng ban mai", "model": "seedance-2.0-mini",
                    "resolution": "720p", "duration": 5, "aspect_ratio": "16:9",
                    "generate_audio": True}},
        {"id": "upscale", "tool": "video.upscale", "after": ["source"],
         "fanout": 1, "max_retry": 0, "on_fail": "retry_same", "verify": None,
         "params": {"video_key": "$source.video_key", "preset": "fast",
                    "target_height": 1080, "codec": "h264", "preview": False}},
        {"id": "subtitle", "tool": "video.subtitle", "after": ["source"],
         "fanout": 1, "max_retry": 0, "on_fail": "retry_same", "verify": None,
         "params": {"video_key": "$source.video_key", "transcript": [
             {"start": 0, "end": 1, "text": "Xin chào"}], "style_id": "default",
                    "quality": "standard"}},
    ]}


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'wf.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close(); dbmod.reset_engine()


def test_plan_canvas_round_trip_preserves_fanout_join_video_gpu_semantics():
    plan = _plan()
    restored = workflows.canvas_to_plan(workflows.plan_to_canvas(plan))
    assert restored == plan


def test_error_branch_round_trip_and_invalid_condition_are_guarded():
    plan = _plan()
    plan["steps"][2]["after"] = []
    plan["steps"][2]["after_error"] = ["source"]
    canvas = workflows.plan_to_canvas(plan)
    error_edge = next(edge for edge in canvas["edges"]
                      if (edge.get("data") or {}).get("condition") == "error")
    assert error_edge["source"] == "source" and error_edge["target"] == "subtitle"
    assert workflows.canvas_to_plan(canvas) == plan
    error_edge["data"]["condition"] = "maybe"
    with pytest.raises(workflows.WorkflowError, match="condition"):
        workflows.canvas_to_plan(canvas)


def test_canvas_rejects_server_fields_size_depth_and_bad_edge():
    canvas = workflows.plan_to_canvas(_plan())
    canvas["nodes"][0]["data"]["price"] = 0
    with pytest.raises(workflows.WorkflowError, match="server"):
        workflows.canvas_to_plan(canvas)
    deep = {"version": 1, "nodes": [], "edges": [], "viewport": {}}
    cursor = deep
    for _ in range(22):
        cursor["x"] = {}; cursor = cursor["x"]
    with pytest.raises(workflows.WorkflowError, match="sâu"):
        workflows.canvas_to_plan(deep)
    bad = workflows.plan_to_canvas(_plan()); bad["edges"][0].pop("source")
    with pytest.raises(workflows.WorkflowError, match="source"):
        workflows.canvas_to_plan(bad)


def test_canvas_cannot_bypass_plan_validator_cycle_type_or_unknown_tool():
    from platform_core.agent.validator import validate_plan

    cycle = workflows.plan_to_canvas(_plan())
    cycle["edges"].append({"id": "back", "source": "upscale", "target": "source"})
    assert any(issue.code == "cycle" for issue in
               validate_plan(workflows.canvas_to_plan(cycle)).issues)

    unknown = workflows.plan_to_canvas(_plan())
    unknown["nodes"][0]["data"]["tool"] = "missing.tool"
    assert any(issue.code == "tool" for issue in
               validate_plan(workflows.canvas_to_plan(unknown)).issues)

    mismatch = workflows.plan_to_canvas(_plan())
    upscale = next(node for node in mismatch["nodes"] if node["id"] == "upscale")
    upscale["data"]["tool"] = "image.generate"
    upscale["data"]["params"] = {"prompt": "$source.video_key",
                                    "model": "gemini-2.5-flash-image", "count": 1}
    assert any(issue.code == "port_type" for issue in
               validate_plan(workflows.canvas_to_plan(mismatch)).issues)


def test_ownership_stale_revision_and_approved_edit_returns_draft(db):
    row = workflows.create(db, user_id="user-a", name="Bản gốc",
                           canvas=workflows.plan_to_canvas(_plan()))
    db.commit(); workflow_id = row.id
    with pytest.raises(workflows.WorkflowError):
        workflows.get_owned(db, workflow_id, "user-b")
    row.status = "approved"; row.estimated = 99; db.commit()
    changed = workflows.as_canvas(row); changed["goal"] = "Mục tiêu mới"
    saved = workflows.save(db, workflow_id=workflow_id, user_id="user-a",
                           revision=1, name="Đã sửa", canvas=changed)
    db.commit()
    assert saved.revision == 2 and saved.status == "draft" and saved.estimated == 0
    assert saved.goal == "Mục tiêu mới"
    with pytest.raises(workflows.WorkflowConflict):
        workflows.save(db, workflow_id=workflow_id, user_id="user-a",
                       revision=1, name="Ghi đè", canvas=changed)


def test_clone_is_independent_and_keeps_source_audit(db):
    original = workflows.create(db, user_id="user-a", name="Gốc",
                                canvas=workflows.plan_to_canvas(_plan()))
    db.flush()
    clone_canvas = copy.deepcopy(workflows.as_canvas(original))
    clone = workflows.create(db, user_id="user-a", name="Bản sao", canvas=clone_canvas,
                             source_workflow_id=original.id)
    db.commit()
    assert clone.id != original.id and clone.source_workflow_id == original.id
    assert workflows.canvas_to_plan(workflows.as_canvas(clone)) == _plan()
