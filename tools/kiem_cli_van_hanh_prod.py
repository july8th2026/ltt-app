"""Run the connector and Claude Desktop against production with a temporary key.

The key is issued only to an existing ``.local`` test account, stays in process
memory, and is revoked in ``finally``.  The report contains status and route
names only; it never contains the token or model response text.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_EMAIL = "canary.api@lttstudios.local"
DEFAULT_URL = "https://app.lttstudios.com"
ROUTES = ("ltt-llm-claude-compat", "ltt-llm-claude-compat-35")
SCOPES = ("tools:read", "jobs:create", "jobs:read", "jobs:cancel",
          "artifacts:read", "credits:read")


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip():
            os.environ[name.strip()] = value


def session_pair():
    from platform_core.db import get_session

    gen = get_session()
    return gen, next(gen)


def close_session(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


def run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    completed = subprocess.run(
        command, cwd=ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=900,
    )
    if completed.returncode:
        tail = ((completed.stdout or "") + (completed.stderr or "")).splitlines()[-12:]
        raise RuntimeError(
            f"{Path(command[0]).name} exited {completed.returncode}: "
            + " | ".join(tail))


def issue_key(email: str) -> tuple[str, str, int]:
    from platform_core import credit, users
    from platform_core.public_api import keys as devkeys

    gen, db = session_pair()
    try:
        user = users.tim_theo_email(db, email)
        if user is None or not user.is_active or user.role != "user":
            raise RuntimeError("The configured active ordinary test account was not found.")
        row, token = devkeys.issue(
            db, user_id=str(user.id), name="H46 Claude Desktop acceptance",
            mode="live", scopes=SCOPES,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=4),
        )
        balance = int(credit.so_du(db, str(user.id)))
        if balance < 20:
            db.rollback()
            raise RuntimeError("The test account does not have enough credit for acceptance.")
        row_id = str(row.id)
        db.commit()
        return row_id, token, balance
    finally:
        close_session(gen)


def revoke_key(row_id: str) -> bool:
    from platform_core.public_api import keys as devkeys
    from platform_core.public_api.tables import DeveloperApiKey

    gen, db = session_pair()
    try:
        row = db.get(DeveloperApiKey, row_id)
        if row is None:
            return False
        changed = devkeys.revoke(db, row)
        db.commit()
        return bool(changed or row.revoked_at is not None)
    finally:
        close_session(gen)


def connector_command(connector: Path, *args: str) -> list[str]:
    if connector.suffix.lower() == ".py":
        return [sys.executable, str(connector), *args]
    return [str(connector), *args]


def sanitized_error(exc: Exception, token: str) -> str:
    message = str(exc)
    return (message.replace(token, "<redacted>") if token else message)[:700]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=DEFAULT_EMAIL)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--env-file", type=Path,
                        default=Path(r"C:\LTTPlatform\secrets\app.env"))
    parser.add_argument("--connector", type=Path, required=True)
    parser.add_argument("--report", type=Path,
                        default=ROOT / "tmp" / "kiem_cli_van_hanh" / "prod.json")
    args = parser.parse_args(argv)

    email = args.email.strip().lower()
    if not email.endswith(".local"):
        parser.error("--email must be a .local test account")
    connector = args.connector.resolve()
    if not connector.is_file():
        parser.error(f"connector not found: {connector}")
    if not args.url.lower().startswith("https://"):
        parser.error("--url must use HTTPS")

    load_env(args.env_file)
    report = {
        "account": email,
        "key": {"created": False, "revoked": False},
        "api": False,
        "connector": False,
        "desktop": [],
        "cleanup": {"connector_go": False, "desktop_restored": False},
        "passed": False,
    }
    row_id = ""
    token = ""
    primary_error: Exception | None = None
    child_env = dict(os.environ)
    try:
        row_id, token, balance = issue_key(email)
        report["key"]["created"] = True
        report["starting_credit"] = balance
        child_env["LTT_API_KEY"] = token

        api_report = args.report.parent / "prod_api.json"
        run(["node", str(ROOT / "tools" / "kiem_cli_van_hanh.mjs"),
             "--api-only", "--wait-capacity", "--url", args.url, "--user", email,
             "--report", str(api_report)], env=child_env)
        report["api"] = bool(json.loads(api_report.read_text(encoding="utf-8"))["passed"])

        run(connector_command(
            connector, "cam", "--goc", args.url, "--model", "ltt-3.8",
            "--muc", "claude-desktop"), env=child_env)
        report["connector"] = True

        desktop_cases = (
            (ROUTES[0], "38", "Calculate 8 * 7. Reply with only the number.", "56"),
            (ROUTES[1], "35", "Calculate 12 * 12. Reply with only the number.", "144"),
        )
        for route, suffix, prompt, expected in desktop_cases:
            desktop_report = args.report.parent / f"prod_desktop_{suffix}.json"
            run([
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(ROOT / "tools" / "kiem_claude_desktop.ps1"),
                "-Model", route, "-Prompt", prompt, "-Expected", expected,
                "-ReportPath", str(desktop_report),
            ])
            item = json.loads(desktop_report.read_text(encoding="utf-8-sig"))
            report["desktop"].append({
                "route": route,
                "models_visible": len(item.get("models_visible", [])),
                "selected": bool(item.get("selected")),
                "sent": bool(item.get("sent")),
                "answered": bool(item.get("answered")),
            })
        report["passed"] = (
            report["api"] and report["connector"]
            and len(report["desktop"]) == 2
            and all(x["models_visible"] == 2 and x["selected"]
                    and x["sent"] and x["answered"] for x in report["desktop"])
        )
    except Exception as exc:  # noqa: BLE001
        primary_error = exc
        report["error"] = sanitized_error(exc, token)
    finally:
        child_env.pop("LTT_API_KEY", None)
        try:
            run(connector_command(connector, "go"), env=child_env)
            report["cleanup"]["connector_go"] = True
        except Exception as exc:  # noqa: BLE001
            report["cleanup"]["connector_error"] = str(exc)[:400]
        if row_id:
            try:
                report["key"]["revoked"] = revoke_key(row_id)
            except Exception as exc:  # noqa: BLE001
                report["key"]["revoke_error"] = str(exc)[:400]
        try:
            run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(ROOT / "tools" / "kiem_claude_desktop.ps1"),
                 "-RestoreOnly"])
            report["cleanup"]["desktop_restored"] = True
        except Exception as exc:  # noqa: BLE001
            report["cleanup"]["desktop_error"] = str(exc)[:400]
        report["passed"] = bool(
            report["passed"] and report["key"]["revoked"]
            and report["cleanup"]["connector_go"]
            and report["cleanup"]["desktop_restored"])
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        token = ""

    if not report["passed"]:
        print(f"FAIL: see sanitized report {args.report}", file=sys.stderr)
        if primary_error:
            print(type(primary_error).__name__, file=sys.stderr)
        return 1
    print(f"PASS: production API and Claude Desktop; report {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
