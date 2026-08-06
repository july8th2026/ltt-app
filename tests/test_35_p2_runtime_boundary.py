"""
P2 — runtime configuration, data, and security boundary tests (first slice).

Verifies:
  - runtime paths resolve correctly from a non-project working directory
  - environment variables override the desktop-relative path defaults
  - LTT_ENV selects a known profile and rejects unknown values
  - settings loading fails clearly (without exposing secret values) when
    config.json is missing or fails validation
  - config.example.json exists, contains no real credential-shaped values,
    and is excluded from the secret scanner by filename
"""
from __future__ import annotations

import json
import os

import pytest

from core.config_validator import ConfigValidationError
from platform_core.runtime_paths import resolve_runtime_paths
from core.settings import (
    CONFIG_SCHEMA_VERSION,
    Environment,
    MissingConfigError,
    UnknownEnvironmentError,
    load_settings,
    resolve_environment,
)


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── runtime_paths ────────────────────────────────────────────────────────────

def test_default_paths_resolve_from_non_project_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # nothing project-related exists here
    paths = resolve_runtime_paths(env={})
    root = _project_root()
    assert paths.data_dir == os.path.join(root, "data")
    assert paths.config_path == os.path.join(root, "data", "config.json")
    assert paths.secrets_dir == os.path.join(root, "secrets")


def test_env_vars_override_path_defaults(tmp_path):
    fake_env = {
        "LTT_DATA_DIR": str(tmp_path / "d"),
        "LTT_SECRETS_DIR": str(tmp_path / "s"),
        "LTT_LOGS_DIR": str(tmp_path / "l"),
        "LTT_TEMP_VIDEO_DIR": str(tmp_path / "t"),
    }
    paths = resolve_runtime_paths(env=fake_env)
    assert paths.data_dir == str(tmp_path / "d")
    assert paths.secrets_dir == str(tmp_path / "s")
    # config_path derives from data_dir when not explicitly overridden
    assert paths.config_path == os.path.join(str(tmp_path / "d"), "config.json")


def test_explicit_config_path_override_wins_over_data_dir():
    fake_env = {"LTT_DATA_DIR": "/somewhere", "LTT_CONFIG_PATH": "/elsewhere/cfg.json"}
    paths = resolve_runtime_paths(env=fake_env)
    assert paths.config_path == "/elsewhere/cfg.json"


def test_ensure_dirs_creates_data_logs_temp_but_not_secrets(tmp_path):
    fake_env = {
        "LTT_DATA_DIR": str(tmp_path / "d"),
        "LTT_SECRETS_DIR": str(tmp_path / "s"),
        "LTT_LOGS_DIR": str(tmp_path / "l"),
        "LTT_TEMP_VIDEO_DIR": str(tmp_path / "t"),
    }
    paths = resolve_runtime_paths(env=fake_env)
    paths.ensure_dirs()
    assert os.path.isdir(paths.data_dir)
    assert os.path.isdir(paths.logs_dir)
    assert os.path.isdir(paths.temp_video_dir)
    assert not os.path.exists(paths.secrets_dir)  # deployment/ACL concern, not ours


# ─── environment profile ──────────────────────────────────────────────────────

def test_resolve_environment_defaults_to_development():
    assert resolve_environment(env={}) == Environment.DEVELOPMENT


@pytest.mark.parametrize("raw,expected", [
    ("development", Environment.DEVELOPMENT),
    ("local-server-test", Environment.LOCAL_SERVER_TEST),
    ("production", Environment.PRODUCTION),
    ("PRODUCTION", Environment.PRODUCTION),
])
def test_resolve_environment_known_values(raw, expected):
    assert resolve_environment(env={"LTT_ENV": raw}) == expected


def test_resolve_environment_rejects_unknown_value():
    with pytest.raises(UnknownEnvironmentError):
        resolve_environment(env={"LTT_ENV": "staging-typo"})


# ─── settings loading ──────────────────────────────────────────────────────────

def test_load_settings_missing_config_raises_without_leaking_path_contents(tmp_path):
    fake_env = {"LTT_CONFIG_PATH": str(tmp_path / "does_not_exist.json")}
    with pytest.raises(MissingConfigError):
        load_settings(env=fake_env)


