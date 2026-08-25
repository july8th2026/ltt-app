"""Q92 / Prompt 07 — upload tickets, media inputs, artifact delivery.

The failures these tests exist to prevent: attaching somebody else's upload to
your job, smuggling a raw storage key into a job parameter, downloading another
account's output, and leaving promoted files behind when the request that
promoted them fails.
"""
from __future__ import annotations

import io
import uuid

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import (UPLOAD_PROMOTED, UPLOAD_READY, Job,
                                  UploadSession)
from platform_core.public_api import keys as devkeys, media
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE)
from platform_core.registry import AppManifest, LoadedApp, ToolSpec
from server.api.inventory import API_V1_PREFIX

PEPPER = "media-test-pepper-" + "v" * 40
TOOL = "image.sample"
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 120


def _cost(params: dict) -> int:
    return 7


def _fixture_apps():
    tool = ToolSpec(
        name=TOOL, job_type="sampleimg.generate",
        description="Fixture image tool.",
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 100},
            "image_key": {"type": "image", "required": False},
        },
        returns={"image_keys": "image[]", "prompt": "text"},
        api_exposed=True,
        api_contract={"scopes": (SCOPE_JOBS_CREATE,)},
    )
    manifest = AppManifest(
        slug="sampleimg", display_name="Sample image app",
        route_prefix="/sampleimg", job_types=("sampleimg.generate",),
        credit_cost=_cost, lifecycle="released", surface="customer",
        tools=(tool,))
    return [LoadedApp(manifest=manifest, router=None, error="")]


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'media.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)

    import platform_core.registry as registry_mod
    monkeypatch.setattr(registry_mod, "discover", _fixture_apps)

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "media-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": TOOL,
    })
    try:
        with TestClient(app) as client:
            yield client
    finally:
        from server.api import deps
        deps.set_principal_resolver(None)
        storage_mod.set_storage(None)
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


def _account(credits: int = 100, scopes=ALL_SCOPES):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"m-{uuid.uuid4().hex[:8]}@example.com",
                              password="a-good-password-12")
        db.flush()
        credit.cap_tay(db, user.id, credits, by="test")
        _key, token = devkeys.issue(db, user_id=user.id, scopes=scopes,
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


def _ticket(api, token, *, size=len(PNG), content_type="image/png",
            field="image_key"):
    return api.post(f"{API_V1_PREFIX}/uploads",
                    json={"tool": TOOL, "field": field, "filename": "photo.png",
                          "content_type": content_type, "size": size},
                    headers=_auth(token))


def _uploaded(api, token) -> str:
    """A confirmed upload id, through the public path only."""
    created = _ticket(api, token)
    assert created.status_code == 201, created.text
    upload_id = created.json()["id"]
    sent = api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
                    files={"file": ("photo.png", PNG, "image/png")},
                    headers=_auth(token))
    assert sent.status_code == 200, sent.text
    confirmed = api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm",
                         headers=_auth(token))
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == UPLOAD_READY
    return upload_id


def _run(api, token, *, image=None, idem="media-job-key-00001"):
    payload = {"prompt": "a cat"}
    if image:
        payload["image_key"] = image
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": TOOL, "input": payload}, headers=_auth(token))
    if quote.status_code != 200:
        # A bad media reference is refused at quote time, before any money is
        # involved. Hand that response back so the caller can assert on it.
        return quote
    return api.post(f"{API_V1_PREFIX}/jobs",
                    json={"tool": TOOL, "quote": quote.json()["quote"],
                          "input": payload},
                    headers=_auth(token, idem))


# ── Upload tickets ────────────────────────────────────────────────────────────

def test_a_ticket_locks_owner_type_and_size(api):
    user_id, token = _account()
    created = _ticket(api, token)
    assert created.status_code == 201
    body = created.json()
    assert body["content_type"] == "image/png"
    assert body["expected_size"] == len(PNG)
    assert body["upload"]["url"].endswith("/content")   # local backend fallback

    gen, db = _session()
    try:
        session = db.get(UploadSession, body["id"])
        assert session.user_id == user_id and session.app_slug == "sampleimg"
        # The staging key is derived, never accepted from the caller.
        assert session.staging_key.startswith(f"staging/{user_id}/sampleimg/")
    finally:
        _close(gen)


def test_a_ticket_never_exposes_a_storage_key(api):
    _user_id, token = _account()
    body = _ticket(api, token).json()
    for leak in ("staging/", "final_key", "bucket", "files/"):
        assert leak not in str(body)


