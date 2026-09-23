"""P10 regression: Canvas model, khoa lac quan, ban chup — va cau Plan v1.

⏭️ 23/09/2026: `canvas_to_plan`/`plan_to_canvas` roi `workflows.py` sang
   `platform_core/agent/plan_v1.py` (spec §17.5 — mo-dun LUU TRU thoi noi
   tieng Plan v1). Cac bai chuyen doi o day theo sang do; cac bai luu/khoa/
   ban chup/scope o lai vi chung do `workflows.py`.

⏭️ `test_scope_node_keo_upstream_nhung_khong_keo_nhanh_ngoai` DA GO cung ham
   `scope_plan`: sau Task 7 khong con route nao goi no (`workflow_frame_export`
   la nguoi dung cuoi). Chay MOT PHAN do thi (node/selection/frame) duoc xep
   lai tren v3 o plan 13 — khi do no se co phep kiem cua no, tren cua no.
"""
from __future__ import annotations

import copy

import pytest

from platform_core.agent import plan_v1, workflows


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
    restored = plan_v1.canvas_to_plan(plan_v1.plan_to_canvas(plan))
    assert restored == plan


def test_error_branch_round_trip_and_invalid_condition_are_guarded():
    plan = _plan()
    plan["steps"][2]["after"] = []
    plan["steps"][2]["after_error"] = ["source"]
    canvas = plan_v1.plan_to_canvas(plan)
    error_edge = next(edge for edge in canvas["edges"]
                      if (edge.get("data") or {}).get("condition") == "error")
    assert error_edge["source"] == "source" and error_edge["target"] == "subtitle"
    assert plan_v1.canvas_to_plan(canvas) == plan
    error_edge["data"]["condition"] = "maybe"
    with pytest.raises(workflows.WorkflowError, match="condition"):
        plan_v1.canvas_to_plan(canvas)


def test_canvas_rejects_server_fields_size_depth_and_bad_edge():
    canvas = plan_v1.plan_to_canvas(_plan())
    canvas["nodes"][0]["data"]["price"] = 0
    with pytest.raises(workflows.WorkflowError, match="server"):
        plan_v1.canvas_to_plan(canvas)
    deep = {"version": 1, "nodes": [], "edges": [], "viewport": {}}
    cursor = deep
    for _ in range(22):
        cursor["x"] = {}; cursor = cursor["x"]
    with pytest.raises(workflows.WorkflowError, match="sâu"):
        plan_v1.canvas_to_plan(deep)
    bad = plan_v1.plan_to_canvas(_plan()); bad["edges"][0].pop("source")
    with pytest.raises(workflows.WorkflowError, match="source"):
        plan_v1.canvas_to_plan(bad)


def test_canvas_cannot_bypass_plan_validator_cycle_type_or_unknown_tool():
    from platform_core.agent.validator import validate_plan

    cycle = plan_v1.plan_to_canvas(_plan())
    cycle["edges"].append({"id": "back", "source": "upscale", "target": "source"})
    assert any(issue.code == "cycle" for issue in
               validate_plan(plan_v1.canvas_to_plan(cycle)).issues)

    unknown = plan_v1.plan_to_canvas(_plan())
    unknown["nodes"][0]["data"]["tool"] = "missing.tool"
    assert any(issue.code == "tool" for issue in
               validate_plan(plan_v1.canvas_to_plan(unknown)).issues)

    mismatch = plan_v1.plan_to_canvas(_plan())
    upscale = next(node for node in mismatch["nodes"] if node["id"] == "upscale")
    upscale["data"]["tool"] = "image.generate"
    upscale["data"]["params"] = {"prompt": "$source.video_key",
                                    "model": "gemini-2.5-flash-image", "count": 1}
    assert any(issue.code == "port_type" for issue in
               validate_plan(plan_v1.canvas_to_plan(mismatch)).issues)


