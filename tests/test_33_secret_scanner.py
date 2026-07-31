"""Tests for the source-boundary secret scanner.

Potential credential samples are assembled at runtime so the scanner does not
flag its own test source.
"""

from pathlib import Path

from tools.scan_source_secrets import (
    _is_excluded_file,
    _looks_like_generic_secret,
    _looks_like_placeholder,
    _scan_line,
)


def test_placeholder_detection():
    assert _looks_like_placeholder("[REDACTED]")
    assert _looks_like_placeholder("fake_access_token")
    assert _looks_like_placeholder("legacy-secret")


def test_help_text_is_not_generic_secret():
    assert not _looks_like_generic_secret(
        "Client Secret TikTok. Never share this value with anyone."
    )


def test_short_synthetic_fixture_is_not_generic_secret():
    assert not _looks_like_generic_secret("fake_token_123")


def test_machine_generated_value_is_generic_secret():
    candidate = "".join(("Ab9_", "xY7-", "Qp2!", "Lm8#", "Rt5$"))
    assert _looks_like_generic_secret(candidate)


def test_private_key_rule_reports_metadata():
    marker = "-----BEGIN " + "PRIVATE KEY-----"
    findings = _scan_line(Path("example.txt"), 7, marker)
    assert [(item.line, item.rule) for item in findings] == [
        (7, "private_key_block")
    ]


def test_known_provider_token_rule_reports_without_value():
    candidate = "AIza" + ("A1b2_" * 7)
    findings = _scan_line(Path("example.txt"), 3, candidate)
    assert any(item.rule == "google_api_key" for item in findings)
    assert all(not hasattr(item, "value") for item in findings)


def test_session_secret_hardcode_bi_bat():
    """W1.7: khoá phiên hardcode trong source bị bắt (trước đây lọt vì tên khoá
    không nằm trong danh sách keyword và giá trị là base64url, không phải 32-hex)."""
    line = 'session_secret = "' + ("a1B2c3D4e5F6" * 3) + '"'
    findings = _scan_line(Path("cfg.py"), 5, line)
    assert any(item.rule == "generic_secret_assignment" for item in findings)


def test_token_encryption_key_hardcode_bi_bat():
    """W1.7: khoá mã hoá token hardcode trong source bị bắt."""
    line = 'token_encryption_key = "' + ("Zx9Yw8Vu7Ts6" * 3) + '"'
    findings = _scan_line(Path("cfg.py"), 5, line)
    assert any(item.rule == "generic_secret_assignment" for item in findings)


def test_runtime_config_is_excluded(tmp_path):
    root = tmp_path
    path = root / "data" / "config.backup.before_release.json"
    path.parent.mkdir()
    path.write_text("{}", encoding="utf-8")
    assert _is_excluded_file(root, path)


def test_source_file_is_not_excluded(tmp_path):
    root = tmp_path
    path = root / "core" / "publisher.py"
    path.parent.mkdir()
    path.write_text("# safe", encoding="utf-8")
    assert not _is_excluded_file(root, path)
