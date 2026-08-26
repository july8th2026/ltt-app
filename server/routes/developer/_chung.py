"""Nhan dung chung cua cong lap trinh vien.

Tach ra 2026-08-26 khi che `developer.py` (1.521 dong / 32 handler) theo USE
CASE. Phan nay KHONG phai rac con lai — no la phan that su duoc moi nhom dung
chung: `router`, `require_account`, cay dieu huong (`SECTIONS`, `NHOM_NAV`,
`CHA_CUA`, `MUC_CON`) va cac ham dung context + `_render`.
"""
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

_log = logging.getLogger("ltt.developers")

router = APIRouter(prefix="/developers", tags=["developers"])

# How many finished/queued API jobs the portal shows. Enough to answer "did my
# integration work"; not a job browser — that is what `/api/v1/jobs` is for.
RECENT_JOBS = 10


def require_account(request: Request):
    """The signed-in database user. The admin-env path has no account to bill.

    Declared **before** the database dependency on every route below, so an
    anonymous visitor is bounced to the login page instead of first opening a
    session — which on a server with no database configured turned a redirect
    into a 500.
    """
    require_login(request)
    user = user_hien_tai(request)
    if user is None:
        # Break-glass admin (Q29) has no `users` row, so no keys and no credit.
        raise _redirect("/login?next=/developers")
    return user


def tai_khoan_tuy_chon(request: Request):
    """Nguoi dang xem, hoac `None` neu chua dang nhap.

    Khac `require_account`: ham do NEM chuyen huong ve `/login`. Dung cho hai
    trang trong `TRANG_CONG_KHAI` — chung khong doc gi cua tai khoan, nen doi
    dang nhap chi de xem chung la mot rao can khong mua duoc gi.
    """
    # KHONG boc try o day. `user_hien_tai` (server/deps.py:44) da tra `None`
    # cho ca ba truong hop ta quan tam — chua dang nhap, dang nhap bang duong
    # admin-env, CSDL chua cau hinh — va no da co try rieng ben trong.
    #
    # Mot lop `except Exception` nua o day khong bat them duoc gi that, nhung
    # no nuot moi loi KHAC: CSDL sap, cau hinh sai, mot bug trong chinh
    # `user_hien_tai`. Ba thu do se im lang bien thanh "khach an danh", va
    # trieu chung la trang van tra 200 voi noi dung sai. Banh coc
    # `tools/check_silent_except.py` bat dung cho nay.
    return user_hien_tai(request)


def _redirect(location: str, status_code: int = 303):
    from fastapi import HTTPException

    return HTTPException(status_code=status_code, headers={"Location": location})


def _webhooks(db: Session, user_id: str) -> list:
    return list(db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user_id,
        WebhookSubscription.enabled.is_(True),
    ).order_by(WebhookSubscription.created_at.desc())).scalars().all())


def _all_webhooks(db: Session, user_id: str) -> list:
    """Including the disabled ones: an endpoint you turned off is still part of
    the story its delivery history tells."""
    return list(db.execute(select(WebhookSubscription).where(
        WebhookSubscription.user_id == user_id,
    ).order_by(WebhookSubscription.created_at.desc())).scalars().all())


def _recent_api_jobs(db: Session, user_id: str) -> list:
    """Jobs this account created through the API, newest first."""
    rows = db.execute(select(Job).where(Job.user_id == user_id)
                      .order_by(Job.created_at.desc()).limit(50)).scalars().all()
    found = []
    for job in rows:
        meta = api_meta(job)
        if not meta:
            continue        # made in the UI, not through the API
        found.append({"id": job.id, "tool": meta.get("tool") or "",
                      "status": job.status, "created_at": job.created_at,
                      "key_id": meta.get("key_id") or ""})
        if len(found) >= RECENT_JOBS:
            break
    return found


def _public_api_config(request: Request):
    """The configuration this application was mounted with.

    Read from app state rather than the environment: the portal must describe
    the API this process is actually serving, and an app built with an explicit
    env mapping (tests, a second instance) would otherwise be described by
    whatever the process environment happens to say.
    """
    config = getattr(request.app.state, "public_api", None)
    return config if config is not None else load_public_api_config()


