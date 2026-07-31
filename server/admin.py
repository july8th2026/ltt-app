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
from platform_core.models import (AppAccess, CreditEntry, Job, PlatformInfo,
                                  Session as DbSession, User)

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
        msg_html = ""
        user_id = ""
        if request.method == "POST":
            form = await request.form()
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
  <label>User ID (UUID — lấy ở mục Người dùng)</label>
  <input name="user_id" value="{escape(user_id)}" required placeholder="vd 3f2a...">
  <label>Số credit (dương = cộng, âm = trừ)</label>
  <input name="amount" type="number" required placeholder="vd 100">
  <label>Ghi chú</label>
  <textarea name="note" rows="2" placeholder="vd khuyến mãi / bồi thường"></textarea>
  <button type="submit">Cấp credit</button>
</form></body></html>"""
        return HTMLResponse(body)


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
    admin.add_view(AppAccessAdmin)
    admin.add_view(JobAdmin)
    admin.add_view(SessionAdmin)
    admin.add_view(PlatformInfoAdmin)
    return True
