"""
UI của app thumbnail (H5 → nâng parity Đợt R).

Router KHÔNG tự viết prefix `/thumbnail` — nền tảng gắn từ MANIFEST.route_prefix.

App tự phục vụ file output qua route `/image/{key}` (kiểm sở hữu theo key), thay
vì dựa vào download_token của storage: token giữ trong RAM của TỪNG tiến trình,
mà worker (tạo file) và web (phục vụ) là hai tiến trình khác nhau nên token
không dùng chung được. Kiểm sở hữu: khoá có dạng `thumbnail/{owner_id}/...`,
chỉ chủ mới xem được ảnh của mình.

Các nhóm lựa chọn (style chữ / phong cách / trend / ngôn ngữ) render ĐỘNG từ
`apps/thumbnail/prompts/*/_labels.json` — thêm/bớt lựa chọn = sửa tài nguyên,
không sửa code (di trú trung thành từ BOT GEMINI).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from apps.thumbnail.jobs import _PROMPTS_DIR
from apps.thumbnail.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

router = APIRouter(tags=["thumbnail"])

# Tỉ lệ Gemini hỗ trợ (khớp registry BOT GEMINI). Thứ tự = thứ tự hiện trên UI.
_ASPECTS = ("16:9", "9:16", "1:1", "4:3", "3:4")
_GROUPS = ("text_style", "phong_cach", "kieu_trend", "ngon_ngu")


def _catalog() -> dict:
    """Danh mục lựa chọn cho UI: {group: [(id, nhãn)]} + mặc định — từ _labels.json."""
    from platform_core import prompt_fragments as pf
    return {g: pf.options(_PROMPTS_DIR, g) for g in _GROUPS}


def _defaults() -> dict:
    from platform_core import prompt_fragments as pf
    return {g: pf.default_option(_PROMPTS_DIR, g) for g in _GROUPS}


def _models() -> list:
    """Model ảnh đang bật (từ Provider Registry) — (id, nhãn)."""
    from platform_core import providers
    from platform_core.models import APIKEY_CAT_IMAGE
    return [(m.id, m.label())
            for m in providers.models_for("gemini", category=APIKEY_CAT_IMAGE)
            if m.is_active]


def _render(request: Request, user: str, *, error: str = "", jobs=None,
            status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, "thumbnail.html", {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "aspects": _ASPECTS, "catalog": _catalog(), "defaults": _defaults(),
        "models": _models(), "error": error, "jobs": jobs or [],
    }, status_code=status_code)


def _jobs_cua_toi(request: Request):
    """Các job thumbnail gần đây của người dùng (để hiện gallery kết quả)."""
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.desc()).limit(12)
        ).scalars().all()
        return [{"id": j.id, "status": j.status, "progress": j.progress,
                 "error": j.error,
                 "image_keys": (j.result or {}).get("image_keys", []) if j.result else []}
                for j in rows]
    finally:
        try: next(gen)
        except StopIteration: pass


def _clean_choice(group: str, value: str) -> str:
    """Chỉ nhận id thuộc _labels.json; rỗng/lạ → mặc định (mục đầu)."""
    from platform_core import prompt_fragments as pf
    labels = pf.load_labels(_PROMPTS_DIR, group)
    return value if value in labels else pf.default_option(_PROMPTS_DIR, group)


@router.get("", response_class=HTMLResponse)
def page(request: Request, user: str = Depends(require_login)):
    return _render(request, user, jobs=_jobs_cua_toi(request))


@router.post("/preview", response_class=HTMLResponse)
def preview(
    request: Request,
    topic: str = Form(""),
    title: str = Form(""),
    subtitle: str = Form(""),
    text_style: str = Form(""),
    phong_cach: str = Form(""),
    kieu_trend: str = Form(""),
    ngon_ngu: str = Form(""),
    aspect_ratio: str = Form("16:9"),
    user: str = Depends(require_login),
):
    """Xem trước prompt sẽ gửi (HTMX) — không sinh ảnh, không tốn credit."""
    from apps.thumbnail.jobs import build_prompt
    from markupsafe import escape
    if not topic.strip():
        return HTMLResponse('<span class="dim">Nhập chủ đề rồi bấm “Xem trước”.</span>')
    prompt = build_prompt(
        topic, title=title, subtitle=subtitle,
        text_style=_clean_choice("text_style", text_style),
        phong_cach=_clean_choice("phong_cach", phong_cach),
        kieu_trend=_clean_choice("kieu_trend", kieu_trend),
        ngon_ngu=_clean_choice("ngon_ngu", ngon_ngu),
        aspect_ratio=aspect_ratio if aspect_ratio in _ASPECTS else "16:9")
    return HTMLResponse(f'<pre class="prompt-preview">{escape(prompt)}</pre>')


@router.post("/queue", response_class=HTMLResponse)
def queue(
    request: Request,
    csrf_token: str = Form(...),
    topic: str = Form(""),
    title: str = Form(""),
    subtitle: str = Form(""),
    text_style: str = Form(""),
    phong_cach: str = Form(""),
    kieu_trend: str = Form(""),
    ngon_ngu: str = Form(""),
    model: str = Form(""),
    aspect_ratio: str = Form("16:9"),
    count: int = Form(1),
    user: str = Depends(require_login),
):
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if not topic.strip():
        return _render(request, user, error="Chưa nhập chủ đề thumbnail.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if aspect_ratio not in _ASPECTS:
        aspect_ratio = "16:9"
    count = max(1, min(int(count or 1), 4))
    model_ids = [m[0] for m in _models()]
    if model not in model_ids:
        model = model_ids[0] if model_ids else "gemini-2.5-flash-image"

    u = user_hien_tai(request)
    if u is None:
        return _render(request, user, error="Cần đăng nhập bằng tài khoản người "
                       "dùng (không phải quản trị nội bộ) để chạy job.",
                       jobs=_jobs_cua_toi(request), status_code=400)

    params = {
        "topic": topic.strip(), "title": title.strip(), "subtitle": subtitle.strip(),
        "text_style": _clean_choice("text_style", text_style),
        "phong_cach": _clean_choice("phong_cach", phong_cach),
        "kieu_trend": _clean_choice("kieu_trend", kieu_trend),
        "ngon_ngu": _clean_choice("ngon_ngu", ngon_ngu),
        "model": model, "aspect_ratio": aspect_ratio, "count": count, "owner_id": u.id,
    }

    gen = get_session(); db = next(gen)
    try:
        try:
            job = submit_with_credit(
                db, user_id=u.id, app_slug=MANIFEST.slug,
                job_type="thumbnail.generate", params=params,
                dedupe_key=dedupe_key_for("thumbnail.generate", params),
            )
            db.commit()
            job_id = job.id
        except credit.ThieuCreditError as exc:
            db.rollback()
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)
        except RegistryError as exc:
            db.rollback()
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass

    return RedirectResponse(f"/jobs/{job_id}", status_code=303)


@router.get("/image/{key:path}", response_class=StreamingResponse)
def image(request: Request, key: str, user: str = Depends(require_login)):
    """Phục vụ ảnh output — chỉ chủ sở hữu (key chứa owner_id) mới xem được."""
    from fastapi import HTTPException

    from platform_core.storage import StorageError, get_storage

    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "thumbnail" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    try:
        stream = get_storage().open(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh.")
    return StreamingResponse(stream, media_type="image/png")
