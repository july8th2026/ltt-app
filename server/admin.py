"""
server/admin.py — trang quản trị (H3-admin, Q15) dựng bằng sqladmin.

Vì sao sqladmin: sinh trang xem/lọc/sửa trực tiếp từ model SQLAlchemy. Trang
quản trị là mặt admin, không phải mặt khách, không đáng viết tay từng trang.

Ba nguyên tắc bắt buộc ở đây:

1. **Chỉ admin vào được.** `AdminAuth` đọc CHÍNH phiên đăng nhập của nền tảng
   (cùng cookie "session" nhờ dùng chung `session_secret`): admin-env
   (`session["user"]`) hoặc user CSDL có `role == "admin"` (`session["sid"]`).
   Không phải admin → đá về `/login`. Không có form đăng nhập riêng.

2. **Sổ credit APPEND-ONLY (H3).** `CreditEntryAdmin` KHOÁ create/edit/delete —
   chỉ xem. Muốn cộng/trừ thì qua `GrantCreditView` (gọi `credit.cap_tay`, ghi
   một bút toán `grant` mới), không bao giờ sửa/xoá bút toán cũ.

3. **Không phá dữ liệu vận hành.** Job không cho sửa tay (worker quản); user
   không cho xoá (giữ dấu vết + sổ credit). Phiên cho xoá = thu hồi đăng nhập.
"""
from __future__ import annotations

import logging

from markupsafe import escape
from sqladmin import Admin, BaseView, ModelView, expose
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from platform_core.db import get_engine, get_session
from platform_core.models import (ApiKey, AppAccess, CreditEntry, Job,
                                  PlatformInfo, Session as DbSession, User)

_log = logging.getLogger(__name__)


def _is_admin(request: Request) -> bool:
    """True nếu phiên hiện tại là admin (admin-env HOẶC user CSDL role=admin)."""
    try:
        session = request.session
    except Exception:
        return False

    ss = getattr(request.app.state, "server_settings", None)
    admin_username = getattr(ss, "admin_username", "admin") if ss else "admin"
    if session.get("user") and session.get("user") == admin_username:
        return True

    sid = session.get("sid")
    if not sid:
        return False
    try:
        from platform_core.users import lay_user_tu_phien
        gen = get_session()
        db = next(gen)
        try:
            u = lay_user_tu_phien(db, sid)
            return bool(u and u.role == "admin")
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return False


class AdminAuth(AuthenticationBackend):
    """Cổng đăng nhập của sqladmin — tái dùng phiên nền tảng, không form riêng."""

    async def login(self, request: Request) -> bool:
        # Không dùng form đăng nhập của sqladmin; đăng nhập ở /login của nền tảng.
        return False

    async def logout(self, request: Request) -> bool:
        return True

    async def authenticate(self, request: Request):
        if _is_admin(request):
            return True
        # Chưa phải admin → đá về trang đăng nhập nền tảng.
        return RedirectResponse("/login", status_code=303)


# ── Vỏ quản trị DARK dùng chung (UX-1) — thay các trang trắng tự viết ─────────
_ADM_NAV = [
    ("/", "LT", "Trang chủ", "home"),
    ("__grp__", "", "Quản trị", ""),
    ("/admin/user/list", "ND", "Người dùng", "user"),
    ("/admin/credit-entry/list", "CR", "Sổ credit", "credit"),
    ("/admin/grant-credit", "+C", "Cấp credit", "grant"),
    ("/admin/apikeys", "AK", "APIKEYS", "apikeys"),
    ("/admin/job/list", "JB", "Job", "job"),
    ("/admin/session/list", "SS", "Phiên", "session"),
    ("__grp__", "", "Thanh toán", ""),
    ("/admin/doanh-thu", "DT", "Doanh thu", "revenue"),
    ("/admin/goi", "GN", "Gói nạp", "goi"),
    ("/admin/don", "DH", "Đơn hàng", "don"),
    ("__grp__", "", "Hệ thống", ""),
    ("/status", "HT", "Tình trạng", "status"),
]

_PROVCOL = {"gemini": ("#4285F4", "G"), "apiai": ("#16a34a", "AI"),
            "cheapkeyai": ("#0ea5e9", "CK"), "byteplus": ("#7c3aed", "BP"),
            "plenx": ("#db2777", "PX")}
_CAT_ICON = {"model_control": ("🧭", "m"), "chat": ("💬", ""),
             "image": ("🖼️", "i"), "video": ("🎬", "v")}
_STATUS = {"active": ("b-ok", "hoạt động"), "cooldown": ("b-warn", "nghỉ (cooldown)"),
           "exhausted": ("b-warn", "hết quota"), "error": ("b-err", "lỗi"),
           "disabled": ("b-err", "vô hiệu")}


def _asset_ver() -> str:
    """Hash nội dung ltt.css để cache-bust (Đợt R). Lazy import tránh vòng import."""
    try:
        from server.templating import ASSET_VER
        return ASSET_VER
    except Exception:
        return "0"


def _admin_shell(title: str, active: str, body: str) -> str:
    nav = ""
    mobile_nav = ""
    for href, ic, label, key in _ADM_NAV:
        if href == "__grp__":
            nav += f'<div class="grp">{escape(label)}</div>'
        else:
            cls = "on" if key == active else ""
            current = ' aria-current="page"' if key == active else ""
            nav += (f'<a class="{cls}" href="{href}"{current}><span class="ic">{ic}</span> '
                    f'{escape(label)}</a>')
            mobile_nav += (f'<a class="{cls}" href="{href}"{current}>'
                           f'{escape(label)}</a>')
    return (f'<!doctype html><html lang="vi"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">'
            f'<link rel="stylesheet" href="/static/ltt.css?v={_asset_ver()}">'
            f'<title>{escape(title)} — Quản trị</title></head><body>'
            f'<a class="skip-link" href="#admin-content">Bỏ qua điều hướng</a>'
            f'<div class="adm"><aside class="adm-side" aria-label="Điều hướng quản trị">'
            f'<div class="adm-brand"><div class="mark">LTT</div>'
            f'<div><b>LTT AI Studio</b><small>quản trị</small></div></div>'
            f'<nav class="adm-nav" aria-label="Các khu vực quản trị">{nav}</nav>'
            f'<div class="adm-sidefoot"><span class="status-live"></span>Hệ thống vận hành</div></aside>'
            f'<main class="adm-main" id="admin-content">'
            f'<header class="adm-mobilebar"><a class="adm-mobilebrand" href="/admin/">'
            f'<span class="mark">LTT</span><span>Quản trị</span></a>'
            f'<details class="adm-mobilemenu"><summary aria-label="Mở điều hướng">Menu</summary>'
            f'<nav aria-label="Điều hướng mobile">{mobile_nav}</nav></details></header>'
            f'{body}</main></div></body></html>')


