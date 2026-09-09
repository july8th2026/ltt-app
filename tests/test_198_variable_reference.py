"""EXT-06 — the variable reference: every published input, documented once.

The rule this file enforces is narrow and strict: a customer must be able to
find out what a parameter *is* without reading the app's source, and the page
that tells them must be generated from the same contract the server validates
against. Two copies of a schema is one copy that will be wrong.
"""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from platform_core.public_api import keys as devkeys, limits
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.registry import (AppManifest, LoadedApp, RegistryError,
                                    ToolSpec, discover)

PEPPER = "varref-test-pepper-" + "v" * 40


def _live_catalog():
    names = ",".join(sorted({tool.name for item in discover() if not item.error
                             for tool in item.manifest.tools}))
    return build_catalog(load_public_api_config(
        {"LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": names}))


# ── The acceptance criterion, checked against the live repository ────────────

def test_every_published_parameter_has_a_description():
    """100% of exposed operations documented — the whole point of EXT-06."""
    missing = [(tool.name, name)
               for tool in _live_catalog()
               for name, spec in tool.input_schema["properties"].items()
               if not str(spec.get("description") or "").strip()]
    assert not missing, f"undocumented public parameters: {missing}"


def test_documentation_never_describes_a_parameter_the_api_refuses():
    """The opposite failure: prose promising an input that does not exist."""
    for item in discover():
        if item.error:
            continue
        for tool in item.manifest.tools:
            contract = tool.api_contract or {}
            documented = set(contract.get("params") or {})
            hidden = set(contract.get("hidden") or ())
            assert documented <= set(tool.params_schema), tool.name
            assert not (documented & hidden), tool.name


#: Cụm được phép: `openai` ở đây là **tên một định dạng dây**, không phải nhà cung
#: cấp model ta bán lại. `text.chat` cố ý tương thích dây OpenAI — đó là **tính
#: năng bán cho khách**, và giấu nó đi làm tài liệu tệ hơn mà không bảo vệ gì
#: (ta không bán lại OpenAI).
#:
#: ⛔ Nhưng KHÔNG miễn trừ cả chuỗi. Chỉ bóc đúng những cụm dưới đây rồi mới dò —
#:    nên `openai` đứng một mình, hay đứng như một model/alias, VẪN đỏ.
#:    Lý lẽ đầy đủ ở `test_187::test_openai_may_be_NAMED_AS_A_FORMAT_but_never_AS_A_MODEL`.
CUM_DINH_DANG_DUOC_PHEP = ("openai format", "openai-compatible",
                           "openai compatible", "openai image_url")


def _boc_ten_dinh_dang(text: str) -> str:
    for cum in CUM_DINH_DANG_DUOC_PHEP:
        text = text.replace(cum, "<dinh-dang>")
    return text


def test_the_public_docs_say_nothing_about_the_vendor():
    text = " ".join(
        str(spec.get("description", "")) + " " + str(spec.get("examples", ""))
        for tool in _live_catalog()
        for spec in tool.input_schema["properties"].values()).lower()
    text = _boc_ten_dinh_dang(text)
    for vendor in ("gemini", "openai", "byteplus", "anthropic", "realesrgan",
                   "whisper", "prompt library"):
        assert vendor not in text, vendor


# ── The contract refuses documentation that would drift ─────────────────────

def _tool_with(params) -> tuple:
    tool = ToolSpec(
        name="text.documented", job_type="sampledoc.run",
        description="Fixture tool.",
        params_schema={"prompt": {"type": "string", "required": True},
                       "secret_knob": {"type": "string"}},
        returns={"text": "text"}, api_exposed=True,
        api_contract={"scopes": ("jobs:create",), "hidden": ("secret_knob",),
                      "params": params})
    manifest = AppManifest(
        slug="sampledoc", display_name="Sample", route_prefix="/sampledoc",
        job_types=("sampledoc.run",), credit_cost=lambda params: 1,
        lifecycle="released", surface="customer", tools=(tool,))
    return manifest, tool


