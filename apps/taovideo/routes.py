"""
UI app `seedance` (A2, Pha 1: text→video). Router KHÔNG tự viết prefix.

Video output serve theo HTTP RANGE (`/v/{key}`) — player tải từng đoạn nhỏ nên
KHÔNG dính trần 100MB của Cloudflare (không cần R2 cho clip ngắn).
"""
from __future__ import annotations

from platform_core.i18n import _ as _t
from platform_core import phat_media
import base64 as _base64
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from apps.taovideo import cost, models, quotes
from apps.taovideo.manifest import MANIFEST
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates
from platform_core.jobs import loi_cho_khach

router = APIRouter(tags=["seedance"])


def _render(request: Request, user: str, *, error: str = "", jobs=None, status_code: int = 200, **extra):
    reg_ui = {k: {"resolutions": v["resolutions"], "durations": v["durations"],
                  "aspects": v["aspects"],
                  "supports_seed": bool(v.get("supports_seed")),
                  "prompt_controls": v.get("prompt_controls", [])}
              for k, v in models.MODELS.items() if v.get("active")}
    if isinstance(jobs, dict):
        # Các nhánh validation/credit dùng cùng payload workspace với GET. Trước
        # đây truyền nguyên dict vào template khiến grid lặp qua key thay vì job.
        extra.setdefault("job_counts", jobs.get("counts", {}))
        extra.setdefault("prompt_history", jobs.get("history", []))
        extra.setdefault("saved_assets", jobs.get("assets", []))
        jobs = jobs.get("items", [])
    context = {
        "user": user, "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "models": models.options(), "reg_ui": reg_ui,
        "default_model": models.DEFAULT_MODEL, "error": error, "jobs": jobs or [],
    }
    context.update(extra)
    return templates.TemplateResponse(request, "taovideo.html", context, status_code=status_code)


def _jobs_cua_toi(request: Request, status: str = "all", sort: str = "newest",
                  model_filter: str = "", aspect_filter: str = ""):
    u = user_hien_tai(request)
    if u is None:
        return []
    from platform_core.db import get_session
    from platform_core.models import JOB_DONE, JOB_ERROR, JOB_QUEUED, JOB_RUNNING, Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(
            select(Job).where(Job.user_id == u.id, Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.asc() if sort == "oldest" else Job.created_at.desc()).limit(60)
        ).scalars().all()
        if model_filter in models.MODELS:
            rows = [j for j in rows if (j.params or {}).get("model") == model_filter]
        else:
            model_filter = ""
        known_aspects = {aspect for item in models.MODELS.values()
                         for aspect in item.get("aspects", [])}
        if aspect_filter in known_aspects:
            rows = [j for j in rows if (j.params or {}).get("aspect_ratio") == aspect_filter]
        else:
            aspect_filter = ""
        counts = {"all": len(rows), "running": 0, "done": 0, "error": 0, "cancelled": 0}
        for j in rows:
            if j.status in (JOB_QUEUED, JOB_RUNNING): counts["running"] += 1
            elif j.status == JOB_DONE: counts["done"] += 1
            elif j.status == JOB_ERROR: counts["error"] += 1
            elif j.status == "cancelled": counts["cancelled"] += 1
        filtered = rows if status == "all" else [j for j in rows if (
            j.status in (JOB_QUEUED, JOB_RUNNING) if status == "running" else j.status == status)]
        history=[]; seen=set(); assets=[]; seen_keys=set()
        for j in rows:
            prompt=str((j.params or {}).get("prompt", "")).strip()
            if prompt and prompt not in seen: history.append(prompt); seen.add(prompt)
            for ref in ((j.params or {}).get("refs") or []):
                key = str(ref.get("storage_key") or "")
                if (not key.startswith(f"taovideo/{u.id}/refs/") or
                        key in seen_keys or len(assets) >= 40):
                    continue
                seen_keys.add(key)
                assets.append({
                    "storage_key": key, "kind": ref.get("kind", "image"),
                    "role": ref.get("role", "reference_image"),
                    "handle": ref.get("handle", ""),
                    "name": ref.get("name") or f"Tài sản {len(assets) + 1}",
                    "size": int(ref.get("size") or 0),
                })
        return {"items": [{"id": j.id, "status": j.status, "progress": j.progress,
                 "progress_msg": j.progress_msg, "error": loi_cho_khach(j),
                 "video_key": (j.result or {}).get("video_key") if j.result else None,
                 "model": (j.result or {}).get("model") or (j.params or {}).get("model"),
                 "model_label": (models.get((j.result or {}).get("model") or
                                  (j.params or {}).get("model")) or {}).get("label", "Seedance"),
                 "prompt": str((j.params or {}).get("prompt", ""))[:180],
                 "raw_prompt": str((j.params or {}).get("raw_prompt") or
                                   (j.params or {}).get("prompt", ""))[:10000],
                 "resolution": (j.params or {}).get("resolution", ""),
                 "duration": (j.params or {}).get("duration", ""),
                 "aspect_ratio": (j.params or {}).get("aspect_ratio", ""),
                 "created_at": j.created_at.strftime("%d/%m/%Y %H:%M") if j.created_at else ""}
                for j in filtered], "counts": counts, "history": history[:10],
                "assets": assets, "model_filter": model_filter,
                "aspect_filter": aspect_filter}
    finally:
        try: next(gen)
        except StopIteration: pass


