"""Trang doc va tai lieu cua cong lap trinh vien."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_core import credit
from platform_core.i18n import N_, _ as _t
from platform_core.models import Job
from platform_core.public_api import keys as devkeys, projects, sandbox, usage
from platform_core.public_api.catalog import build_catalog
from platform_core.public_api.config import load_public_api_config
from platform_core.public_api.invocation import api_meta
from platform_core.public_api.scopes import DEFAULT_SCOPES, KNOWN_SCOPES
from platform_core.public_api.tables import WebhookSubscription
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

from server.routes.developer._chung import (  # noqa: F401
    RETRY_EXAMPLE, _goc_url, _log, _overview_counts, _public_api_config, _redirect, _render, _usage_context, require_account, router)


@router.get("", response_class=HTMLResponse)
def developer_overview(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    config = _public_api_config(request)
    # Bước cuối phải là một lệnh CHẠY ĐƯỢC, không phải một liên kết tới tài
    # liệu. `GET /tools` vì nó là lượt gọi rẻ nhất chứng minh được khoá sống:
    # không báo giá, không job, không tốn credit — nếu nó trả 200 thì mọi thứ
    # từ xác thực tới phạm vi đều đúng.
    return _render(request, db, user, "overview", "dev_overview.html",
                   counts=_overview_counts(db, user),
                   lenh_thu=("curl -s " + _goc_url(request) + "/api/v1/tools \
"
                             '  -H "Authorization: Bearer $LTT_API_KEY"'),
                   **_usage_context(db, user, config))


@router.get("/quickstart", response_class=HTMLResponse)
def developer_quickstart(request: Request, tool: str = "",
                         user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """Everything a new integration needs, generated from the live catalog.

    The snippets are not written here and not stored anywhere: they are built
    from the same contract the API validates against, so an example cannot
    describe a call the server would reject.
    """
    from platform_core.public_api import examples

    config = _public_api_config(request)
    catalog = build_catalog(config)
    chosen = None
    for candidate in catalog:
        if candidate.name == str(tool or "") or (not tool and chosen is None):
            chosen = candidate
            if tool:
                break

    snippets = []
    if chosen is not None:
        snippets = [
            ("cURL — " + _t("báo giá"), examples.curl_quote(chosen)),
            ("cURL — " + _t("chạy job"), examples.curl_submit(chosen)),
            ("Python", examples.python_snippet(chosen)),
            ("TypeScript", examples.typescript_snippet(chosen)),
            ("PowerShell", examples.powershell_snippet(chosen)),
            ("HTTP", examples.raw_http_snippet(chosen)),
        ]
    # Cửa chat chỉ hiện khi tool đứng sau nó THẬT SỰ đang mở. Dạy một lời gọi
    # mà tài khoản này chưa gọi được là dạy người ta gặp 403 — fail-closed của
    # Q92 phải nhìn thấy được ở tài liệu, không chỉ ở máy chủ.
    co_chat = any(item.name == "text.chat" for item in catalog)
    return _render(
        request, db, user, "quickstart", "dev_quickstart.html",
        env_vars=examples.ENV_VARS, shells=examples.SHELL_EXPORTS,
        no_code=examples.NO_CODE_RECIPES,
        tool={"name": chosen.name} if chosen is not None else None,
        tool_names=[item.name for item in catalog],
        snippets=snippets,
        chat_snippets=examples.chat_snippets() if co_chat else (),
        chat_khac_biet=examples.CHAT_DIFFERENCES if co_chat else (),
        retry_snippet=RETRY_EXAMPLE)

@router.get("/pricing", response_class=HTMLResponse)
def developer_pricing(request: Request, user=Depends(require_account),
                      db: Session = Depends(get_db)):
    """What a call would cost, priced by the code that really charges.

    The number here comes from `invocation.price` — the same function the quote
    route calls — bounded by the same published regime. A simulator with its own
    arithmetic would answer a question nobody asked: what matters is what the
    customer will actually be billed, and that stays true only while one piece
    of code produces both numbers.

    Nothing is charged and no quote token is minted, so a simulation cannot be
    presented at `POST /jobs`.
    """
    from platform_core.public_api import examples, pricing

    config = _public_api_config(request)
    catalog = build_catalog(config)
    wanted = str(request.query_params.get("tool") or "")
    tool = next((item for item in catalog if item.name == wanted),
                catalog[0] if catalog else None)

    raw_input = str(request.query_params.get("input") or "").strip()
    payload, error, result = {}, "", None
    if tool is not None:
        if raw_input:
            import json

            try:
                payload = json.loads(raw_input)
                if not isinstance(payload, dict):
                    raise ValueError(_t("input phải là một object JSON"))
            except (ValueError, TypeError) as exc:
                error = str(exc)
                payload = {}
        else:
            payload = examples.example_input(tool)

        if not error:
            try:
                result = pricing.simulate(db, tool=tool, params=payload)
            except Exception as exc:  # noqa: BLE001 - shown to this customer
                # Surfaced rather than swallowed: a price that cannot be
                # computed is exactly what somebody came here to find out.
                _log.warning("mo phong gia that bai cho %s: %s: %s",
                             tool.name, type(exc).__name__, exc)
                error = _t("Không tính được giá cho đầu vào này.")

    import json as _json

    return _render(request, db, user, "pricing", "dev_pricing.html",
                   tools=[item.name for item in catalog],
                   chosen=tool.name if tool is not None else "",
                   input_json=_json.dumps(payload, ensure_ascii=False,
                                          indent=2),
                   result=result, error=error)


@router.get("/playground", response_class=HTMLResponse)
def developer_playground(request: Request, tool: str = "",
                         user=Depends(require_account),
                         db: Session = Depends(get_db)):
    """A request builder that calls the public API the way a customer does.

    The page holds no credential and the server mints none for it: the browser
    sends the developer's own key straight to `/api/v1`. A portal endpoint that
    borrowed the session instead would be a second road to the chargeable path,
    and the platform has exactly one on purpose — a policy bug on the second one
    costs real money.
    """
    import json

    config = _public_api_config(request)
    catalog = build_catalog(config)
    published = [tool.to_public_dict() for tool in catalog]
    # Trang không điền hộ khoá được (xem docstring), nhưng nó BIẾT khách có
    # khoá nào — nửa công khai của khoá không phải bí mật. Nói ra để một người
    # chưa có khoá không mắc kẹt trước một ô nhập họ không điền được nổi.
    now = datetime.now(timezone.utc)
    khoa = [k for k in devkeys.list_for_user(db, user.id) if k.is_usable(now=now)]
    ten = {item["name"] for item in published}
    return _render(request, db, user, "playground", "dev_playground.html",
                   # Chi nhan ten CO THAT trong danh muc. Doi chieu voi danh
                   # muc chu khong loc ky tu: mot ten la thi bo qua, va o chon
                   # ve mac dinh — khong dung nao de mot chuoi tu URL di thang
                   # vao trang.
                   tool_chon=tool if tool in ten else "",
                   khoa_dung_duoc=[
                       {"key_id": k.key_id, "name": k.name,
                        "mode": str(getattr(k, "mode", "live") or "live")}
                       for k in khoa],
                   catalog=[{"name": item["name"],
                             "execution_mode": item["execution_mode"]}
                            for item in published],
                   # Escaped for embedding in a <script> block: a schema that
                   # happened to contain "</script>" would otherwise end the
                   # element and become markup.
                   catalog_json=json.dumps(published, ensure_ascii=False)
                   .replace("<", "\\u003c"))


@router.get("/cli", response_class=HTMLResponse)
def developer_cli(request: Request, user=Depends(require_account),
                  db: Session = Depends(get_db)):
    """Cấu hình sẵn cho Codex, Claude Code và Claude Desktop.

    ⭐ VÌ SAO TRANG NÀY TỒN TẠI. Thứ chặn một lập trình viên gần như không bao
       giờ là giao thức — nó là **điền đúng một file cấu hình**. Hai base URL
       lệch nhau bốn ký tự, một tên model phải khớp chính xác, và một biến môi
       trường phải đặt ở cấp người dùng chứ không phải trong một cửa sổ terminal.
       Mỗi thứ đó hỏng lặng lẽ với một triệu chứng vô ích.

    ⛔ Trang này **không** chèn khoá thật vào cấu hình. Khoá chỉ hiện một lần lúc
       tạo và máy chủ không giữ lại được — cùng luật mà mọi ví dụ khác trong
       `examples.py` đã theo: *"No snippet ever contains a key."*
    """
    from platform_core.public_api import examples
    from server.routes.tai_lieu_api import bo_cai_moi_nhat

    goc = str(request.base_url).rstrip("/")
    return _render(
        request, db, user, "cli", "dev_cli.html",
        base_url=goc,
        codex_config=examples.codex_config(goc),
        codex_profile=examples.codex_profile(),
        claude_env=examples.claude_code_env(goc),
        claude_settings=examples.claude_code_settings(goc),
        desktop=examples.claude_desktop_steps(goc),
        vscode_claude=examples.vscode_claude_settings(goc),
        vscode_codex=examples.vscode_codex_config(goc),
        vscode_bay=examples.VSCODE_BAY,
        desktop_reg=examples.claude_desktop_registry(goc),
        be_mat=examples.be_mat_cam(goc),
        # Bo cai .exe: cung nguon `bo_cai_moi_nhat()` ma trang cong khai dung,
        # nen so phien ban va bam SHA-256 khong the lech giua hai trang.
        bo_cai=bo_cai_moi_nhat(),
        bay=examples.CLI_BAY,
        model=examples.CLI_MODEL,
        model_desktop=examples.DESKTOP_MODEL,
        env_key=examples.ENV_API_KEY)


@router.get("/docs", response_class=HTMLResponse)
def developer_docs(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    # The origin as the caller's browser sees it, so the copyable curl example
    # works on a laptop, behind the tunnel and in a test alike.
    return _render(request, db, user, "docs", "dev_docs.html",
                   base_url=str(request.base_url).rstrip("/"))


@router.get("/openapi/download")
def developer_openapi_download(request: Request,
                               user=Depends(require_account)):
    """The spec as a file, with the API version in its name.

    The same document `/api/v1/openapi.json` serves — fetched from the running
    app rather than rebuilt, because two ways of producing a spec is one way
    too many. What this adds is a *name*: a generated client is only debuggable
    six months later if you can tell which spec produced it.
    """
    import json

    from starlette.responses import Response

    from platform_core.public_api import protocol
    from server.api.inventory import API_V1_PREFIX

    document = None
    for route in request.app.routes:
        sub = getattr(route, "app", None)
        if sub is not None and getattr(route, "path", "") == "/api/v1" \
                and hasattr(sub, "openapi"):
            document = sub.openapi()
            break
    if document is None:
        raise _redirect("/developers/docs")

    # FastAPI adds `servers` when it *serves* the document, from the mount
    # path — so a copy taken straight from `sub.openapi()` would arrive without
    # one, and a client generated from it would have no base URL to call. Caught
    # by comparing the two byte for byte, which is the only way this kind of
    # difference gets noticed.
    document.setdefault("servers", [{"url": API_V1_PREFIX}])

    name = f"ltt-public-api-{protocol.API_VERSION}-openapi.json"
    return Response(
        json.dumps(document, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}"',
                 "Cache-Control": "no-store"})
