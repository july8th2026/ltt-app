"""P12 integration: Canvas snapshot executes all seven real ToolSpec contracts."""
from __future__ import annotations

import pytest


@pytest.fixture()
def db_user(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'p12.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    dbmod.reset_engine(); dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="p12@example.com", password="Strong-pass-123",
                          is_verified=True)
    db.commit()
    try:
        yield db, user
    finally:
        db.close(); dbmod.reset_engine()


def _plan():
    base = {"fanout": 1, "max_retry": 0, "on_fail": "retry_same", "verify": None}
    return {"version": 1, "goal": "Tạo bộ nội dung đủ ảnh chữ video GPU",
            "budget_max_credit": 5000, "steps": [
        # `text.script` (tool cua `kichban`) DA GO o Q109. Thay bang
        # `text.prompt_package` — buoc van la "sinh van ban", va bo test van
        # kiem dung thu no sinh ra de kiem: mot chuoi bay buoc di het.
        {"id": "text", "tool": "text.prompt_package", "after": [], **base,
         "params": {"title": "Cách làm phim ngắn",
                    "story": "Một hướng dẫn ngắn về dựng phim.",
                    "scene_count": 3, "aspect_ratio": "16:9"}},
        {"id": "image", "tool": "image.generate", "after": [], **base, "fanout": 2,
         "params": {"prompt": "Một thành phố tương lai", "model": "hidream-o1",
                    "aspect_ratio": "16:9", "count": 1}},
        {"id": "thumb", "tool": "image.thumbnail", "after": [], **base,
         "params": {"topic": "Du lịch Việt Nam", "model": "hidream-o1",
                    "aspect_ratio": "16:9", "count": 1}},
        {"id": "video", "tool": "video.generate", "after": [], **base,
         "params": {"prompt": "Máy quay tiến qua khu rừng", "model": "seedance-2.0-mini",
                    "resolution": "720p", "duration": 5, "aspect_ratio": "16:9",
                    "generate_audio": True}},
        {"id": "subtitle", "tool": "video.subtitle", "after": ["video"], **base,
         "params": {"video_key": "$video.video_key",
                    "transcript": [{"start": 0, "end": 1, "text": "Xin chào"}],
                    "style_id": "default", "quality": "standard"}},
        {"id": "upscale", "tool": "video.upscale", "after": ["video"], **base,
         "params": {"video_key": "$video.video_key", "preset": "quality",
                    "target_height": 2160, "codec": "hevc", "preview": False}},
        {"id": "clips", "tool": "video.short_clips", "after": ["video"], **base,
         "params": {"video_key": "$video.video_key", "tier": "high_quality",
                    "genre": "talking_head", "aspect_ratio": "9:16", "language": "vi",
                    "target_clip_count": 10, "min_clip_duration_sec": 15,
                    "max_clip_duration_sec": 60}},
    ]}


def test_canvas_to_immutable_run_all_seven_tools_resume_and_settle(db_user):
    db, user = db_user
    from platform_core import credit, jobs
    from platform_core.agent import budget, executor, runs, workflows
    from platform_core.agent.validator import validate_plan
    from platform_core.agent.tools import discover_tools

    plan = _plan(); validation = validate_plan(plan, db=db, user=user)
    assert validation.valid, validation.issues
    canvas = workflows.plan_to_canvas(plan)
    assert workflows.canvas_to_plan(canvas) == plan
    row = workflows.create(db, user_id=user.id, name="P12 seven tools", canvas=canvas)
    snapshot = workflows.canvas_to_plan(workflows.as_canvas(row))
    run = runs.create_run(db, user_id=user.id, goal=row.goal, plan=snapshot,
                          budget_max=row.budget_max)
    budget.set_quote(db, run, plan=snapshot, validation=validation)
    credit.cap_tay(db, user.id, run.estimated + 100, by="p12-test")
    budget.approve(db, run_id=run.id, user_id=user.id, approved_by=user.id,
                   expected_version=run.version)
    db.commit()

    results = {
        "text.prompt_package": {"prompt_package": {"title": "T"},
                                "master_prompt": "M"},
        "image.generate": {"image_keys": ["image/test/1.png"], "prompt": "p"},
        "image.thumbnail": {"image_keys": ["thumbnail/test/1.png"], "prompt": "p"},
        "video.generate": {"video_key": "taovideo/test/1.mp4"},
        "video.subtitle": {"video_key": "autosubvideo/test/1.mp4", "srt_key": "s", "ass_key": "a"},
        "video.upscale": {"video_key": "upscalevideo/test/1.mp4"},
        "video.short_clips": {"clips": [{"video_key": "taoclipngan/test/1.mp4"}]},
    }
    tool_by_step = {step["id"]: step["tool"] for step in plan["steps"]}
    seen = set()
    for _ in range(12):
        executor.tick(db, run_id=run.id, user_id=user.id); db.commit()
        # Repeating a tick before completion simulates a restarted orchestrator.
        before = len(runs.children(db, run))
        executor.tick(db, run_id=run.id, user_id=user.id); db.commit()
        assert len(runs.children(db, run)) == before
        for child in runs.children(db, run):
            if child.status == "queued":
                tool = tool_by_step[child.step_id]; seen.add(tool)
                jobs.complete(db, child, results[tool])
        db.commit()
        if run.status == "done":
            break
    if run.status != "done":
        executor.tick(db, run_id=run.id, user_id=user.id); db.commit()
    assert run.status == "done"
    assert seen == set(tool_by_step.values())
    assert run.actual <= run.estimated
    settle = next(item for item in reversed(run.decision_log) if item["event"] == "settle")
    assert settle["refunded"] == run.estimated - run.actual
    assert snapshot == run.plan  # immutable even if the workflow draft changes later
    from apps.agent.routes._shared import _run_json
    artifacts = _run_json(run)["artifacts"]
    assert {item["step_id"] for item in artifacts} == {
        "image", "thumb", "video", "subtitle", "upscale", "clips"}
    assert all(item["url"].startswith(f"/agent/api/runs/{run.id}/artifacts/")
               for item in artifacts)


def test_concurrent_run_cap_is_enforced_at_creation_boundary(db_user):
    db, user = db_user
    from platform_core.agent import runs
    for index in range(runs.MAX_ACTIVE_RUNS_PER_USER):
        runs.create_run_capped(db, user_id=user.id, goal=f"run {index}")
    with pytest.raises(runs.AgentRunError, match="tối đa"):
        runs.create_run_capped(db, user_id=user.id, goal="one too many")
