"""H15.S2.2 Job Center controls, isolation and artifact guards."""

from pathlib import Path

from server.routes.jobs import _artifacts


ROOT = Path(__file__).resolve().parents[1]


def test_artifacts_only_come_from_result_key_fields():
    result = {"video_key": "owned/out.mp4", "prompt": "secret",
              "image_keys": ["owned/a.png", "owned/b.png"],
              "nested": [{"srt_key": "owned/sub.srt"}]}
    items = _artifacts(result)
    assert [item["key"] for item in items] == [
        "owned/out.mp4", "owned/a.png", "owned/b.png", "owned/sub.srt"]
    assert all("secret" not in item.values() for item in items)


def test_job_routes_have_owner_actions_and_opaque_artifact_index():
    source = (ROOT / "server" / "routes" / "jobs.py").read_text(encoding="utf-8")
    assert '@router.post("/jobs/{job_id}/cancel")' in source
    assert '@router.post("/jobs/{job_id}/retry")' in source
    assert '@router.get("/jobs/{job_id}/artifacts/{index}")' in source
    assert '@router.get("/ops/jobs/{job_id}/events")' in source
    assert "job.user_id != u.id" in source
    assert "old.user_id != u.id" in source


def test_job_templates_have_filters_actions_progress_and_artifacts():
    jobs = (ROOT / "server" / "templates" / "jobs.html").read_text(encoding="utf-8")
    detail = (ROOT / "server" / "templates" / "job_detail.html").read_text(encoding="utf-8")
    progress = (ROOT / "server" / "templates" / "_job_progress.html").read_text(encoding="utf-8")
    assert 'name="status"' in jobs and 'name="app"' in jobs
    assert 'name="date_from"' in jobs and 'name="date_to"' in jobs
    assert "/cancel" in detail and "/retry" in detail and "/artifacts/" in detail
    assert 'role="progressbar"' in progress and 'aria-live="polite"' in progress
    assert "job-timeline" in progress and "job.correlation_id" in detail
    assert "job.result | tojson" not in progress
    assert "job.error" not in progress
