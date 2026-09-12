"""Q92 / Prompt 11 — wave 1: the first real tools on the public API.

This is the first time the public surface points at production apps rather than
a fixture, so the tests ask three things:

* does the whole chain work — catalog → quote → job → **the app's own handler in
  the worker** → artifact → settle → usage → webhook;
* does the API charge exactly what the UI charges for the same operation;
* did anything that must stay closed (internal apps, unexposed tools) open.

The provider call is stubbed. A real canary belongs on a deployment with keys
and a budget, not in a test suite that must be free and offline.
"""
from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient

from platform_core.models import CREDIT_SETTLE, CreditEntry, Job
from platform_core.public_api import keys as devkeys
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.scopes import (SCOPE_ARTIFACTS_READ,
                                             SCOPE_CREDITS_READ,
                                             SCOPE_JOBS_CANCEL, SCOPE_JOBS_CREATE,
                                             SCOPE_JOBS_READ, SCOPE_TOOLS_READ,
                                             SCOPE_UPLOADS_WRITE,
                                             SCOPE_USAGE_READ,
                                             SCOPE_WEBHOOKS_MANAGE)
from platform_core.registry import discover
from server.api.inventory import API_V1_PREFIX

PEPPER = "wave1-test-pepper-" + "r" * 40
WAVE1 = ("image.thumbnail", "image.generate")
# Later waves add to the same catalog, so the *total* published set is read from
# the golden snapshot rather than repeated here — one list to update per wave,
# in the file that already has to be updated.
GOLDEN = Path(__file__).parent / "golden" / "public_api_catalog_v1.json"
PUBLISHED = tuple(entry["name"] for entry in
                  json.loads(GOLDEN.read_text(encoding="utf-8"))["tools"])
ALL_SCOPES = (SCOPE_TOOLS_READ, SCOPE_JOBS_CREATE, SCOPE_JOBS_READ,
              SCOPE_JOBS_CANCEL, SCOPE_UPLOADS_WRITE, SCOPE_ARTIFACTS_READ,
              SCOPE_CREDITS_READ, SCOPE_USAGE_READ, SCOPE_WEBHOOKS_MANAGE)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 200


# ── What wave 1 opened, and what stayed shut ─────────────────────────────────

def test_the_wave_one_tools_are_exposed():
    exposed = sorted(tool.name for item in discover() if not item.error
                     for tool in item.manifest.tools if tool.api_exposed)
    assert set(WAVE1).issubset(exposed)
    assert exposed == sorted(PUBLISHED)


def test_the_retired_and_internal_apps_stayed_closed():
    """The traps Prompt 01 called out, checked against the live registry.

    Three of the four apps this test used to name — `kichban` (retired),
    `demo` (infrastructure canary) and `mediatools` (runtime-only, and the one
    that fetches a caller-supplied URL) — were deleted on 2026-08-25 under Q108
    and Q109. Deletion closes them harder than any flag could, so the check that
    remains is the one still capable of failing: an internal app must never
    acquire `api_exposed` by accident.
    """
    by_slug = {item.manifest.slug: item for item in discover()}

    # Operator tooling stays off the customer surface.
    manifest = by_slug["qualitylab"].manifest
    assert manifest.surface == "admin" and manifest.lifecycle == "internal"
    assert not any(tool.api_exposed for tool in manifest.tools)

    # And nothing that is not a customer surface may publish a tool at all.
    for item in discover():
        if item.manifest.surface == "customer":
            continue
        assert not any(tool.api_exposed for tool in item.manifest.tools),             item.manifest.slug


def test_the_published_contract_matches_the_golden_snapshot():
    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED)})
    catalog = build_catalog(config)
    snapshot = {"tools": [tool.to_public_dict() for tool in catalog]}
    assert snapshot == json.loads(GOLDEN.read_text(encoding="utf-8"))


def test_the_public_contract_names_no_vendor_and_no_internal_path():
    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED)})
    document = json.dumps({"tools": [tool.to_public_dict()
                                     for tool in build_catalog(config)]}).lower()
    for leak in ("gemini", "byteplus", "flash-image", "pro-image",
                 "prompts/", "thumbnail/", "taoanh/", "job_type", "app_slug",
                 "api_key"):
        assert leak not in document, leak


