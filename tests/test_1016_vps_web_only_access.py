"""VPS V4 D01/D09 — no public API and exact-ID owner rollout."""
from __future__ import annotations

from types import SimpleNamespace


def test_manifest_is_private_and_has_no_toolspec():
    from apps.vps.manifest import MANIFEST
    assert MANIFEST.public is False
    assert MANIFEST.tools == ()
    assert not any(str(route).startswith("/api/v1/vps") for route in MANIFEST.nav)


def test_production_rollout_defaults_off_and_allowlist_uses_id_not_email():
    import apps.vps as vps
    owner = SimpleNamespace(id="canonical-owner-id", role="user",
                            email="akakenly.design@gmail.com")
    impostor = SimpleNamespace(id="different-id", role="user",
                               email="akakenly.design@gmail.com")
    assert vps.rollout_mode({"LTT_ENV": "production"}) == "off"
    env = {"LTT_ENV": "production", "LTT_VPS_ROLLOUT": "allowlist",
           "LTT_VPS_USER_IDS": "canonical-owner-id"}
    assert vps.access_allowed(owner, env) is True
    assert vps.access_allowed(impostor, env) is False


def test_invalid_rollout_value_fails_closed():
    import apps.vps as vps
    admin = SimpleNamespace(id="admin-id", role="admin")
    env = {"LTT_ENV": "production", "LTT_VPS_ROLLOUT": "everyone"}
    assert vps.rollout_mode(env) == "off"
    assert vps.access_allowed(admin, env) is False
