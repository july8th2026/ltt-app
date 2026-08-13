"""Q92 / Prompt 12 — wave 2: the GPU workload, and two deliberate deferrals.

Wave 2 connects the long/expensive path: a job that needs a GPU lease, runs in
the worker, and can be cancelled. It opens `image.upscale` and **not**
`video.upscale` or `video.generate` — each for a reason this file pins down with
a test, so the deferral cannot quietly become "we forgot".
"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import Job
from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE, SCOPE_USAGE_READ)
from platform_core.registry import discover
from server.api.inventory import API_V1_PREFIX

PEPPER = "wave2-test-pepper-" + "q" * 40
GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"
# The whole published set, read from the snapshot every wave updates.
WAVE = tuple(entry["name"] for entry in
             json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"])
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ,
              SCOPE_CREDITS_READ, SCOPE_USAGE_READ)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200


def _config():
    return load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(WAVE)})


# ── What wave 2 opened ───────────────────────────────────────────────────────

def test_the_gpu_tool_is_published_and_matches_the_golden_contract():
    catalog = {tool.name: tool for tool in build_catalog(_config())}
    assert "image.upscale" in catalog
    snapshot = {"tools": [tool.to_public_dict()
                          for tool in build_catalog(_config())]}
    assert snapshot == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_the_gpu_tool_contract_names_no_engine_or_vendor():
    document = json.dumps(build_catalog(_config())[-1].to_public_dict()).lower()
    for leak in ("esrgan", "gpu", "vram", "upscalevideo", "engine", "cuda"):
        assert leak not in document, leak


def test_the_gpu_tool_is_recognised_as_a_scarce_resource():
    """Capacity limits key off what the manifest declares it needs."""
    manifest = next(item.manifest for item in discover()
                    if item.manifest.slug == "upscalevideo")
    assert limits.resource_class(manifest) == "gpu"
    # And the platform knows how much VRAM one of its jobs reserves.
    assert manifest.vram_for("upscalevideo.render") > 0


# ── The two deferrals, each with its reason ──────────────────────────────────

def test_video_upscale_stays_closed_because_its_hold_can_grow():
    """Its price depends on a duration the caller declares, and the worker tops
    the hold up once it measures the real one — fine for a person choosing a
    file, not for a signed machine quote (Q84)."""
    tool = next(spec for item in discover()
                if item.manifest.slug == "upscalevideo"
                for spec in item.manifest.tools if spec.name == "video.upscale")
    assert tool.api_exposed is False
    assert "image.upscale" in [entry.name for entry in build_catalog(_config())]
    assert "video.upscale" not in [entry.name for entry in build_catalog(_config())]

    # The behaviour that makes it unsafe to publish today still exists, so the
    # deferral is real rather than a stale note.
    from apps.upscalevideo import jobs as upscale_jobs

    assert hasattr(upscale_jobs, "_dam_bao_giu_cho")
    source = Path("apps/upscalevideo/jobs.py").read_text(encoding="utf-8")
    assert "credit.giu_cho(db, user_id, need - held, job_id)" in source


def test_video_generate_stays_closed_because_its_options_depend_on_the_model():
    """`resolution`/`duration`/`aspect_ratio` are declared `depends_on: model`
    and the valid sets differ per model. Publishing their union would let a
    caller pay for a combination the provider then refuses."""
    tool = next(spec for item in discover()
                if item.manifest.slug == "taovideo"
                for spec in item.manifest.tools if spec.name == "video.generate")
    assert tool.api_exposed is False
    assert tool.params_schema["resolution"]["depends_on"] == "model"

    from apps.taovideo import models

    per_model = {name: tuple(spec["resolutions"])
                 for name, spec in models.MODELS.items()}
    # The sets really do differ — that is the whole reason for the deferral.
    assert len(set(per_model.values())) > 1


# ── End to end on the GPU path ───────────────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wave2.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    limits.reset()

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "wave2-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": ",".join(WAVE),
        "LTT_PUBLIC_API_CLASS_CONCURRENCY": "gpu:1",
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        storage_mod.set_storage(None)
        limits.reset()
        dbmod.reset_engine()


def _session():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def _close(gen):
    try:
        next(gen)
    except StopIteration:
        pass


def _account(credits: int = 200):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"g-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=ALL_SCOPES,
                                    env={devkeys.PEPPER_ENV: PEPPER})
        db.commit()
        return user.id, token
    finally:
        _close(gen)


def _auth(token, idem=""):
    headers = {"Authorization": f"Bearer {token}"}
    if idem:
        headers["Idempotency-Key"] = idem
    return headers


def _uploaded_image(api, token) -> str:
    created = api.post(f"{API_V1_PREFIX}/uploads",
                       json={"tool": "image.upscale", "field": "image_key",
                             "filename": "in.png", "content_type": "image/png",
                             "size": len(PNG)},
                       headers=_auth(token))
    assert created.status_code == 201, created.text
    upload_id = created.json()["id"]
    api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
             files={"file": ("in.png", PNG, "image/png")}, headers=_auth(token))
    api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm", headers=_auth(token))
    return upload_id


def _run(api, token, upload_id, preset="fast", idem="wave2-upscale-0001"):
    payload = {"image_key": upload_id, "preset": preset}
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": "image.upscale", "input": payload},
                     headers=_auth(token))
    assert quote.status_code == 200, quote.text
    created = api.post(f"{API_V1_PREFIX}/jobs",
                       json={"tool": "image.upscale", "quote": quote.json()["quote"],
                             "input": payload},
                       headers=_auth(token, idem))
    return quote.json(), created


def test_a_gpu_job_is_queued_not_run_inside_the_request(api):
    """Nothing long may happen in HTTP: Cloudflare cuts the request at 100 s."""
    user_id, token = _account()
    upload_id = _uploaded_image(api, token)
    quote, created = _run(api, token, upload_id)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "queued"
    assert quote["credit"] == 2 and body["credit"]["held"] == 2

    gen, db = _session()
    try:
        job = db.get(Job, body["id"])
        assert job.status == "queued"
        assert job.app_slug == "upscalevideo"
        assert job.params["owner_id"] == user_id
        # The promoted input satisfies the handler's ownership rule.
        assert job.params["image_key"].startswith(f"upscalevideo/{user_id}/")
    finally:
        _close(gen)


def test_the_quality_preset_costs_what_the_ui_charges(api):
    from apps.upscalevideo.manifest import _cost

    _user_id, token = _account()
    upload_id = _uploaded_image(api, token)
    quote, _created = _run(api, token, upload_id, preset="quality",
                           idem="wave2-quality-0001")
    assert quote["credit"] == _cost({"image_key": "x", "preset": "quality"}) == 4


def test_gpu_capacity_stops_a_second_concurrent_job(api):
    """Backpressure on the scarce resource, before credit is held."""
    user_id, token = _account()
    first = _run(api, token, _uploaded_image(api, token), idem="wave2-gpu-first01")
    assert first[1].status_code == 201

    second = _run(api, token, _uploaded_image(api, token), idem="wave2-gpu-secnd1")
    assert second[1].status_code == 429
    body = second[1].json()
    assert body["code"] == "concurrency_limited" and body["resource"] == "gpu"

    from platform_core.models import CREDIT_HOLD, CreditEntry

    gen, db = _session()
    try:
        holds = db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.user_id == user_id,
            CreditEntry.kind == CREDIT_HOLD)).scalar_one()
        assert holds == 1
    finally:
        _close(gen)


def test_cancelling_a_queued_gpu_job_refunds_and_frees_capacity(api):
    user_id, token = _account()
    _quote, created = _run(api, token, _uploaded_image(api, token),
                           idem="wave2-cancel-0001")
    job_id = created.json()["id"]

    cancelled = api.post(f"{API_V1_PREFIX}/jobs/{job_id}/cancel",
                         headers=_auth(token))
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 200

    # The slot is free again, so a new job is accepted.
    again = _run(api, token, _uploaded_image(api, token), idem="wave2-after-cancel")
    assert again[1].status_code == 201


def test_an_engine_failure_refunds_and_reveals_nothing(api, monkeypatch):
    user_id, token = _account()
    _quote, created = _run(api, token, _uploaded_image(api, token),
                           idem="wave2-engine-fail1")
    job_id = created.json()["id"]

    from apps.upscalevideo import engine

    def _not_ready():
        return False

    monkeypatch.setattr(engine, "check_engine", _not_ready)

    from platform_core.job_runner import _chay_mot_job
    from datetime import datetime, timezone

    for _ in range(6):
        if not _chay_mot_job("wave2-test-worker"):
            break
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            if job.status in ("error", "cancelled"):
                break
            job.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "failed"
    assert detail["error"] == {"message": "The job could not be completed."}
    assert "esrgan" not in json.dumps(detail).lower()
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 200
    # Failure refunds once, never twice.
    from platform_core.models import CREDIT_REFUND, CreditEntry

    gen, db = _session()
    try:
        refunds = db.execute(sa.select(sa.func.count(CreditEntry.id)).where(
            CreditEntry.job_id == job_id,
            CreditEntry.kind == CREDIT_REFUND)).scalar_one()
        assert refunds == 1
    finally:
        _close(gen)


def test_a_retry_of_the_same_request_does_not_charge_twice(api):
    user_id, token = _account()
    upload_id = _uploaded_image(api, token)
    payload = {"image_key": upload_id, "preset": "fast"}
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": "image.upscale", "input": payload},
                     headers=_auth(token))
    body = {"tool": "image.upscale", "quote": quote.json()["quote"],
            "input": payload}
    first = api.post(f"{API_V1_PREFIX}/jobs", json=body,
                     headers=_auth(token, "wave2-retry-key-001"))
    second = api.post(f"{API_V1_PREFIX}/jobs", json=body,
                      headers=_auth(token, "wave2-retry-key-001"))
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 198
