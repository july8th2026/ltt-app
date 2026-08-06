"""
settings_service.py — read/validate/save data/config.json from the web UI.

Safety properties this enforces, all learned from real incidents in this
project:

  * Secret values are never sent to the browser. An empty submission for a
    secret field means "keep the stored value", so a round-trip through the
    form cannot silently blank an App Secret.
  * The file is written atomically (utils.atomic_io), so a crash mid-save
    cannot truncate a working config.
  * A timestamped backup is kept before every write, because a bad column
    mapping silently stops the bot (docs/_luutru/AUDIT_REPORT.md B3).
  * The new config is validated *before* it replaces the old one. Invalid
    input is rejected with per-field errors and nothing is written.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

from core.config_defaults import DEFAULTS
from core.config_validator import ConfigValidationError, validate_config
from platform_core.runtime_paths import resolve_runtime_paths
from server.services.settings_schema import BOOL, JSONLIST, NUMBER, GROUPS
from utils.atomic_io import atomic_write_json

SECRET_PLACEHOLDER = ""      # secrets render as empty; empty means "unchanged"
MAX_BACKUPS = 20


def config_path(env: dict | None = None) -> str:
    return resolve_runtime_paths(env).config_path


def load_config(env: dict | None = None) -> dict:
    path = config_path(env)
    if not os.path.exists(path):
        return dict(DEFAULTS)
    # utf-8-sig, not utf-8: an operator who edits this file in Notepad on
    # Windows gets a UTF-8 BOM, and json.load() raises on it. That failure
    # surfaced as an opaque 503 from /health/ready with the service running
    # normally — expensive to diagnose, trivial to tolerate.
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def view_model(config: dict) -> dict:
    """Values shaped for the template. Secrets are replaced by a flag, never
    by their value — so a token cannot leak into rendered HTML."""
    out: dict = {}
    for group in GROUPS:
        for f in group.fields:
            raw = config.get(f.key, f.default)
            if f.secret:
                out[f.key] = {"value": SECRET_PLACEHOLDER, "is_set": bool(str(raw or "").strip())}
            elif f.kind == JSONLIST:
                out[f.key] = {"value": json.dumps(raw if raw is not None else [],
                                                  ensure_ascii=False, indent=2)}
            elif f.kind == BOOL:
                out[f.key] = {"value": _as_bool(raw)}
            else:
                out[f.key] = {"value": "" if raw is None else str(raw)}
    return out


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes", "on")


def apply_form(config: dict, form: dict) -> tuple[dict, dict]:
    """Merge submitted form values into *config*.

    Returns (new_config, field_errors). A non-empty field_errors means
    nothing should be saved.
    """
    new = dict(config)
    errors: dict = {}

    for group in GROUPS:
        for f in group.fields:
            submitted = form.get(f.key)

            if f.kind == BOOL:
                # Unchecked checkboxes are simply absent from the form body.
                new[f.key] = f.key in form
                continue

            if submitted is None:
                continue                      # field not on this submission

            raw = str(submitted).strip()

            if f.secret:
                if raw == "":
                    continue                  # keep existing secret
                new[f.key] = raw
                continue

            if f.kind == NUMBER:
                if raw == "":
                    new[f.key] = 0
                    continue
                try:
                    new[f.key] = int(raw) if "." not in raw else float(raw)
                except ValueError:
                    errors[f.key] = f"'{raw}' không phải số hợp lệ"
                continue

            if f.kind == JSONLIST:
                if raw == "":
                    new[f.key] = []
                    continue
                try:
                    new[f.key] = json.loads(raw)
                except json.JSONDecodeError as exc:
                    errors[f.key] = f"JSON không hợp lệ: {exc.msg} (dòng {exc.lineno})"
                continue

            new[f.key] = raw

    return new, errors


def _backup(path: str) -> str | None:
    """Timestamped copy of the current config, pruned to MAX_BACKUPS."""
    if not os.path.exists(path):
        return None
    folder = os.path.dirname(path) or "."
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(folder, f"config.backup_{stamp}.json")
    shutil.copy2(path, dest)

    backups = sorted(
        (f for f in os.listdir(folder) if f.startswith("config.backup_")),
        reverse=True,
    )
    for stale in backups[MAX_BACKUPS:]:
        try:
            os.remove(os.path.join(folder, stale))
        except OSError:
            pass
    return dest


def save_config(new_config: dict, env: dict | None = None) -> tuple[bool, list, list]:
    """Validate then atomically write. Returns (saved, errors, warnings).

    On validation failure nothing is written — the running config survives.
    """
    try:
        warnings = validate_config(new_config)
    except ConfigValidationError as exc:
        return False, list(exc.errors), list(exc.warnings)

    path = config_path(env)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    _backup(path)
    atomic_write_json(path, new_config)
    return True, [], list(warnings)


def list_backups(env: dict | None = None) -> list:
    folder = os.path.dirname(config_path(env)) or "."
    if not os.path.isdir(folder):
        return []
    return sorted(
        (f for f in os.listdir(folder) if f.startswith("config.backup_")),
        reverse=True,
    )
