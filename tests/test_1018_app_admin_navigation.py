"""The app admin contribution is additive and scoped to the serving request."""
from dataclasses import replace
from types import SimpleNamespace

import pytest


def _app(**changes):
    from platform_core.registry import AppManifest, LoadedApp, NavEntry
    manifest = AppManifest(
        slug="testapp", display_name="Test", route_prefix="/testapp",
        admin_nav=(NavEntry("Test admin", "/testapp/admin", nav_key="home"),
                   NavEntry("Profiles", "/testapp/admin/profiles", nav_key="profiles")))
    return LoadedApp(replace(manifest, **changes))


def test_app_admin_nav_is_empty_by_default():
    from platform_core.registry import AppManifest
    assert AppManifest(slug="old", display_name="Old", route_prefix="/old").admin_nav == ()


@pytest.mark.parametrize("path", ["https://outside.invalid", "/admin/", "/other/admin", "/testapp/admin/../x"])
def test_admin_nav_cannot_escape_app_owned_admin_paths(path):
    from platform_core.registry import NavEntry, RegistryError, _validate
    manifest = _app(admin_nav=(NavEntry("Bad", path, nav_key="bad"),)).manifest
    with pytest.raises(RegistryError, match="admin_nav"):
        _validate(manifest, set(), set())


def test_request_scoped_nav_keeps_old_tree_and_adds_exact_active_parent():
    from server.routes.admin import _chung
    baseline = _chung.dieu_huong("tong_quan")
    nav = _chung.dieu_huong("app_testapp_profiles", apps=[_app()])
    assert len(nav["thanh_ben"]) == len(baseline["thanh_ben"]) + 1
    assert [m["nhan"] for m in nav["thanh_ben"] if m["active"]] == ["Test admin"]
    assert nav["banh_mi"] == [{"href": "/testapp/admin", "nhan": "Test admin"}]
    assert [m["nhan"] for m in nav["muc_con"] if m["active"]] == ["Profiles"]
    assert _chung.dieu_huong("tong_quan") == baseline


def test_disabled_or_failed_app_has_no_admin_contribution():
    from server.routes.admin import _chung
    failed = _app()
    failed.error = "load failed"
    baseline = _chung.dieu_huong("tong_quan")
    assert _chung.dieu_huong("tong_quan", apps=[_app(enabled=False), failed]) == baseline


@pytest.mark.asyncio
async def test_admin_nav_context_is_reset_even_when_request_raises():
    from server.routes.admin import _chung
    baseline = _chung.dieu_huong("tong_quan")
    seen = []

    async def endpoint(scope, receive, send):
        seen.append(_chung.dieu_huong("app_testapp_profiles"))
        raise RuntimeError("request failed")

    middleware = _chung.AdminNavigationContextMiddleware(endpoint)
    scope = {"type": "http", "app": SimpleNamespace(
        state=SimpleNamespace(loaded_apps=[_app()]))}
    with pytest.raises(RuntimeError, match="request failed"):
        await middleware(scope, None, None)
    assert seen[0]["thanh_ben"][-1]["active"] is True
    assert _chung.dieu_huong("tong_quan") == baseline