def _prov_dot(provider: str) -> str:
    col, ab = _PROVCOL.get(provider, ("#555a66", (provider or "?")[:2].upper()))
    return f'<span class="provdot" style="background:{col}">{escape(ab)}</span>'


def _cat_chips(cats) -> str:
    out = []
    for c in (cats or []):
        ic, cls = _CAT_ICON.get(c, ("•", ""))
        out.append(f'<span class="chip {cls}">{ic}</span>')
    return " ".join(out)


def _status_badge(key) -> str:
    if not key.enabled:
        return '<span class="badge b-grey"><span class="dot"></span>đã tắt</span>'
    cls, lbl = _STATUS.get(key.status, ("b-grey", key.status))
    return f'<span class="badge {cls}"><span class="dot"></span>{escape(lbl)}</span>'


def _health_bar(h: int) -> str:
    col = "var(--ok)" if h >= 80 else "var(--warn)" if h >= 50 else "var(--err)"
    w = max(0, min(100, int(h)))
    return (f'<span class="health"><span style="width:{w}%;background:{col}"></span></span> '
            f'<span class="tnum muted" style="font-size:11px">{h}</span>')


class ApiKeysConsole(BaseView):
    """Console APIKEYS custom dark (UX-1) — bề mặt chính quản khoá API."""

    name = "APIKEYS"
    icon = "fa-solid fa-key"

    @expose("/apikeys", methods=["GET"])
    async def console(self, request: Request):
        from platform_core import api_keys, api_pool, providers
        from server.auth.csrf import issue_csrf_token
        _co_refresh = {p.id for p in providers.list_all() if p.list_models_path}

        cat = request.query_params.get("cat", "all")
        gen = get_session(); db = next(gen)
        try:
            keys = api_keys.liet_ke(db)
        finally:
            try: next(gen)
            except StopIteration: pass
        token = issue_csrf_token(request)

        cnt = {"all": len(keys)}
        for c in ("model_control", "chat", "image", "video"):
            cnt[c] = sum(1 for k in keys if c in (k.categories or []))
        shown = keys if cat == "all" else [k for k in keys if cat in (k.categories or [])]

        def tab(c, label):
            on = "on" if cat == c else ""
            return (f'<a class="{on}" href="/admin/apikeys?cat={c}">{label} '
                    f'<span class="n">{cnt.get(c, 0)}</span></a>')
        tabs = (tab("all", "Tất cả") + tab("model_control", "🧭 Điều khiển model")
                + tab("chat", "💬 Chat") + tab("image", "🖼️ Ảnh")
                + tab("video", "🎬 Video"))

        def act_form(k, op, label):
            return (f'<form method="post" action="/admin/api-key-action" style="display:inline">'
                    f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                    f'<input type="hidden" name="id" value="{escape(k.id)}">'
                    f'<input type="hidden" name="op" value="{op}">'
                    f'<button class="btn ghost sm">{label}</button></form>')

        rows = ""
        for k in shown:
            toggle = act_form(k, "enable", "Bật") if not k.enabled else act_form(k, "disable", "Tắt")
            refresh = act_form(k, "refresh", "Làm mới") if k.provider in _co_refresh else ""
            _rpm = api_pool.rpm(k)
            cap = f'/{k.rpm_limit}' if k.rpm_limit else ''
            rows += (
                f'<tr><td><span class="prov">{_prov_dot(k.provider)}{escape(k.provider)}</span></td>'
                f'<td>{escape(k.name or "")}</td>'
                f'<td class="mono muted">{escape(k.key_preview or "")}</td>'
                f'<td>{_cat_chips(k.categories)}</td>'
                f'<td>{_status_badge(k)}</td>'
                f'<td>{_health_bar(k.health_score)}</td>'
                f'<td class="tnum">{k.priority}</td>'
                f'<td class="tnum muted" style="font-size:12px">{_rpm}{cap}/min<br>{k.total_tokens} tok</td>'
                f'<td><div class="rowactions">'
                f'<a class="btn ghost sm" href="/admin/api-key-test?id={escape(k.id)}">Test</a>'
                f'{refresh}{toggle}{act_form(k, "reset", "Reset")}</div></td></tr>')
        if not shown:
            rows = ('<tr><td colspan="9" class="muted" style="padding:26px;text-align:center">'
                    'Chưa có key nào ở mục này. Bấm “＋ Thêm key”.</td></tr>')

        active_cnt = sum(1 for k in keys if k.enabled and k.status == "active")
        body = (
            f'<div class="adm-top"><span class="eyebrow">Nguồn API của nền tảng</span>'
            f'<span class="pill"><span class="dot" style="background:var(--ok);width:7px;'
            f'height:7px;border-radius:50%"></span> {active_cnt}/{len(keys)} key hoạt động</span></div>'
            f'<div class="adm-content"><div class="pagehead"><div><h1>APIKEYS</h1>'
            f'<p>Kho khoá API tập trung — app xin khoá theo provider &amp; loại. '
            f'Credential luôn mã hoá; chỉ hiện 4 số cuối.</p></div>'
            f'<div class="actions"><a class="btn ghost" href="/admin/api-models">🧩 Models</a>'
            f'<a class="btn" href="/admin/api-key-them">＋ Thêm key</a></div></div>'
            f'<div class="tabs">{tabs}</div>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Provider</th><th>Tên</th><th>Preview</th><th>Loại</th><th>Trạng thái</th>'
            f'<th>Health</th><th>Ưu tiên</th><th>Tải</th><th style="text-align:right">Thao tác</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("APIKEYS", "apikeys", body))


class UserAdmin(ModelView, model=User):
    name = "Người dùng"
    name_plural = "Người dùng"
    icon = "fa-solid fa-user"
    column_list = [User.email, User.display_name, User.role, User.is_active,
                   User.is_verified, User.created_at, User.last_login_at]
    column_searchable_list = [User.email, User.display_name]
    column_sortable_list = [User.email, User.created_at, User.last_login_at]
    column_default_sort = [(User.created_at, True)]
    # KHÔNG cho sửa email hay password_hash qua form (email là danh tính; mật
    # khẩu chỉ đổi qua luồng đổi-mật-khẩu đã băm đúng cách).
    form_columns = [User.display_name, User.role, User.is_active, User.is_verified]
    can_create = False   # user tạo qua đăng ký; tạo admin-trong-DB làm ở bước sau
    can_delete = False   # giữ dấu vết + sổ credit gắn user_id


class CreditEntryAdmin(ModelView, model=CreditEntry):
    name = "Bút toán credit"
    name_plural = "Sổ credit"
    icon = "fa-solid fa-coins"
    column_list = [CreditEntry.created_at, CreditEntry.user_id, CreditEntry.kind,
                   CreditEntry.delta, CreditEntry.job_id, CreditEntry.note]
    column_searchable_list = [CreditEntry.user_id, CreditEntry.kind, CreditEntry.job_id]
    column_sortable_list = [CreditEntry.created_at, CreditEntry.delta]
    column_default_sort = [(CreditEntry.created_at, True)]
    # SỔ APPEND-ONLY: chỉ xem. Cộng/trừ qua "Cấp credit" (ghi bút toán mới).
    can_create = False
    can_edit = False
    can_delete = False


class AppAccessAdmin(ModelView, model=AppAccess):
    name = "Quyền app"
    name_plural = "Quyền app"
    icon = "fa-solid fa-lock"
    column_list = [AppAccess.user_id, AppAccess.app_slug, AppAccess.level]
    column_searchable_list = [AppAccess.user_id, AppAccess.app_slug]
    # CRUD đầy đủ: chỉ lưu NGOẠI LỆ so với mặc định "mở" (Q25). Xoá dòng = về
    # mặc định mở. level hợp lệ: enabled / locked / hidden.
    form_columns = [AppAccess.user_id, AppAccess.app_slug, AppAccess.level]
    # level chỉ nhận enabled/locked/hidden — dropdown thay vì free-text để không
    # ghi giá trị rác (vd "superuser") làm phân quyền cư xử sai âm thầm (W1.3).
    form_choices = {
        "level": [("enabled", "enabled — mở"),
                  ("locked", "locked — khoá"),
                  ("hidden", "hidden — ẩn")],
    }


class JobAdmin(ModelView, model=Job):
    name = "Job"
    name_plural = "Job"
    icon = "fa-solid fa-list-check"
    column_list = [Job.created_at, Job.user_id, Job.app_slug, Job.job_type,
                   Job.status, Job.progress, Job.attempts]
    column_searchable_list = [Job.user_id, Job.app_slug, Job.status, Job.job_type]
    column_sortable_list = [Job.created_at, Job.status]
    column_default_sort = [(Job.created_at, True)]
    # Worker quản job; admin chỉ xem (sửa tay dễ làm sai kế toán credit).
    can_create = False
    can_edit = False
    can_delete = False


class SessionAdmin(ModelView, model=DbSession):
    name = "Phiên"
    name_plural = "Phiên đăng nhập"
    icon = "fa-solid fa-key"
    # KHÔNG hiển thị DbSession.id: nó CHÍNH LÀ token cookie phiên (thô, dùng làm
    # PK — users.py:tao_phien). Render nó ra trang admin = ai xem/chụp màn hình
    # trang này đều lấy được token sống → mạo danh không cần mật khẩu. Chỉ hiện
    # thông tin nhận dạng an toàn; xoá dòng vẫn thu hồi được phiên qua PK nội bộ.
    column_list = [DbSession.user_id, DbSession.created_at,
                   DbSession.expires_at, DbSession.ip, DbSession.user_agent]
    column_details_list = [DbSession.user_id, DbSession.created_at,
                           DbSession.expires_at, DbSession.ip,
                           DbSession.user_agent]
    column_searchable_list = [DbSession.user_id]
    column_default_sort = [(DbSession.created_at, True)]
    can_create = False
    can_edit = False
    can_delete = True   # xoá = thu hồi phiên đăng nhập đó


class PlatformInfoAdmin(ModelView, model=PlatformInfo):
    name = "Thông tin nền tảng"
    name_plural = "Nền tảng"
    icon = "fa-solid fa-circle-info"
    column_list = [PlatformInfo.id, PlatformInfo.app_version,
                   PlatformInfo.installed_at, PlatformInfo.note]
    can_create = False
    can_edit = False
    can_delete = False


class GrantCreditView(BaseView):
    """Cấp/điều chỉnh credit tay — ghi MỘT bút toán `grant` (append-only)."""

    name = "Cấp credit"
    icon = "fa-solid fa-hand-holding-dollar"

    @expose("/grant-credit", methods=["GET", "POST"])
    async def grant(self, request: Request):
        from server.auth.csrf import issue_csrf_token, verify_csrf_token

        msg_html = ""
        user_id = ""
        status = 200
        if request.method == "POST":
            form = await request.form()
            # CSRF: mutation ghi sổ credit PHẢI có token hợp lệ. Trước đây chỉ dựa
            # SameSite=Lax; thêm synchronizer token cho đồng nhất với route nền
            # tảng (W1.3) — chống bị lừa POST cấp credit.
            if not verify_csrf_token(request, (form.get("csrf_token") or "")):
                msg_html = ('<p style="color:#b91c1c;">Phiên hết hạn hoặc CSRF '
                            'không hợp lệ — tải lại trang rồi thử lại.</p>')
                status = 400
            else:
                user_id = (form.get("user_id") or "").strip()
                amount_raw = (form.get("amount") or "").strip()
                note = (form.get("note") or "").strip()
                try:
                    amount = int(amount_raw)
                    if amount == 0:
                        raise ValueError("Số credit phải khác 0.")
                    from platform_core.credit import cap_tay, so_du
                    gen = get_session()
                    db = next(gen)
                    try:
                        cap_tay(db, user_id, amount, by="admin", note=note)
                        db.commit()
                        bal = so_du(db, user_id)
                        msg_html = (f'<p style="color:#1a7f37;">Đã cấp '
                                    f'<b>{amount:+d}</b> credit cho '
                                    f'<code>{escape(user_id)}</code>. '
                                    f'Số dư mới: <b>{bal}</b>.</p>')
                    finally:
                        try:
                            next(gen)
                        except StopIteration:
                            pass
                except Exception as e:
                    msg_html = f'<p style="color:#b91c1c;">Lỗi: {escape(str(e))}</p>'
                    status = 400

        csrf_token = issue_csrf_token(request)
        body = f"""<div class="adm-content" style="max-width:600px">
<div class="pagehead"><div><h1>Cấp / điều chỉnh credit</h1>
<p>Ghi một bút toán <code>grant</code> mới (số âm để trừ). Sổ credit append-only.</p></div></div>
{msg_html}
<div class="ui-card"><form method="post">
  <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
  <div class="field"><label>User ID (UUID — lấy ở mục Người dùng)</label>
    <input class="inp mono" name="user_id" value="{escape(user_id)}" required placeholder="3f2a..."></div>
  <div class="field"><label>Số credit (dương = cộng, âm = trừ)</label>
    <input class="inp tnum" name="amount" type="number" required placeholder="100"></div>
  <div class="field"><label>Ghi chú</label>
    <input class="inp" name="note" placeholder="khuyến mãi / bồi thường"></div>
  <button class="btn" type="submit">Cấp credit</button>
</form></div></div>"""
        return HTMLResponse(_admin_shell("Cấp credit", "grant", body), status_code=status)


class ApiKeyAdmin(ModelView, model=ApiKey):
    name = "API key"
    name_plural = "APIKEYS"
    # sqladmin tự đặt identity = slugify(ApiKey) = "api-key" → URL /admin/api-key/...
    icon = "fa-solid fa-key"
    # TUYỆT ĐỐI không hiện credential_enc (secret). Chỉ preview 4 số cuối (H8).
    column_list = [ApiKey.provider, ApiKey.name, ApiKey.key_preview,
                   ApiKey.categories, ApiKey.status, ApiKey.enabled,
                   ApiKey.priority, ApiKey.health_score, ApiKey.last_used_at]
    column_details_list = [ApiKey.id, ApiKey.provider, ApiKey.name,
                           ApiKey.key_preview, ApiKey.categories, ApiKey.base_url,
                           ApiKey.supported_models, ApiKey.default_model,
                           ApiKey.status, ApiKey.enabled, ApiKey.priority,
                           ApiKey.health_score, ApiKey.error_count,
                           ApiKey.auth_error_count, ApiKey.cooldown_until,
                           ApiKey.last_used_at, ApiKey.last_error,
                           ApiKey.total_requests, ApiKey.total_success,
                           ApiKey.total_failed, ApiKey.created_at]
    column_searchable_list = [ApiKey.provider, ApiKey.name]
    column_default_sort = [(ApiKey.provider, False)]
    # Tạo key qua view riêng (mã hoá credential). Sửa: chỉ field an toàn, KHÔNG
    # cho sửa credential_enc thô (sẽ ghi plaintext vào cột mã hoá). Đổi credential
    # = tạo key mới rồi xoá key cũ.
    can_create = False
    form_columns = [ApiKey.name, ApiKey.base_url, ApiKey.default_model,
                    ApiKey.priority, ApiKey.enabled]
    can_delete = True


class AddApiKeyView(BaseView):
    """Thêm API key — nhập credential THÔ, view mã hoá trước khi lưu (H8)."""

    name = "Thêm API key"
    icon = "fa-solid fa-plus"

    @expose("/api-key-them", methods=["GET", "POST"])
    async def them(self, request: Request):
        from platform_core import api_keys, providers
        from platform_core.models import (APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE,
                                          APIKEY_CAT_MODEL, APIKEY_CAT_VIDEO)
        from server.auth.csrf import issue_csrf_token, verify_csrf_token

        msg = ""
        status = 200
        if request.method == "POST":
            form = await request.form()
            if not verify_csrf_token(request, (form.get("csrf_token") or "")):
                msg = '<p style="color:#b91c1c;">CSRF không hợp lệ — tải lại trang.</p>'
                status = 400
            else:
                cats = [c for c in form.getlist("categories")]
                sup = [m.strip() for m in (form.get("supported_models") or "").split(",") if m.strip()]
                gen = get_session(); db = next(gen)
                try:
                    api_keys.tao_key(
                        db, provider=(form.get("provider") or ""),
                        credential=(form.get("credential") or ""),
                        name=(form.get("name") or ""), categories=cats,
                        base_url=(form.get("base_url") or ""),
                        supported_models=sup,
                        default_model=(form.get("default_model") or ""),
                        priority=int(form.get("priority") or 100),
                    )
                    db.commit()
                    msg = '<p style="color:#1a7f37;">Đã thêm API key.</p>'
                except Exception as e:
                    db.rollback()
                    msg = f'<p style="color:#b91c1c;">Lỗi: {escape(str(e))}</p>'
                    status = 400
                finally:
                    try: next(gen)
                    except StopIteration: pass

        token = issue_csrf_token(request)
        opts = "".join(
            f'<option value="{escape(p.id)}">{escape(p.display_name)} '
            f'[{escape(p.auth_style)}]</option>' for p in providers.list_all())
        _catlbl = {APIKEY_CAT_MODEL: "🧭 Điều khiển model", APIKEY_CAT_CHAT: "💬 Chat",
                   APIKEY_CAT_IMAGE: "🖼️ Ảnh", APIKEY_CAT_VIDEO: "🎬 Video"}
        cat_boxes = "".join(
            f'<label><input type="checkbox" name="categories" value="{c}"> {_catlbl[c]}</label>'
            for c in (APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE, APIKEY_CAT_VIDEO))
        body = f"""<div class="adm-content" style="max-width:640px">
<div class="pagehead"><div><h1>Thêm API key</h1>
<p>Credential nhập vào sẽ được <b>mã hoá</b> trước khi lưu; chỉ 4 số cuối hiện lại.</p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; APIKEYS</a>
<a class="btn ghost" href="/admin/api-models">🧩 Models</a></div></div>
{msg}
<div class="ui-card"><form method="post">
  <input type="hidden" name="csrf_token" value="{escape(token)}">
  <div class="field"><label>Provider</label><select class="inp" name="provider" required>{opts}</select></div>
  <div class="field"><label>Tên gợi nhớ</label><input class="inp" name="name" placeholder="gemini-chinh"></div>
  <div class="field"><label>Credential (khoá THÔ — sẽ mã hoá)</label>
    <input class="inp" name="credential" type="password" required autocomplete="off" placeholder="AIza••••••"></div>
  <div class="field"><label>Loại (năng lực)</label>
    <div class="catpick">{cat_boxes}</div></div>
  <div class="field"><label>base_url (để trống = mặc định provider)</label><input class="inp" name="base_url"></div>
  <div class="field"><label>supported_models (phẩy phân cách, trống = mọi model)</label>
    <input class="inp mono" name="supported_models" placeholder="gemini-2.5-flash-image, ..."></div>
  <div class="field"><label>default_model</label><input class="inp mono" name="default_model"></div>
  <div class="field"><label>priority (cao = ưu tiên)</label><input class="inp tnum" name="priority" type="number" value="100"></div>
  <button class="btn" type="submit">Lưu API key</button>
</form></div></div>
<style>.catpick{{display:flex;gap:8px;flex-wrap:wrap}}.catpick label{{display:flex;gap:6px;align-items:center;
padding:7px 11px;border:1px solid var(--line2);border-radius:8px;font-size:12.5px;cursor:pointer;color:var(--muted)}}
.catpick input{{accent-color:var(--accent)}}</style>"""
        return HTMLResponse(_admin_shell("Thêm API key", "apikeys", body), status_code=status)


class ApiKeyActionView(BaseView):
    """Hành động trên một key: test (probe sống) / bật / tắt / reset cooldown."""

    name = "Tác vụ key"
    icon = "fa-solid fa-bolt"
    # Ẩn khỏi menu trái (gọi qua nút/URL), tránh trùng lặp điều hướng.
    def is_visible(self, request: Request) -> bool:  # noqa: D401
        return False

    @expose("/api-key-test", methods=["GET"])
    async def test(self, request: Request):
        from platform_core import api_keys, providers
        key_id = request.query_params.get("id", "")
        gen = get_session(); db = next(gen)
        try:
            key = api_keys.lay_key_theo_id(db, key_id)
            if key is None:
                return HTMLResponse("Không thấy key.", status_code=404)
            prov = providers.get(key.provider)
            cred = api_keys.lay_credential(db, key)
            code, detail = _probe_key(prov, cred)
        finally:
            try: next(gen)
            except StopIteration: pass
        ok = code == 200
        badge = (f'<span class="badge {"b-ok" if ok else "b-err"}"><span class="dot"></span>'
                 f'HTTP {code}</span>')
        body = f"""<div class="adm-content" style="max-width:640px">
<div class="pagehead"><div><h1>Test key</h1>
<p>{_prov_dot(key.provider)} {escape(key.provider)} · <span class="mono">{escape(key.key_preview)}</span></p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; APIKEYS</a></div></div>
<div class="ui-card"><p style="margin:0 0 8px">{badge}</p>
<p class="muted mono" style="margin:0;font-size:12.5px;word-break:break-word">{escape(str(detail))}</p></div></div>"""
        return HTMLResponse(_admin_shell("Test key", "apikeys", body))

    @expose("/api-key-action", methods=["POST"])
    async def action(self, request: Request):
        from platform_core import api_keys
        from platform_core.models import APIKEY_ACTIVE
        from server.auth.csrf import verify_csrf_token
        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)
        key_id = form.get("id", ""); op = form.get("op", "")
        gen = get_session(); db = next(gen)
        try:
            key = api_keys.lay_key_theo_id(db, key_id)
            if key is None:
                return HTMLResponse("Không thấy key.", status_code=404)
            if op == "enable":
                key.enabled = True
            elif op == "disable":
                key.enabled = False
            elif op == "reset":
                key.status = APIKEY_ACTIVE; key.cooldown_until = None
                key.error_count = 0; key.auth_error_count = 0
            elif op == "refresh":
                # Làm mới model sống từ provider -> ghi supported_models (H8 Pha 2).
                from platform_core import providers, providers_live
                prov = providers.get(key.provider)
                try:
                    models = providers_live.lay_models_song(prov, api_keys.lay_credential(db, key))
                    api_keys.cap_nhat_supported_models(db, key, models)
                except providers_live.ProviderLiveError:
                    pass      # không làm mới được thì giữ nguyên, không làm sập trang
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/apikeys", status_code=303)


