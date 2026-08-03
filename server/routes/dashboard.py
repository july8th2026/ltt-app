"""Trang chủ — danh sách app, sinh từ apps/*/manifest.py.

Trước đây "/" chỉ hiện tóm tắt blocker. Giờ nó là cửa vào của nền tảng nhiều
app, nhưng vẫn giữ phần blocker ở trên: đây là trang thấy đầu tiên sau khi
đăng nhập, nên là chỗ đúng nhất để nói "bot chưa đăng được vì thiếu X".

Phần blocker dùng lại tools/doctor.py để trang chủ, /status và CLI không bao
giờ nói khác nhau. Bỏ qua kiểm tra Sheet vì trang này tải mỗi lần đăng nhập,
mà kiểm tra Sheet tốn một vòng gọi mạng.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from server.auth.session import current_identity_optional
from server.templating import templates

router = APIRouter(tags=["home"])

_CATEGORY_BY_GROUP = {
    "Ảnh": "AI Image", "Video": "AI Video", "Chat": "Chat & Prompt",
    "Kịch bản": "Chat & Prompt", "AI Studio": "Automation",
}


def _home_category(group: str) -> str:
    """Taxonomy launcher; không thay đổi hợp đồng manifest của từng app."""
    return _CATEGORY_BY_GROUP.get(group or "", "Utilities")


def _workspace_data(visible: list, db_user) -> dict:
    """Dữ liệu dashboard owner-scoped, trừ aggregate Popular chỉ dùng để sort."""
    from platform_core.db import get_session
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job
    from sqlalchemy import func, select

    result = {"popularity": {}, "recent": [], "running": [], "used_slugs": set()}
    if db_user is None:
        return result
    manifest_by_slug = {item.manifest.slug: item.manifest for item in visible}
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(select(Job.app_slug, func.count(Job.id)).group_by(Job.app_slug))
        result["popularity"] = {slug: int(count) for slug, count in rows
                                if slug in manifest_by_slug}
        result["recent"] = db.execute(
            select(Job).where(Job.user_id == db_user.id)
            .order_by(Job.created_at.desc()).limit(5)).scalars().all()
        result["running"] = db.execute(
            select(Job).where(Job.user_id == db_user.id,
                              Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
            .order_by(Job.created_at.desc()).limit(5)).scalars().all()
        # "My Apps" là toàn bộ app user từng chạy, không phải chỉ app xuất hiện
        # trong 5 hoạt động gần nhất. Query riêng giữ recent rail nhỏ mà filter
        # launcher vẫn đúng theo toàn bộ lịch sử owner.
        result["used_slugs"] = set(db.execute(
            select(Job.app_slug).where(Job.user_id == db_user.id).distinct()
        ).scalars().all())
        detached: set[str] = set()
        for job in [*result["recent"], *result["running"]]:
            manifest = manifest_by_slug.get(job.app_slug)
            job.app_name = manifest.display_name if manifest else job.app_slug
            job.app_icon = manifest.icon if manifest else "✦"
            if job.id not in detached:
                db.expunge(job)
                detached.add(job.id)
    finally:
        try: next(gen)
        except StopIteration: pass
    return result


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Trang chủ = CATALOG (H6/Q30).

    CÔNG KHAI: khách chưa đăng nhập vẫn xem được danh sách app (chỉ app
    `enabled and public`), bấm một app thì mới cần đăng nhập. Đã đăng nhập thì
    lọc theo quyền (AppAccess) và hiện blocker/app-lỗi như trước.
    """
    from platform_core.registry import discover

    user = current_identity_optional(request)
    authed = user is not None
    loaded = discover()
    ok_apps = [a for a in loaded if not a.error]

    if not authed:
        # Khách: chỉ hiện app self-serve công khai; KHÔNG lộ blocker/app-lỗi.
        visible = [a for a in ok_apps
                   if a.manifest.enabled and a.manifest.public]
        return templates.TemplateResponse(request, "home.html", {
            "user": None, "authed": False, "nav": "home",
            "apps": visible, "broken": [], "app_setup": {},
        })

    # Đã đăng nhập: lọc theo quyền (H1.4) + tính "cần thiết lập" theo TỪNG app.
    # Bọc an toàn: DB trục trặc / admin-env thì hiện đủ, không để phân quyền làm
    # trang trắng.
    from tools import doctor
    report = doctor.run(check_sheet_flag=False)
    visible = ok_apps
    db_user = None
    try:
        db_user = _user_hien_tai(request)
        if db_user is not None:
            from platform_core.app_access import loc_app_hien_thi
            from platform_core.db import get_session
            gen = get_session(); db = next(gen)
            try:
                visible = loc_app_hien_thi(db, db_user, visible)
            finally:
                try: next(gen)
                except StopIteration: pass
    except Exception:
        pass

    # Blocker doctor gắn vào ĐÚNG thẻ app (H6.6): không còn banner FB/TikTok toàn
    # cục. Khớp theo manifest.blocker_titles do app tự khai — nền tảng KHÔNG
    # hardcode tên app. Blocker không thuộc app nào vẫn xem đầy đủ ở /status.
    block_sections = [s for s in report.sections if s["status"] == doctor.BLOCK]
    app_setup: dict = {}
    for item in visible:
        titles = getattr(item.manifest, "blocker_titles", ()) or ()
        hits = [s for s in block_sections if s["check"] in titles]
        if hits:
            app_setup[item.manifest.slug] = hits

    workspace = _workspace_data(visible, db_user)
    for item in visible:
        item.home_category = _home_category(item.manifest.group)
        item.home_popularity = workspace["popularity"].get(item.manifest.slug, 0)
        item.home_used = item.manifest.slug in workspace["used_slugs"]

    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "authed": True,
        "nav": "home",
        "apps": visible,
        "broken": [a for a in loaded if a.error],
        "app_setup": app_setup,
        "home_workspace": True,
        "workspace": workspace,
    })


def _user_hien_tai(request: Request):
    """User CSDL từ phiên, hoặc None (admin-env / ẩn danh / chưa có DB)."""
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            return lay_user_tu_phien(db, sid)
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return None