def test_openai_may_be_NAMED_AS_A_FORMAT_but_never_AS_A_MODEL():
    """⚠️ `openai` đã ra khỏi danh sách cấm ở trên, và đây là chỗ giải thích.

    Danh sách đó trộn **hai rủi ro khác nhau**:

      ① tên **nhà cung cấp model ta bán lại** (gemini, byteplus, …) — lộ ra thì
         ngày đổi nhà cung cấp là một thay đổi phá vỡ tích hợp của khách;
      ② **đường dẫn nội bộ** (prompts/, job_type, app_slug) — lộ ra là hở ruột.

    `openai` vào danh sách khi chưa tool nào tương thích dây OpenAI. Nay `text.chat`
    **cố ý** tương thích, và cụm *"OpenAI-compatible message format"* là một **lời
    hứa với khách về giao thức**, không phải tiết lộ thứ gì chạy đằng sau — ta
    không bán lại OpenAI. Giấu nó đi làm tài liệu tệ hơn mà không bảo vệ gì.

    ⛔ Nhưng miễn trừ cả chuỗi thì mất chốt. Nên đổi lấy một chốt **hẹp hơn và
       chặt hơn**: `openai` được phép xuất hiện trong **văn xuôi mô tả**, và
       TUYỆT ĐỐI KHÔNG được là một **model, alias hay enum** — vì đó mới đúng là
       rủi ro ① mà danh sách kia sinh ra để chặn.
    """
    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED)})
    for tool in build_catalog(config):
        d = tool.to_public_dict()
        for ten, schema in (d.get("input_schema", {}).get("properties", {})).items():
            for khoa in ("enum", "default", "examples"):
                gia_tri = json.dumps(schema.get(khoa, ""), ensure_ascii=False).lower()
                assert "openai" not in gia_tri, (
                    f"{d['name']}.{ten}.{khoa} dat ten OpenAI nhu mot model/alias — "
                    "do la rui ro danh sach cam sinh ra de chan")
        for khoa in ("models", "model_aliases"):
            gia_tri = json.dumps(d.get(khoa, ""), ensure_ascii=False).lower()
            assert "openai" not in gia_tri, f"{d['name']}.{khoa} dat ten OpenAI"


def test_model_choice_is_published_only_where_price_follows_it():
    """Otherwise a caller buys the dearest model at the cheapest price.

    🔴 Rewritten 2026-09-09 (AI CLEAN REBUILD V2 pha 06.3). The rule in the
       title is unchanged; what changed is which side of it `image.generate`
       falls on.

       It used to publish three aliases over three Gemini models, and that was
       correct *because the price followed the choice* (5 / 5 / 8). The tool now
       runs a single internal model priced per image, so the choice buys
       nothing — and publishing it would sell three names for one product.
       The whole alias block went with the engine; see CHANGELOG.md.
    """
    config = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(WAVE1)})
    catalog = {tool.name: tool for tool in build_catalog(config)}

    image = catalog["image.generate"]
    assert "model" not in image.input_schema["properties"], (
        "gia thoi phu thuoc model — cong bo lua chon la ban ba ten cho mot mon")
    assert not image.model_aliases

    # ⭐ Đối chứng: luật này chỉ có nghĩa nếu nó CÒN cho phép công bố ở nơi giá
    #    thật sự đi theo model. Thiếu vế này thì "không tool nào công bố model"
    #    cũng làm phép kiểm xanh — kể cả khi cơ chế công bố đã hỏng hẳn.
    day_du = load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": ",".join(PUBLISHED)})
    video = {t.name: t for t in build_catalog(day_du)}["video.generate"]
    assert video.input_schema["properties"]["model"]["enum"]

    # The thumbnail tool prices every image the same, so it publishes no choice.
    assert "model" not in catalog["image.thumbnail"].input_schema["properties"]


# ── End to end, with a stubbed provider ──────────────────────────────────────