# The area's information architecture, in one place. `href=None` means the
# section is named but not built yet: EXT-08 owns the playground, EXT-09 the
# request logs, EXT-11 the notifications. Showing them greyed is honest about
# the shape of the area; a link that 404s is not. OAuth apps are absent rather
# than greyed, because D1 decided not to build them at all.
SECTIONS = (
    ("overview", "/developers", N_("Tổng quan")),
    ("quickstart", "/developers/quickstart", N_("Bắt đầu nhanh")),
    ("projects", "/developers/projects", N_("Project")),
    ("keys", "/developers/keys", N_("Khóa API")),
    ("tools", "/developers/tools", N_("Công cụ & model")),
    ("playground", "/developers/playground", N_("Playground")),
    ("pricing", "/developers/pricing", N_("Giá & mô phỏng")),
    # ⭐ "Hoat dong" chu khong phai "Nhat ky request": muc nay nay gom CA nhat
    # ky (loi goi HTTP) va job (viec chay bat dong bo). Dat ten cha trung ten
    # mot dua con la noi rang dua con kia la thu phu — ma no khong phai.
    ("logs", "/developers/logs", N_("Hoạt động")),
    ("jobs", "/developers/jobs", N_("Job")),
    ("usage", "/developers/usage", N_("Sử dụng & credit")),
    ("webhooks", "/developers/webhooks", N_("Webhook")),
    ("notifications", "/developers/notifications", N_("Thông báo")),
    ("cli", "/developers/cli", N_("Cắm vào công cụ")),
    ("docs", "/developers/docs", N_("Tài liệu & SDK")),
    ("settings", "/developers/settings", N_("Cài đặt & bảo mật")),
    ("privacy", "/developers/privacy", N_("Dữ liệu & lưu trữ")),
)

# ── Điều hướng: BA NHÓM, mười mục — không phải mười sáu mục phẳng ────────────
#
# 🔴 VÌ SAO ĐỔI. Mười sáu mục nằm trên một dải cuộn ngang không phải là điều
#    hướng, nó là một danh sách. Và nó trộn **ba nghề khác nhau** vào cùng một
#    hàng ngang cấp:
#
#      "làm sao cắm được"      quickstart · cli · docs
#      "API này nhận gì"       tools · pricing · playground
#      "tài khoản tôi ra sao"  keys · projects · logs · jobs · usage · …
#
#    Ba nghề đó khách làm ở BA THỜI ĐIỂM khác nhau — cắm một lần, tra cứu khi
#    viết mã, xem tài khoản khi vận hành. Xếp chúng ngang nhau buộc khách quét
#    cả mười sáu mục mỗi lần cần một mục.
#
# ⭐ Hai trang tham chiếu (soi thật 25/08) đều KHÔNG có điều hướng phẳng:
#    `api.nghimmo.com/huongdan` không có điều hướng nào cả — một ô chọn ở đầu
#    vẽ lại toàn bộ bên dưới; `plenxai.com/developer` gom vào thanh bên ba khu.
#
# ⚠️ SÁU MỤC BỊ HẠ KHỎI CẤP CAO NHẤT VẪN CÒN NGUYÊN ROUTE. Chúng thành mục con
#    của trang cha (xem `CHA_CUA`), không bị xoá. Lý do rất cụ thể: một URL đã
#    đi vào dấu trang, tin nhắn hỗ trợ và ảnh chụp màn hình thì việc nó 404 là
#    thiệt hại thật, còn việc nó rời khỏi thanh điều hướng thì không.
NHOM_NAV = (
    (N_("Bắt đầu"), ("overview", "cli")),
    (N_("Tham chiếu"), ("tools", "pricing", "docs")),
    (N_("Tài khoản"), ("keys", "logs", "usage", "webhooks", "settings")),
)

#: Mục con → mục cha. Mở một mục con thì mục cha sáng, nên khách luôn biết
#: mình đang đứng ở đâu trong cây — thay vì thấy thanh bên không có gì sáng cả.
CHA_CUA = {
    "quickstart": "cli",
    "projects": "keys",
    "playground": "tools",
    "jobs": "logs",
    "notifications": "overview",
    "privacy": "settings",
}

#: Dải mục con hiện bên trong trang cha. Trống nghĩa là trang không có mục con.
#:
#: ⭐ Nhãn ở đây là nhãn TRONG NGỮ CẢNH của cha, nên nó khác nhãn ở `SECTIONS`:
#:    đứng trong "Khóa API" thì mục con tên "Project" là đủ, không cần nói lại
#:    nó là project của cái gì.
MUC_CON = {
    "cli": (("cli", N_("Cắm vào công cụ")), ("quickstart", N_("Bốn bước đầu"))),
    "keys": (("keys", N_("Khóa")), ("projects", N_("Project"))),
    "tools": (("tools", N_("Danh mục")), ("playground", N_("Chạy thử"))),
    "logs": (("logs", N_("Nhật ký request")), ("jobs", N_("Job"))),
    "settings": (("settings", N_("Bảo mật")), ("privacy", N_("Dữ liệu & lưu trữ"))),
    "overview": (("overview", N_("Tổng quan")), ("notifications", N_("Thông báo"))),
}


