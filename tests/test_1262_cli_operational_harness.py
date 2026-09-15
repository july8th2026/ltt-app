"""Behavior checks for the operational connector/Desktop acceptance harness."""
from __future__ import annotations

import argparse
import json
import importlib.util
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
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
    wire = [json.loads(line) for line in
            (tmp_path / "wire.jsonl").read_text(encoding="utf-8").splitlines()]
    by_model = {}
    for item in wire:
        by_model.setdefault(item["model"], set()).add(item["reasoning_effort"])
    assert by_model["ltt-llm-claude-compat"] == {"xhigh"}
    assert by_model["ltt-llm-claude-compat-35"] == {None}


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


def check_generated_config_in_codex_app_server(
        binary: str, tmp_path: pathlib.Path, model: str) -> None:
    """Run one generated model config through a real Codex app-server.

    This is an explicit operational probe rather than an environment-dependent
    pytest test.  A missing binary is therefore a failed command, never a
    silently skipped test in the repository gate.
    """
    executable = pathlib.Path(binary)
    if not executable.is_file():
        raise FileNotFoundError(f"Codex binary is absent: {executable}")

    from platform_core.public_api import examples

    home = tmp_path / "codex-home"
    home.mkdir(parents=True)
    catalog = home / "ltt_model_catalog.json"
    catalog.write_text(examples.codex_catalog(), encoding="utf-8")
    config = examples.codex_desktop_config("http://127.0.0.1:9", model)
    config = config.replace(examples.TEP_CATALOG_CODEX, catalog.as_posix())
    (home / "config.toml").write_text(config, encoding="utf-8")

    process = subprocess.Popen(
        [str(executable), "app-server", "--strict-config", "--stdio"],
        cwd=ROOT,
        env={**os.environ, "CODEX_HOME": str(home),
             "LTT_API_KEY": "mock_key_for_local_config_parse_only"},
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8",
    )
    assert process.stdin is not None and process.stdout is not None
    messages: queue.Queue[dict] = queue.Queue()

    def read_stdout():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                continue

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    requests = [
        {"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "ltt-config-audit", "version": "1"},
            "capabilities": {"experimentalApi": True}}},
        {"method": "initialized", "params": {}},
        {"id": 2, "method": "config/read", "params": {"cwd": str(ROOT)}},
        {"id": 3, "method": "model/list", "params": {"includeHidden": True}},
    ]
    for request in requests:
        process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()

    responses = {}
    deadline = time.monotonic() + 15
    try:
        while time.monotonic() < deadline and not {1, 2, 3} <= responses.keys():
            try:
                message = messages.get(timeout=0.25)
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            if message.get("id") in (1, 2, 3):
                responses[message["id"]] = message
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    stderr = process.stderr.read() if process.stderr else ""
    assert {1, 2, 3} <= responses.keys(), stderr
    assert all("error" not in responses[item] for item in (1, 2, 3)), responses
    config_read = responses[2]["result"]["config"]
    assert config_read["model"] == model
    assert config_read["model_provider"] == "ltt"
    listed = responses[3]["result"]["data"]
    assert [item["model"] for item in listed] == ["ltt-3.8", "ltt-3.5"]
    assert [item["displayName"] for item in listed] == [
        "LTT 3.8 (Strong)", "LTT 3.5 (Fast)"]


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check generated LTT config against a real Codex app-server")
    parser.add_argument("--codex-binary", required=True)
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="ltt-codex-app-server-") as raw:
        base = pathlib.Path(raw)
        for model in ("ltt-3.8", "ltt-3.5"):
            check_generated_config_in_codex_app_server(
                args.codex_binary, base / model, model)
    version = subprocess.run(
        [args.codex_binary, "--version"], text=True, capture_output=True,
        timeout=10, check=True).stdout.strip()
    print(json.dumps({"passed": True, "binary": version,
                      "models": ["ltt-3.8", "ltt-3.5"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
