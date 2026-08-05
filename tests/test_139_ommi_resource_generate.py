"""Sinh ảnh cho tài nguyên OMMI — điều phối ở OMMI, provider dùng lại Tạo ảnh.

Ba điều file này phải chứng minh:

1. Báo giá và trừ tiền dùng CÙNG một công thức, và chưa xác nhận thì chưa nộp
   job — không có đường nào tiêu tiền mà người dùng chưa đồng ý.
2. Ảnh tham chiếu chỉ nhận ảnh của chính người gọi. Nhận ID của người khác là
   ép provider đọc ảnh riêng tư của họ — rò rỉ qua đường vòng.
3. `from-job` suy quyền từ chính job, và không cho gắn job của người khác.
"""
from __future__ import annotations

import io
import json
import re

import pytest
from fastapi.testclient import TestClient

PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)


@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'ommi-gen.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("LTT_STORAGE", raising=False)
    monkeypatch.setenv("LTT_PROMPT_AI_OMMI_ROLLOUT", "public")
    import platform_core.storage as storage_mod
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))

    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())

    db = next(dbmod.get_session())
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung
    ids = {}
    for email in ("gen-a@example.com", "gen-b@example.com"):
        user = tao_nguoi_dung(db, email=email, password="Strong-pass-123",
                              is_verified=True)
        ids[email] = user.id
        credit.cap_tay(db, user.id, 500, by="test")
    db.commit(); db.close(); dbmod.reset_engine()

    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"job_delay_seconds": 1, "max_retries": 1,
                               "sheet_id": "test"}), encoding="utf-8")
    from server.app import create_app
    app = create_app(env={"LTT_ENV": "local-server-test",
                          "LTT_CONFIG_PATH": str(cfg),
                          "LTT_SESSION_SECRET": "ommi-generate-test",
                          "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": ""})

    def login(email):
        client = TestClient(app, base_url="https://testserver",
                            follow_redirects=True)
        page = client.get("/login")
        token = re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)
        assert client.post("/login", data={
            "username": email, "password": "Strong-pass-123",
            "csrf_token": token, "next": "/prompt-ai-ommi"}).status_code == 200
        studio = client.get("/prompt-ai-ommi")
        csrf = re.search(r'name="csrf_token" value="([^"]+)"', studio.text).group(1)
        return client, csrf

    a, token_a = login("gen-a@example.com")
    b, token_b = login("gen-b@example.com")
    yield (a, token_a, ids["gen-a@example.com"],
           b, token_b, ids["gen-b@example.com"])
    a.close(); b.close(); dbmod.reset_engine(); storage_mod._storage = None


def _resource(client, token, name="Nhân vật", prompt="mot nhan vat hoat hinh"):
    made = client.post("/prompt-ai-ommi/api/resources",
                       headers={"X-CSRF-Token": token},
                       json={"kind": "character", "name": name,
                             "prompt_text": prompt})
    assert made.status_code == 201, made.text
    return made.json()["id"]


def _upload(client, token, rid):
    return client.post(
        f"/prompt-ai-ommi/api/resources/{rid}/images",
        data={"csrf_token": token, "label": "goc"},
        files={"file": ("a.png", io.BytesIO(PNG), "image/png")}).json()


def _gen(client, token, rid, **body):
    return client.post(f"/prompt-ai-ommi/api/resources/{rid}/images/generate",
                       headers={"X-CSRF-Token": token}, json=body)


def test_quote_does_not_submit_anything(api):
    a, token_a, id_a, *_ = api
    rid = _resource(a, token_a)
    quoted = _gen(a, token_a, rid, count=2)
    assert quoted.status_code == 200
    body = quoted.json()
    assert body["confirmed"] is False and body["credit"] > 0
    assert body["count"] == 2

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        assert db.query(Job).filter(Job.user_id == id_a).count() == 0
    finally:
        db.close()


def test_confirmed_run_submits_a_taoanh_job_priced_by_that_app(api):
    a, token_a, id_a, *_ = api
    rid = _resource(a, token_a)
    quoted = _gen(a, token_a, rid, count=3).json()
    started = _gen(a, token_a, rid, count=3, confirmed=True)
    assert started.status_code == 200, started.text
    assert started.json()["credit"] == quoted["credit"], (
        "giá báo và giá trừ phải cùng một công thức")

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.query(Job).filter(Job.user_id == id_a).one()
        # Điều phối thuộc OMMI, lời gọi provider thuộc Tạo ảnh.
        assert job.job_type == "taoanh.generate"
        assert job.app_slug == "prompt_ai_ommi"
        assert job.params["count"] == 3
        assert job.params["owner_id"] == id_a
    finally:
        db.close()