def _clean(model, resolution, duration, aspect):
    m = models.get(model) or models.get(models.DEFAULT_MODEL)
    mid = model if models.get(model) else models.DEFAULT_MODEL
    if resolution not in m["resolutions"]:
        resolution = m["resolutions"][0]
    if aspect not in m["aspects"]:
        aspect = m["aspects"][0]
    try:
        duration = int(duration)
    except (TypeError, ValueError):
        duration = 5
    if duration not in m["durations"]:
        duration = 5 if 5 in m["durations"] else m["durations"][0]
    return mid, resolution, duration, aspect


_CAMERA = {
    "static": "locked-off static camera",
    "dolly_in": "slow cinematic dolly-in",
    "tracking": "smooth subject tracking shot",
    "orbit": "controlled orbit shot around the subject",
    "aerial": "wide aerial establishing shot",
    "handheld": "subtle handheld documentary movement",
}
_MOTION = {
    "subtle": "subtle natural motion",
    "dynamic": "dynamic energetic motion",
    "cinematic": "cinematic paced motion with smooth acceleration",
}
_VISUAL_STYLE = {
    "realistic": "photorealistic, natural detail",
    "cinematic": "cinematic lighting and filmic color grading",
    "anime": "polished anime visual style",
    "product": "premium commercial product photography",
}


def _compose_prompt(prompt: str, camera: str = "", motion: str = "",
                    visual_style: str = "") -> str:
    """Prompt guidance tất định; không giả đây là tham số camera native."""
    base = str(prompt or "").strip()
    guidance = [mapping[value] for mapping, value in (
        (_CAMERA, camera), (_MOTION, motion), (_VISUAL_STYLE, visual_style)
    ) if value in mapping]
    return (base + ("\n\nDirection: " + "; ".join(guidance) + "." if guidance else ""))[:10000]


def _clean_seed(value: str) -> int | None:
    if str(value or "").strip() == "":
        return None
    try:
        seed = int(value)
    except (TypeError, ValueError):
        raise ValueError(_t('Seed phải là số nguyên từ 0 đến 2147483647.'))
    if not 0 <= seed <= 2_147_483_647:
        raise ValueError(_t('Seed phải là số nguyên từ 0 đến 2147483647.'))
    return seed


@router.get("", response_class=HTMLResponse)
def page(request: Request, status: str = "all", sort: str = "newest",
         model: str = "", aspect: str = "", tu_studio: str = "",
         user: str = Depends(require_login)):
    status = status if status in {"all", "running", "done", "error", "cancelled"} else "all"
    sort = sort if sort in {"newest", "oldest"} else "newest"
    data = _jobs_cua_toi(request, status, sort, model, aspect)
    return _render(request, user, jobs=data["items"], job_counts=data["counts"],
                   prompt_history=data["history"], saved_assets=data["assets"],
                   active_status=status, active_sort=sort,
                   active_model=data["model_filter"], active_aspect=data["aspect_filter"],
                   tu_studio_ticket_id=tu_studio[:64])