class ModelsView(BaseView):
    """Danh sách Provider + Model (registry, chỉ đọc) — H8."""

    name = "Models"
    icon = "fa-solid fa-cubes"

    @expose("/api-models", methods=["GET"])
    async def models(self, request: Request):
        from platform_core import providers
        rows = ""
        for p in providers.list_all():
            ms = " ".join(
                f'<span class="chip {"" if m.is_active else "m"}">{escape(m.id)}'
                f'{"" if m.is_active else " · Soon"}</span>' for m in p.models
            ) or '<span class="muted" style="font-size:12px">chưa khai model — key nhận mọi model</span>'
            kind = ('<span class="badge b-grey"><span class="dot"></span>async</span>'
                    if p.async_poll else '<span class="badge b-ok"><span class="dot"></span>sync</span>')
            refresh = (f'<a class="btn ghost sm" href="/admin/api-models-refresh?provider={escape(p.id)}">Làm mới</a>'
                       if p.list_models_path else '<span class="muted" style="font-size:12px">—</span>')
            rows += (f'<tr><td><span class="prov">{_prov_dot(p.id)}{escape(p.id)}</span></td>'
                     f'<td class="mono muted" style="font-size:12px">{escape(p.auth_style)}</td>'
                     f'<td>{escape(", ".join(p.categories))}</td>'
                     f'<td style="line-height:2">{ms}</td><td>{kind}</td><td>{refresh}</td></tr>')
        body = f"""<div class="adm-content">
<div class="pagehead"><div><h1>Provider &amp; Models</h1>
<p>Registry: <code>platform_core/providers.py</code>. Thêm provider/model = sửa file này.
“Làm mới” gọi endpoint sống của provider (dùng key ưu tiên nhất) để lấy model thật.</p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; APIKEYS</a>
<a class="btn" href="/admin/api-key-them">＋ Thêm key</a></div></div>
<div class="tablewrap"><table class="ui-table"><thead><tr>
<th>Provider</th><th>Auth</th><th>Category</th><th>Models (registry)</th><th>Kiểu</th><th>Sống</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>"""
        return HTMLResponse(_admin_shell("Models", "apikeys", body))

    @expose("/api-models-refresh", methods=["GET"])
    async def refresh(self, request: Request):
        """Lấy danh sách model SỐNG từ provider (dùng key active ưu tiên nhất) và
        hiện ra — chỉ đọc. Ghi vào key thì bấm “Làm mới” ở từng key (POST)."""
        from platform_core import api_keys, providers, providers_live
        from platform_core.models import APIKEY_ACTIVE
        prov_id = request.query_params.get("provider", "")
        prov = providers.get(prov_id)
        gen = get_session(); db = next(gen)
        try:
            candidates = [k for k in api_keys.liet_ke(db, provider=prov_id)
                          if k.enabled and k.status == APIKEY_ACTIVE]
            if prov is None:
                note, models = "Provider không tồn tại.", []
            elif not candidates:
                note, models = "Chưa có key active cho provider này.", []
            else:
                try:
                    models = providers_live.lay_models_song(
                        prov, api_keys.lay_credential(db, candidates[0]))
                    note = f"{len(models)} model sống (qua key {escape(candidates[0].key_preview)})."
                except providers_live.ProviderLiveError as e:
                    note, models = f"Lỗi làm mới: {escape(str(e))}", []
        finally:
            try: next(gen)
            except StopIteration: pass
        chips = " ".join(f'<span class="chip">{escape(m)}</span>' for m in models) \
            or '<span class="muted" style="font-size:12px">—</span>'
        body = f"""<div class="adm-content" style="max-width:760px">
<div class="pagehead"><div><h1>Model sống — {escape(prov_id)}</h1><p>{note}</p></div>
<div class="actions"><a class="btn ghost" href="/admin/api-models">&larr; Models</a></div></div>
<div class="ui-card" style="line-height:2.2">{chips}</div></div>"""
        return HTMLResponse(_admin_shell("Model sống", "apikeys", body))


