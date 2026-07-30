"""
config_validator.py — Startup configuration validation.

Validates required keys and types in the app config dict.
Raises ConfigValidationError with a clear, actionable message if
anything critical is missing or misconfigured.

Usage (called once at app startup, before any API calls):
    from core.config_validator import validate_config, ConfigValidationError
    try:
        validate_config(config)
    except ConfigValidationError as exc:
        # Show error dialog, then exit
        ...
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ConfigValidationError(Exception):
    """Raised when the config is missing required keys or has invalid values."""

    def __init__(self, errors: list[str], warnings: list[str] = None):
        self.errors   = errors
        self.warnings = warnings or []
        lines = ["Configuration errors found:"]
        for e in errors:
            lines.append(f"  ❌  {e}")
        if warnings:
            lines.append("Configuration warnings:")
            for w in warnings:
                lines.append(f"  ⚠️  {w}")
        super().__init__("\n".join(lines))


# ─── Validation rules ────────────────────────────────────────────────────────

@dataclass
class _Rule:
    key:      str
    label:    str
    required: bool = False          # True → error if missing/empty
    warn_if_empty: bool = False     # True → warning if missing/empty
    min_len:  int  = 0              # minimum string length when set
    valid_values: list = field(default_factory=list)   # allowed enum values


# Rules that apply when Facebook is in use
_FACEBOOK_RULES: list[_Rule] = [
    _Rule("meta_app_id",     "Meta App ID",     warn_if_empty=True),
    _Rule("meta_app_secret", "Meta App Secret", warn_if_empty=True),
    _Rule("graph_api_version", "Graph API Version", warn_if_empty=True),
]

# Rules that apply when TikTok is in use
_TIKTOK_RULES: list[_Rule] = [
    _Rule("tiktok_client_key",    "TikTok Client Key",    warn_if_empty=True),
    _Rule("tiktok_client_secret", "TikTok Client Secret", warn_if_empty=True),
    _Rule("tiktok_privacy_level", "TikTok Privacy Level",
          valid_values=["SELF_ONLY", "FOLLOWER_OF_CREATOR",
                        "MUTUAL_FRIEND_FRIENDS", "PUBLIC_TO_EVERYONE"]),
    _Rule("tiktok_publish_mode", "TikTok Publish Mode",
          valid_values=["draft_upload", "direct_private", "direct_public"]),
]

# Rules that always apply
# NOTE: sheet_id/sheet_tab dropped from the auto-warn list because the
# multi-sheet upgrade made them legacy/fallback only — see custom check
# in validate_config() that warns if BOTH sheets[] and sheet_id are empty.
_GLOBAL_RULES: list[_Rule] = [
    _Rule("google_credentials_path", "Google Credentials Path", warn_if_empty=True),
    _Rule("timezone",    "Timezone",         warn_if_empty=True),
    _Rule("temp_video_dir", "Temp Video Dir", warn_if_empty=True),
]

# Security-critical checks
_SECURITY_RULES: list[tuple[str, str]] = [
    # (key, warning message)
    ("tiktok_audit_approved",
     "'tiktok_audit_approved' is set to True — ensure TikTok has officially "
     "approved your app before enabling direct public posting."),
]


# ─── Public API ──────────────────────────────────────────────────────────────

def validate_config(config: dict, *, strict: bool = False) -> list[str]:
    """
    Validate *config* dict. Returns list of warning strings.

    Raises ConfigValidationError if any error-level rule is violated.
    If strict=True, warnings are also treated as errors.

    Always safe to call at startup — will not modify the config.
    """
    errors:   list[str] = []
    warnings: list[str] = []

    # Global rules
    for rule in _GLOBAL_RULES:
        _check_rule(rule, config, errors, warnings)

    # Facebook rules (warn only — user may be TikTok-only)
    for rule in _FACEBOOK_RULES:
        _check_rule(rule, config, errors, warnings)

    # TikTok rules
    for rule in _TIKTOK_RULES:
        _check_rule(rule, config, errors, warnings)

    # Multi-sheet: warn only if BOTH new sheets[] and legacy sheet_id are empty
    sheets = config.get("sheets", []) or []
    has_sheets = bool(sheets) and any(
        str(s.get("id", "")).strip() for s in sheets
    )
    has_legacy = bool(str(config.get("sheet_id", "")).strip())
    if not has_sheets and not has_legacy:
        warnings.append(
            "Chưa có sheet nào được cấu hình ('sheets' trống và 'sheet_id' "
            "cũng trống). Vào Cài đặt → Google Sheets để thêm."
        )

    # Security advisory checks
    for key, msg in _SECURITY_RULES:
        val = config.get(key)
        if str(val).lower() in ("true", "1", "yes"):
            warnings.append(msg)

    # Numeric sanity
    _check_positive_int(config, "job_delay_seconds",    10, errors)
    _check_positive_int(config, "max_retries",           0, errors)
    _check_positive_int(config, "tiktok_poll_interval_s", 1, errors)
    _check_positive_int(config, "tiktok_upload_timeout_s", 30, errors)
    _check_positive_int(config, "tiktok_request_timeout_s", 5, errors)

    if strict:
        errors.extend(warnings)
        warnings = []

    if errors:
        raise ConfigValidationError(errors, warnings)

    return warnings   # caller may log these


def get_tiktok_publish_mode(config: dict) -> str:
    """
    Return the normalised TikTok publish mode from config.
    Falls back to "draft_upload" (safest default).
    """
    raw = str(config.get("tiktok_publish_mode", "draft_upload")).lower().strip()
    valid = {"draft_upload", "direct_private", "direct_public"}
    return raw if raw in valid else "draft_upload"


def is_tiktok_audit_approved(config: dict) -> bool:
    """Return True only if explicitly set to true/1/yes in config."""
    return str(config.get("tiktok_audit_approved", "false")).lower() in ("true", "1", "yes")


def is_direct_post_enabled(config: dict) -> bool:
    """Return True only if explicitly enabled in config."""
    return str(config.get("tiktok_enable_direct_post", "false")).lower() in ("true", "1", "yes")


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _check_rule(rule: _Rule, config: dict, errors: list, warnings: list):
    val = config.get(rule.key, "")
    val_str = str(val).strip() if val is not None else ""
    empty = not val_str

    if rule.required and empty:
        errors.append(f"'{rule.key}' ({rule.label}) is required but not set.")
        return

    if rule.warn_if_empty and empty:
        warnings.append(f"'{rule.key}' ({rule.label}) is not configured.")

    if rule.valid_values and val_str and val_str not in rule.valid_values:
        errors.append(
            f"'{rule.key}' ({rule.label}) has invalid value '{val_str}'. "
            f"Must be one of: {', '.join(rule.valid_values)}"
        )

    if rule.min_len and val_str and len(val_str) < rule.min_len:
        errors.append(
            f"'{rule.key}' ({rule.label}) is too short "
            f"(got {len(val_str)}, min {rule.min_len})."
        )


def _check_positive_int(config: dict, key: str, minimum: int, errors: list):
    val = config.get(key)
    if val is None:
        return   # missing → use default elsewhere
    try:
        n = int(val)
        if n < minimum:
            errors.append(
                f"'{key}' must be ≥ {minimum} (got {n})."
            )
    except (TypeError, ValueError):
        errors.append(f"'{key}' must be an integer (got '{val}').")
