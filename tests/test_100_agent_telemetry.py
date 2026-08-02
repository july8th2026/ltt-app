import sys
from types import SimpleNamespace

from server.telemetry import before_send, init_sentry


def test_sentry_scrubber_removes_pii_secret_prompt_and_body():
    event = {"request": {"headers": {"Authorization": "Bearer secret"}},
             "extra": {"email": "person@example.com", "goal": "private goal",
                       "safe": "contact person@example.com using correlation abc"}}
    cleaned = before_send(event, {})
    assert cleaned["request"] == "[Filtered]"
    assert cleaned["extra"]["email"] == "[Filtered]"
    assert cleaned["extra"]["goal"] == "[Filtered]"
    assert "person@example.com" not in cleaned["extra"]["safe"]
    assert "correlation abc" in cleaned["extra"]["safe"]


def test_sentry_is_off_without_dsn_and_wired_with_pii_disabled(monkeypatch):
    assert init_sentry({}) is False
    seen = {}
    monkeypatch.setitem(sys.modules, "sentry_sdk", SimpleNamespace(
        init=lambda **kwargs: seen.update(kwargs)))
    assert init_sentry({"LTT_SENTRY_DSN": "https://public.invalid/1",
                        "LTT_SENTRY_TRACES_SAMPLE_RATE": "2"}) is True
    assert seen["send_default_pii"] is False
    assert seen["before_send"] is before_send
    assert seen["traces_sample_rate"] == 1.0