@pytest.fixture()
def api(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wave1.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-used-by-the-stub")

    import platform_core.db as dbmod
    import platform_core.storage as storage_mod
    dbmod.reset_engine()
    storage_mod.set_storage(storage_mod.LocalStorage(str(tmp_path / "files")))
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    # Job anh gianh `anh_3090` tu dual-model 5.5, va luat 0 fail-closed: khong co
    # dong `gpu_residency` thi worker chi tra job ve hang doi, khong chay handler.
    # Ly do day du: `tests/conftest.py::mo_cu_tru_3090`.
    from platform_core.llm import residency as _residency

    from tests.conftest import mo_cu_tru_3090
    mo_cu_tru_3090(_residency.ANH)

    # The render gateway is the only thing stubbed: the prompt building,
    # storage, credit reporting and result shape all run for real.
    #
    # 🔴 Pha 06.3: trước đây chỗ này vá `_goi_gemini` của cả hai app. Cả hai
    #    hàm ấy đã bị xoá cùng động cơ Gemini, nên ranh giới vá mới là
    #    `_dieu_phoi()` — đúng chỗ được tách ra để tiêm được mà không chạm mạng.
    import apps.taoanh.jobs as taoanh_jobs
    import apps.thumbnail.jobs as thumbnail_jobs
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi

    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs, taoanh_jobs)

    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test", "LTT_SESSION_SECRET": "wave1-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"), "LTT_PUBLIC_API": "1",
        "LTT_PUBLIC_API_TOOLS": ",".join(WAVE1),
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