def test_documenting_an_unknown_parameter_is_refused():
    from platform_core.registry import _validate_api_contract

    manifest, tool = _tool_with({"ghost": {"description": "nope"}})
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, tool)
    assert "ghost" in str(raised.value)


def test_documenting_a_hidden_parameter_is_refused():
    """A caller cannot send it, so describing it is a promise nobody keeps."""
    from platform_core.registry import _validate_api_contract

    manifest, tool = _tool_with({"secret_knob": {"description": "internal"}})
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, tool)
    assert "secret_knob" in str(raised.value)


def test_an_empty_description_is_refused():
    from platform_core.registry import _validate_api_contract

    manifest, tool = _tool_with({"prompt": {"example": "hello"}})
    with pytest.raises(RegistryError):
        _validate_api_contract(manifest, tool)


def test_an_unknown_documentation_key_is_refused():
    from platform_core.registry import _validate_api_contract

    manifest, tool = _tool_with({"prompt": {"description": "ok",
                                            "internal_note": "leak"}})
    with pytest.raises(RegistryError) as raised:
        _validate_api_contract(manifest, tool)
    assert "internal_note" in str(raised.value)


def test_the_description_reaches_the_published_schema():
    manifest, _tool = _tool_with({"prompt": {"description": "What to write.",
                                             "example": "a haiku"}})
    catalog = build_catalog(
        load_public_api_config({"LTT_PUBLIC_API": "1",
                                "LTT_PUBLIC_API_TOOLS": "text.documented"}),
        apps=[LoadedApp(manifest=manifest, router=None, error="")])
    published = catalog[0].input_schema["properties"]["prompt"]
    assert published["description"] == "What to write."
    # JSON Schema 2020-12 spells this `examples`, and it is a list.
    assert published["examples"] == ["a haiku"]
    assert "secret_knob" not in catalog[0].input_schema["properties"]


# ── The reference pages ──────────────────────────────────────────────────────

@pytest.fixture()
def portal(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'varref.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    published = ",".join(tool.name for tool in _live_catalog())
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "varref-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": published,
    })
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        yield client
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


def _sign_in(client) -> None:
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.users import tao_nguoi_dung

    email = f"ref-{uuid.uuid4().hex[:6]}@example.com"
    gen = get_session()
    db = next(gen)
    try:
        user = tao_nguoi_dung(db, email=email, password="a-good-password-12")
        user.is_verified = True
        db.flush()
        credit.cap_tay(db, user.id, 100, by="test")
        db.commit()
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    page = client.get("/login").text
    token = re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)
    client.post("/login", data={"username": email,
                                "password": "a-good-password-12",
                                "csrf_token": token}, follow_redirects=False)


def test_every_published_tool_has_a_reference_page(portal):
    for tool in _live_catalog():
        response = portal.get(f"/developers/tools/{tool.name}")
        assert response.status_code == 200, tool.name


def test_the_page_lists_exactly_the_parameters_the_server_accepts(portal):
    """Docs fields == server schema. Not a subset, not a superset."""
    for tool in _live_catalog():
        page = portal.get(f"/developers/tools/{tool.name}").text
        table = re.search(r"Biến đầu vào.*?</table>", page,
                          re.S)
        assert table, tool.name
        listed = set(re.findall(r"<td><code>([a-z_]+)</code></td>",
                                table.group(0)))
        assert listed == set(tool.input_schema["properties"]), tool.name


def test_the_page_shows_what_a_caller_needs_to_fill_a_parameter_in(portal):
    page = portal.get("/developers/tools/image.thumbnail").text
    # Type, bound, default, enum values and the description all reach the page.
    # `bold_impact` thuộc nhóm `text_style`, đã gỡ cùng chữ-trong-ảnh ở pha
    # 06.3. Lấy một giá trị của nhóm CÒN SỐNG.
    assert "cinematic" in page                        # an enum value
    assert "16:9" in page                             # a default
    # `5 MINUTE FIX` là ví dụ của tham số `title`, đã rời hợp đồng ở pha
    # 06.3. Lấy ví dụ của một tham số CÒN SỐNG.
    assert "How to fix a leaking tap in 5 minutes" in page   # an example
    assert "How many variations to generate" in page  # a description
    assert "tối đa 2000" in page or "2000" in page    # a maxLength bound


