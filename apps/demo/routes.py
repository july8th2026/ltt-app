"""
UI của app demo.

Lưu ý về đường dẫn: router này KHÔNG tự viết prefix `/demo`. Nền tảng gắn
prefix từ `MANIFEST.route_prefix` khi mount. Nhờ vậy đổi prefix chỉ cần sửa
manifest, không phải sửa từng route — và không thể xảy ra chuyện manifest khai
một đường mà route nằm ở đường khác.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from apps.demo import jobs
from apps.demo.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.templating import templates

router = APIRouter(tags=["demo"])


@router.get("", response_class=HTMLResponse)
def demo_page(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse(request, "demo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "result": None, "error": "",
    })


@router.post("", response_class=HTMLResponse)
def demo_run(
    request: Request,
    csrf_token: str = Form(...),
    text: str = Form(""),
    user: str = Depends(require_login),
):
    """Chạy job ngay trong request — CHỈ hợp lệ vì job này mất vài ms.

    App thật KHÔNG được làm thế này: Cloudflare cắt request ở 100 giây (lỗi
    524), nên mọi việc dài phải đi qua hàng đợi job. Ở đây chạy trực tiếp là để
    chứng minh chuỗi web → handler → kết quả trước, rồi mới lắp hàng đợi vào.
    """
    ctx_result = {"error": "", "result": None}

    if not verify_csrf_token(request, csrf_token):
        ctx_result["error"] = "Phiên đã hết hạn — tải lại trang rồi thử lại."
    else:
        params = {"text": text}
        try:
            from platform_core.registry import credit_for
            cost = credit_for("demo.reverse", params)
            ctx_result["result"] = dict(jobs.handle(params), credit_cost=cost)
        except Exception as exc:
            ctx_result["error"] = f"{type(exc).__name__}: {exc}"

    return templates.TemplateResponse(request, "demo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        **ctx_result,
    }, status_code=200 if ctx_result["result"] else 400)
