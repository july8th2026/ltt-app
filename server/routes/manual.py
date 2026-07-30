"""
Manual publish pages — web port of gui/operation_tab.py.

Flow differs from the desktop in two forced ways (see
server/services/manual_publish.py): the video is uploaded rather than picked
from a local path, and publishing runs as a background job that the page
polls, because an HTTP request cannot outlast a multi-minute upload.

The TikTok consent step is kept on the critical path. It is a TikTok audit
requirement, so it is a separate confirm screen that must be submitted
before any publish job is created — the equivalent of the desktop's modal
`publish_confirm_dialog`.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse

from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.services import ui_constants as UI
from server.services.accounts import list_facebook_accounts, list_tiktok_accounts
from server.services.manual_publish import (
    registry,
    safe_upload_name,
    start_facebook_publish,
    start_tiktok_publish,
    temp_video_dir,
    validate_facebook,
    validate_tiktok,
)
from server.templating import templates

router = APIRouter(tags=["manual"])

CHUNK = 1024 * 1024


def _config(request: Request) -> dict:
    cs = getattr(request.app.state, "core_settings", None)
    return dict(cs.config) if cs else {}


def _page_options() -> list:
    """Flat "Page ← Account" options, same label shape as the desktop."""
    listing = list_facebook_accounts()
    out = []
    for acc in listing.accounts:
        for p in acc.pages:
            if p.selected:
                out.append({"label": f"{p.name}  ← {acc.name}",
                            "page": p.name, "account": acc.name})
    return out


def _tiktok_accounts() -> list:
    return [{"label": a.name, "account_id": a.account_id}
            for a in list_tiktok_accounts().accounts]


def _fb_context(request: Request, user: str, **extra) -> dict:
    ctx = {
        "user": user, "nav": "manual_fb", "platform": "facebook",
        "title": "Manual FB",
        "page_options": _page_options(),
        "privacy_options": UI.PRIVACY_OPTIONS,
        "privacy_default": UI.PRIVACY_DEFAULT_LABEL,
        "title_limit": UI.FB_TITLE_LIMIT,
        "desc_limit": UI.FB_DESC_LIMIT,
        "accept": ",".join(UI.VIDEO_EXTS_FB),
        "image_accept": ",".join(UI.IMAGE_EXTS),
        "colors": UI.COLORS,
        "csrf_token": issue_csrf_token(request),
        "job": registry().latest("facebook"),
        "error": "", "notice": "",
    }
    ctx.update(extra)
    return ctx


def _tt_context(request: Request, user: str, **extra) -> dict:
    cfg = _config(request)
    approved = str(cfg.get("tiktok_audit_approved", "")).lower() in ("true", "1", "yes")
    # Desktop filters out the public option until the app is audited.
    options = [o for o in UI.TIKTOK_POST_OPTIONS
               if approved or "Công khai" not in o[0]]
    ctx = {
        "user": user, "nav": "manual_tiktok", "platform": "tiktok",
        "title": "Manual TikTok",
        "accounts": _tiktok_accounts(),
        "post_options": options,
        "audit_approved": approved,
        "audit_hint": "" if approved else UI.TIKTOK_AUDIT_HINT,
        "caption_limit": UI.TT_CAPTION_LIMIT,
        "accept": ",".join(UI.VIDEO_EXTS_TT),
        "colors": UI.COLORS,
        "csrf_token": issue_csrf_token(request),
        "job": registry().latest("tiktok"),
        "error": "", "notice": "",
        "pending": None,
    }
    ctx.update(extra)
    return ctx


async def _save_upload(upload: UploadFile, config: dict) -> str:
    """Stream to disk — never read a multi-GB upload into memory."""
    folder = temp_video_dir(config)
    target = os.path.join(folder, safe_upload_name(upload.filename or ""))
    with open(target, "wb") as out:
        while True:
            chunk = await upload.read(CHUNK)
            if not chunk:
                break
            out.write(chunk)
    return target


# ── Facebook ──────────────────────────────────────────────────────────────────

@router.get("/manual/facebook", response_class=HTMLResponse)
def manual_fb_page(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse(request, "manual_fb.html",
                                      _fb_context(request, user))


@router.post("/manual/facebook", response_class=HTMLResponse)
async def manual_fb_publish(
    request: Request,
    csrf_token: str = Form(...),
    page: str = Form(""),
    title: str = Form(""),
    description: str = Form(""),
    privacy: str = Form(UI.PRIVACY_DEFAULT_LABEL),
    schedule: str = Form(""),
    video: UploadFile = File(...),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "manual_fb.html",
            _fb_context(request, user, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)

    config = _config(request)
    selected = next((o for o in _page_options() if o["label"] == page), None)
    if selected is None:
        return templates.TemplateResponse(
            request, "manual_fb.html",
            _fb_context(request, user,
                        error="Vui lòng chọn Page đăng (vào /facebook để tick chọn page)"),
            status_code=400)

    video_path = await _save_upload(video, config)

    err = validate_facebook(
        account=selected["account"], page=selected["page"],
        video_path=video_path, title=title, description=description,
        thumbnail="", schedule=schedule,
    )
    if err:
        # A rejected upload must not be left behind on disk.
        try:
            os.remove(video_path)
        except OSError:
            pass
        return templates.TemplateResponse(
            request, "manual_fb.html",
            _fb_context(request, user, error=err), status_code=400)

    task = {
        "video_path": video_path,
        "page": selected["page"],
        "page_id": "",
        "title": title.strip(),
        "description": description.strip(),
        "thumbnail": "",
        "privacy": dict(UI.PRIVACY_OPTIONS).get(privacy, UI.PRIVACY_FALLBACK_ENUM),
        "schedule": schedule.strip(),
    }
    job = start_facebook_publish(config, task)
    return templates.TemplateResponse(
        request, "manual_fb.html",
        _fb_context(request, user, job=job,
                    notice=f"Đã bắt đầu đăng (job {job.id})."))


# ── TikTok: upload → consent → publish ────────────────────────────────────────

@router.get("/manual/tiktok", response_class=HTMLResponse)
def manual_tt_page(request: Request, user: str = Depends(require_login)):
    return templates.TemplateResponse(request, "manual_tiktok.html",
                                      _tt_context(request, user))


@router.post("/manual/tiktok/prepare", response_class=HTMLResponse)
async def manual_tt_prepare(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(""),
    post_label: str = Form(UI.TIKTOK_POST_DEFAULT_LABEL),
    title: str = Form(""),
    description: str = Form(""),
    video: UploadFile = File(...),
    user: str = Depends(require_login),
):
    """Validate + fetch creator info, then show the consent screen.

    Nothing is published here. The desktop showed a modal at this exact
    point and TikTok's audit depends on it, so the web keeps it as a
    mandatory second step rather than a checkbox on the first form.
    """
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)

    config = _config(request)
    accounts = _tiktok_accounts()
    account = next((a for a in accounts if a["account_id"] == account_id), None)
    if account is None:
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user,
                        error="Chưa có tài khoản TikTok.\n"
                              "Vào /tiktok để kết nối tài khoản trước."),
            status_code=400)

    video_path = await _save_upload(video, config)
    err = validate_tiktok(account=account["label"], video_path=video_path,
                          title=title, description=description)
    if err:
        try:
            os.remove(video_path)
        except OSError:
            pass
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user, error=err), status_code=400)

    info = _creator_info(config, account_id)
    privacy_options = [(p, UI.TIKTOK_PRIVACY_LABELS.get(p, p))
                       for p in info["privacy_level_options"]]

    return templates.TemplateResponse(request, "manual_tiktok.html", _tt_context(
        request, user,
        pending={
            "account_id": account_id,
            "account_label": account["label"],
            "post_label": post_label,
            "title": title, "description": description,
            "video_path": video_path,
            "video_name": os.path.basename(video_path),
            "info": info,
            "privacy_options": privacy_options,
        },
    ))


def _creator_info(config: dict, open_id: str) -> dict:
    """Query TikTok for what this creator is allowed to do.

    Failure degrades to SELF_ONLY only — same conservative fallback the
    desktop used. Unlike the desktop, the failure is surfaced to the
    operator instead of only being logged.
    """
    fallback = {
        "privacy_level_options": ["SELF_ONLY"],
        "comment_disabled": False, "duet_disabled": False,
        "stitch_disabled": False, "creator_username": "",
        "fetch_error": "",
    }
    try:
        from core.tiktok.creator_info import query_creator_info
        from core.tiktok.token_store import get_default_store
        account = get_default_store().get_account(open_id)
        if not account or not account.access_token:
            fallback["fetch_error"] = "Không đọc được access token của tài khoản."
            return fallback
        info = query_creator_info(account.access_token)
        return {
            "privacy_level_options": list(info.privacy_level_options) or ["SELF_ONLY"],
            "comment_disabled": bool(info.comment_disabled),
            "duet_disabled": bool(info.duet_disabled),
            "stitch_disabled": bool(info.stitch_disabled),
            "creator_username": getattr(info, "creator_username", "") or "",
            "fetch_error": "",
        }
    except Exception as exc:
        fallback["fetch_error"] = (
            f"Không lấy được creator_info từ TikTok ({type(exc).__name__}). "
            "Chỉ cho phép SELF_ONLY để an toàn."
        )
        return fallback


@router.post("/manual/tiktok/publish", response_class=HTMLResponse)
def manual_tt_publish(
    request: Request,
    csrf_token: str = Form(...),
    account_id: str = Form(...),
    post_label: str = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    video_path: str = Form(...),
    privacy_level: str = Form(...),
    allow_comment: str = Form(""),
    allow_duet: str = Form(""),
    allow_stitch: str = Form(""),
    is_ai: str = Form(""),
    branded: str = Form(""),
    acknowledge: str = Form(""),
    user: str = Depends(require_login),
):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user, error="Phiên đã hết hạn, tải lại trang."),
            status_code=400)

    # The consent checkbox gates publishing in the desktop dialog; it gates
    # it here too, server-side, so a tampered form cannot skip it.
    if acknowledge != "1":
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user,
                        error="Bạn phải tick xác nhận nội dung tuân thủ điều khoản "
                              "TikTok trước khi đăng."),
            status_code=400)

    config = _config(request)
    info = _creator_info(config, account_id)

    # Privacy must be one TikTok says this creator may use. Re-checked here
    # rather than trusting the submitted value.
    if privacy_level not in info["privacy_level_options"]:
        return templates.TemplateResponse(
            request, "manual_tiktok.html",
            _tt_context(request, user,
                        error=f"Mức riêng tư '{privacy_level}' không được phép cho "
                              "tài khoản này theo TikTok."),
            status_code=400)

    post_type, forced_privacy = next(
        ((pt, pl) for label, pt, pl in UI.TIKTOK_POST_OPTIONS if label == post_label),
        ("tiktok_draft", ""),
    )

    from datetime import datetime, timezone
    task = {
        "video_path": video_path,
        "account": account_id,
        "title": title.strip(),
        "description": description.strip(),
        "post_type": post_type,
        "privacy_level": forced_privacy or privacy_level,
        # An interaction the creator disabled stays disabled — the desktop
        # hard-locked those toggles and so does this.
        "disable_comment": info["comment_disabled"] or allow_comment != "1",
        "disable_duet": info["duet_disabled"] or allow_duet != "1",
        "disable_stitch": info["stitch_disabled"] or allow_stitch != "1",
        "is_ai_generated": is_ai == "1",
        "brand_content_toggle": branded == "1",
        "user_confirmed_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
    }
    job = start_tiktok_publish(config, task)
    return templates.TemplateResponse(
        request, "manual_tiktok.html",
        _tt_context(request, user, job=job,
                    notice=f"Đã bắt đầu đăng TikTok (job {job.id})."))


@router.get("/api/manual/{platform}/status")
def manual_status(platform: str, request: Request,
                  user: str = Depends(require_login)):
    job = registry().latest("tiktok" if platform == "tiktok" else "facebook")
    return job.to_dict() if job else {"state": "idle", "log": []}