def test_the_page_documents_the_call_itself(portal):
    page = portal.get("/developers/tools/image.generate").text
    for fragment in ("/api/v1/quotes", "/api/v1/jobs", "Idempotency-Key",
                     "ASYNC_JOB", "jobs:create", "job.succeeded",
                     "insufficient_credit", "request/"):
        assert fragment in page, fragment


def test_the_example_request_is_built_from_the_tool_s_own_examples(portal):
    import html

    # Unescaped, because the page escapes the quotes in the JSON body — which
    # is exactly what it should do with anything a manifest wrote.
    page = html.unescape(portal.get("/developers/tools/image.generate").text)
    assert "curl -X POST" in page
    assert '"tool": "image.generate"' in page
    assert "a paper boat" in page                     # the declared example


def test_a_data_tool_says_the_result_is_data_not_a_file(portal):
    page = portal.get("/developers/tools/text.prompt_package").text
    assert "không phải tệp" in page or "artifact" not in page.split("Kết quả")[1][:400]


def test_the_reference_page_leaks_no_vendor(portal):
    for tool in _live_catalog():
        page = portal.get(f"/developers/tools/{tool.name}").text.lower()
        for vendor in ("gemini", "byteplus", "realesrgan", "credential"):
            assert vendor not in page, f"{tool.name}: {vendor}"


def test_an_unknown_tool_does_not_get_a_page(portal):
    assert portal.get("/developers/tools/nope.nothing",
                      follow_redirects=False).status_code == 404


def test_a_tool_the_deployment_does_not_publish_has_no_page(tmp_path,
                                                            monkeypatch):
    """The page must not become a directory of unpublished capability."""
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'varref2.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(devkeys.PEPPER_ENV, PEPPER)
    limits.reset()

    import platform_core.db as dbmod
    dbmod.reset_engine()
    import platform_core.models  # noqa: F401
    from platform_core.db import Base, get_engine

    Base.metadata.create_all(get_engine())
    from server.app import create_app

    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "varref-secret-value",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(tmp_path / "config.json"),
        # Only one tool is published on this deployment.
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": "image.thumbnail",
    })
    with TestClient(app, base_url="https://testserver") as client:
        _sign_in(client)
        assert client.get("/developers/tools/image.thumbnail").status_code == 200
        assert client.get("/developers/tools/image.generate",
                          follow_redirects=False).status_code == 404
    from server.api import deps
    deps.set_principal_resolver(None)
    limits.reset()
    dbmod.reset_engine()


# ── Search and filter ────────────────────────────────────────────────────────

def test_the_tool_list_can_be_searched_by_name_description_or_parameter(portal):
    by_name = portal.get("/developers/tools?q=thumbnail").text
    assert "image.thumbnail" in by_name and "image.upscale" not in by_name

    by_param = portal.get("/developers/tools?q=scene_count").text
    assert "story.storyboard" in by_param and "image.thumbnail" not in by_param

    nothing = portal.get("/developers/tools?q=zzzzz").text
    assert "Không công cụ nào khớp" in nothing


def test_the_tool_list_can_be_filtered_by_capability(portal):
    images = portal.get("/developers/tools?capability=image").text
    assert "image.thumbnail" in images
    assert "story.storyboard" not in images


def test_filtering_narrows_the_model_list_with_it(portal):
    """Otherwise a filtered page shows models for tools it is not showing."""
    page = portal.get("/developers/tools?q=upscale").text
    assert "image.upscale" in page
    assert "standard-lite" not in page