def _probe_key(prov, credential: str):
    """Gọi thử endpoint liệt kê model để kiểm key còn sống. Trả (http_code, detail).
    Che credential khỏi thông báo lỗi."""
    from platform_core import providers as P
    if prov is None or not prov.list_models_path:
        return None, "provider không có endpoint để test (video async)"
    import httpx
    url = prov.base_url + prov.list_models_path
    try:
        if prov.auth_style == P.AUTH_QUERY_KEY:
            r = httpx.get(url, params={"key": credential}, timeout=10)
        elif prov.auth_style == P.AUTH_BEARER:
            r = httpx.get(url, headers={"Authorization": f"Bearer {credential}"}, timeout=10)
        else:
            r = httpx.get(url, headers={"X-API-Key": credential}, timeout=10)
        detail = "OK" if r.status_code == 200 else r.text[:200]
    except Exception as e:  # noqa: BLE001
        return 0, _che(str(e), credential)
    return r.status_code, _che(detail, credential)


def _che(msg: str, secret: str) -> str:
    if secret and len(secret) > 6:
        msg = msg.replace(secret, "***")
    return msg[:200]


# ── H9: quản trị thanh toán (gói nạp + đơn hàng + doanh thu) ──────────────────
_ORDER_ST = {"pending": ("b-warn", "chờ trả"), "paid": ("b-ok", "đã trả"),
             "expired": ("b-grey", "hết hạn"), "cancelled": ("b-grey", "huỷ"),
             "failed": ("b-err", "lỗi")}