@pytest.mark.parametrize("bad", [
    {"content_type": "application/x-msdownload"},
    {"size": 0},
    {"size": 64 * 1024 * 1024},          # above the image ceiling
    {"field": "prompt"},                 # not a media parameter
    {"field": "nope"},                   # not a parameter at all
])
def test_bad_tickets_are_refused(api, bad):
    _user_id, token = _account()
    assert _ticket(api, token, **bad).status_code == 400


def test_confirm_checks_the_bytes_not_the_promise(api):
    _user_id, token = _account()
    created = _ticket(api, token).json()
    # Right size, wrong content: the magic-byte check is what catches this.
    api.post(f"{API_V1_PREFIX}/uploads/{created['id']}/content",
             files={"file": ("photo.png", b"x" * len(PNG), "image/png")},
             headers=_auth(token))
    refused = api.post(f"{API_V1_PREFIX}/uploads/{created['id']}/confirm",
                       headers=_auth(token))
    assert refused.status_code == 400


def test_one_account_cannot_touch_another_accounts_ticket(api):
    _alice_id, alice = _account()
    _bob_id, bob = _account()
    upload_id = _ticket(api, alice).json()["id"]

    assert api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm",
                    headers=_auth(bob)).status_code == 404
    assert api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
                    files={"file": ("x.png", PNG, "image/png")},
                    headers=_auth(bob)).status_code == 404


def test_uploads_need_their_own_scope(api):
    _user_id, token = _account(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE))
    assert _ticket(api, token).status_code == 403


# ── Media as job input ────────────────────────────────────────────────────────

def test_an_upload_becomes_a_job_input_only_after_the_hold(api):
    user_id, token = _account()
    upload_id = _uploaded(api, token)
    response = _run(api, token, image=upload_id)
    assert response.status_code == 201, response.text
    job_id = response.json()["id"]

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        session = db.get(UploadSession, upload_id)
        assert session.status == UPLOAD_PROMOTED
        assert session.job_id == job_id
        # The job holds a real key; the caller never saw it.
        assert job.params["image_key"] == session.final_key
        assert job.params["image_key"].startswith(f"sampleimg/{user_id}/{job_id}/")
        assert "upload:" not in job.params["image_key"]
    finally:
        _close(gen)
    assert "image_key" not in str(response.json())


def test_a_raw_storage_key_is_not_a_valid_reference(api):
    _user_id, token = _account()
    upload_id = _uploaded(api, token)
    gen, db = _session()
    try:
        staging_key = db.get(UploadSession, upload_id).staging_key
    finally:
        _close(gen)

    for smuggled in (staging_key, "../../secrets/app.env", "files/anything.png"):
        response = _run(api, token, image=smuggled, idem=f"smuggle-{uuid.uuid4().hex[:8]}")
        assert response.status_code == 400, smuggled
        assert response.json()["code"] == "invalid_request"


def test_another_accounts_upload_cannot_be_attached(api):
    _alice_id, alice = _account()
    _bob_id, bob = _account()
    alice_upload = _uploaded(api, alice)
    response = _run(api, bob, image=alice_upload, idem="cross-tenant-attach1")
    assert response.status_code == 400


def test_an_unconfirmed_or_reused_ticket_is_refused(api):
    _user_id, token = _account()
    unconfirmed = _ticket(api, token).json()["id"]
    assert _run(api, token, image=unconfirmed,
                idem="unconfirmed-ticket01").status_code == 400

    used = _uploaded(api, token)
    assert _run(api, token, image=used, idem="first-use-of-ticket").status_code == 201
    replayed = _run(api, token, image=used, idem="second-use-of-ticket")
    assert replayed.status_code == 400


def test_a_failed_submit_leaves_no_promoted_orphan(api, monkeypatch):
    """Storage does not roll back with the database, so it is compensated."""
    user_id, token = _account()
    upload_id = _uploaded(api, token)

    from platform_core.public_api import idempotency as idem_mod

    def _boom(*args, **kwargs):
        raise RuntimeError("crash after promote, before commit")

    monkeypatch.setattr(idem_mod, "complete", _boom)
    with pytest.raises(RuntimeError):
        _run(api, token, image=upload_id, idem="crash-after-promote1")

    from platform_core.storage import get_storage

    gen, db = _session()
    try:
        session = db.get(UploadSession, upload_id)
        # Row is back to READY (transaction rolled back) and the object is back
        # in staging, where the sweeper still owns it.
        assert session.status == UPLOAD_READY
        assert get_storage().exists(session.staging_key)
        assert db.execute(sa.select(sa.func.count(Job.id))).scalar_one() == 0
    finally:
        _close(gen)


