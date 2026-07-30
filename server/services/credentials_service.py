"""
credentials_service.py — upload and validate the Google credentials file.

Why this exists (docs/_luutru/WEB_PARITY_PLAN.md B-1/B-3): the desktop picked the
credentials file with a native `filedialog`, and `utils/sheet_client.py`
falls back to `InstalledAppFlow.run_local_server()` — a browser on the
machine running the code. Neither works on a remote server, so:

  * the file is uploaded through the web form instead of picked locally;
  * an `installed` / `web` OAuth client is REJECTED with an explanation,
    because accepting it would produce a config that appears valid and
    then hangs waiting for a browser that will never open;
  * only a **service account** is accepted — that path in sheet_client.py
    needs no browser.

The uploaded JSON is a credential: it is written into the secrets
directory with tightened permissions, and its contents are never returned
to the browser. Only the derived `client_email` and `project_id` are shown,
because the operator needs `client_email` to share the Sheet with.
"""
from __future__ import annotations

import json
import os
import stat

from core.runtime_paths import resolve_runtime_paths

CREDENTIALS_FILENAME = "google_service_account.json"


class CredentialsError(RuntimeError):
    """Rejected upload — the message is meant to be shown to the operator."""


def credentials_path(env: dict | None = None) -> str:
    return os.path.join(resolve_runtime_paths(env).secrets_dir, CREDENTIALS_FILENAME)


def describe_stored(path: str | None = None, env: dict | None = None) -> dict:
    """Non-secret facts about the stored credentials, for the UI."""
    target = path or credentials_path(env)
    if not os.path.exists(target):
        return {"exists": False}
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as exc:
        return {"exists": True, "valid": False, "error": str(exc)}
    return {
        "exists": True,
        "valid": data.get("type") == "service_account",
        "type": data.get("type", "?"),
        # client_email is not a secret and the operator MUST see it: the
        # Sheet has to be shared with this address or every read 403s.
        "client_email": data.get("client_email", ""),
        "project_id": data.get("project_id", ""),
        "path": target,
    }


def validate_service_account(raw: bytes) -> dict:
    """Parse and reject anything that cannot authenticate headless."""
    if not raw or not raw.strip():
        return _reject("File rỗng — hãy chọn file JSON của service account.")

    try:
        data = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return _reject("File không phải UTF-8 — đây có phải file JSON không?")
    except json.JSONDecodeError as exc:
        return _reject(f"JSON không hợp lệ: {exc.msg} (dòng {exc.lineno})")

    if not isinstance(data, dict):
        return _reject("Nội dung JSON phải là một object.")

    kind = data.get("type")
    if kind != "service_account":
        if "installed" in data or "web" in data or kind in ("installed", "web"):
            return _reject(
                "Đây là OAuth client (loại 'installed'/'web'), không dùng được "
                "trên máy chủ: nó cần mở trình duyệt để người dùng bấm đồng ý. "
                "Hãy tạo SERVICE ACCOUNT trong Google Cloud Console → "
                "IAM & Admin → Service Accounts → Keys → Add key (JSON), "
                "rồi CHIA SẺ Google Sheet cho email của service account đó."
            )
        return _reject(
            f"Loại credentials không hỗ trợ: '{kind or '(không có)'}'. "
            "Chỉ nhận service account."
        )

    missing = [k for k in ("client_email", "private_key", "token_uri")
               if not str(data.get(k, "")).strip()]
    if missing:
        return _reject(f"File service account thiếu trường: {', '.join(missing)}")

    return {"ok": True, "client_email": data["client_email"],
            "project_id": data.get("project_id", "")}


def _reject(message: str) -> dict:
    return {"ok": False, "error": message}


def store_credentials(raw: bytes, env: dict | None = None) -> tuple[bool, str, dict]:
    """Validate then write. Returns (ok, message, info)."""
    result = validate_service_account(raw)
    if not result.get("ok"):
        return False, result["error"], {}

    target = credentials_path(env)
    folder = os.path.dirname(target)
    os.makedirs(folder, exist_ok=True)

    tmp = target + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, target)

    # Best-effort: strip group/other access. On Windows the meaningful
    # protection is the directory ACL that install.ps1 already applied to
    # the secrets folder; chmod is a no-op there but correct on Linux.
    try:
        os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass

    return True, (
        f"✅ Đã lưu credentials. Service account: {result['client_email']}\n"
        "⚠ BƯỚC BẮT BUỘC: mở Google Sheet của bạn → Share → thêm email trên "
        "với quyền Editor. Không chia sẻ thì bot đọc sheet sẽ báo lỗi 403."
    ), result


def test_sheet_connection(config: dict) -> tuple[bool, str]:
    """Run the real connectivity check (SheetClient.test_connection)."""
    from utils.sheet_client import SheetClient
    try:
        ok, msg = SheetClient(config).test_connection()
    except Exception as exc:
        return False, f"❌ {type(exc).__name__}: {str(exc)[:300]}"
    return ok, ("✅ " if ok else "❌ ") + str(msg)[:400]