def _account(credits: int = 500):
    from platform_core import credit
    from platform_core.users import tao_nguoi_dung

    gen, db = _session()
    try:
        user = tao_nguoi_dung(db, email=f"w-{uuid.uuid4().hex[:8]}@example.com",
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


def _quote_and_run(api, token, tool, payload, idem):
    quote = api.post(f"{API_V1_PREFIX}/quotes",
                     json={"tool": tool, "input": payload}, headers=_auth(token))
    assert quote.status_code == 200, quote.text
    created = api.post(f"{API_V1_PREFIX}/jobs",
                       json={"tool": tool, "quote": quote.json()["quote"],
                             "input": payload},
                       headers=_auth(token, idem))
    return quote.json(), created


def _run_worker_once() -> bool:
    """Run the real worker step: claim, execute the app handler, settle."""
    from platform_core.job_runner import _chay_mot_job

    return _chay_mot_job("wave1-test-worker")


def test_thumbnail_runs_end_to_end_through_the_worker(api):
    user_id, token = _account()
    # ⛔ `title` và `text_style` đã rời hợp đồng ở pha 06.3 cùng chữ-trong-ảnh —
    #    gửi chúng nay là `400 Unknown input field`, và đó là hành vi ĐÚNG.
    payload = {"topic": "cách nướng bánh mì", "phong_cach": "cinematic",
               "aspect_ratio": "16:9", "count": 2}
    quote, created = _quote_and_run(api, token, "image.thumbnail", payload,
                                    "wave1-thumbnail-001")
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    # Hai ảnh, theo đúng HÀM GIÁ của app — không gõ lại con số ở đây. Con số cũ
    # (10) là giá của động cơ cũ; một hằng số gõ tay chỉ đo được rằng ai đó chưa
    # sửa nó.
    from apps.thumbnail.manifest import _cost as _gia_thumbnail
    gia_hai_anh = _gia_thumbnail({"count": 2})
    assert quote["credit"] == gia_hai_anh
    assert created.json()["credit"]["held"] == gia_hai_anh

    assert _run_worker_once() is True

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "succeeded"
    assert detail["credit"] == {"held": gia_hai_anh, "charged": gia_hai_anh}
    assert len(detail["outputs"]) == 2

    # The artifact resolves, downloads, and never shows a storage key.
    artifact = detail["outputs"][0]["id"]
    described = api.get(f"{API_V1_PREFIX}/artifacts/{artifact}",
                        headers=_auth(token))
    assert described.status_code == 200 and "thumbnail/" not in described.text
    content = api.get(f"{API_V1_PREFIX}/artifacts/{artifact}/content",
                      headers=_auth(token))
    # Bytes do MÁY VẼ sinh ra (thật hay giả), không phải hằng số của tệp này.
    assert content.status_code == 200 and content.content[1:4] == b"PNG"

    # Usage and balance agree with the ledger.
    usage = api.get(f"{API_V1_PREFIX}/usage", headers=_auth(token)).json()
    assert usage["totals"]["net_charged_credit"] == gia_hai_anh
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 500 - gia_hai_anh


def test_image_generation_no_longer_sells_a_model_choice(api):
    """🔴 Thay `test_image_generation_prices_by_model_alias` (pha 06.3).

    Bản cũ chốt *"alias rẻ 5, alias đắt 8, và alias tới handler dưới dạng id
    thật"*. Cả ba mệnh đề chết cùng khối alias: một model, một giá.

    ⭐ Cái thay nó chốt hai thứ MẠNH HƠN, vì cả hai đều là điều kiện an toàn chứ
       không phải mô tả bảng giá:

         · một alias cũ gửi lên phải bị **từ chối**, không được lặng lẽ rơi về
           model mặc định rồi tính tiền như thường;
         · giá **không** đổi theo `model`, nên không có cách nào mua model đắt
           với giá rẻ — chính điều mà bản cũ phải dùng ba lượt gọi để canh.
    """
    user_id, token = _account()
    tu_choi = api.post(f"{API_V1_PREFIX}/quotes",
                       json={"tool": "image.generate",
                             "input": {"prompt": "a red bicycle",
                                       "model": "enhanced", "count": 1}},
                       headers=_auth(token))
    assert tu_choi.status_code == 400, tu_choi.text
    assert "model" in tu_choi.text

    mot, _created = _quote_and_run(
        api, token, "image.generate", {"prompt": "a red bicycle", "count": 1},
        "wave1-image-one001")
    hai, _created2 = _quote_and_run(
        api, token, "image.generate", {"prompt": "a red bicycle", "count": 2},
        "wave1-image-two001")
    assert hai["credit"] == 2 * mot["credit"], "gia phai theo SO ANH"

    gen, db = _session()
    try:
        jobs = db.execute(sa.select(Job).order_by(Job.created_at)).scalars().all()
        assert jobs[0].params["owner_id"] == user_id
    finally:
        _close(gen)


def test_the_api_charges_what_the_ui_charges(api):
    """Parity is not a copy of the price — it is the same cost function."""
    from apps.taoanh.manifest import _cost as taoanh_cost
    from apps.thumbnail.manifest import _cost as thumbnail_cost

    _user_id, token = _account()
    for tool, payload, ui_cost in (
        ("image.thumbnail", {"topic": "x", "count": 3},
         thumbnail_cost({"count": 3})),
        ("image.generate", {"prompt": "x", "count": 2},
         taoanh_cost({"count": 2})),
    ):
        quote = api.post(f"{API_V1_PREFIX}/quotes",
                         json={"tool": tool, "input": payload},
                         headers=_auth(token))
        assert quote.json()["credit"] == ui_cost, tool


def test_a_reference_image_travels_from_upload_to_handler(api):
    user_id, token = _account()
    created = api.post(f"{API_V1_PREFIX}/uploads",
                       json={"tool": "image.generate", "field": "image_key",
                             "filename": "ref.png", "content_type": "image/png",
                             "size": len(PNG)},
                       headers=_auth(token))
    assert created.status_code == 201, created.text
    upload_id = created.json()["id"]
    api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/content",
             files={"file": ("ref.png", PNG, "image/png")}, headers=_auth(token))
    api.post(f"{API_V1_PREFIX}/uploads/{upload_id}/confirm", headers=_auth(token))

    _quote, response = _quote_and_run(
        api, token, "image.generate",
        {"prompt": "same bike, new colour", "image_key": upload_id, "count": 1},
        "wave1-reference-001")
    assert response.status_code == 201, response.text

    gen, db = _session()
    try:
        job = db.get(Job, response.json()["id"])
        key = job.params["image_key"]
        # The handler's ownership rule is `<app>/<owner>/...` — the promoted key
        # has to satisfy it, or every reference would be rejected at run time.
        assert key.startswith(f"taoanh/{user_id}/")
        from apps.taoanh.jobs import _canvas_reference_keys

        assert _canvas_reference_keys(job.params, user_id) == [key]
    finally:
        _close(gen)