def test_load_settings_invalid_config_raises_config_validation_error_no_secret_leak(tmp_path):
    cfg_path = tmp_path / "config.json"
    secret_value = "sk_live_should_never_appear_in_any_error_message_ABC123"
    cfg_path.write_text(json.dumps({
        "job_delay_seconds": -5,           # fails numeric sanity rule
        "meta_app_secret": secret_value,   # must never be echoed back
    }), encoding="utf-8")

    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(env={"LTT_CONFIG_PATH": str(cfg_path)}, strict=False)

    message = str(exc_info.value)
    assert secret_value not in message
    assert "job_delay_seconds" in message  # key names are fine to report


# ─── schema version ────────────────────────────────────────────────────────

def _write_config(tmp_path, extra: dict) -> str:
    cfg_path = tmp_path / "config.json"
    base = {
        "job_delay_seconds": 30, "max_retries": 3,
        "tiktok_poll_interval_s": 5, "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10, "sheet_id": "abc",
    }
    base.update(extra)
    cfg_path.write_text(json.dumps(base), encoding="utf-8")
    return str(cfg_path)


def test_missing_schema_version_is_treated_as_current(tmp_path):
    cfg_path = _write_config(tmp_path, {})  # no _schema_version key — legacy config
    settings = load_settings(env={"LTT_CONFIG_PATH": cfg_path})
    assert settings.config["sheet_id"] == "abc"


def test_schema_version_at_current_is_accepted(tmp_path):
    cfg_path = _write_config(tmp_path, {"_schema_version": CONFIG_SCHEMA_VERSION})
    settings = load_settings(env={"LTT_CONFIG_PATH": cfg_path})
    assert settings.config["_schema_version"] == CONFIG_SCHEMA_VERSION


def test_schema_version_newer_than_supported_is_rejected(tmp_path):
    cfg_path = _write_config(tmp_path, {"_schema_version": CONFIG_SCHEMA_VERSION + 1})
    with pytest.raises(ConfigValidationError) as exc_info:
        load_settings(env={"LTT_CONFIG_PATH": cfg_path})
    assert "schema version" in str(exc_info.value).lower()


def test_schema_version_non_integer_is_rejected(tmp_path):
    cfg_path = _write_config(tmp_path, {"_schema_version": "not-a-number"})
    with pytest.raises(ConfigValidationError):
        load_settings(env={"LTT_CONFIG_PATH": cfg_path})


def test_load_settings_success_returns_environment_paths_and_config(tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({
        "job_delay_seconds": 30,
        "max_retries": 3,
        "tiktok_poll_interval_s": 5,
        "tiktok_upload_timeout_s": 60,
        "tiktok_request_timeout_s": 10,
        "sheet_id": "abc",
    }), encoding="utf-8")

    settings = load_settings(env={
        "LTT_ENV": "local-server-test",
        "LTT_CONFIG_PATH": str(cfg_path),
    })
    assert settings.environment == Environment.LOCAL_SERVER_TEST
    assert settings.config["sheet_id"] == "abc"
    assert settings.paths.config_path == str(cfg_path)


# ─── config.example.json ──────────────────────────────────────────────────────

def test_example_config_exists_and_is_valid_json():
    example_path = os.path.join(_project_root(), "config.example.json")
    assert os.path.exists(example_path), "config.example.json must exist for P2"
    with open(example_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict) and data


def test_example_config_has_no_real_looking_credential_values():
    example_path = os.path.join(_project_root(), "config.example.json")
    with open(example_path, encoding="utf-8") as f:
        data = json.load(f)

    sensitive_keys = [
        k for k in data
        if any(term in k.lower() for term in ("secret", "token", "password"))
    ]
    assert sensitive_keys, "expected at least one sensitive-shaped key to check"
    for key in sensitive_keys:
        value = data[key]
        if isinstance(value, str) and value:
            assert "REPLACE_ME" in value or value == "", (
                f"{key} in config.example.json looks like a real value, not a placeholder"
            )


def test_example_config_has_zero_secret_scanner_findings():
    from pathlib import Path
    from tools.scan_source_secrets import _scan_line

    example_path = Path(_project_root()) / "config.example.json"
    findings = []
    with open(example_path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            findings.extend(_scan_line(example_path, lineno, line))
    assert findings == []