# Trang MO cho khach chua dang nhap. Ranh gioi la mot cau, va no da duoc viet
# ra o `KE_HOACH_MVP_CONG_LAP_TRINH_VIEN.md` §2.3: **thu giup nguoi ta quyet
# dinh mua thi cong khai; thu gan voi tai khoan thi sau dang nhap.**
#
# `quickstart` va `tools` khong doc mot dong nao cua tai khoan — chung dung tu
# catalog. Dat chung sau `require_account` la bat mot nguoi dang CAN NHAC phai
# tao tai khoan truoc khi biet ta ban gi.
#
# Du an da hoc dung bai nay ba lan (trang gia, huong dan cam, trang VPS) va moi
# lan chi sua dung trang dang dau. Danh sach nay ton tai de lan sau khong phai
# hoc lai — va `test_300` chot no ca HAI chieu: mo them mot trang rieng tu vao
# day la gate do.
# 🔴 RONG, va do la mot CHOT chu khong phai mot viec chua lam.
#
# Chu san pham chot 25/08 (nguyen van o
# `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md` §1):
#
#   "/developers/tools dung sau dang nhap la dung roi. he thong cua ta API
#    can phai dang nhap moi duoc kich hoat"
#
# ⇒ Danh muc cong cu la trang cua MOT TAI KHOAN (cong cu nao dang mo cho tai
#   khoan nay), khong phai trang ban hang. Cai ban hang la `/gia-api` va
#   `/huong-dan`, ca hai da cong khai.
#
# `quickstart` khong nam trong chot do, va no KHONG duoc mo theo suy dien: mo
# mot trang ra roi dong lai te hon la mo cham.
#
# Cau phan biet, de lan sau khong phai hoi lai: **thu tra loi "co dang mua
# khong" thi cong khai; thu tra loi "toi dang dung cai gi" thi sau dang nhap.**
#
# Bo may duoi day giu nguyen va dung ngay duoc khi co chot mo mot trang nao:
# them khoa cua trang do vao day la du, va `test_300` chot CA HAI chieu.
TRANG_CONG_KHAI: frozenset = frozenset()


def _duong(key: str) -> str:
    for k, href, _label in SECTIONS:
        if k == key:
            return href
    return "/developers"


def _nav(active: str, da_dang_nhap: bool = True) -> list:
    """Thanh dieu huong ben trai, gom theo NHOM_NAV.

    Khach an danh chi thay nhung trang ho vao duoc: hien du muc cho ho nghia la
    mot thanh dieu huong ma phan lon la ngo cut bat ve `/login`.

    Mo mot muc con thi muc cha sang — nen khong bao gio co trang nao lam thanh
    ben trong rong khong co gi duoc chon.
    """
    sang = CHA_CUA.get(active, active)
    ra = []
    for ten_nhom, khoa in NHOM_NAV:
        muc = []
        for key in khoa:
            if not da_dang_nhap and key not in TRANG_CONG_KHAI:
                continue
            muc.append({"key": key, "href": _duong(key),
                        "label": _title(key), "active": key == sang})
        # Nhom rong thi bo han tieu de: mot tieu de nhom khong co muc nao la
        # mot dong chu khong noi gi.
        if muc:
            ra.append({"nhom": _t(ten_nhom), "muc": muc})
    return ra


def _muc_con(active: str) -> list:
    """Dai muc con cua trang dang mo, hoac rong.

    ⚠️ Lay theo CHA chu khong theo `active`: dung o `/developers/projects` thi
       dai nay van phai la dai cua "Khoa API", voi "Project" dang duoc chon.
    """
    cha = CHA_CUA.get(active, active)
    return [{"key": key, "href": _duong(key), "label": _t(label),
             "active": key == active}
            for key, label in MUC_CON.get(cha, ())]


def _title(active: str) -> str:
    for key, _href, label in SECTIONS:
        if key == active:
            return _t(label)
    return _t(N_("Tổng quan"))


def _base_context(request: Request, db: Session, user, active: str,
                  error: str = "") -> dict:
    """What every section needs: navigation, service state, CSRF."""
    config = _public_api_config(request)
    return {
        "csrf_token": issue_csrf_token(request),
        "api_enabled": config.enabled,
        "read_only": config.read_only,
        "nav": _nav(active, da_dang_nhap=user is not None),
        "muc_con": _muc_con(active),
        # Tieu de trang la tieu de cua CHA khi dang o mot muc con: dai muc con
        # ngay ben duoi da noi ro dang o nhanh nao, nen lap lai ten nhanh o
        # tieu de la mot dong thua noi cung mot thu hai lan.
        "section_title": _title(CHA_CUA.get(active, active)),
        "error": error,
        # Trang cong khai dung no de doi loi keu goi: khach an danh thay "Dang
        # ky lay khoa", khach da dang nhap thay duong toi khoa cua ho.
        "da_dang_nhap": user is not None,
        # So thong bao chua doc — cho chuong o thanh tren cua khu. Mot COUNT re,
        # va chi chay khi da dang nhap; khach an danh khong co thong bao nao.
        "unread": (_unread_count(db, user) if user is not None else 0),
    }