@router.post("/estimate", response_class=HTMLResponse)
def estimate(request: Request, model: str = Form(""), resolution: str = Form("480p"),
             duration: str = Form("5"), aspect_ratio: str = Form("16:9"),
             count: str = Form("1"),
             quote_has_video: str = Form("0"),
             user: str = Depends(require_login)):
    from markupsafe import escape
    mid, res, dur, asp = _clean(model, resolution, duration, aspect_ratio)
    try:
        quantity = max(1, min(int(count or 1), 2))
    except (TypeError, ValueError):
        quantity = 1
    u = user_hien_tai(request) if request is not None else None
    owner_id = u.id if u is not None else str(user)
    has_video = str(quote_has_video).strip().lower() in {"1", "true", "yes"}
    priced = {"model": mid, "resolution": res, "duration": dur,
              "aspect_ratio": asp}
    if has_video:
        priced["refs"] = [{"kind": "video"}]
    e = cost.uoc_luong(mid, res, dur, has_video)
    try:
        quote_id, quote = quotes.issue(owner_id, priced, quantity, has_video)
    except RuntimeError as exc:
        return HTMLResponse(f'<span class="tv-quote-error">{escape(str(exc))}</span>', 503)
    held = int(quote["unit_hold"]) * quantity
    estimated = e["credit"] * quantity
    details = _t('{quantity} video · dự kiến {estimated} credit; không thu vượt mức xác nhận').format(
        quantity=quantity, estimated=estimated)
    return HTMLResponse(
        f'<strong>{held} {_t("credit tối đa")}</strong> '
        f'<span class="dim">({details})</span>'
        f'<input type="hidden" name="quote_id" value="{escape(quote_id)}">')


@router.post("/translate", response_class=HTMLResponse)
async def translate(request: Request, prompt: str = Form(""), target: str = Form("en"),
                    csrf_token: str = Form(""), user: str = Depends(require_login)):
    """Dịch prompt qua Gemini chat (HTMX trả <textarea> mới). Không tốn credit."""
    from markupsafe import escape
    from starlette.concurrency import run_in_threadpool
    from apps.taovideo import translate as tr
    if not verify_csrf_token(request, csrf_token):   # chống lạm dụng quota dịch cross-site
        return HTMLResponse('<span class="dim">Phiên hết hạn — tải lại trang.</span>')
    p = prompt.strip()[:10000]
    if not p:
        return HTMLResponse('<span class="dim">Nhập mô tả rồi bấm dịch.</span>')
    try:
        # dich() gọi httpx đồng bộ + DB → đẩy khỏi event loop để không chặn web.
        out = await run_in_threadpool(tr.dich, p, target if target in ("en", "zh", "vi") else "en")
    except Exception:  # noqa: BLE001
        return HTMLResponse('<span class="dim">Dịch lỗi — thử lại sau.</span>')
    return HTMLResponse(
        f'<textarea id="tv-prompt" name="prompt" rows="4" form="sdform" '
        f'aria-describedby="tv-prompt-hint" maxlength="10000" required '
        f'style="width:100%">{escape(out)}</textarea>'
        f'<div class="dim" style="font-size:12px;margin-top:4px">Đã dịch → {escape(target)}. '
        f'Sửa nếu cần rồi bấm Tạo video.</div>')


@router.post("/prompt-assist", response_class=HTMLResponse)
def prompt_assist(request: Request, prompt: str = Form(""), camera: str = Form(""),
                  motion: str = Form(""), visual_style: str = Form(""),
                  csrf_token: str = Form(""), user: str = Depends(require_login)):
    """Preview prompt final bằng cùng helper mà queue dùng; không gọi provider."""
    from markupsafe import escape
    if not verify_csrf_token(request, csrf_token):
        return HTMLResponse('<span class="tv-assist-error">Phiên hết hạn — tải lại trang.</span>', 400)
    final = _compose_prompt(prompt, camera, motion, visual_style)
    if not final:
        return HTMLResponse('<span class="tv-assist-error">Nhập prompt để xem gợi ý.</span>', 400)
    return HTMLResponse(f'<pre class="tv-assist-preview">{escape(final)}</pre>')


_CAP = {"image": 20 * 1024 * 1024, "video": 60 * 1024 * 1024, "audio": 20 * 1024 * 1024}


def _actual_uploads(*groups) -> list[UploadFile]:
    """Gộp ba input file; bỏ dependency marker khi unit test gọi route trực tiếp."""
    out = []
    for group in groups:
        if not isinstance(group, (list, tuple)):
            continue
        out.extend(f for f in group if f and getattr(f, "filename", ""))
    return out


