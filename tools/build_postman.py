"""Sinh Postman collection + environment TU OpenAPI.

    python tools\\build_postman.py            # ghi ra sdk/postman/
    python tools\\build_postman.py --check    # fail neu da cu

Vi sao sinh chu khong viet tay: mot collection viet tay la ban sao THU HAI cua
hop dong, va ban thu hai luon la ban troi dat. Khi no troi, no khong bao loi —
no chi day nguoi moi vao mot lo goi sai roi de ho tu doan.

OpenAPI o day duoc dung tu chinh `create_app()` chu khong phai goi HTTP mot may
chu dang chay, nen lenh nay chay duoc tren may khong co CSDL.

`--check` nam trong `tools/gate.py`, cung co che voi ho so he thong: sinh ra roi
quen commit thi gate bao ngay, khong doi toi luc ai do tai ve mot file cu.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "sdk" / "postman"
COLLECTION = OUT_DIR / "ltt-public-api.postman_collection.json"
ENVIRONMENT = OUT_DIR / "ltt-public-api.postman_environment.json"

def _utf8_stdout() -> None:
    """Console cua Windows khong mac dinh UTF-8, ma cac thong bao o day co dau.

    Goi TRONG `main()` chu khong o cap module: file nay cung duoc `import` tu
    test, va doi `sys.stdout` luc import se cuop mat co che bat output cua
    pytest — dung nghia den, no lam vo phien chay test.
    """
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                      errors="replace", line_buffering=True)


def _openapi() -> dict:
    """The document this code serves, built in-process.

    Every published tool is switched on for the build: the collection describes
    the API we offer, not the subset one machine happens to have enabled.
    """
    from platform_core.registry import discover
    from server.app import create_app

    names = ",".join(sorted(
        tool.name for item in discover() if not item.error
        for tool in item.manifest.tools if tool.api_exposed))
    work = pathlib.Path(tempfile.mkdtemp(prefix="ltt-postman-"))
    os.environ.setdefault("LTT_DATABASE_URL",
                          f"sqlite:///{(work / 'build.db').as_posix()}")
    app = create_app(env={
        "LTT_ENV": "local-server-test",
        "LTT_SESSION_SECRET": "postman-build-secret",
        "LTT_ADMIN_USERNAME": "", "LTT_ADMIN_PASSWORD_HASH": "",
        "LTT_CONFIG_PATH": str(work / "config.json"),
        "LTT_PUBLIC_API": "1", "LTT_PUBLIC_API_TOOLS": names,
    })
    for route in app.routes:
        sub = getattr(route, "app", None)
        if sub is not None and hasattr(sub, "openapi") and \
                getattr(route, "path", "") == "/api/v1":
            return sub.openapi()
    raise SystemExit("khong tim thay sub-app /api/v1 de lay OpenAPI")


def _example_body(operation: dict) -> str | None:
    """A body a person can actually send, from the schema the spec publishes."""
    content = ((operation.get("requestBody") or {})
               .get("content", {}).get("application/json", {}))
    example = content.get("example")
    if example is not None:
        return json.dumps(example, ensure_ascii=False, indent=2)
    schema = content.get("schema") or {}
    if not schema:
        return None
    # The public routes take free-form objects at this level; a placeholder that
    # names the variables is more use than an invented payload that will not
    # validate.
    return json.dumps({"tool": "{{tool}}", "input": {}}, indent=2)


def build() -> tuple[dict, dict]:
    document = _openapi()
    items = []
    for path, methods in sorted((document.get("paths") or {}).items()):
        for method, operation in sorted(methods.items()):
            if method.upper() not in ("GET", "POST", "DELETE", "PUT", "PATCH"):
                continue
            # Postman variables, not literals: the collection has to work
            # against a local instance and against production without editing.
            url = "{{base_url}}" + path.replace("{", "{{").replace("}", "}}")
            request = {
                "method": method.upper(),
                "header": [{"key": "Authorization",
                            "value": "Bearer {{api_key}}", "type": "text"}],
                "url": {"raw": url,
                        "host": ["{{base_url}}"],
                        "path": [part for part in path.strip("/").split("/")
                                 if part]},
                "description": operation.get("description")
                or operation.get("summary", ""),
            }
            body = _example_body(operation)
            if body is not None:
                request["header"].append({"key": "Content-Type",
                                          "value": "application/json"})
                if method.upper() == "POST" and path.endswith("/jobs"):
                    # The one header that costs money to forget.
                    request["header"].append({
                        "key": "Idempotency-Key",
                        "value": "{{$guid}}",
                        "description": "Bat buoc. Gui lai cung mot key khi thu "
                                       "lai, neu khong ban se bi tinh hai lan."})
                request["body"] = {"mode": "raw", "raw": body,
                                   "options": {"raw": {"language": "json"}}}
            items.append({"name": f"{method.upper()} {path}",
                          "request": request})

    collection = {
        "info": {
            "name": f"LTT Public API {document.get('info', {}).get('version', 'v1')}",
            "description": (
                "Sinh tu OpenAPI bang `python tools/build_postman.py`. "
                "DUNG sua tay: lan sinh sau se ghi de, va mot collection sua "
                "tay la ban sao thu hai cua hop dong."),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/"
                      "collection.json",
        },
        "item": items,
        "variable": [
            {"key": "base_url", "value": "https://app.lttstudios.com/api/v1"},
            {"key": "tool", "value": "image.thumbnail"},
        ],
    }

    environment = {
        "name": "LTT Public API — local",
        "values": [
            {"key": "base_url", "value": "http://127.0.0.1:8100/api/v1",
             "enabled": True},
            # Secret by type so Postman does not print it in shared runs, and
            # empty by default so a committed file never carries a real key.
            {"key": "api_key", "value": "", "type": "secret", "enabled": True},
            {"key": "tool", "value": "image.thumbnail", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }
    return collection, environment


def _dump(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2,
                      sort_keys=True) + "\n"


def main() -> int:
    _utf8_stdout()
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    collection, environment = build()
    files = ((COLLECTION, _dump(collection)), (ENVIRONMENT, _dump(environment)))

    if args.check:
        stale = [path for path, text in files
                 if not path.is_file()
                 or path.read_text(encoding="utf-8") != text]
        if stale:
            for path in stale:
                print(f"STALE: {path.relative_to(ROOT)}")
            print("Run: python tools/build_postman.py")
            return 1
        print(f"Postman khop OpenAPI ({len(collection['item'])} request).")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in files:
        path.write_text(text, encoding="utf-8", newline="")
        print(f"WROTE: {path.relative_to(ROOT)}")
    print(f"{len(collection['item'])} request.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
