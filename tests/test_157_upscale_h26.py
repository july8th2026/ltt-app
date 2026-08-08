"""Regression H26.5 cho download/UX Upscale customer-facing."""
from __future__ import annotations

import io
import subprocess
import pytest


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'up-h26.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "test-secret-up-h26")
    monkeypatch.setenv("LTT_ADMIN_USERNAME", "admin")
    monkeypatch.delenv("TURNSTILE_SECRET_KEY", raising=False)
    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from server.app import create_app
    test_client = TestClient(create_app(), base_url="https://testserver",
                             follow_redirects=False)
    try:
        yield test_client
    finally:
        dbmod.reset_engine()


def _csrf(client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    import re
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def test_download_output_owner_only_va_ep_attachment(client, tmp_path):
    import platform_core.db as dbmod
    from platform_core.models import JOB_DONE, Job
    from platform_core.storage import LocalStorage, set_storage
    from platform_core.users import tao_nguoi_dung

    storage = LocalStorage(str(tmp_path / "upscale-download"))
    set_storage(storage)
    try:
        gen = dbmod.get_session(); db = next(gen)
        try:
            mine = tao_nguoi_dung(db, email="up-download@example.com",
                                  password="matkhau-tot-12", is_verified=True)
            other = tao_nguoi_dung(db, email="up-download-other@example.com",
                                   password="matkhau-tot-12", is_verified=True)
            key = f"upscalevideo/{mine.id}/job/output.mp4"
            storage.put(key, io.BytesIO(b"UPSCALED"), content_type="video/mp4")
            own = Job(user_id=mine.id, app_slug="upscalevideo",
                      job_type="upscalevideo.render", status=JOB_DONE,
                      params={"source_name": "video của tôi.mov", "target_height": 1440},
                      result={"video_key": key, "target_height": 1440})
            foreign = Job(user_id=other.id, app_slug="upscalevideo",
                          job_type="upscalevideo.render", status=JOB_DONE,
                          result={"video_key": f"upscalevideo/{other.id}/private.mp4"})
            db.add_all([own, foreign]); db.commit()
            own_id, foreign_id = own.id, foreign.id
        finally:
            try: next(gen)
            except StopIteration: pass

        token = _csrf(client, "/login")
        logged = client.post("/login", data={"username": "up-download@example.com",
                                              "password": "matkhau-tot-12",
                                              "csrf_token": token})
        assert logged.status_code == 303
        response = client.get(f"/upscalevideo/jobs/{own_id}/download")
        assert response.status_code == 200 and response.content == b"UPSCALED"
        assert response.headers["content-disposition"] == (
            'attachment; filename="video-c-a-t-i-upscaled-1440p.mp4"')
        assert response.headers["x-content-type-options"] == "nosniff"
        assert client.get(f"/upscalevideo/jobs/{foreign_id}/download").status_code == 404
    finally:
        set_storage(None)


def test_customer_copy_khong_lo_watch_research_hoac_jargon_noi_bo():
    # Template contract: Watch chỉ nằm trong admin condition và customer copy
    # không còn dòng hoãn Q47/điều khiển nghiên cứu.
    from pathlib import Path
    page = Path("apps/upscalevideo/templates/upscalevideo.html").read_text(
        encoding="utf-8")
    assert "Pause và Delete đang hoãn theo Q47" not in page
    assert "NGHIÊN CỨU" not in page
    assert page.index("{% if is_admin(request) %}") < page.index("up-step up-watch")


def test_engine_ghim_ncnn_vulkan_vao_gpu_lease_va_giu_khi_fallback(
        tmp_path, monkeypatch):
    from apps.upscalevideo import engine
    from apps.upscalevideo.schemas import TuneResult

    calls = []

    class Process:
        returncode = 1

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = -9

    def fake_popen(args, **kwargs):
        calls.append((args, kwargs))
        process = Process()
        # Lần fallback thành công; `_count_png` được mock theo số lần gọi.
        process.returncode = 0 if len(calls) == 2 else 1
        return process

    counts = iter((0, 1))
    monkeypatch.setattr(engine.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(engine, "_count_png", lambda _path: next(counts))
    tune = TuneResult(model="realesr-general-x4v3", tile=384, threads="1:2:2",
                      est_alloc_mb=1000, free_mb=12000, budget_mb=9000,
                      fast_path=True)
    env = {"CUDA_VISIBLE_DEVICES": "GPU-lease"}
    assert engine.run_upscale(str(tmp_path / "in"), str(tmp_path / "out"),
                              tune, 1, gpu_index=1, env=env) == "done"
    assert len(calls) == 2
    for command, kwargs in calls:
        assert command[-2:] == ["-g", "1"]
        assert kwargs["env"] is env


def test_job_map_uuid_sang_gpu_index_va_ffmpeg_env(monkeypatch):
    from apps.upscalevideo import jobs
    from platform_core import gpu

    selected = gpu.GpuInfo(index=1, name="RTX", uuid="GPU-b", total_mb=16311,
                           free_mb=15000, util_pct=0)
    monkeypatch.setattr(gpu, "by_uuid", lambda uuid: selected if uuid == "GPU-b" else None)

    class Context:
        gpu_uuid = "GPU-b"

        @staticmethod
        def gpu_env():
            return {"CUDA_VISIBLE_DEVICES": "GPU-b"}

    index, env = jobs._gpu_runtime(Context())
    assert index == 1 and env["CUDA_VISIBLE_DEVICES"] == "GPU-b"
    with pytest.raises(RuntimeError, match="không còn khả dụng"):
        jobs._gpu_runtime(type("Missing", (), {
            "gpu_uuid": "GPU-missing", "gpu_env": staticmethod(lambda: {})})())


def test_ffmpeg_subprocess_nhan_gpu_env(monkeypatch):
    from apps.upscalevideo import ff

    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(ff.subprocess, "run", fake_run)
    env = {"CUDA_VISIBLE_DEVICES": "GPU-b"}
    ff._run(["ffmpeg", "-version"], env=env)
    assert captured["env"] is env