async def _luu_refs(u_id: str, files, roles, handles=None, *, copies: int = 1,
                    grouped: bool = False) -> list:
    """Stage ref owner-scoped; ``copies`` tách input cho từng job trong batch.

    File chưa thành asset bền vững ở đây. Queue chỉ promote bản tương ứng sau
    khi job đó đã giữ credit, nên batch hai video không dùng chung một file có
    thể bị cleanup nhầm khi một job thất bại.
    """
    from platform_core import upload_sessions
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    storage = get_storage()
    prepared = []
    actual = [f for f in (files or []) if f and getattr(f, "filename", "")]
    if len(actual) > 4:
        raise ValueError(_t('Tối đa 4 file tham chiếu.'))
    for i, f in enumerate(actual):
        if not f or not getattr(f, "filename", ""):
            continue
        ct = (f.content_type or "").lower()
        if ct.startswith("image/"):
            kind = "image"
        elif ct in {"video/mp4", "video/quicktime", "video/webm"}:
            kind = "video"
        elif ct.startswith("audio/"):
            kind = "audio"
        else:
            raise ValueError(f"Định dạng tham chiếu không hỗ trợ: {f.filename}")
        data = await f.read()
        if not data:
            raise ValueError(f"File tham chiếu rỗng: {f.filename}")
        if len(data) > _CAP[kind]:
            raise ValueError(f"File tham chiếu vượt giới hạn: {f.filename}")
        role = roles[i] if roles and i < len(roles) else "reference_image"
        role = (role if kind == "image" and role in
                {"reference_image", "first_frame", "last_frame", "mask"}
                else f"reference_{kind}")
        name = PurePath(str(f.filename).replace("\\", "/")).name[:120]
        prepared.append((kind, ct, data, role, name,
                         (handles[i] if handles and i < len(handles) else "")[:32]))
    copies = max(1, min(int(copies), 2))
    groups = [[] for _ in range(copies)]
    staged_keys = []
    gen = get_session(); db = next(gen)
    try:
        try:
            for variant in range(copies):
                for kind, ct, data, role, name, handle in prepared:
                    session = upload_sessions.stage_bytes(
                        db, storage, user_id=u_id, app_slug=MANIFEST.slug,
                        filename=name, content_type=ct, data=data,
                        max_size=_CAP[kind],
                        allowed_types=(
                            "image/png", "image/jpeg", "image/webp",
                            "video/mp4", "video/quicktime", "video/webm",
                            "audio/wav", "audio/x-wav", "audio/mpeg",
                            "audio/mp3", "audio/mp4", "audio/x-m4a",
                        ),
                    )
                    staged_keys.append(session.staging_key)
                    groups[variant].append({
                        "kind": kind, "storage_key": session.staging_key,
                        "upload_id": session.id, "role": role, "handle": handle,
                        "name": name, "content_type": ct, "size": len(data),
                    })
            db.commit()
        except Exception:
            db.rollback()
            for key in staged_keys:
                storage.delete(key)
            raise
    finally:
        try: next(gen)
        except StopIteration: pass
    return groups if grouped else groups[0]


#: Tran ref prefill. `taovideo` von cho toi da 4 tai san moi job
#: (`_luu_refs` + `_saved_refs_for_user`), con ben giao bai cho toi 9 anh. Hai
#: tran KHAC NHAU va day la cho chung gap nhau: ta giu tran 4 cua app nay
#: (app `lifecycle="released"`, doi tran la doi hanh vi cho khach dang dung),
#: va tra ve SO anh bi bo (`bo_qua`) de JS noi ro voi khach. Cat am tham la
#: dung con bo N-1 ma ca pha nay dang chua.
TRAN_REF_PREFILL = 4

