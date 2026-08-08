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
from server.deps import require_operator
from server.templating import templates

router = APIRouter(tags=["demo"])


@router.get("", response_class=HTMLResponse)
def demo_page(request: Request, user: str = Depends(require_operator)):
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
    user: str = Depends(require_operator),
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


@router.post("/queue", response_class=HTMLResponse)
def demo_queue(
    request: Request,
    csrf_token: str = Form(...),
    text: str = Form(""),
    user: str = Depends(require_operator),
):
    """Chạy demo QUA HÀNG ĐỢI — đây mới là khuôn cho app thật (Q1/H4).

    Khác `demo_run` (chạy ngay trong request): tạo job + giữ chỗ credit trong
    một giao dịch, rồi chuyển người dùng sang trang tiến độ; worker chạy job
    nền. Đây là chuỗi mà mọi app tính phí phải đi qua.
    """
    from fastapi.responses import RedirectResponse

    from platform_core import credit
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError
    from server.deps import user_hien_tai

    if not verify_csrf_token(request, csrf_token):
        return _loi(request, user, "Phiên đã hết hạn — tải lại trang rồi thử lại.")

    u = user_hien_tai(request)
    if u is None:
        return _loi(request, user, "Chạy qua hàng đợi cần đăng nhập bằng tài "
                    "khoản người dùng (không phải tài khoản quản trị nội bộ).")

    from platform_core.db import get_session
    gen = get_session(); db = next(gen)
    try:
        try:
            params = {"text": text}
            job = submit_with_credit(
                db, user_id=u.id, app_slug=MANIFEST.slug,
                job_type="demo.reverse", params=params,
                dedupe_key=dedupe_key_for("demo.reverse", params),
            )
            db.commit()
        except credit.ThieuCreditError as exc:
            db.rollback()
            return _loi(request, user, str(exc))
        except RegistryError as exc:
            db.rollback()
            return _loi(request, user, str(exc))
        job_id = job.id
    finally:
        try: next(gen)
        except StopIteration: pass

    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


def _loi(request: Request, user: str, msg: str) -> HTMLResponse:
    return templates.TemplateResponse(request, "demo.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "result": None, "error": msg,
    }, status_code=400)
