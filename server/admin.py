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
        body = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Cấp credit — Quản trị</title>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:40px auto;padding:0 16px;}}
label{{display:block;margin:12px 0 4px;font-size:14px;}}
input,textarea{{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font-size:14px;}}
button{{margin-top:16px;padding:9px 16px;border:0;border-radius:6px;background:#3b6ef2;color:#fff;cursor:pointer;}}
a{{color:#3b6ef2;}}</style></head><body>
<p><a href="/admin">&larr; Về trang quản trị</a></p>
<h2>Cấp / điều chỉnh credit</h2>
<p style="color:#555;font-size:13px;">Ghi một bút toán <code>grant</code> mới (số âm để trừ).
Sổ credit là append-only — không sửa/xoá bút toán cũ.</p>
{msg_html}
<form method="post">
  <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
  <label>User ID (UUID — lấy ở mục Người dùng)</label>
  <input name="user_id" value="{escape(user_id)}" required placeholder="vd 3f2a...">
  <label>Số credit (dương = cộng, âm = trừ)</label>
  <input name="amount" type="number" required placeholder="vd 100">
  <label>Ghi chú</label>
  <textarea name="note" rows="2" placeholder="vd khuyến mãi / bồi thường"></textarea>
  <button type="submit">Cấp credit</button>
</form></body></html>"""
        return HTMLResponse(body, status_code=status)


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
        cat_boxes = "".join(
            f'<label style="font-weight:400"><input type="checkbox" name="categories" '
            f'value="{c}"> {c}</label> '
            for c in (APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE, APIKEY_CAT_VIDEO))
        body = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Thêm API key</title>
<style>body{{font-family:system-ui,sans-serif;max-width:620px;margin:40px auto;padding:0 16px;}}
label{{display:block;margin:12px 0 4px;font-size:14px;}}
input,select,textarea{{width:100%;padding:8px;border:1px solid #ccc;border-radius:6px;font-size:14px;}}
button{{margin-top:16px;padding:9px 16px;border:0;border-radius:6px;background:#3b6ef2;color:#fff;cursor:pointer;}}
a{{color:#3b6ef2;}}</style></head><body>
<p><a href="/admin">&larr; Về quản trị</a> &nbsp;|&nbsp; <a href="/admin/api-models">Xem Models</a></p>
<h2>Thêm API key</h2>{msg}
<form method="post">
  <input type="hidden" name="csrf_token" value="{escape(token)}">
  <label>Provider</label><select name="provider" required>{opts}</select>
  <label>Tên gợi nhớ</label><input name="name" placeholder="vd gemini-chinh">
  <label>Credential (khoá THÔ — sẽ mã hoá)</label>
  <input name="credential" type="password" required autocomplete="off">
  <label>Category (năng lực)</label><div>{cat_boxes}</div>
  <label>base_url (để trống = mặc định provider)</label><input name="base_url">
  <label>supported_models (phân cách dấu phẩy, để trống = mọi model)</label>
  <input name="supported_models" placeholder="gemini-2.5-flash-image, ...">
  <label>default_model</label><input name="default_model">
  <label>priority (cao = ưu tiên)</label><input name="priority" type="number" value="100">
  <button type="submit">Lưu API key</button>
</form></body></html>"""
        return HTMLResponse(body, status_code=status)


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
        color = "#1a7f37" if code == 200 else "#b91c1c"
        return HTMLResponse(
            f'<p><a href="/admin/api-key/list">&larr; APIKEYS</a></p>'
            f'<h3>Test key {escape(key.key_preview)} ({escape(key.provider)})</h3>'
            f'<p style="color:{color};">HTTP {code} — {escape(str(detail))}</p>')

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
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/api-key/list", status_code=303)


class ModelsView(BaseView):
    """Danh sách Provider + Model (registry, chỉ đọc) — H8."""

    name = "Models"
    icon = "fa-solid fa-cubes"

    @expose("/api-models", methods=["GET"])
    async def models(self, request: Request):
        from platform_core import providers
        rows = ""
        for p in providers.list_all():
            ms = ", ".join(
                f'{escape(m.id)}{"" if m.is_active else " (Soon)"}' for m in p.models
            ) or "<i>chưa khai model — key nhận mọi model provider</i>"
            rows += (f"<tr><td><b>{escape(p.id)}</b></td>"
                     f"<td>{escape(p.auth_style)}</td>"
                     f"<td>{escape(', '.join(p.categories))}</td>"
                     f"<td>{ms}</td>"
                     f"<td>{'async' if p.async_poll else 'sync'}</td></tr>")
        body = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<title>Models</title><style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:30px auto;padding:0 16px;}}
table{{border-collapse:collapse;width:100%;font-size:13px;}}td,th{{border:1px solid #ddd;padding:6px 8px;text-align:left;vertical-align:top;}}
a{{color:#3b6ef2;}}</style></head><body>
<p><a href="/admin">&larr; Về quản trị</a> &nbsp;|&nbsp; <a href="/admin/api-key-them">+ Thêm API key</a></p>
<h2>Provider &amp; Models (registry)</h2>
<p style="color:#555;font-size:13px;">Nguồn: <code>platform_core/providers.py</code>.
Thêm provider/model = sửa file này (Pha 1). Làm-mới-model tự động: Pha 2.</p>
<table><tr><th>Provider</th><th>Auth</th><th>Category</th><th>Models</th><th>Kiểu</th></tr>
{rows}</table></body></html>"""
        return HTMLResponse(body)


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

    admin = Admin(
        app,
        engine,
        title="LTT AI Studio — Quản trị",
        authentication_backend=AdminAuth(secret_key=session_secret),
    )
    admin.add_view(UserAdmin)
    admin.add_view(CreditEntryAdmin)
    admin.add_view(GrantCreditView)
    admin.add_view(ApiKeyAdmin)
    admin.add_view(AddApiKeyView)
    admin.add_view(ApiKeyActionView)
    admin.add_view(ModelsView)
    admin.add_view(AppAccessAdmin)
    admin.add_view(JobAdmin)
    admin.add_view(SessionAdmin)
    admin.add_view(PlatformInfoAdmin)
    return True