#: Duoi tep theo content-type — ba kieu nay khop `allowed_types` duoi day.
#: KHONG dung `.bin`: `upload_sessions.promote()` lay duoi cua `filename` lam
#: duoi cua `final_key`, va mot key `.bin` lam moi cho doan kieu theo duoi
#: (route phat media, CDN) thay `application/octet-stream` — mot lech im lang
#: giua HAI duong nop cho CUNG mot thu (da do that tren trinh duyet).
_DUOI_ANH = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _stage_prefill_refs(u_id: str, refs: list, *, tran: int = TRAN_REF_PREFILL
                        ) -> tuple[list, int]:
    """Giai ma refs cua ve giao bai (anh: data URL) thanh `upload_sessions`.

    Tra `(staged, bo_qua)`. Chi xu ly `kind == "image"` voi `url` dang `data:`
    — day la duong duy nhat ben giao bai tao ra cho anh (da qua
    `normalize_image`/`image_to_inline`). Video/audio mang URL http/duong dan
    app, khong tu dong tai ve o Pha 2; chung duoc dem vao `bo_qua` de JS noi
    ro, chu khong bien mat im lang.
    """
    from platform_core import upload_sessions
    from platform_core.db import get_session
    from platform_core.storage import get_storage
    storage = get_storage()
    staged: list[dict] = []
    bo_qua = 0
    gen = get_session(); db = next(gen)
    try:
        for index, ref in enumerate(refs or []):
            url = str((ref or {}).get("url") or "")
            if str((ref or {}).get("kind") or "") != "image" or not url.startswith("data:"):
                bo_qua += 1
                continue
            if len(staged) >= max(0, int(tran)):
                bo_qua += 1
                continue
            header, _, b64data = url.partition(",")
            try:
                data = _base64.b64decode(b64data, validate=True)
            except (ValueError, TypeError):
                bo_qua += 1
                continue
            ct = (header.split(";")[0][5:] or "image/png").lower()
            if not data or len(data) > _CAP["image"]:
                bo_qua += 1
                continue
            try:
                session = upload_sessions.stage_bytes(
                    db, storage, user_id=u_id, app_slug=MANIFEST.slug,
                    filename=f"prefill-{index}{_DUOI_ANH.get(ct, '.png')}",
                    content_type=ct, data=data, max_size=_CAP["image"],
                    allowed_types=("image/png", "image/jpeg", "image/webp"))
            except (ValueError, upload_sessions.UploadSessionError):
                bo_qua += 1
                continue
            staged.append({"kind": "image", "upload_id": session.id,
                           "role": str((ref or {}).get("role") or "reference_image"),
                           "handle": str((ref or {}).get("handle") or "")[:32]})
        db.commit()
        return staged, bo_qua
    except Exception:
        db.rollback()
        raise
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/prefill")
async def prefill_apply(request: Request, user: str = Depends(require_login)):
    """Nhan payload giao bai (JSON tho) tu JS, tra gia tri dien form + ref da stage.

    Route nay KHONG BAO GIO tu goi sang `/prompt-ai-ommi/...`: trinh duyet da tu
    `fetch()` payload (cung goc, cung phien) roi POST nguyen van sang day. Neu
    thay minh sap viet `httpx.get("/prompt-ai-ommi/...")` o day, do la dau hieu
    dang pha ranh gioi app->app — dung lai.
    """
    body = await request.json()
    if not verify_csrf_token(request, str((body or {}).get("csrf_token") or "")):
        return JSONResponse({"error": _t('Phiên đã hết hạn — tải lại trang.')},
                            status_code=400)
    u = user_hien_tai(request)
    if u is None:
        return JSONResponse({"error": _t('Cần đăng nhập bằng tài khoản người dùng.')},
                            status_code=403)
    tho = (body or {}).get("payload")
    payload = tho if isinstance(tho, dict) else {}
    from apps.taovideo import prefill
    values = prefill.build_form_values(payload)
    refs = payload.get("refs")
    try:
        ref_keys, bo_qua = _stage_prefill_refs(
            u.id, refs if isinstance(refs, list) else [])
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return {"values": values, "ref_keys": ref_keys, "bo_qua": bo_qua}


def _saved_refs_for_user(user_id: str, keys: list[str]) -> list[dict]:
    """Resolve key từ lịch sử job owner; browser không được tự khai storage key."""
    requested = list(dict.fromkeys(str(k) for k in (keys or [])))
    if not requested:
        return []
    if len(requested) > 4:
        raise ValueError(_t('Tối đa 4 tài sản đã lưu.'))
    data = _jobs_cua_toi_for_user(user_id)
    allowed = {a["storage_key"]: a for a in data}
    from platform_core.storage import get_storage
    storage = get_storage(); out = []
    for key in requested:
        asset = allowed.get(key)
        if asset is None or not storage.exists(key):
            raise ValueError(_t('Tài sản đã lưu không hợp lệ hoặc không còn tồn tại.'))
        clean = dict(asset)
        kind = str(clean.get("kind") or "image")
        if kind not in {"image", "video", "audio"}:
            raise ValueError(_t('Loại tài sản đã lưu không hợp lệ.'))
        role = str(clean.get("role") or "")
        clean["role"] = (role if kind == "image" and role in
                         {"reference_image", "first_frame", "last_frame", "mask"}
                         else f"reference_{kind}")
        clean["handle"] = str(clean.get("handle") or "")[:32]
        out.append(clean)
    return out