def _vnd(n) -> str:
    return f"{int(n):,}đ"


def _order_badge(status: str) -> str:
    cls, lbl = _ORDER_ST.get(status, ("b-grey", status))
    return f'<span class="badge {cls}"><span class="dot"></span>{escape(lbl)}</span>'


class RevenueView(BaseView):
    """Bảng doanh thu (H9) — tổng VND đã thu, credit đã bán, số đơn."""

    name = "Doanh thu"
    icon = "fa-solid fa-chart-line"

    @expose("/doanh-thu", methods=["GET"])
    async def revenue(self, request: Request):
        from platform_core import billing
        gen = get_session(); db = next(gen)
        try:
            dt = billing.doanh_thu(db)
            gan_day = billing.liet_ke_don(db, status="paid", limit=10)
            rows = ""
            for o in gan_day:
                rows += (f'<tr><td class="mono">{o.order_code}</td>'
                         f'<td class="mono muted">{escape(o.user_id[:8])}</td>'
                         f'<td class="tnum">{_vnd(o.price_vnd)}</td>'
                         f'<td class="tnum">{o.credits:,}</td>'
                         f'<td class="muted" style="font-size:12px">{o.paid_at:%Y-%m-%d %H:%M}</td></tr>'
                         if o.paid_at else "")
        finally:
            try: next(gen)
            except StopIteration: pass
        cards = (
            f'<div class="grid" style="grid-template-columns:repeat(3,1fr);gap:14px">'
            f'<div class="ui-card"><div class="dim">Tổng đã thu</div>'
            f'<div style="font-size:26px;font-weight:700">{_vnd(dt["vnd"])}</div></div>'
            f'<div class="ui-card"><div class="dim">Credit đã bán</div>'
            f'<div style="font-size:26px;font-weight:700">{dt["credits"]:,}</div></div>'
            f'<div class="ui-card"><div class="dim">Đơn đã trả</div>'
            f'<div style="font-size:26px;font-weight:700">{dt["orders"]:,}</div></div></div>')
        body = (f'<div class="adm-content"><div class="pagehead"><div><h1>Doanh thu</h1>'
                f'<p>Chỉ tính đơn đã trả (đi qua sổ credit H3).</p></div>'
                f'<div class="actions"><a class="btn ghost" href="/admin/goi">💠 Gói nạp</a>'
                f'<a class="btn ghost" href="/admin/don">🧾 Đơn hàng</a></div></div>'
                f'{cards}<h2 style="margin:22px 0 10px">Đơn đã trả gần đây</h2>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>Mã đơn</th><th>User</th><th>Tiền</th><th>Credit</th><th>Trả lúc</th>'
                f'</tr></thead><tbody>{rows or "<tr><td colspan=5 class=muted style=padding:20px;text-align:center>Chưa có đơn nào.</td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Doanh thu", "revenue", body))


class PackagesView(BaseView):
    """Quản lý gói nạp (H9): thêm/sửa/bật-tắt/xoá. Giá/credit/bonus admin tự đặt."""

    name = "Gói nạp"
    icon = "fa-solid fa-box"

    @expose("/goi", methods=["GET", "POST"])
    async def packages(self, request: Request):
        from platform_core import billing_math
        from platform_core.models import CreditPackage
        from server.auth.csrf import issue_csrf_token, verify_csrf_token
        msg = ""; status = 200
        gen = get_session(); db = next(gen)
        try:
            if request.method == "POST":
                form = await request.form()
                if not verify_csrf_token(request, (form.get("csrf_token") or "")):
                    return HTMLResponse("CSRF", status_code=400)
                try:
                    name = (form.get("name") or "").strip()
                    price = int(form.get("price_vnd") or 0)
                    bonus = int(form.get("bonus_percent") or 0)
                    order = int(form.get("sort_order") or 100)
                    if price <= 0:
                        raise ValueError("Giá phải dương.")
                    if bonus < 0:
                        raise ValueError("Bonus không âm.")
                    base = billing_math.credits_base_tu_vnd(price)
                    pkg = CreditPackage(name=name or f"Gói {price:,}đ", price_vnd=price,
                                        credits_base=base, bonus_percent=bonus, sort_order=order)
                    db.add(pkg); db.commit()
                    msg = f'<div class="alert alert-ok">Đã thêm gói {escape(pkg.name)}.</div>'
                except Exception as e:  # noqa: BLE001
                    db.rollback()
                    msg = f'<div class="alert alert-err">Lỗi: {escape(str(e))}</div>'; status = 400
            token = issue_csrf_token(request)
            pkgs = db.execute(
                __import__("sqlalchemy").select(CreditPackage)
                .order_by(CreditPackage.sort_order, CreditPackage.price_vnd)
            ).scalars().all()
            rows = ""
            for p in pkgs:
                total = billing_math.tong_credits(p.credits_base, p.bonus_percent)
                on = ('<span class="badge b-ok"><span class="dot"></span>bật</span>' if p.active
                      else '<span class="badge b-grey"><span class="dot"></span>tắt</span>')
                def act(op, label):
                    return (f'<form method="post" action="/admin/goi/action" style="display:inline">'
                            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                            f'<input type="hidden" name="id" value="{escape(p.id)}">'
                            f'<input type="hidden" name="op" value="{op}">'
                            f'<button class="btn ghost sm">{label}</button></form>')
                rows += (f'<tr><td class="tnum">{p.sort_order}</td><td>{escape(p.name)}</td>'
                         f'<td class="tnum">{_vnd(p.price_vnd)}</td>'
                         f'<td class="tnum">{p.credits_base:,}</td>'
                         f'<td class="tnum">+{p.bonus_percent}%</td>'
                         f'<td class="tnum"><strong>{total:,}</strong></td><td>{on}</td>'
                         f'<td><div class="rowactions">'
                         f'{act("toggle", "Bật/Tắt")}{act("delete", "Xoá")}</div></td></tr>')
        finally:
            try: next(gen)
            except StopIteration: pass
        form_html = (
            f'<div class="ui-card" style="max-width:640px;margin-bottom:18px"><form method="post">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<div class="field"><label>Tên gói</label><input class="inp" name="name" placeholder="Gói 100k"></div>'
            f'<div class="field"><label>Giá (VNĐ)</label><input class="inp tnum" name="price_vnd" type="number" required placeholder="100000"></div>'
            f'<div class="field"><label>Bonus (%)</label><input class="inp tnum" name="bonus_percent" type="number" value="0"></div>'
            f'<div class="field"><label>Thứ tự hiện</label><input class="inp tnum" name="sort_order" type="number" value="100"></div>'
            f'<p class="dim" style="font-size:12px;margin:0 0 10px">Tỉ giá 1 credit = 100đ → credit gốc = giá // 100. Tổng = gốc + bonus%.</p>'
            f'<button class="btn">＋ Thêm gói</button></form></div>')
        body = (f'<div class="adm-content"><div class="pagehead"><div><h1>Gói nạp</h1>'
                f'<p>Khách thấy gói bật ở trang <code>/nap</code>. Đổi giá không ảnh hưởng đơn cũ.</p></div>'
                f'<div class="actions"><a class="btn ghost" href="/admin/doanh-thu">📈 Doanh thu</a>'
                f'<a class="btn ghost" href="/admin/don">🧾 Đơn hàng</a></div></div>{msg}{form_html}'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>#</th><th>Tên</th><th>Giá</th><th>Gốc</th><th>Bonus</th><th>Tổng</th>'
                f'<th>Trạng thái</th><th style="text-align:right">Thao tác</th></tr></thead>'
                f'<tbody>{rows or "<tr><td colspan=8 class=muted style=padding:22px;text-align:center>Chưa có gói. Thêm ở trên.</td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Gói nạp", "goi", body), status_code=status)

    @expose("/goi/action", methods=["POST"])
    async def package_action(self, request: Request):
        from platform_core.models import CreditPackage
        from server.auth.csrf import verify_csrf_token
        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)
        pid = form.get("id", ""); op = form.get("op", "")
        gen = get_session(); db = next(gen)
        try:
            p = db.get(CreditPackage, pid)
            if p is not None:
                if op == "toggle":
                    p.active = not p.active
                elif op == "delete":
                    db.delete(p)
                db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/goi", status_code=303)


class OrdersView(BaseView):
    """Đơn hàng nạp (H9): lọc theo trạng thái + xác nhận trả tay (dự phòng)."""

    name = "Đơn hàng"
    icon = "fa-solid fa-receipt"

    @expose("/don", methods=["GET"])
    async def orders(self, request: Request):
        from platform_core import billing
        from server.auth.csrf import issue_csrf_token
        st = request.query_params.get("st", "all")
        gen = get_session(); db = next(gen)
        try:
            allrows = billing.liet_ke_don(db, limit=300)
            token = issue_csrf_token(request)
            cnt = {"all": len(allrows)}
            for s in ("pending", "paid", "expired", "cancelled", "failed"):
                cnt[s] = sum(1 for o in allrows if o.status == s)
            shown = allrows if st == "all" else [o for o in allrows if o.status == st]
            rows = ""
            for o in shown:
                markpaid = ""
                if o.status == "pending":
                    markpaid = (f'<form method="post" action="/admin/don/action" style="display:inline">'
                                f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                                f'<input type="hidden" name="order_code" value="{o.order_code}">'
                                f'<button class="btn ghost sm">Đã trả</button></form>')
                rows += (f'<tr><td class="mono">{o.order_code}</td>'
                         f'<td class="mono muted">{escape(o.user_id[:8])}</td>'
                         f'<td class="tnum">{_vnd(o.price_vnd)}</td>'
                         f'<td class="tnum">{o.credits:,}{(" +%d%%" % o.bonus_percent) if o.bonus_percent else ""}</td>'
                         f'<td>{_order_badge(o.status)}</td>'
                         f'<td class="muted" style="font-size:12px">{escape(o.gateway or "-")}</td>'
                         f'<td class="muted" style="font-size:12px">{o.created_at:%m-%d %H:%M}</td>'
                         f'<td><div class="rowactions">{markpaid}</div></td></tr>')
        finally:
            try: next(gen)
            except StopIteration: pass
        def tab(s, label):
            cls = "on" if st == s else ""
            return f'<a class="{cls}" href="/admin/don?st={s}">{label} <span class="n">{cnt.get(s,0)}</span></a>'
        tabs = (tab("all", "Tất cả") + tab("pending", "Chờ trả") + tab("paid", "Đã trả")
                + tab("expired", "Hết hạn") + tab("cancelled", "Huỷ") + tab("failed", "Lỗi"))
        body = (f'<div class="adm-content"><div class="pagehead"><div><h1>Đơn hàng</h1>'
                f'<p>“Đã trả” = xác nhận tay khi webhook lỗi (vẫn idempotent, cộng credit đúng một lần).</p></div>'
                f'<div class="actions"><a class="btn ghost" href="/admin/doanh-thu">📈 Doanh thu</a>'
                f'<a class="btn ghost" href="/admin/goi">💠 Gói nạp</a></div></div>'
                f'<div class="tabs">{tabs}</div>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>Mã đơn</th><th>User</th><th>Tiền</th><th>Credit</th><th>Trạng thái</th>'
                f'<th>Cổng</th><th>Tạo lúc</th><th style="text-align:right">Thao tác</th></tr></thead>'
                f'<tbody>{rows or "<tr><td colspan=8 class=muted style=padding:22px;text-align:center>Chưa có đơn.</td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Đơn hàng", "don", body))

    @expose("/don/action", methods=["POST"])
    async def order_action(self, request: Request):
        from platform_core import billing
        from server.auth.csrf import verify_csrf_token
        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)
        try:
            code = int(form.get("order_code") or 0)
        except ValueError:
            return RedirectResponse("/admin/don", status_code=303)
        gen = get_session(); db = next(gen)
        try:
            billing.ghi_nhan_tra(db, code, by="admin")   # idempotent
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/don", status_code=303)


def setup_admin(app, *, session_secret: str) -> bool:
    """Gắn trang quản trị vào app. Trả True nếu gắn được.

    Bọc phòng thủ: khi chưa cấu hình CSDL (nhiều test không dựng PostgreSQL),
    `get_engine()` ném lỗi — khi đó BỎ QUA admin thay vì làm hỏng cả app. Trang
    quản trị chỉ có ý nghĩa khi có CSDL.
    """
    try:
        engine = get_engine()
    except Exception as exc:
        _log.info("Bỏ qua trang quản trị (chưa có CSDL): %s", type(exc).__name__)
        return False

    import os as _os
    _adm_tpl = _os.path.join(_os.path.dirname(__file__), "admin_templates")
    admin = Admin(
        app,
        engine,
        title="LTT AI Studio — Quản trị",
        authentication_backend=AdminAuth(secret_key=session_secret),
        templates_dir=_adm_tpl,   # override sqladmin/base.html -> theme dark (UX-1)
    )
    admin.add_view(UserAdmin)
    admin.add_view(CreditEntryAdmin)
    admin.add_view(GrantCreditView)
    admin.add_view(ApiKeysConsole)
    admin.add_view(ApiKeyAdmin)
    admin.add_view(AddApiKeyView)
    admin.add_view(ApiKeyActionView)
    admin.add_view(ModelsView)
    admin.add_view(AppAccessAdmin)
    admin.add_view(JobAdmin)
    admin.add_view(SessionAdmin)
    admin.add_view(PlatformInfoAdmin)
    admin.add_view(RevenueView)
    admin.add_view(PackagesView)
    admin.add_view(OrdersView)
    return True