def test_a_provider_failure_refunds_and_says_nothing_internal(api, monkeypatch):
    import apps.thumbnail.jobs as thumbnail_jobs

    user_id, token = _account()
    _quote, created = _quote_and_run(api, token, "image.thumbnail",
                                     {"topic": "x", "count": 1},
                                     "wave1-provider-fail")
    job_id = created.json()["id"]

    # ⛔ Thông điệp lỗi mang một mẩu trông như khoá thật: phép kiểm này canh
    #    việc **không một chữ nào của thượng nguồn** đi ra câu trả lời công
    #    khai. Nguồn lỗi đổi (Gemini → cổng render) nhưng mệnh đề thì không.
    from platform_core.image_gen.dieu_phoi import DieuPhoiError
    from tests.gia_dieu_phoi_anh import tiem as _tiem_dieu_phoi

    _tiem_dieu_phoi(monkeypatch, thumbnail_jobs,
                    no=DieuPhoiError(
                        "quota exhausted for key sk-live-abcdef123456"))
    # `max_attempts` retries are the platform's; run until the job is terminal.
    for _ in range(5):
        if not _run_worker_once():
            break
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            if job.status in ("error", "cancelled"):
                job_finished = True
                break
        finally:
            _close(gen)
        # Retries are scheduled into the future; pull them forward.
        gen, db = _session()
        try:
            job = db.get(Job, job_id)
            from datetime import datetime, timezone

            job.next_run_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            _close(gen)

    detail = api.get(f"{API_V1_PREFIX}/jobs/{job_id}", headers=_auth(token)).json()
    assert detail["status"] == "failed"
    assert detail["error"] == {"message": "The job could not be completed."}
    # No provider text, no key fragment, anywhere in the public answer.
    assert "sk-live" not in json.dumps(detail) and "quota" not in json.dumps(detail)
    # And the customer was made whole.
    assert api.get(f"{API_V1_PREFIX}/credits/balance",
                   headers=_auth(token)).json()["balance"] == 500
    assert api.get(f"{API_V1_PREFIX}/usage",
                   headers=_auth(token)).json()["totals"]["net_charged_credit"] == 0


def test_a_finished_job_queues_its_webhook(api):
    user_id, token = _account()

    gen, db = _session()
    try:
        import uuid as uuid_mod
        from datetime import datetime, timezone

        from platform_core import secretbox
        from platform_core.public_api.tables import WebhookSubscription

        db.add(WebhookSubscription(
            id=str(uuid_mod.uuid4()), user_id=user_id, key_id="",
            url="https://receiver.example.com/hook",
            secret_enc=secretbox.ma_hoa("wave1-webhook-secret"),
            events=[], enabled=True, created_at=datetime.now(timezone.utc)))
        db.commit()
    finally:
        _close(gen)

    _quote, created = _quote_and_run(api, token, "image.thumbnail",
                                     {"topic": "x", "count": 1},
                                     "wave1-webhook-job1")
    assert _run_worker_once() is True

    deliveries = api.get(f"{API_V1_PREFIX}/webhooks/deliveries",
                         headers=_auth(token)).json()["items"]
    assert len(deliveries) == 1
    assert deliveries[0]["event_type"] == "job.succeeded"
    assert deliveries[0]["job_id"] == created.json()["id"]


def test_hidden_inputs_cannot_be_supplied_by_a_caller(api):
    _user_id, token = _account()
    for tool, payload in (
        ("image.thumbnail", {"topic": "x", "model": "gemini-3-pro-image"}),
        ("image.generate", {"prompt": "x", "image_keys": ["a", "b"]}),
    ):
        response = api.post(f"{API_V1_PREFIX}/quotes",
                            json={"tool": tool, "input": payload},
                            headers=_auth(token))
        assert response.status_code == 400, tool
        assert "Unknown input field" in response.json()["detail"]


def test_curated_enum_values_are_the_only_ones_accepted(api):
    _user_id, token = _account()
    good = api.post(f"{API_V1_PREFIX}/quotes",
                    json={"tool": "image.thumbnail",
                          "input": {"topic": "x", "phong_cach": "cinematic"}},
                    headers=_auth(token))
    assert good.status_code == 200

    # An internal-only style id is not part of the public contract.
    bad = api.post(f"{API_V1_PREFIX}/quotes",
                   json={"tool": "image.thumbnail",
                         "input": {"topic": "x", "phong_cach": "khanh"}},
                   headers=_auth(token))
    assert bad.status_code == 400


def test_no_ui_route_became_public(api):
    """The API adds a surface; it must not open the app's own pages."""
    for path in ("/thumbnail", "/taoanh", "/thumbnail/api/tao"):
        response = api.get(path, follow_redirects=False)
        assert response.status_code in (303, 401, 404, 405), path
        assert "text/html" in response.headers.get("content-type", "") or \
            response.status_code in (303, 404, 405)