def _unread_count(db: Session, user) -> int:
    """So thong bao chua doc cua tai khoan, hoac 0 neu co bat ky truc trac gi.

    Chuong o thanh tren la trang tri thong tin, khong phai duong song con: mot
    loi khi dem thong bao khong duoc lam sap ca trang. Nen boc va tra 0."""
    try:
        from platform_core.public_api import notifications
        return int(notifications.unread_count(db, user_id=user.id))
    except Exception as exc:  # noqa: BLE001 - chuong hong thi trang van phai len
        _log.warning("dev topbar: dem thong bao chua doc that bai: %s", exc)
        return 0


def _projects_context(db: Session, user) -> dict:
    rows = projects.list_for(db, user_id=user.id)
    return {"projects": [
        {"id": project.id, "name": project.name, "slug": project.slug,
         "created_at": project.created_at,
         "key_count": len(projects.keys_of(db, project_id=project.id))}
        for project in rows]}


def _keys_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    return {
        "keys": [
            {
                "key_id": key.key_id, "name": key.name,
                "status": key.status(now=now),
                "scopes": list(key.scopes or ()),
                "allowed_tools": list(key.allowed_tools or ()),
                "allowed_ips": list(key.allowed_ips or ()),
                "project": names.get(str(key.project_id or ""), ""),
                "mode": str(getattr(key, "mode", "live") or "live"),
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at,
            }
            for key in devkeys.list_for_user(db, user.id)
        ],
        "scopes": sorted(KNOWN_SCOPES),
        "default_scopes": list(DEFAULT_SCOPES),
        "modes": list(sandbox.MODES),
        "tools": [tool.name for tool in build_catalog(config)],
    }


def _usage_context(db: Session, user, config) -> dict:
    now = datetime.now(timezone.utc)
    window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "balance": credit.so_du(db, user.id),
        "usage_today": usage.usage_totals(db, user_id=user.id,
                                          since=window_start, until=now),
        "limits": {
            "request_rpm": config.request_rpm,
            "create_rpm": config.create_rpm,
            "max_active_jobs": config.max_active_jobs,
            "daily_credit_limit": config.daily_credit_limit,
        },
    }


def _overview_counts(db: Session, user) -> dict:
    """The numbers the overview answers "is anything wrong?" with."""
    from sqlalchemy import func

    from platform_core.public_api.tables import (WEBHOOK_DEAD, WEBHOOK_FAILED,
                                                 ApiRequestLog, WebhookDelivery)

    now = datetime.now(timezone.utc)
    active_keys = sum(1 for key in devkeys.list_for_user(db, user.id)
                      if key.is_usable(now=now))
    failures = int(db.execute(
        select(func.count(WebhookDelivery.id)).where(
            WebhookDelivery.user_id == user.id,
            WebhookDelivery.status.in_((WEBHOOK_FAILED, WEBHOOK_DEAD)),
        )).scalar_one())
    since = now - timedelta(days=30)
    api_jobs = sum(1 for job in db.execute(
        select(Job).where(Job.user_id == user.id,
                          Job.created_at >= since)).scalars().all()
        if api_meta(job))
    # Đã từng gọi API chưa — KHÔNG suy ra từ `api_jobs`: phần lớn lượt gọi
    # đầu tiên là `GET /tools` hoặc `/credits/balance`, chúng không tạo job
    # nào. Suy từ job sẽ nói "chưa gọi bao giờ" với người vừa gọi xong, và đó
    # là kiểu sai làm người ta ngờ cả phần còn lại của trang.
    da_goi = bool(db.execute(
        select(func.count(ApiRequestLog.id)).where(
            ApiRequestLog.user_id == user.id)).scalar_one())
    return {
        "projects": len(projects.list_for(db, user_id=user.id)),
        "active_keys": active_keys,
        "webhooks": len(_webhooks(db, user.id)),
        "webhook_failures": failures,
        "api_jobs": api_jobs,
        "da_goi_api": da_goi,
    }


