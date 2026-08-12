"""Q88: app APIs always receive JSON errors, while browser pages stay HTML."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.testclient import TestClient


def test_nested_app_api_error_is_json_but_page_error_is_html(monkeypatch, tmp_path):
    monkeypatch.setenv("LTT_DATABASE_URL", f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    monkeypatch.setenv("LTT_DATA_DIR", str(tmp_path / "data"))
    import platform_core.db as dbmod
    dbmod.reset_engine()
    from server.app import create_app
    app = create_app(env={"LTT_ENV":"local-server-test",
        "LTT_SESSION_SECRET":"api-error-contract", "LTT_ADMIN_USERNAME":"",
        "LTT_ADMIN_PASSWORD_HASH":"", "LTT_CONFIG_PATH":str(tmp_path / "config.json")})
    router = APIRouter()

    @router.get("/sample/api/fail")
    def api_fail():
        raise HTTPException(status_code=422, detail="actionable")

    @router.get("/sample/page/fail")
    def page_fail():
        raise HTTPException(status_code=422, detail="page")

    app.include_router(router)
    try:
        with TestClient(app, base_url="https://testserver") as client:
            api = client.get("/sample/api/fail")
            page = client.get("/sample/page/fail")
        assert api.status_code == 422 and api.json()["detail"] == "actionable"
        assert api.headers["content-type"].startswith("application/json")
        assert api.headers["cache-control"] == "no-store"
        assert page.status_code == 422 and page.headers["content-type"].startswith("text/html")
    finally:
        # create_app uses the process-wide DB engine. Leaving this engine bound
        # to pytest's soon-to-be-removed tmp_path poisons later page tests in a
        # full-suite run even though this file passes in isolation.
        dbmod.reset_engine()


def test_json_error_detail_drops_request_input_and_exception_context():
    from server.app import _json_error_detail
    detail = [{"type":"value_error", "msg":"invalid", "input":{"secret":"x"},
               "ctx":{"error":ValueError("boom")}, "loc":("body", "field")}]
    assert _json_error_detail(detail) == [{"type":"value_error", "msg":"invalid",
                                           "loc":["body", "field"]}]
