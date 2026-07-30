"""
settings.py — environment profile + config loading boundary (P2).

Earlier builds loaded `data/config.json` inline with a bare
`json.load(open(...))` (see gui/main_window.py, gui/settings_tab.py). That
still works and is left untouched here. This module adds the boundary a
headless/server process needs on top of it: which environment profile is
this process running as, where do its runtime files actually live
(core.runtime_paths), and did the config it loaded pass startup
validation — all without ever logging or returning a secret value, since
`core.config_validator.validate_config()` only ever reports rule/key names.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum

from core.config_validator import ConfigValidationError, validate_config
from core.runtime_paths import RuntimePaths, resolve_runtime_paths

# Bumped whenever config.json's expected shape changes in a way an older
# build cannot safely interpret. Configs written before this field existed
# have no "_schema_version" key at all — those are treated as the current
# version rather than rejected, so existing desktop installs are unaffected.
CONFIG_SCHEMA_VERSION = 1


class Environment(Enum):
    DEVELOPMENT       = "development"
    LOCAL_SERVER_TEST = "local-server-test"
    PRODUCTION        = "production"


class UnknownEnvironmentError(ValueError):
    """LTT_ENV was set to a value that isn't a defined profile."""


class MissingConfigError(RuntimeError):
    """config.json was not found at the resolved path."""


def resolve_environment(env: dict | None = None) -> Environment:
    e = os.environ if env is None else env
    raw = (e.get("LTT_ENV") or "development").strip().lower()
    for member in Environment:
        if member.value == raw:
            return member
    raise UnknownEnvironmentError(
        f"Unknown LTT_ENV '{raw}'. Must be one of: "
        f"{', '.join(m.value for m in Environment)}"
    )


@dataclass(frozen=True)
class AppSettings:
    environment: Environment
    paths:       RuntimePaths
    config:      dict


def load_settings(*, env: dict | None = None, strict: bool = False) -> AppSettings:
    """Resolve environment + paths, load config.json, and validate it.

    Raises MissingConfigError if the config file doesn't exist, or
    core.config_validator.ConfigValidationError if it fails validation.
    Neither error path includes a secret value — only rule/key names.
    """
    environment = resolve_environment(env)
    paths = resolve_runtime_paths(env)

    if not os.path.exists(paths.config_path):
        raise MissingConfigError(
            f"Config not found at '{paths.config_path}'. Copy "
            "config.example.json to that path and fill in real values, "
            "or set LTT_CONFIG_PATH to an existing config file."
        )

    # utf-8-sig, not utf-8: an operator who edits this file in Notepad on
    # Windows gets a UTF-8 BOM, and json.load() raises on it. That failure
    # surfaced as an opaque 503 from /health/ready with the service running
    # normally — expensive to diagnose, trivial to tolerate.
    with open(paths.config_path, "r", encoding="utf-8-sig") as f:
        config = json.load(f)

    _check_schema_version(config)
    validate_config(config, strict=strict)

    return AppSettings(environment=environment, paths=paths, config=config)


def _check_schema_version(config: dict) -> None:
    """Reject a config written by a *newer* build than this one supports —
    protects against silently misinterpreting a shape change after a
    rollback. Never raises for a config with no declared version (legacy)
    or one at/below the currently supported version."""
    declared = config.get("_schema_version", CONFIG_SCHEMA_VERSION)
    try:
        declared = int(declared)
    except (TypeError, ValueError):
        raise ConfigValidationError(
            [f"'_schema_version' must be an integer (got '{declared}')."]
        )
    if declared > CONFIG_SCHEMA_VERSION:
        raise ConfigValidationError([
            f"config.json declares schema version {declared}, but this "
            f"build only supports up to {CONFIG_SCHEMA_VERSION}. Upgrade "
            "the application before using this config, or restore a "
            "matching release."
        ])