def _chart_points(series: list, *, width: int = 560, height: int = 150,
                  pad: int = 6) -> dict:
    """Turn `request_log.daily()` rows into ready-to-draw SVG geometry.

    Both lines share one Y scale (the demo's axis does), so a flat line is an
    honest "almost nothing happened that day", not a rescaled illusion. Returns
    ``None`` when there is nothing to draw — the template shows an empty state
    rather than a line through zeros.
    """
    if not series or all(r["requests"] == 0 and r["credit"] == 0
                         for r in series):
        return None
    ymax = max(1, max(max(r["requests"], r["credit"]) for r in series))
    n = len(series)
    span_x = width - 2 * pad
    span_y = height - 2 * pad

    def _xy(index: int, value: int) -> str:
        x = pad + (span_x * index / (n - 1) if n > 1 else span_x / 2)
        y = pad + span_y * (1 - value / ymax)
        return f"{x:.1f},{y:.1f}"

    req = " ".join(_xy(i, r["requests"]) for i, r in enumerate(series))
    credit = " ".join(_xy(i, r["credit"]) for i, r in enumerate(series))
    # Closed polygons for the translucent area fill under each line (demo look):
    # the line, then down to the baseline and back to the start.
    base = f"{pad + span_x:.1f},{pad + span_y:.1f} {pad:.1f},{pad + span_y:.1f}"
    req_area = f"{req} {base}"
    credit_area = f"{credit} {base}"
    labels = [{"x": pad + (span_x * i / (n - 1) if n > 1 else span_x / 2),
               "text": r["date"].strftime("%d/%m"),
               # First/last labels anchor inward so they never clip the edge.
               "anchor": ("start" if i == 0 else
                          "end" if i == n - 1 else "middle")}
              for i, r in enumerate(series)
              # At most ~7 x-axis labels so they never collide.
              if n <= 8 or i % (n // 7 or 1) == 0]
    return {"width": width, "height": height, "ymax": ymax,
            "req_points": req, "credit_points": credit,
            "req_area": req_area, "credit_area": credit_area, "labels": labels}


#: Palette for the tool-breakdown donut — distinct hues that read on carbon,
#: assigned by rank so the biggest slice is always the same colour run to run.
_DONUT_MAU = ("#2bb8c9", "#c8548f", "#8b5cc8", "#d08a2c", "#4a9d5a",
              "#ef3731", "#5882dc", "#6b7280")


def _donut(rows: list, *, by: str = "credit") -> dict:
    """Segments for an SVG donut of `by_tool()` rows, or None if nothing to show.

    The circumference trick: each slice is a circle stroke whose dasharray is
    (arc, rest) and whose offset stacks the previous arcs. Returns the segments
    plus a legend so the template draws no arithmetic of its own.
    """
    items = [row for row in (rows or []) if int(row.get(by, 0)) > 0]
    if not items:
        return None
    total = sum(int(row[by]) for row in items)
    if total <= 0:
        return None
    radius = 60.0
    circ = 2 * 3.141592653589793 * radius
    segments, legend = [], []
    offset = 0.0
    for index, row in enumerate(items[:8]):
        value = int(row[by])
        frac = value / total
        arc = frac * circ
        colour = _DONUT_MAU[index % len(_DONUT_MAU)]
        segments.append({"color": colour, "dash": round(arc, 2),
                         "gap": round(circ - arc, 2),
                         "offset": round(-offset, 2)})
        legend.append({"tool": row["tool"], "color": colour,
                       "percent": round(frac * 100, 1),
                       "value": value, "calls": row.get("calls", 0)})
        offset += arc
    return {"radius": radius, "circ": round(circ, 2), "total": total,
            "segments": segments, "legend": legend}


def _render(request: Request, db: Session, user, active: str, template: str,
            **extra) -> HTMLResponse:
    context = _base_context(request, db, user, active,
                            error=str(extra.pop("error", "") or ""))
    context.update(extra)
    return templates.TemplateResponse(request, template, context)


def _keys_page(request: Request, db: Session, user, *, revealed: str = "",
               error: str = "", created_key=None,
               mode_filter: str = "") -> HTMLResponse:
    config = _public_api_config(request)
    # `mode_filter` chi loc HIEN THI (tab Tat ca / Live / Test cua anh demo) —
    # khong them route, nen `test_197` van chot dung 32. Loc o template tren
    # danh sach nho; khong dung truy van rieng.
    return _render(request, db, user, "keys", "dev_keys.html",
                   error=error, revealed_secret=revealed,
                   created_key=created_key,
                   mode_filter=(mode_filter if mode_filter in ("live", "test")
                                else ""),
                   **_projects_context(db, user),
                   **_keys_context(db, user, config))


# One idempotency key per logical call, reused on every retry of it. Written
# out rather than described, because "reuse the key" is the sentence everyone
# agrees with and then implements as `uuid4()` inside the retry loop.
RETRY_EXAMPLE = """key = str(uuid.uuid4())          # ONCE, outside the loop

for attempt in range(5):
    try:
        job = call("POST", "/jobs", body, {"Idempotency-Key": key})
        break
    except Timeout:               # the request may have succeeded
        time.sleep(2 ** attempt)  # same key -> replay, not a second job"""


#: Status filters people actually think in. "4xx" is a question, "412" is not.
STATUS_CHOICES = (("2xx", N_("Thành công (2xx)")),
                  ("4xx", N_("Lỗi của request (4xx)")),
                  ("401", N_("Không xác thực được (401)")),
                  ("403", N_("Thiếu quyền (403)")),
                  ("409", N_("Xung đột (409)")),
                  ("422", N_("Sai dữ liệu (422)")),
                  ("429", N_("Vượt hạn mức (429)")),
                  ("5xx", N_("Lỗi máy chủ (5xx)")))


def _the_cong_cu(tool) -> dict:
    """Mot the trong danh muc — DU de doc het ma khong roi trang.

    🔴 VI SAO DOI. Danh muc cu la mot BANG PHANG: ten, nhom, che do chay, pham
       vi. Muon biet mot cong cu nhan tham so gi thi phai mo mot trang khac —
       nen so sanh hai cong cu la hai lan tai trang, va quet ca be mat API la N
       lan tai trang.

    ⭐ `plenxai.com/developer` (soi that 25/08) lam nguoc lai: the GAP MAC DINH,
       mo mot cai moi lan, va trong the mo co du bang tham so + vi du + phan
       hoi mau. Ca be mat API lot vao MOT man hinh duoi dang danh sach quet
       duoc; trai phang thi trang dai 4.000 pixel va khong ai nhin thay cai thu
       hai.

    ⚠️ Bang tham so o day sinh tu DUNG mot ham ma trang chi tiet dung
       (`_tham_so`). Hai noi hien thi, mot ban sinh — nen chung khong the lech.
    """
    body = tool.to_public_dict()
    params = _tham_so(body["input_schema"])
    return {"name": tool.name, "description": tool.description,
            "capability": tool.capability,
            "execution_mode": tool.execution_mode,
            "scopes": list(tool.scopes),
            # So model alias khai cho tool nay (ảnh demo: "N model"). Lay tu
            # hop dong cong khai, khong dem tay.
            "model_count": len((getattr(tool, "api_contract", {}) or {}).get(
                "models", {})),
            "params": params,
            "example_request": _example_request(tool, params),
            "outputs": _vi_du_outputs(body["output_schema"].get("properties", {}))}


def _tham_so(schema: dict) -> list:
    """Bang tham so, SINH TU `input_schema` — khong go tay.

    ⛔ Go tay mot bang tham so la tao ban sao thu hai cua hop dong, va ban sao
       do se lech AM THAM: khach doc trang, gui tham so theo trang, nhan 422.
       Xem `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md` §5.

    ⭐ Tach ra khoi route chi tiet 25/08 de danh muc cong cu dung LAI duoc no:
       tu do moi the trong danh muc bung ra duoc bang tham so day du ma khong
       phai tai mot trang khac. Mot ban sinh, hai noi dung.
    """
    required = set(schema.get("required", ()))
    ra = []
    for name, spec in schema.get("properties", {}).items():
        bounds = ""
        if "minimum" in spec or "maximum" in spec:
            bounds = f"{spec.get('minimum', '')}–{spec.get('maximum', '')}"
        elif "maxLength" in spec:
            bounds = _t("tối đa %(n)s ký tự") % {"n": spec["maxLength"]}
        ra.append({
            "name": name, "type": spec.get("type", "string"),
            "required": name in required, "enum": spec.get("enum"),
            "bounds": bounds, "default": spec.get("default"),
            "description": spec.get("description", ""),
            "example": (spec.get("examples") or [None])[0],
            # "Chỉ dùng khi mode = edit, subject" — lấy từ hợp đồng, không đọc
            # câu tiếng Anh trong `description` rồi đoán. Xem `catalog.py`.
            "only_when": spec.get("x-ltt-only-when") or {},
        })
    return ra


def _vi_du_outputs(outputs: dict) -> str:
    """Một mẩu `outputs[]` thật, dựng từ `output_schema`.

    🔴 VÌ SAO CẦN. Bảng "Kết quả" liệt kê tên trường và kiểu, nên người đọc suy
       ra `result.<tên trường>` — chỗ đó **không có gì**. Artifact nằm ở
       `outputs[]`, `result` chỉ giữ phần dữ liệu thuần.

    ⛔ Đo 25/08 bằng một lượt gọi thật: kịch bản làm đúng theo tài liệu đã dừng
       lại **sau khi job xong và tiền đã bị thu**. Không lỗi nào từ máy chủ —
       chỉ là mã của khách tìm sai chỗ.

    ⚠️ Sinh từ schema chứ không gõ tay: một mẩu JSON chép tay là bản sao thứ hai
       của hợp đồng, và nó sẽ lệch đúng vào hôm ai đó đổi tên trường.
    """
    import json

    mau = []
    for ten, spec in outputs.items():
        if not str(spec.get("type", "")).startswith("artifact"):
            continue
        mau.append({"id": f"<job_id>.{ten}.0", "field": ten, "index": 0})
    return json.dumps({"outputs": mau or [{"id": "<job_id>.<field>.0",
                                           "field": "<field>", "index": 0}],
                       "result": {"…": _t("phần dữ liệu thuần, không phải tệp")}},
                      ensure_ascii=False, indent=2)


def _example_request(tool, params) -> str:
    """A quote call a reader can paste — the SMALLEST one that works.

    🔴 VÌ SAO KHÔNG NHÉT MỌI THAM SỐ VÀO. Bản trước dựng ví dụ từ **mọi** thuộc
       tính có `examples`, và với `image.ltt` nó cho ra một thân tự mâu thuẫn:

           "mode": "t2i",
           "image_key": "upl_from_POST_/api/v1/uploads"

       Trong khi chính `description` của `image_key` nói *"Required for edit and
       subject; **ignored for t2i**"*. Tức ví dụ mẫu dạy khách gửi một trường mà
       chế độ đang chọn bỏ qua.

    ⛔ Một ví dụ tự mâu thuẫn tệ hơn không có ví dụ: nó **chạy được**, nên không
       ai phát hiện, và khách bê nguyên cấu trúc đó vào mã của họ.

    ⭐ Nên luật là: **bắt buộc, cộng những gì có `default`.** Tham số tuỳ chọn
       không có mặc định là tham số chỉ dùng trong một số ca — và ví dụ đầu tiên
       không phải chỗ để trình bày mọi ca. Bảng ngay dưới đã liệt kê đủ.

    ⚠️ Đây **không** phải chỗ sửa gốc. Gốc là `input_schema` chưa khai được điều
       kiện "trường này chỉ dùng khi mode=edit". Xem
       `docs/PUBLIC_API/QUY_CHUAN_TRANG_TAI_LIEU_API.md` §9.
    """
    import json

    payload = {}
    for param in params:
        if not param["required"] and param["default"] is None:
            continue
        if param["example"] is not None:
            payload[param["name"]] = param["example"]
        elif param["default"] is not None:
            payload[param["name"]] = param["default"]
        else:
            payload[param["name"]] = f"<{param['type']}>"
    body = json.dumps({"tool": tool.name, "input": payload},
                      ensure_ascii=False, indent=2)
    return (f'curl -X POST "$LTT_BASE_URL/api/v1/quotes" \\\n'
            f'  -H "Authorization: Bearer $LTT_API_KEY" \\\n'
            f'  -H "Content-Type: application/json" \\\n'
            f"  -d '{body}'")


def _usage_page(request: Request, db: Session, user, *, tool: str = "",
                key_id: str = "", status: str = "",
                error: str = "") -> HTMLResponse:
    from platform_core.public_api import budgets as budget_mod
    from platform_core.public_api import request_log

    config = _public_api_config(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=30)
    lines = usage.usage_lines(db, user_id=user.id, since=window_start,
                              until=now, tool=tool, key_id=key_id, limit=50)
    # Biểu đồ 30 ngày (ảnh demo) — tái dùng đúng hàm chỉ-đọc của overview, cửa
    # sổ rộng hơn. None ⇒ template hiện trạng thái rỗng, không vẽ đường phẳng.
    chart30 = _chart_points(
        request_log.daily(db, user_id=user.id,
                          since=now - timedelta(days=29), until=now),
        width=660, height=170)
    # Vòng phân bổ theo công cụ (ảnh demo: "Phân bổ theo công cụ") — dữ liệu
    # thật từ sổ credit, gom theo tool. None ⇒ trạng thái rỗng.
    tool_rows = usage.by_tool(db, user_id=user.id,
                              since=now - timedelta(days=29), until=now)
    donut = _donut(tool_rows)
    # Hai chỉ số 30 ngày cho thẻ (ảnh demo có 4 thẻ): credit đã tiêu + số request.
    used_30d = sum(int(r["credit"]) for r in tool_rows)
    req_30d = request_log.counts(db, user_id=user.id,
                                 since=now - timedelta(days=30))["requests"]
    if status:
        lines = [line for line in lines if line.get("status") == status]

    names = {project.id: project.name
             for project in projects.list_for(db, user_id=user.id,
                                              include_archived=True)}
    rows = []
    for budget in budget_mod.list_for(db, user_id=user.id):
        state = budget_mod.status(db, budget)
        rows.append({
            "budget": budget, "spent": state["spent"],
            "amount": state["amount"], "percent": state["percent"],
            "scope_label": (names.get(budget.project_id, budget.project_id)
                            if budget.scope == budget_mod.SCOPE_PROJECT
                            else _t("cả tài khoản")),
        })

    return _render(
        request, db, user, "usage", "dev_usage.html", error=error,
        budgets=rows, lines=lines, chart=chart30, donut=donut,
        used_30d=used_30d, req_30d=req_30d,
        tools=[item.name for item in build_catalog(config)],
        keys=[{"key_id": key.key_id, "name": key.name}
              for key in devkeys.list_for_user(db, user.id)],
        statuses=["queued", "running", "succeeded", "failed", "cancelled"],
        filters={"tool": tool, "key_id": key_id, "status": status},
        **_projects_context(db, user),
        **_usage_context(db, user, config))


#: Session slot for a value that must be shown once and never persisted.
SECRET_ONCE_KEY = "webhook_secret_once"

VERIFY_SNIPPET = """import hmac, hashlib, time

def verify(secret, headers, body):                 # body = raw bytes
    stamp = int(headers["X-LTT-Timestamp"])
    if abs(time.time() - stamp) > 300:             # replay window
        return False
    signed = f"{stamp}.{headers['X-LTT-Event-Id']}.".encode() + body
    expected = "v1=" + hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    # The header may carry several signatures during a secret rotation.
    return any(hmac.compare_digest(expected, part.strip())
               for part in headers["X-LTT-Signature"].split(","))"""


def _goc_url(request: Request) -> str:
    """Gốc URL công khai, để lệnh mẫu chép ra là chạy được ngay.

    Viết cứng `https://app.lttstudios.com` thì lệnh sẽ SAI trên mọi cài đặt
    khác — và nó sai một cách im lặng: khách chép, chạy, nhận lỗi mạng, và
    không nghĩ rằng chính trang hướng dẫn đưa nhầm địa chỉ.
    """
    goc = os.environ.get("LTT_BASE_URL", "").strip().rstrip("/")
    if goc:
        return goc
    return str(request.base_url).rstrip("/")


def _kiem_cau_hinh_khoa() -> str:
    """Chuỗi lỗi cho khách nếu MÁY CHỦ chưa cấu hình được để cấp khoá.

    Trả chuỗi rỗng khi mọi thứ ổn.

    `current_pepper()` là hàm **chỉ** kiểm cấu hình máy chủ, nên gọi riêng nó
    tách được hai loại lỗi mà không cần khớp chuỗi: hỏng ở đây là lỗi của ta,
    hỏng ở `devkeys.issue()` là thứ khách sửa được.

    Khách nhận một câu nói rõ đây không phải lỗi của họ và họ không sửa được;
    tên biến môi trường đi vào log. Một khách đọc `LTT_API_KEY_PEPPER is missing`
    học được cấu hình nội bộ của ta và vẫn không làm gì được.
    """
    from platform_core.public_api import keys as _keys

    try:
        _keys.current_pepper()
    except Exception as exc:  # noqa: BLE001 — mọi lỗi ở đây đều là lỗi của ta
        _log.error("developer keys: may chu chua cau hinh cap khoa: %s", exc)
        return _t("Máy chủ chưa cấu hình xong để cấp khóa. Đây là lỗi phía "
                  "chúng tôi, không phải của bạn — chúng tôi đã được báo. "
                  "Vui lòng thử lại sau.")
    return ""


def _split_ips(value: str) -> list:
    """Accept commas, newlines or spaces — people paste all three."""
    raw = str(value or "").replace("\n", ",").replace(" ", ",")
    return [part.strip() for part in raw.split(",") if part.strip()]


def _expiry_from_days(value: str):
    """Turn "90" into a timestamp, or nothing at all.

    A key with no expiry is the default because most integrations run for years
    and a surprise expiry at 3am is worse than a long-lived key that can be
    revoked in one click. An expiry is offered because a key handed to a
    contractor should stop working on its own.
    """
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        days = int(raw)
    except ValueError as exc:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải là một số nguyên.")) from exc
    if days <= 0:
        raise devkeys.DeveloperKeyError(
            _t("Số ngày hết hạn phải lớn hơn 0."))
    return datetime.now(timezone.utc) + timedelta(days=days)