def _jobs_cua_toi_for_user(user_id: str) -> list[dict]:
    """Danh sách asset lịch sử tối thiểu cho submit; owner-scoped tại DB."""
    from platform_core.db import get_session
    from platform_core.models import Job
    from sqlalchemy import select
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(select(Job).where(
            Job.user_id == user_id, Job.app_slug == MANIFEST.slug
        ).order_by(Job.created_at.desc()).limit(60)).scalars().all()
        out=[]; seen=set()
        for job in rows:
            for ref in ((job.params or {}).get("refs") or []):
                key=str(ref.get("storage_key") or "")
                if key.startswith(f"taovideo/{user_id}/refs/") and key not in seen:
                    seen.add(key); out.append(dict(ref))
        return out
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/queue", response_class=HTMLResponse)
async def queue(request: Request, csrf_token: str = Form(...), prompt: str = Form(""),
                model: str = Form(""), resolution: str = Form("480p"),
                duration: str = Form("5"), aspect_ratio: str = Form("16:9"),
                generate_audio: str = Form(""), count: str = Form("1"),
                camera: str = Form(""), motion: str = Form(""),
                visual_style: str = Form(""), seed: str = Form(""),
                ref_images: list[UploadFile] = File(default=[]),
                ref_videos: list[UploadFile] = File(default=[]),
                ref_audios: list[UploadFile] = File(default=[]),
                ref_roles: list[str] = Form(default=[]), ref_handles: list[str] = Form(default=[]),
                saved_ref_keys: list[str] = Form(default=[]),
                prefill_upload_ids: list[str] = Form(default=[]),
                prefill_roles: list[str] = Form(default=[]),
                prefill_handles: list[str] = Form(default=[]),
                quote_id: str = Form(""),
                user: str = Depends(require_login)):
    from platform_core import credit, upload_sessions
    from platform_core.db import get_session
    from platform_core.registry import RegistryError

    if not verify_csrf_token(request, csrf_token):
        return _render(request, user, error="Phiên đã hết hạn — tải lại trang.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    if not prompt.strip():
        return _render(request, user, error="Chưa nhập mô tả video.",
                       jobs=_jobs_cua_toi(request), status_code=400)
    mid, res, dur, asp = _clean(model, resolution, duration, aspect_ratio)
    try:
        fixed_seed = _clean_seed(seed)
    except ValueError as exc:
        return _render(request, user, error=str(exc), jobs=_jobs_cua_toi(request), status_code=400)
    try:
        n = max(1, min(int(count or 1), 2))
    except (TypeError, ValueError):
        n = 1
    u = user_hien_tai(request)
    if u is None:
        return _render(request, user, error="Cần đăng nhập bằng tài khoản người dùng.",
                       jobs=_jobs_cua_toi(request), status_code=400)

    try:
        saved_refs = _saved_refs_for_user(u.id, saved_ref_keys)
        actual_files = _actual_uploads(ref_images, ref_videos, ref_audios)
        new_count = len(actual_files)
        if len(saved_refs) + new_count > 4:
            raise ValueError(_t('Tổng tài sản đã lưu và file mới không được vượt quá 4.'))
    except ValueError as exc:
        return _render(request, user, error=str(exc), jobs=_jobs_cua_toi(request), status_code=400)
    has_video = any((getattr(f, "content_type", "") or "").lower() in
                    {"video/mp4", "video/quicktime", "video/webm"}
                    for f in actual_files) or any(r.get("kind") == "video" for r in saved_refs)
    quote_params = {"model": mid, "resolution": res, "duration": dur,
                    "aspect_ratio": asp}
    verified_quote = quotes.verify(quote_id, u.id, quote_params, n, has_video)
    if verified_quote is None:
        return _render(
            request, user,
            error=_t('Báo giá đã hết hạn hoặc cấu hình đã đổi. Vui lòng chờ báo giá mới.'),
            jobs=_jobs_cua_toi(request), status_code=409,
        )

    from platform_core.storage import get_storage
    storage = get_storage(); promotions = []
    gen = get_session(); db = next(gen)
    try:
        try:
            prior = quotes.existing_jobs(db, u.id, verified_quote["intent"], n)
            if prior:
                db.commit()
                return RedirectResponse("/taovideo", status_code=303)
            staged_ref_groups = await _luu_refs(
                u.id, actual_files, ref_roles, ref_handles,
                copies=n, grouped=True)
            # Ref da stage san boi `/prefill` (duong giao bai). Khong co
            # `prefill_upload_ids` thi khoi nay la KHONG-OP — moi duong cu
            # (file moi / tai san da luu) chay y nhu truoc.
            con_cho = max(0, 4 - len(saved_refs) - len(actual_files))
            for i, upload_id in enumerate(prefill_upload_ids[:con_cho]):
                session = upload_sessions.owned(
                    db, session_id=upload_id, user_id=u.id,
                    app_slug=MANIFEST.slug)
                if session is None:
                    continue  # phien het han/da dung — bo qua, khong chan submit
                role = (prefill_roles[i] if i < len(prefill_roles)
                        else "reference_image")
                handle = (prefill_handles[i] if i < len(prefill_handles) else "")
                # CHI nhom dau tien: mot `upload_session` chi `promote` duoc MOT
                # lan, nen dua cung mot ve cho hai variant se lam job thu hai vo
                # (dung ly do `_luu_refs` phai stage BAN SAO rieng cho tung
                # variant). Duong giao bai luon `count=1` (JS ep vay).
                staged_ref_groups[0].append({
                    "kind": "image", "storage_key": session.staging_key,
                    "upload_id": session.id, "role": role,
                    "handle": handle[:32], "name": session.filename,
                    "content_type": session.content_type,
                    "size": session.actual_size,
                })
        except ValueError as exc:
            db.rollback()
            return _render(request, user, error=str(exc),
                           jobs=_jobs_cua_toi(request), status_code=400)

        final_prompt = _compose_prompt(prompt, camera, motion, visual_style)
        base_params = {"prompt": final_prompt, "raw_prompt": prompt.strip()[:10000],
                       "camera": camera if camera in _CAMERA else "",
                       "motion": motion if motion in _MOTION else "",
                       "visual_style": visual_style if visual_style in _VISUAL_STYLE else "",
                       "model": mid, "resolution": res,
                       "duration": dur, "aspect_ratio": asp,
                       "generate_audio": bool(generate_audio), "owner_id": u.id,
                       "refs": saved_refs}
        jobs = quotes.submit_batch(
            db, user_id=u.id, quote=verified_quote,
            base_params=base_params, fixed_seed=fixed_seed,
            variant_refs=[saved_refs + refs for refs in staged_ref_groups],
        )
        for job, refs in zip(jobs, staged_ref_groups):
            final_refs = list(saved_refs)
            for index, ref in enumerate(refs):
                session = upload_sessions.owned(
                    db, session_id=ref["upload_id"], user_id=u.id,
                    app_slug=MANIFEST.slug)
                if session is None:
                    raise upload_sessions.UploadSessionError(
                        _t("Vé upload tham chiếu không hợp lệ."))
                suffix = PurePath(session.filename).suffix.lower()[:12]
                final_key = (f"taovideo/{u.id}/refs/{job.id}/"
                             f"{index}-{ref['role']}{suffix}")
                key = upload_sessions.promote(
                    db, storage, session, job=job, final_key=final_key)
                promotions.append((session.staging_key, final_key,
                                   session.content_type))
                final_refs.append({key: value for key, value in ref.items()
                                   if key != "upload_id"} | {"storage_key": key})
            job.params = dict(job.params or {}, refs=final_refs)
        if any(MANIFEST.credit_cost(job.params or {}) != verified_quote["unit_hold"]
               for job in jobs):
            raise RuntimeError(_t('Báo giá không còn khớp với cấu hình hệ thống.'))
        db.commit()
    except (credit.ThieuCreditError, RegistryError, RuntimeError,
            upload_sessions.UploadSessionError) as exc:
        db.rollback()
        upload_sessions.compensate(storage, promotions)
        return _render(request, user, error=str(exc),
                       jobs=_jobs_cua_toi(request), status_code=400)
    except Exception:
        db.rollback()
        upload_sessions.compensate(storage, promotions)
        raise
    finally:
        try: next(gen)
        except StopIteration: pass
    # Luôn về /taovideo (có player "Video của tôi") thay vì /jobs/{id} (chỉ JSON thô).
    return RedirectResponse("/taovideo", status_code=303)


def _owned_video_job(db, user_id: str, job_id: str):
    from platform_core.models import JOB_DONE, Job
    job = db.get(Job, job_id)
    if job is None or job.user_id != user_id or job.app_slug != MANIFEST.slug or job.status != JOB_DONE:
        return None
    if not (job.result or {}).get("video_key"):
        return None
    return job


@router.post("/upscale-quote")
def upscale_quote(request: Request, job_id: str = Form(""), target_height: str = Form("1080"),
                  preset: str = Form("fast"), user: str = Depends(require_login)):
    """Server-side quote for a completed, owned Seedance video; never trust browser price."""
    u = user_hien_tai(request)
    from platform_core.db import get_session
    from apps.upscalevideo import cost as upscale_cost
    gen = get_session(); db = next(gen)
    try:
        job = _owned_video_job(db, u.id if u else "", job_id)
        if job is None:
            return JSONResponse({"ok": False, "error": "Video không hợp lệ."}, status_code=404)
        try: height = int(target_height)
        except ValueError: height = 1080
        height = height if height in (1080, 1440, 2160) else 1080
        preset = preset if preset in ("fast", "quality") else "fast"
        duration = float((job.result or {}).get("duration") or (job.params or {}).get("duration") or 0)
        return {"ok": True, "job_id": job.id, "credit": upscale_cost.uoc_luong_credit(duration, height, preset),
                "duration_s": duration, "target_height": height, "preset": preset}
    finally:
        try: next(gen)
        except StopIteration: pass


@router.post("/upscale-confirm")
def upscale_confirm(request: Request, csrf_token: str = Form(...), job_id: str = Form(""),
                    target_height: str = Form("1080"), preset: str = Form("fast"),
                    codec: str = Form("h264"), user: str = Depends(require_login)):
    """Confirm the quoted action: submit exactly one shared Upscale job + credit hold."""
    if not verify_csrf_token(request, csrf_token):
        return JSONResponse({"ok": False, "error": "Phiên đã hết hạn."}, status_code=400)
    u = user_hien_tai(request)
    from platform_core import credit
    from platform_core.db import get_session
    from platform_core.registry import RegistryError
    from apps.upscalevideo.service import submit_upscale_job
    gen = get_session(); db = next(gen)
    try:
        source = _owned_video_job(db, u.id if u else "", job_id)
        if source is None:
            return JSONResponse({"ok": False, "error": "Video không hợp lệ."}, status_code=404)
        try: height = int(target_height)
        except ValueError: height = 1080
        duration = float((source.result or {}).get("duration") or
                         (source.params or {}).get("duration") or 0)
        output = submit_upscale_job(db, user_id=u.id,
                                    video_key=(source.result or {})["video_key"],
                                    preset=preset, target_height=height, codec=codec,
                                    duration_s=duration)
        db.commit()
        return {"ok": True, "upscale_job_id": output.id, "redirect": f"/jobs/{output.id}"}
    except (credit.ThieuCreditError, RegistryError) as exc:
        db.rollback()
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    finally:
        try: next(gen)
        except StopIteration: pass


@router.get("/v/{key:path}")
def video(request: Request, key: str, user: str = Depends(require_login)):
    """Serve video theo HTTP Range (né trần 100MB CF). Chỉ chủ sở hữu."""
    from fastapi import HTTPException
    from platform_core.storage import StorageError, get_storage

    u = user_hien_tai(request)
    segs = key.split("/")
    if len(segs) < 2 or segs[0] != "taovideo" or u is None or segs[1] != u.id:
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy video.'))
    storage = get_storage()
    # R2 (H10): trả presigned URL → trình duyệt tải THẲNG từ R2, né trần 100MB.
    direct = storage.try_url_for(key)
    if direct:
        return RedirectResponse(direct, status_code=302)
    try:
        total = storage.size(key)
    except (StorageError, FileNotFoundError):
        raise HTTPException(status_code=404, detail=_t('Không tìm thấy video.'))

    # ⭐ HTTP Range đi qua `platform_core.phat_media`, không tự viết ở đây.
    #
    #    Bản cũ ở chỗ này là một trong **năm** bản chép gần như giống nhau từng
    #    dòng (`taovideo`, `taoclipngan`, `upscalevideo`, `agent`,
    #    `autosubvideo`), và cả năm mang cùng bốn khiếm khuyết: không bao giờ trả
    #    `416`; `bytes=-500` trả 501 byte ĐẦU thay vì 500 byte cuối; `bytes=0-`
    #    nuốt cả tệp vào RAM; `start > end` xử lý mỗi nơi một kiểu.
    #
    # ⚠️ Phép kiểm sở hữu ở TRÊN vẫn ở lại app — đó là ranh giới: app giữ quyền,
    #    lớp dùng chung giữ đường ống. Xem `docs/MOBILE/04_SHARED_CONTRACT.md`.
    return phat_media.phat_tu_kho(
        storage, key, kieu_noi_dung="video/mp4",
        dai_range=request.headers.get("range"), tong=total)
