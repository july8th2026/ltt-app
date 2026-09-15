"""Behavior checks for the operational connector/Desktop acceptance harness."""
from __future__ import annotations

import json
import importlib.util
import os
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests" / "fixtures" / "cli_compat_server.py"
HARNESS = ROOT / "tools" / "kiem_cli_van_hanh.mjs"
DESKTOP = ROOT / "tools" / "kiem_claude_desktop.ps1"
PROD = ROOT / "tools" / "kiem_cli_van_hanh_prod.py"


def _server(tmp_path: pathlib.Path, mode: str = "ok"):
    process = subprocess.Popen(
        [sys.executable, str(SERVER), str(tmp_path / "wire.jsonl"), mode],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    assert process.stdout is not None
    port = int(process.stdout.readline().strip())
    return process, port


def test_api_harness_runs_both_models_stream_and_two_turn_tools(tmp_path):
    process, port = _server(tmp_path)
    report_path = tmp_path / "report.json"
    env = {**os.environ, "LTT_API_KEY": "ltt_sk_mock_only_not_a_secret"}
    try:
        run = subprocess.run(
            ["node", str(HARNESS), "--api-only", "--url",
             f"http://127.0.0.1:{port}", "--report", str(report_path)],
            cwd=ROOT, env=env, text=True, capture_output=True, timeout=30,
        )
    finally:
        process.terminate()
        process.wait(timeout=10)

    assert run.returncode == 0, run.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert [(item["label"], item["status"]) for item in report["api"]] == [
        ("tools", 200), ("credits", 200),
        ("messages:ltt-llm-claude-compat", 200),
        ("responses:ltt-llm-claude-compat", 200),
        ("tool-call:ltt-llm-claude-compat", 200),
        ("tool-result:ltt-llm-claude-compat", 200),
        ("messages:ltt-llm-claude-compat-35", 200),
        ("responses:ltt-llm-claude-compat-35", 200),
        ("tool-call:ltt-llm-claude-compat-35", 200),
        ("tool-result:ltt-llm-claude-compat-35", 200),
    ]
    assert "ltt_sk_" not in report_path.read_text(encoding="utf-8")


def test_desktop_driver_is_ascii_and_harness_never_accepts_password():
    assert all(byte < 128 for byte in DESKTOP.read_bytes())
    source = HARNESS.read_text(encoding="utf-8")
    assert "--pass" not in source
    assert "LTT_SMOKE_PASS" not in source
    assert "revokeKey(page, keyId)" in source
    assert "runConnector('go')" in source
    assert "Stop-ClaudeFully" in DESKTOP.read_text(encoding="ascii")


def test_production_orchestrator_revokes_and_cleans_after_api_failure(
        tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("kiem_prod", PROD)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)

    connector = tmp_path / "cam.exe"
    connector.write_bytes(b"test")
    report_path = tmp_path / "prod.json"
    token = "ltt_sk_should_never_reach_the_report"
    revoked = []
    commands = []
    monkeypatch.setattr(module, "load_env", lambda _path: None)
    monkeypatch.setattr(module, "issue_key", lambda _email: ("row-1", token, 100))
    monkeypatch.setattr(
        module, "revoke_key", lambda row_id: revoked.append(row_id) or True)

    def fake_run(command, **_kwargs):
        commands.append(command)
        if any("kiem_cli_van_hanh.mjs" in str(part) for part in command):
            raise RuntimeError(f"API failed while using {token}")

    monkeypatch.setattr(module, "run", fake_run)
    result = module.main([
        "--connector", str(connector), "--env-file", str(tmp_path / "env"),
        "--report", str(report_path),
    ])

    report_text = report_path.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert result == 1
    assert revoked == ["row-1"]
    assert report["key"]["revoked"] is True
    assert report["cleanup"] == {"connector_go": True, "desktop_restored": True}
    assert token not in report_text
    assert any(command[-1] == "go" for command in commands if command[0] == str(connector))
    assert any("-RestoreOnly" in command for command in commands)
