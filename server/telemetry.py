"""Optional Sentry boundary with deny-by-default PII/secret scrubbing."""
from __future__ import annotations

import re
import os

_DENY = {"authorization", "cookie", "set-cookie", "password", "password_hash",
         "token", "secret", "api_key", "credential", "email", "goal", "prompt",
         "params", "plan", "checkpoint", "request", "body"}
_EMAIL = re.compile(r"(?i)\b[^\s@]+@[^\s@]+\.[^\s@]+\b")


def scrub_event(value):
    if isinstance(value, dict):
        return {str(key): "[Filtered]" if str(key).lower().replace("-", "_") in _DENY
                else scrub_event(item) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_event(item) for item in value]
    if isinstance(value, tuple):
        return tuple(scrub_event(item) for item in value)
    if isinstance(value, str):
        return _EMAIL.sub("[Filtered email]", value)[:2000]
    return value


def before_send(event, _hint):
    return scrub_event(event)


def init_sentry(env: dict | None = None) -> bool:
    """Enable Sentry only when a DSN exists; never enable default PII collection."""
    source = os.environ if env is None else env
    dsn = str(source.get("LTT_SENTRY_DSN", "")).strip()
    if not dsn:
        return False
    import sentry_sdk
    try:
        sample_rate = float(source.get("LTT_SENTRY_TRACES_SAMPLE_RATE", "0.05"))
    except (TypeError, ValueError):
        sample_rate = 0.05
    sentry_sdk.init(dsn=dsn, before_send=before_send, send_default_pii=False,
                    traces_sample_rate=max(0.0, min(1.0, sample_rate)))
    return True