def test_ownership_stale_revision_and_approved_edit_returns_draft(db):
    row = workflows.create(db, user_id="user-a", name="Bản gốc",
                           canvas=plan_v1.plan_to_canvas(_plan()))
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
                                canvas=plan_v1.plan_to_canvas(_plan()))
    db.flush()
    clone_canvas = copy.deepcopy(workflows.as_canvas(original))
    clone = workflows.create(db, user_id="user-a", name="Bản sao", canvas=clone_canvas,
                             source_workflow_id=original.id)
    db.commit()
    assert clone.id != original.id and clone.source_workflow_id == original.id
    assert plan_v1.canvas_to_plan(workflows.as_canvas(clone)) == _plan()


def test_snapshot_moi_revision_va_restore_tao_revision_moi(db):
    row = workflows.create(db, user_id="user-a", name="Gốc",
                           canvas=plan_v1.plan_to_canvas(_plan()))
    changed = workflows.as_canvas(row); changed["goal"] = "Đã đổi"
    row = workflows.save(db, workflow_id=row.id, user_id="user-a", revision=1,
                         name="Đổi", canvas=changed)
    items = workflows.snapshots(db, row.id, "user-a")
    assert [item.revision for item in items] == [2, 1]
    restored = workflows.restore_snapshot(db, workflow_id=row.id, user_id="user-a",
                                          revision=1, expected_revision=2)
    assert restored.revision == 3 and restored.goal == _plan()["goal"]
    assert workflows.snapshots(db, row.id, "user-a")[0].reason == "restore"


def test_canvas_v2_preserves_pages_frames_annotations_and_executes_active_page(db):
    active = plan_v1.plan_to_canvas(_plan())
    document = {"version": 2, "goal": active["goal"],
                "budget_max_credit": active["budget_max_credit"],
                "active_page_id": "main", "pages": [
        {"id": "main", "name": "Main", "nodes": active["nodes"],
         "edges": active["edges"], "viewport": active["viewport"],
         "frames": [{"id": "f1", "name": "Render", "node_ids": ["source"]}],
         "notes": [{"id": "n1", "text": "Kiểm tra màu"}],
         "comments": [{"id": "c1", "text": "Duyệt trước khi chạy"}]},
        {"id": "drafts", "name": "Drafts", "nodes": [], "edges": [],
         "viewport": {"x": 0, "y": 0, "zoom": 1}, "frames": [],
         "notes": [], "comments": []},
    ]}
    assert plan_v1.canvas_to_plan(document) == _plan()
    row = workflows.create(db, user_id="user-a", name="V2", canvas=document)
    db.commit()
    assert workflows.as_canvas(row) == document
    assert row.nodes == active["nodes"] and row.edges == active["edges"]


@pytest.mark.parametrize("mutate, message", [
    (lambda doc: doc.update(active_page_id="missing"), "active_page_id"),
    (lambda doc: doc["pages"].append(copy.deepcopy(doc["pages"][0])), "Page id"),
    (lambda doc: doc["pages"][0].update(notes=[{}] * 201), "annotation"),
])
def test_canvas_v2_rejects_invalid_document(mutate, message):
    canvas = plan_v1.plan_to_canvas(_plan())
    document = {"version": 2, "goal": canvas["goal"],
                "budget_max_credit": canvas["budget_max_credit"],
                "active_page_id": "main", "pages": [{"id": "main", "name": "Main",
                    "nodes": canvas["nodes"], "edges": canvas["edges"],
                    "viewport": canvas["viewport"], "frames": [], "notes": [],
                    "comments": []}]}
    mutate(document)
    with pytest.raises(workflows.WorkflowError, match=message):
        plan_v1.canvas_to_plan(document)


def test_scope_frame_resolve_tu_document_server():
    canvas = plan_v1.plan_to_canvas(_plan())
    document = {"version": 2, "goal": canvas["goal"],
                "budget_max_credit": canvas["budget_max_credit"], "active_page_id": "p1",
                "pages": [{"id": "p1", "name": "Page", "nodes": canvas["nodes"],
                           "edges": canvas["edges"], "viewport": canvas["viewport"],
                           "frames": [{"id": "f1", "name": "Render", "node_ids": ["source"]}],
                           "notes": [], "comments": []}]}
    targets, audit = workflows.scope_targets(document, {"mode": "frame", "frame_id": "f1"})
    assert targets == ["source"] and audit["frame_name"] == "Render"