@pytest.mark.parametrize("case", ["cua-nguoi-khac", "cua-tai-nguyen-khac"])
def test_reference_ids_outside_this_resource_never_reach_the_provider(api, case):
    """Ảnh tham chiếu đi THẲNG vào tham số job, tức vào provider.

    Hai nguồn ID lạ đều phải rơi ra: ảnh của người dùng khác, và ảnh của chính
    mình nhưng thuộc tài nguyên khác. Trường hợp thứ hai mới là cái dễ lọt —
    nó không vi phạm quyền sở hữu nên một bộ lọc chỉ nhìn `owner_id` sẽ cho qua.
    """
    a, token_a, _id_a, b, token_b, _id_b = api
    rid_a = _resource(a, token_a)
    if case == "cua-nguoi-khac":
        other = _upload(b, token_b, _resource(b, token_b))
    else:
        other = _upload(a, token_a, _resource(a, token_a, name="Tài nguyên khác"))

    started = _gen(a, token_a, rid_a, confirmed=True,
                   reference_variant_ids=[other["id"]])
    assert started.status_code == 200

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.query(Job).filter(Job.params["prompt"].isnot(None)).all()[-1]
        assert "image_keys" not in job.params, (
            f"ID {case} không được lọt vào tham số job")
    finally:
        db.close()


def test_own_reference_images_are_passed_through(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    mine = _upload(a, token_a, rid)
    started = _gen(a, token_a, rid, confirmed=True,
                   reference_variant_ids=[mine["id"]])
    assert started.status_code == 200

    from platform_core.db import get_session
    from platform_core.models import Job
    db = next(get_session())
    try:
        job = db.query(Job).one()
        assert job.params["image_keys"] == [mine["storage_key"]]
    finally:
        db.close()


def test_generate_on_someone_elses_resource_is_404(api):
    a, token_a, _id_a, b, token_b, _id_b = api
    rid = _resource(a, token_a)
    assert _gen(b, token_b, rid, confirmed=True).status_code == 404


def test_too_short_a_prompt_is_rejected(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a, name="X", prompt="")
    assert _gen(a, token_a, rid, prompt="ngan").status_code == 422


def _finish_job(job_id, keys):
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, Job
    db = next(get_session())
    try:
        job = db.get(Job, job_id)
        job.status = JOB_DONE
        job.result = {"image_keys": keys}
        db.commit()
    finally:
        db.close()


def test_attaching_a_finished_job_adds_variants(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    job_id = _gen(a, token_a, rid, count=2, confirmed=True).json()["id"]
    _finish_job(job_id, ["taoanh/x/1.png", "taoanh/x/2.png"])

    attached = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/from-job",
                      headers={"X-CSRF-Token": token_a}, json={"job_id": job_id})
    assert attached.status_code == 201, attached.text
    assert len(attached.json()["variants"]) == 2
    detail = a.get(f"/prompt-ai-ommi/api/resources/{rid}").json()
    assert len(detail["variants"]) == 2
    assert detail["cover_variant_id"] == attached.json()["variants"][0]["id"]


def test_cannot_attach_someone_elses_job(api):
    a, token_a, _id_a, b, token_b, _id_b = api
    rid_a = _resource(a, token_a)
    rid_b = _resource(b, token_b)
    job_id = _gen(b, token_b, rid_b, confirmed=True).json()["id"]
    _finish_job(job_id, ["taoanh/x/1.png"])

    stolen = a.post(f"/prompt-ai-ommi/api/resources/{rid_a}/images/from-job",
                    headers={"X-CSRF-Token": token_a}, json={"job_id": job_id})
    assert stolen.status_code == 404
    assert a.get(f"/prompt-ai-ommi/api/resources/{rid_a}"
                 ).json()["variants"] == []


def test_cannot_attach_a_job_that_has_not_finished(api):
    a, token_a, *_ = api
    rid = _resource(a, token_a)
    job_id = _gen(a, token_a, rid, confirmed=True).json()["id"]
    response = a.post(f"/prompt-ai-ommi/api/resources/{rid}/images/from-job",
                      headers={"X-CSRF-Token": token_a}, json={"job_id": job_id})
    assert response.status_code == 409