# ── Artifacts ─────────────────────────────────────────────────────────────────

def _finish(job_id: str, keys: list[str]):
    from platform_core import credit, jobs as jobq
    from platform_core.storage import get_storage

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        for key in keys:
            get_storage().put(key, io.BytesIO(PNG), content_type="image/png")
        jobq.complete(db, job, {"image_keys": keys, "prompt": "a cat"})
        credit.quyet_toan(db, job.user_id, job_id, 7)
        db.commit()
    finally:
        _close(gen)


def test_a_finished_job_lists_artifact_ids_not_keys(api):
    user_id, token = _account()
    job_id = _run(api, token).json()["id"]
    _finish(job_id, [f"sampleimg/{user_id}/{job_id}/out-0.png"])

    body = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert body["status"] == "succeeded"
    assert body["outputs"] == [{"id": f"{job_id}.image_keys.0",
                                "field": "image_keys", "index": 0}]
    assert "sampleimg/" not in str(body)


def test_an_artifact_resolves_to_a_download_for_its_owner_only(api):
    user_id, token = _account()
    _bob_id, bob = _account()
    job_id = _run(api, token).json()["id"]
    _finish(job_id, [f"sampleimg/{user_id}/{job_id}/out-0.png"])
    artifact = f"{job_id}.image_keys.0"

    described = api.get(f"{API_V1_PREFIX}/artifacts/{artifact}", headers=_auth(token))
    assert described.status_code == 200
    assert described.headers["cache-control"] == "no-store"
    assert "sampleimg/" not in described.text

    content = api.get(f"{API_V1_PREFIX}/artifacts/{artifact}/content",
                      headers=_auth(token))
    assert content.status_code == 200 and content.content == PNG

    for path in (f"{API_V1_PREFIX}/artifacts/{artifact}",
                 f"{API_V1_PREFIX}/artifacts/{artifact}/content"):
        assert api.get(path, headers=_auth(bob)).status_code == 404


@pytest.mark.parametrize("bad", [
    "not-an-id", "../../etc/passwd", "00000000-0000-0000-0000-000000000000.x.0",
])
def test_malformed_or_unknown_artifact_ids_are_all_404(api, bad):
    _user_id, token = _account()
    assert api.get(f"{API_V1_PREFIX}/artifacts/{bad}",
                   headers=_auth(token)).status_code == 404


def test_artifacts_need_their_own_scope(api):
    user_id, token = _account(scopes=(SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE,
                                      SCOPE_JOBS_READ))
    job_id = _run(api, token).json()["id"]
    _finish(job_id, [f"sampleimg/{user_id}/{job_id}/out-0.png"])
    denied = api.get(f"{API_V1_PREFIX}/artifacts/{job_id}.image_keys.0",
                     headers=_auth(token))
    assert denied.status_code == 403


def test_only_published_output_fields_become_artifacts(api):
    """A result field outside the contract must not become downloadable."""
    user_id, token = _account()
    job_id = _run(api, token).json()["id"]

    from platform_core import credit, jobs as jobq

    gen, db = _session()
    try:
        job = db.get(Job, job_id)
        jobq.complete(db, job, {"image_keys": [], "debug_dump": "internal/secret.txt"})
        credit.quyet_toan(db, user_id, job_id, 7)
        db.commit()
    finally:
        _close(gen)

    body = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert body["outputs"] == []
    assert "debug_dump" not in str(body)
    assert api.get(f"{API_V1_PREFIX}/artifacts/{job_id}.debug_dump.0",
                   headers=_auth(token)).status_code == 404


# ── Unit-level guards ─────────────────────────────────────────────────────────

def test_artifact_ids_round_trip_and_reject_garbage():
    assert media.parse_artifact_id(media.artifact_id("a" * 8 + "-0000-0000-0000-" + "b" * 12, "field", 3))
    from platform_core.public_api.errors import ApiError

    for bad in ("", "a.b", "x" * 40 + ".field.0", "job.field.9999"):
        with pytest.raises(ApiError):
            media.parse_artifact_id(bad)
