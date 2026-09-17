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

import json
from urllib.parse import quote_plus
import logging

from markupsafe import Markup, escape
from datetime import datetime
from sqladmin import Admin, BaseView, ModelView, expose
from sqladmin.authentication import AuthenticationBackend, login_required as _login_required
from sqladmin.formatters import BASE_FORMATTERS

from server.routes.admin._chung import (
    AnTrongMenuSqlAdmin as _AnTrongMenuSqlAdmin)
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from platform_core.db import get_engine, get_session
from platform_core.models import (ApiKey, AppAccess, CreditEntry, Job,
                                  NhatKyAdmin, PlatformInfo,
                                  Session as DbSession, User)

_log = logging.getLogger(__name__)
_DINH_DANG_SQLADMIN: dict = BASE_FORMATTERS  # Golden UI C3: ngày giờ list/details dd/mm/yyyy HH:MM, không ISO kèm micro giây
_DINH_DANG_SQLADMIN[datetime] = lambda v: v.strftime("%d/%m/%Y %H:%M")


def _is_admin(request: Request) -> bool:
    """True nếu phiên hiện tại là admin (admin-env HOẶC user CSDL role=admin).

    Uỷ quyền cho `server.deps.is_operator` thay vì tự kiểm lại. Trước
    2026-08-06 đây là bản sao thứ hai của cùng một luật; hai bản của một luật
    quyền là hai chỗ có thể trôi dạt, và lúc đó "admin" nghĩa là hai thứ khác
    nhau tuỳ đường vào.
    """
    from server.deps import is_operator

    return is_operator(request)


def _email_admin(request: Request) -> str:
    """Email của admin đang thao tác. Rỗng nếu không xác định được."""
    from server.deps import user_hien_tai
    u = user_hien_tai(request)
    if u is not None:
        return u.email
    # Hoi thang scope thay vi bat ngoai le — cung ly do da ghi o
    # server/routes/ngon_ngu.py: bat rong roi `return ""` se giau ca loi phien
    # that, ma trieu chung chi la "nhat ky khong biet ai lam".
    if "session" not in request.scope:
        return ""
    return str(request.session.get("user") or "")


def ghi_nhat_ky(db, request: Request, hanh_dong: str, doi_tuong: str = "",
                chi_tiet: str = "") -> None:
    """Ghi một dòng nhật ký thao tác quản trị (F-06). KHÔNG commit.

    Cố ý **không** nuốt lỗi: nếu không ghi được nhật ký thì thao tác đó cũng
    không nên coi là đã xảy ra một cách yên tâm. Với thao tác động tới tiền hay
    quyền, mất dấu vết còn tệ hơn thất bại có báo.
    """
    from platform_core.models import NhatKyAdmin
    db.add(NhatKyAdmin(admin_email=_email_admin(request)[:255],
                       hanh_dong=hanh_dong[:64],
                       doi_tuong=str(doi_tuong)[:255],
                       chi_tiet=str(chi_tiet)))


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


# ── Vỏ quản trị dùng chung ───────────────────────────────────────────────────
#
# 🔴 `_ADM_NAV` ĐÃ BỊ GỠ — một trong BA danh sách điều hướng từng sống song song cho cùng một cây
#    (cùng `server/admin_api.NAV` và năm thẻ <a> viết tay trong `sqladmin/base.html`): hai trong ba
#    luôn là bản bị quên khi thêm trang, và nửa SQLAdmin từng có bộ điều hướng khác hẳn.
#
#    Nguồn duy nhất bây giờ: `server/routes/admin/_chung.py`.
#    Bố cục đã đóng băng ở `docs/admin_mvp_v3/03_IA_FREEZE.md`; hợp đồng thêm
#    trang ở `docs/admin_mvp_v3/04_EXTENSION_CONTRACT.md`.
#
# ⭐ Bảng cầu tạm `_KHOA_CU` ĐÃ GỠ (29/08). Nó từng dịch khoá `active` cũ
#    ("chitiet", "revenue", "goi", ...) sang khoá của `SECTIONS`, để đổi vỏ mà
#    không phải sửa 29 chỗ gọi trong cùng một lô — đổi vỏ và đổi thân là hai rủi
#    ro khác nhau, và trộn chúng thì một lần đỏ không chỉ ra được nguyên nhân
#    nào. Nay mọi chỗ gọi khai thẳng khoá của `SECTIONS`, nên cây cầu không còn
#    ai đi và một khoá lạ trở thành lỗi nhìn thấy được thay vì im lặng đi qua.

_PROVCOL = {"gemini": ("#1a73e8", "G"), "apiai": ("#15803d", "AI"),
            "cheapkeyai": ("#0369a1", "CK"), "byteplus": ("#7c3aed", "BP"),
            "plenx": ("#be185d", "PX")}
_CAT_ICON = {"model_control": ("Điều khiển", "m"), "chat": ("Chat", ""),
             "image": ("Ảnh", "i"), "video": ("Video", "v")}
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


def _admin_shell(title: str, active: str, body: str, **thug) -> str:
    """Dựng một trang quản trị hoàn chỉnh.

    Chữ ký ba tham số đầu giữ NGUYÊN như bản f-string cũ, nên mọi chỗ gọi hiện
    có chạy tiếp không sửa. Trang đã chuyển sang template truyền thêm `tieu_de`,
    `mo_ta`, `hanh_dong`, `canh_bao`, `loi`, `thanh_cong`, `q_khach`.

    Vỏ nằm ở `server/templates/admin/_vo.html`; điều hướng ở
    `server/routes/admin/_chung.py`. Không dựng vỏ thứ hai ở bất kỳ đâu.
    """
    from server.routes.admin._chung import dieu_huong
    from server.templating import templates

    try:
        nav = dieu_huong(active)
    except KeyError:
        # Khoá lạ (trang mới quên khai ở `SECTIONS`). Vẫn render được trang —
        # mất trạng thái sáng của thanh bên thì khó chịu, còn ném 500 vào mặt
        # người đang xử sự cố thì tệ hơn nhiều. `test_310` bắt trường hợp này ở
        # cổng, chứ không phải lúc chạy.
        nav = dieu_huong("tong_quan")

    return templates.env.get_template("admin/_vo.html").render(
        title=title, than=body, nav=nav, asset_ver=_asset_ver(), **thug)


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
            f'<span class="tnum muted u-fs11">{h}</span>')


class ChiTietNguoiDungView(_AnTrongMenuSqlAdmin, BaseView):
    """Hồ sơ khách hàng 360 — trang trung tâm của Golden Journey 1.

    Trang này đã tồn tại từ audit 2026-08-07 (F-04) với đúng lý do của nó: muốn
    biết một người đang thế nào phải mở bốn trang và tự nối chúng bằng một UUID
    chép tay. Đợt `admin_mvp_v3` mở rộng nó thành tám khối, thêm phiên đăng nhập,
    quyền app, dấu vết admin, và **hành động tách theo mức nguy hiểm**.

    Truy vấn chuyển sang `platform_core/admin_console.ho_so_khach()`: trang danh
    sách cần đúng bộ truy vấn đó cộng thêm, và hai bản của cùng một định nghĩa
    "một khách hàng đang thế nào" là hai bản sẽ trôi khỏi nhau.

    Hợp đồng: `docs/admin_mvp_v3/05_PAGE_CONTRACT_MATRIX.md` P3.
    """

    name = "Hồ sơ 360"
    icon = "fa-solid fa-id-card"

    @expose("/nguoi-dung", methods=["GET"])
    async def chi_tiet(self, request: Request):
        from server.auth.csrf import issue_csrf_token
        from server.templating import templates
        from platform_core import admin_console

        tim = (request.query_params.get("q") or "").strip()
        ho_so = None
        if tim:
            gen = get_session(); db = next(gen)
            try:
                ho_so = admin_console.ho_so_khach(db, khoa=tim)
            finally:
                try: next(gen)
                except StopIteration: pass

        than = templates.env.get_template("admin/ho_so_360.html").render(
            ho_so=ho_so, tim=tim, csrf_token=issue_csrf_token(request))

        tieu_de = ho_so["user"].email if ho_so else "Hồ sơ khách hàng"
        return HTMLResponse(
            _admin_shell(tieu_de, "ho_so_360", than,
                         tieu_de=tieu_de,
                         mo_ta=("Toàn cảnh một khách và những thao tác an toàn "
                                "có thể làm với họ."),
                         q_khach=tim,
                         thanh_cong=request.query_params.get("ok") or "",
                         loi=request.query_params.get("loi") or ""),
            status_code=200 if (ho_so or not tim) else 404)

    @expose("/nguoi-dung/thu-hoi-phien", methods=["POST"])
    async def thu_hoi_phien(self, request: Request):
        """Thu hồi MỌI phiên đăng nhập của một khách.

        Trước đợt này thao tác an ninh đó chỉ làm được bằng cách vào bảng thô
        `/admin/session/list`, lọc bằng UUID, rồi bấm "xoá dòng" từng dòng một —
        tức một thao tác an ninh thực hiện bằng nút xoá của một bảng dữ liệu, và
        không để lại dấu vết admin nào.

        Ở đây nó có CSRF, có xác nhận, và **có ghi nhật ký** — vì "ai đăng xuất
        khách này, lúc nào" là câu đầu tiên bộ phận hỗ trợ sẽ hỏi.
        """
        from server.auth.csrf import verify_csrf_token
        from platform_core.users import thu_hoi_moi_phien

        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)
        uid = (form.get("user_id") or "").strip()
        if not uid:
            return RedirectResponse("/admin/nguoi-dung", status_code=303)

        gen = get_session(); db = next(gen)
        try:
            u = db.get(User, uid)
            if u is None:
                return RedirectResponse("/admin/nguoi-dung", status_code=303)
            so = thu_hoi_moi_phien(db, uid)
            ghi_nhat_ky(db, request, "thu_hoi_phien", uid,
                        f"{so} phien cua {u.email}")
            db.commit()
            email = u.email
        finally:
            try: next(gen)
            except StopIteration: pass

        from urllib.parse import quote
        return RedirectResponse(
            f"/admin/nguoi-dung?q={quote(uid)}&ok="
            f"{quote(f'Da thu hoi {so} phien cua {email}.')}",
            status_code=303)


class ApiKeysConsole(_AnTrongMenuSqlAdmin, BaseView):
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
        tabs = (tab("all", "Tất cả") + tab("model_control", "Điều khiển model")
                + tab("chat", "Chat") + tab("image", "Ảnh")
                + tab("video", "Video"))

        def act_form(k, op, label):
            return (f'<form method="post" action="/admin/api-key-action" class="adm-form-inline">'
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
                # ⭐ Khoá đang lỗi thì trạng thái phải dẫn đi đâu đó.
                #    Hợp đồng P9 đòi "provider/khoá lỗi → API Operations / ngữ
                #    cảnh Job", và trước đợt này trang này không có MỘT liên kết
                #    nào sang khu Operations: người vận hành thấy một khoá ở
                #    trạng thái `error`, đọc `last_error`, rồi hết đường đi.
                #    Đích là danh sách lời gọi hỏng, vì đó là nơi thấy được lỗi
                #    của provider đã tới tay khách như thế nào.
                + (f'<td>{_status_badge(k)}<br>'
                   f'<a class="muted u-fs11" '
                   f'href="/admin/api-request?status=failed">lời gọi hỏng →</a>'
                   f'</td>'
                   if (k.status in ("error", "exhausted") or not k.enabled)
                   else f'<td>{_status_badge(k)}</td>')
                + f'<td>{_health_bar(k.health_score)}</td>'
                f'<td class="tnum">{k.priority}</td>'
                f'<td class="tnum muted u-fs12">{_rpm}{cap}/min<br>{k.total_tokens} tok</td>'
                f'<td><div class="rowactions">'
                f'<a class="btn ghost sm" href="/admin/api-key-test?id={escape(k.id)}">Test</a>'
                f'<a class="btn ghost sm" href="/admin/api-key-sua?id={escape(k.id)}">Sửa</a>'
                f'{refresh}{toggle}{act_form(k, "reset", "Reset")}</div></td></tr>')
        if not shown:
            rows = ('<tr><td colspan="9" class="muted o-trong"><span class="o-trong-chu">'
                    'Chưa có key nào ở mục này. Bấm “＋ Thêm key”.</span></td></tr>')

        active_cnt = sum(1 for k in keys if k.enabled and k.status == "active")
        body = (
            # Dải `.adm-top` thứ hai đã bị gỡ: vỏ chung đã có một thanh trên
            # thật (ô tìm khách hàng), và hai thanh dính cùng lớp chồng lên nhau
            # khi cuộn. Con số "N/M key hoạt động" là thông tin thật nên nó về
            # đúng chỗ của nó — đầu trang.
            f'<div class="adm-content"><div class="pagehead"><div>'
            f'<h1>Provider Credentials</h1>'
            f'<p>Kho khoá API của <strong>nền tảng</strong> — app xin khoá theo '
            f'provider &amp; loại. Credential luôn mã hoá; chỉ hiện 4 số cuối. '
            f'Đây <em>không</em> phải khoá API của khách: khoá của khách ở '
            f'<a href="/admin/api-khoa">API Platform → Access</a>.</p>'
            f'<p><span class="pill"><span class="dot" style="background:var(--ok);'
            f'width:7px;height:7px;border-radius:50%"></span> '
            f'{active_cnt}/{len(keys)} key hoạt động</span></p></div>'
            f'<div class="actions"><a class="btn ghost" href="/admin/api-models">Nhà cung cấp &amp; model</a>'
            f'<a class="btn" href="/admin/api-key-them">＋ Thêm credential</a></div></div>'
            f'<div class="tabs">{tabs}</div>'
            f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
            f'<th>Provider</th><th>Tên</th><th>Preview</th><th>Loại</th><th>Trạng thái</th>'
            f'<th>Health</th><th>Ưu tiên</th><th>Tải</th><th class="u-phai">Thao tác</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Provider Credentials", "van_hanh", body))


class UserAdmin(ModelView, model=User):
    name = "Người dùng"
    name_plural = "Người dùng"
    icon = "fa-solid fa-user"
    # F-04 (audit 2026-08-07): SO DU phai co o day — con so van hanh quan trong nhat ve mot nguoi.
    column_list = [User.email, "so_du_credit", User.display_name, User.role,
                   User.is_active, User.is_verified, User.created_at, User.last_login_at]
    column_labels = {"so_du_credit": "Số dư", User.email: "Email", User.display_name: "Tên hiển thị",
                     User.role: "Vai trò", User.is_active: "Đang hoạt động", User.is_verified: "Đã xác thực email",
                     User.created_at: "Tạo lúc", User.last_login_at: "Đăng nhập cuối", "id": "User ID", "email_chuan": "Email chuẩn hoá", "registration_ip": "IP đăng ký"}

    async def on_model_change(self, data, model, is_created, request) -> None:
        """F-06: doi vai tro / vo hieu hoa tai khoan phai de lai dau vet.

        Truoc day chi co credit la truy duoc (`cap_tay(by=)`). Doi `role` hay
        `is_active` thi khong ai biet ai lam, luc nao — va do la hai thao tac co
        hau qua lon nhat trong trang nay.
        """
        from platform_core.db import get_session
        cu_gia = {k: getattr(model, k, None)
                  for k in ("role", "is_active", "is_verified", "display_name")}
        thay = {k: (cu_gia[k], data.get(k)) for k in cu_gia
                if k in data and data.get(k) != cu_gia[k]}
        if not thay:
            return
        gen = get_session(); db = next(gen)
        try:
            ghi_nhat_ky(db, request, "sua_nguoi_dung",
                        doi_tuong=getattr(model, "email", "") or str(model),
                        chi_tiet="; ".join(f"{k}: {a!r} -> {b!r}"
                                           for k, (a, b) in sorted(thay.items())))
            db.commit()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    column_searchable_list = [User.email, User.display_name]
    column_sortable_list = [User.email, User.created_at, User.last_login_at]
    column_default_sort = [(User.created_at, True)]
    column_formatters = column_formatters_detail = {User.role: lambda m, a: {"admin": "Quản trị viên", "user": "Thành viên"}.get(getattr(m, "role", ""), getattr(m, "role", ""))}
    # KHÔNG cho sửa email hay password_hash qua form (email là danh tính; mật khẩu chỉ đổi qua luồng đổi-mật-khẩu đã băm).
    form_columns = [User.display_name, User.role, User.is_active, User.is_verified]
    form_overrides = {"role": __import__("wtforms").SelectField}; form_args = {"role": {"choices": [("user", "Thành viên"), ("admin", "Quản trị viên")]}}  # ô chọn thay ô gõ; giá trị lưu giữ nguyên (sqladmin 0.20 KHÔNG có form_choices)
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
    """Bảng job — đích của Golden Journey 3 (điều tra việc chạy hỏng).

    🔴 ĐO TRÊN PRODUCTION 29/08. Hàng đợi chú ý ở `/admin/` báo "4 việc chạy
       hỏng" và dẫn tới đây. Trang này khi đó hiện:

         · `user_id` là **UUID trần, không bấm được** — muốn biết đó là ai phải
           chép nó sang một trang khác;
         · **không có cột lỗi nào cả** — `Job.error` tồn tại trong model nhưng
           không nằm trong `column_list`.

       Nên người vận hành đi hết hàng đợi rồi vẫn không biết **vì sao hỏng** và
       **của ai**. Đó là một ngõ cụt, và nó nằm ở đúng bước cuối của GJ3.

    ⭐ Hợp đồng P1 nói mỗi mục chú ý phải mở trang **giải quyết được** nó. Một
       bảng chỉ nói "error" thì chưa giải quyết được gì.
    """

    name = "Job"
    name_plural = "Job"
    icon = "fa-solid fa-list-check"
    column_list = [Job.created_at, Job.user_id, Job.app_slug, Job.job_type,
                   Job.status, Job.error, Job.attempts]
    column_labels = {Job.error: "Lỗi"}
    column_searchable_list = [Job.user_id, Job.app_slug, Job.status, Job.job_type]
    column_sortable_list = [Job.created_at, Job.status]
    column_default_sort = [(Job.created_at, True)]
    # `progress` rời khỏi danh sách để nhường chỗ cho `error`: một job đã hỏng
    # thì phần trăm tiến độ của nó không dẫn tới hành động nào, còn thông báo
    # lỗi thì có. Cả hai vẫn còn ở trang chi tiết.
    column_details_exclude_list = []
    column_formatters = {
        # `user_id` thành liên kết sang Hồ sơ 360. Đây là chỗ luồng copy-UUID
        # cuối cùng còn sót lại sau đợt `admin_mvp_v3`.
        Job.user_id: lambda m, a: Markup(
            f'<a href="/admin/nguoi-dung?q={escape(m.user_id)}">'
            f'{escape(m.user_id[:8])}…</a>') if m.user_id else "",
        # Lỗi cắt ngắn ở danh sách; bản đầy đủ ở trang chi tiết. Không cắt thì
        # một traceback dài đẩy bảng rộng ra và che mọi cột khác.
        Job.error: lambda m, a: Markup(
            f'<span title="{escape(m.error)}">{escape(m.error[:70])}'
            f'{"…" if len(m.error) > 70 else ""}</span>') if m.error else "",
    }
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


class GrantCreditView(_AnTrongMenuSqlAdmin, BaseView):
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
                msg_html = ('<p class="alert alert-err">Phiên hết hạn hoặc CSRF '
                            'không hợp lệ — tải lại trang rồi thử lại.</p>')
                status = 400
            else:
                # `user_id` la ten o cu (UUID). Giu de script/test cu khong gay;
                # `cap_hang_loat` nhan ca email lan UUID nen mot duong xu ly la du.
                nguoi_raw = ((form.get("nguoi") or form.get("user_id") or "").strip())
                amount_raw = (form.get("amount") or "").strip()
                note = (form.get("note") or "").strip()
                user_id = nguoi_raw
                try:
                    amount = int(amount_raw)
                    if amount == 0:
                        raise ValueError("Số credit phải khác 0.")
                    # Tách theo xuống dòng, dấu phẩy và chấm phẩy — admin dán từ
                    # bảng tính hoặc từ chat, không ai gõ đúng một định dạng.
                    tach = nguoi_raw.replace(",", "\n").replace(";", "\n")
                    ds = [x for x in tach.splitlines() if x.strip()]
                    from platform_core.credit import cap_hang_loat, so_du
                    gen = get_session()
                    db = next(gen)
                    try:
                        kq = cap_hang_loat(db, ds, amount, by="admin", note=note)
                        if not kq.thanh_cong:
                            # D4: mot email sai thi KHONG AI duoc cap. Rollback cho
                            # chac, du cap_hang_loat chua ghi gi khi co email sai.
                            db.rollback()
                            ds_sai = ", ".join(escape(x) for x in kq.khong_thay)
                            msg_html = (
                                f'<p class="alert alert-err">Không tìm thấy tài khoản: '
                                f'<b>{ds_sai}</b>.<br>'
                                f'<b>Chưa cấp cho ai cả</b> — sửa lại rồi gửi lần nữa.</p>')
                            status = 400
                        else:
                            db.commit()
                            dong = "".join(
                                f"<li><code>{escape(e)}</code> — số dư mới "
                                f"<b>{so_du(db, uid)}</b></li>"
                                for e, uid in kq.da_cap)
                            canh = ""
                            if kq.trung:
                                canh = (f'<p class="alert alert-warn">Bỏ qua '
                                        f'{len(kq.trung)} email lặp — mỗi người chỉ '
                                        f'cấp một lần.</p>')
                            ghi_nhat_ky(
                                db, request, "cap_credit",
                                doi_tuong=", ".join(e for e, _ in kq.da_cap)[:255],
                                chi_tiet=f"{amount:+d} credit cho {len(kq.da_cap)} "
                                         f"tai khoan; ghi chu: {note}")
                            db.commit()
                            msg_html = (
                                f'<p class="alert alert-ok">Đã cấp <b>{amount:+d}</b> '
                                f'credit cho <b>{len(kq.da_cap)}</b> tài khoản.</p>'
                                f'{canh}<ul>{dong}</ul>')
                            user_id = ""
                    finally:
                        try:
                            next(gen)
                        except StopIteration:
                            pass
                except Exception as e:
                    msg_html = f'<p class="alert alert-err">Lỗi: {escape(str(e))}</p>'
                    status = 400

        csrf_token = issue_csrf_token(request)
        body = f"""<div class="adm-content adm-hep-600">
<div class="pagehead"><div><h1>Cấp / điều chỉnh credit</h1>
<p>Ghi một bút toán <code>grant</code> cho mỗi người (số âm để trừ). Sổ credit append-only. Cấp được cho nhiều người một lượt.</p></div></div>
{msg_html}
<div class="ui-card"><form method="post">
  <input type="hidden" name="csrf_token" value="{escape(csrf_token)}">
  <div class="field"><label>Email tài khoản — mỗi dòng một người</label>
    <textarea class="inp" name="nguoi" rows="6" required
      placeholder="nhanvien1@congty.com&#10;nhanvien2@congty.com">{escape(user_id)}</textarea>
    <small>Dán được cả danh sách. Ngăn bằng xuống dòng, dấu phẩy hoặc chấm phẩy.
    <b>Một email sai thì không ai được cấp</b> — để bạn không phải đối soát tay.</small></div>
  <div class="field"><label for="f-amount">Số credit (dương = cộng, âm = trừ)</label>
    <input id="f-amount" class="inp tnum" name="amount" type="number" required placeholder="100"></div>
  <div class="field"><label for="f-note">Ghi chú</label>
    <input id="f-note" class="inp" name="note" placeholder="khuyến mãi / bồi thường"></div>
  <button class="btn" type="submit">Cấp credit</button>
</form></div></div>"""
        return HTMLResponse(_admin_shell("Cấp credit", "cap_credit", body), status_code=status)


class NhatKyAdminView(ModelView, model=NhatKyAdmin):
    """Nhật ký thao tác quản trị — CHỈ XEM (F-06).

    Khoá create/edit/delete cùng lý do với sổ credit: một nhật ký sửa được thì
    không còn là nhật ký.
    """

    name = "Nhật ký admin"
    name_plural = "Nhật ký admin"
    icon = "fa-solid fa-clipboard-list"
    column_list = [NhatKyAdmin.created_at, NhatKyAdmin.admin_email,
                   NhatKyAdmin.hanh_dong, NhatKyAdmin.doi_tuong, NhatKyAdmin.chi_tiet]
    column_searchable_list = [NhatKyAdmin.admin_email, NhatKyAdmin.doi_tuong]
    column_sortable_list = [NhatKyAdmin.created_at, NhatKyAdmin.admin_email]
    column_default_sort = [(NhatKyAdmin.created_at, True)]
    can_create = False
    can_edit = False
    can_delete = False


class ApiKeyAdmin(ModelView, model=ApiKey):
    name = "API key"
    # ⛔ KHÔNG đặt lại là "APIKEYS". `ApiKeysConsole` đã mang tên đó, và **hai mục
    #    menu cùng tên** là lý do chủ dự án ngày 23/08 vào nhầm trang này rồi báo
    #    *"Provider đâu có ltt_image"* — trang này có `can_create = False` nên nó
    #    không có nút tạo và không có dropdown provider nào cả.
    #
    #    Đây là bảng dữ liệu thô để tra cứu và xoá. Chỗ làm việc là
    #    `/admin/apikeys`.
    name_plural = "APIKEYS (bảng thô)"
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


class AddApiKeyView(_AnTrongMenuSqlAdmin, BaseView):
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
                msg = '<p class="alert alert-err">CSRF không hợp lệ — tải lại trang.</p>'
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
                    ghi_nhat_ky(db, request, "them_provider_credential",
                                (form.get("provider") or ""),
                                f"ten={(form.get('name') or '')[:60]}")
                    db.commit()
                    msg = '<p class="alert alert-ok">Đã thêm API key.</p>'
                except Exception as e:
                    db.rollback()
                    msg = f'<p class="alert alert-err">Lỗi: {escape(str(e))}</p>'
                    status = 400
                finally:
                    try: next(gen)
                    except StopIteration: pass

        token = issue_csrf_token(request)
        opts = "".join(
            f'<option value="{escape(p.id)}">{escape(p.display_name)} '
            f'[{escape(p.auth_style)}]</option>' for p in providers.list_all())
        # Bản đồ provider -> category nó phục vụ, cho đoạn script tick sẵn bên dưới.
        cat_map = json.dumps({p.id: list(p.categories or ()) for p in providers.list_all()})
        _catlbl = {APIKEY_CAT_MODEL: "Điều khiển model", APIKEY_CAT_CHAT: "Chat",
                   APIKEY_CAT_IMAGE: "Ảnh", APIKEY_CAT_VIDEO: "Video"}
        cat_boxes = "".join(
            f'<label><input type="checkbox" name="categories" value="{c}"> {_catlbl[c]}</label>'
            for c in (APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE, APIKEY_CAT_VIDEO))
        body = f"""<div class="adm-content adm-hep-640">
<div class="pagehead"><div><h1>Thêm API key</h1>
<p>Credential nhập vào sẽ được <b>mã hoá</b> trước khi lưu; chỉ 4 số cuối hiện lại.</p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; Provider Credentials</a>
<a class="btn ghost" href="/admin/api-models">Nhà cung cấp &amp; model</a></div></div>
{msg}
<div class="ui-card"><form method="post">
  <input type="hidden" name="csrf_token" value="{escape(token)}">
  <div class="field"><label for="prov">Provider</label><select class="inp" name="provider" id="prov" required>{opts}</select></div>
  <div class="field"><label for="f-name">Tên gợi nhớ</label><input id="f-name" class="inp" name="name" placeholder="ltt-image-chinh"></div>
  <div class="field"><label for="f-credential">Credential (khoá THÔ — sẽ mã hoá)</label>
    <input id="f-credential" class="inp" name="credential" type="password" required autocomplete="off" placeholder="AIza••••••"></div>
  <div class="field"><label>Loại (năng lực)</label>
    <div class="catpick">{cat_boxes}</div></div>
  <div class="field"><label for="f-base-url">base_url (để trống = mặc định provider)</label><input id="f-base-url" class="inp" name="base_url"></div>
  <div class="field"><label for="f-supported-models">supported_models (phẩy phân cách, trống = mọi model)</label>
    <input id="f-supported-models" class="inp mono" name="supported_models" placeholder="hidream-o1, ..."></div>
  <div class="field"><label for="f-default-model">default_model</label><input id="f-default-model" class="inp mono" name="default_model"></div>
  <div class="field"><label for="f-priority">priority (cao = ưu tiên)</label><input id="f-priority" class="inp tnum" name="priority" type="number" value="100"></div>
  <button class="btn" type="submit">Lưu API key</button>
</form></div></div>
<style>.catpick{{display:flex;gap:8px;flex-wrap:wrap}}.catpick label{{display:flex;gap:6px;align-items:center;
padding:7px 11px;border:1px solid var(--line2);border-radius:8px;font-size:12.5px;cursor:pointer;color:var(--muted)}}
.catpick input{{accent-color:var(--accent)}}.catpick label.mo{{opacity:.35}}</style>
<script>
// Tick san category ma provider PHUC VU, va lam mo nhung cai no khong phuc vu.
// Su co 23/08: khoa ltt_image duoc tao voi category `model_control`. Hop le ve
// mat danh sach nen form nhan, nhung provider do chi phuc vu `image` — nen
// api_pool khong bao gio cap phat no, va loi bao ra la "khong co API key kha
// dung", tuc la mot cau noi ve mot thu KHAC voi nguyen nhan that.
const PHUC_VU = {cat_map};
function apDung() {{
  const p = document.getElementById('prov').value;
  const ok = PHUC_VU[p] || [];
  document.querySelectorAll('.catpick input[name=categories]').forEach(function (o) {{
    const duoc = ok.length === 0 || ok.indexOf(o.value) >= 0;
    o.checked = duoc && ok.length > 0;
    o.disabled = !duoc;
    o.parentElement.classList.toggle('mo', !duoc);
  }});
}}
document.getElementById('prov').addEventListener('change', apDung);
apDung();
</script>"""
        return HTMLResponse(_admin_shell("Thêm API key", "provider_them", body), status_code=status)


class SuaApiKeyView(_AnTrongMenuSqlAdmin, BaseView):
    """Sửa một API key — **giữ nguyên id và toàn bộ lịch sử**.

    ⛔ VÌ SAO TRANG NÀY TỒN TẠI (sự cố 2026-08-23).

       Trước đây không có đường sửa nào. `ApiKeyAdmin` (sqladmin) cho sửa đúng
       năm trường an toàn — `name`, `base_url`, `default_model`, `priority`,
       `enabled` — và **không** cho sửa `categories`, cũng **không** cho xoay
       credential. Chú thích trong mã ghi thẳng cách chữa: *"đổi credential = tạo
       key mới rồi xoá key cũ"*.

       Cái giá của cách đó chỉ lộ ra khi cần dùng: khoá mang `total_requests`,
       `total_success`, `health_score`, `last_used_at`, và một **id mà nhật ký
       vận hành đang tham chiếu**. Tạo lại là **mất hết** — chỉ vì tick nhầm một
       ô, hoặc vì một credential bị lộ cần xoay.

       Ngày 23/08 chuyện đó xảy ra thật: khoá `ltt_image` vào với category
       `model_control`, và cách duy nhất để chữa qua giao diện là xoá đi tạo lại.

    ⭐ Credential để **trống** thì giữ nguyên. Đó là mặc định an toàn: sửa một ô
       category không được phép vô tình xoá mất khoá.
    """

    name = "Sửa API key"
    icon = "fa-solid fa-pen"

    def is_visible(self, request: Request) -> bool:  # noqa: D401
        return False          # vao tu nut tren console, khong lam ban menu trai

    @expose("/api-key-sua", methods=["GET", "POST"])
    async def sua(self, request: Request):
        from platform_core import api_keys, providers
        from platform_core.models import (APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE,
                                          APIKEY_CAT_MODEL, APIKEY_CAT_VIDEO)
        from server.auth.csrf import issue_csrf_token, verify_csrf_token

        key_id = request.query_params.get("id", "")
        msg, status = "", 200

        if request.method == "POST":
            form = await request.form()
            key_id = form.get("id", "")  # type: ignore[assignment]  # Starlette FormData union
            if not verify_csrf_token(request, (form.get("csrf_token") or "")):
                msg = '<p class="alert alert-err">CSRF khong hop le - tai lai trang.</p>'
                status = 400
            else:
                gen = get_session()
                db = next(gen)
                try:
                    key = api_keys.lay_key_theo_id(db, key_id)
                    if key is None:
                        return HTMLResponse("Khong thay key.", status_code=404)
                    api_keys.cap_nhat_categories(db, key, form.getlist("categories"))
                    key.name = (form.get("name") or key.provider).strip()
                    key.base_url = (form.get("base_url") or "").strip()
                    key.default_model = (form.get("default_model") or "").strip()
                    key.priority = int(form.get("priority") or 100)
                    api_keys.cap_nhat_supported_models(db, key, [
                        m.strip()
                        for m in (form.get("supported_models") or "").split(",")
                        if m.strip()])
                    xoay = (form.get("credential") or "").strip()
                    if xoay:
                        api_keys.dat_credential(db, key, xoay)
                    # ⛔ Ghi lai VIEC co xoay credential hay khong, khong bao gio
                    #    ghi gia tri. "Khoa nay bi xoay luc nao" la cau phai tra
                    #    duoc; "khoa nay la gi" thi khong.
                    ghi_nhat_ky(db, request, "sua_provider_credential", key.id,
                                f"{key.provider}"
                                + (" | credential DA XOAY" if xoay else ""))
                    db.commit()
                    them = " - credential DA XOAY." if xoay else "."
                    msg = ('<p class="alert alert-ok">Da luu. Id va lich su giu '
                           'nguyen' + them + '</p>')
                except Exception as e:                        # noqa: BLE001
                    db.rollback()
                    msg = f'<p class="alert alert-err">Loi: {escape(str(e))}</p>'
                    status = 400
                finally:
                    try:
                        next(gen)
                    except StopIteration:
                        pass

        gen = get_session()
        db = next(gen)
        try:
            key = api_keys.lay_key_theo_id(db, key_id)
            if key is None:
                return HTMLResponse("Khong thay key.", status_code=404)
            prov = providers.get(key.provider)
            phuc_vu = list(getattr(prov, "categories", ()) or [])
            dang_co = list(key.categories or [])
            nhan = {APIKEY_CAT_MODEL: "Dieu khien model", APIKEY_CAT_CHAT: "Chat",
                    APIKEY_CAT_IMAGE: "Anh", APIKEY_CAT_VIDEO: "Video"}
            o = []
            for c in (APIKEY_CAT_MODEL, APIKEY_CAT_CHAT, APIKEY_CAT_IMAGE,
                      APIKEY_CAT_VIDEO):
                duoc = (not phuc_vu) or (c in phuc_vu)
                o.append(
                    '<label class="{}"><input type="checkbox" name="categories" '
                    'value="{}"{}{}> {}</label>'.format(
                        "" if duoc else "mo", c,
                        " checked" if c in dang_co else "",
                        "" if duoc else " disabled", nhan[c]))
            boxes = "".join(o)
            goi_y = ""
            if phuc_vu:
                goi_y = ('<p class="dim">Provider <b>{}</b> chi phuc vu: <b>{}</b>. '
                         'Cac o khac bi khoa.</p>').format(
                             escape(key.provider), escape(", ".join(phuc_vu)))
            token = issue_csrf_token(request)
            body = _sua_key_html(key, boxes, goi_y, token, msg)
            return HTMLResponse(_admin_shell("Sua API key", "provider_sua", body),
                                status_code=status)
        finally:
            try:
                next(gen)
            except StopIteration:
                pass


def _sua_key_html(key, boxes: str, goi_y: str, token: str, msg: str) -> str:
    """Thân trang sửa key. Tách ra để hàm view không thành một khối chuỗi dài."""
    lich_su = "{}/{} luot thanh cong, health {}".format(
        key.total_success, key.total_requests, key.health_score)
    return """<div class="adm-content adm-hep-640">
<div class="pagehead"><div><h1>Sua API key</h1>
<p>Id va lich su <b>giu nguyen</b>: {lich_su}.</p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; Provider Credentials</a></div></div>
{msg}
<div class="ui-card"><form method="post">
  <input type="hidden" name="csrf_token" value="{token}">
  <input type="hidden" name="id" value="{kid}">
  <div class="field"><label>Provider</label><input class="inp" value="{prov}" disabled></div>
  <div class="field"><label for="f-name">Ten goi nho</label><input id="f-name" class="inp" name="name" value="{ten}"></div>
  <div class="field"><label for="f-credential">Credential moi (<b>de trong = giu nguyen</b>, dang ...{pv})</label>
    <input id="f-credential" class="inp" name="credential" type="password" autocomplete="off"
           placeholder="de trong neu khong xoay"></div>
  <div class="field"><label>Loai (nang luc)</label><div class="catpick">{boxes}</div>{goi_y}</div>
  <div class="field"><label for="f-base-url">base_url</label><input id="f-base-url" class="inp" name="base_url" value="{base}"></div>
  <div class="field"><label for="f-supported-models">supported_models (phay phan cach)</label>
    <input id="f-supported-models" class="inp mono" name="supported_models" value="{sup}"></div>
  <div class="field"><label for="f-default-model">default_model</label><input id="f-default-model" class="inp mono" name="default_model" value="{dm}"></div>
  <div class="field"><label for="f-priority">priority</label><input id="f-priority" class="inp tnum" name="priority" type="number" value="{pri}"></div>
  <button class="btn" type="submit">Luu</button>
</form></div></div>
<style>.catpick{{display:flex;gap:8px;flex-wrap:wrap}}.catpick label{{display:flex;gap:6px;
align-items:center;padding:7px 11px;border:1px solid var(--line2);border-radius:8px;
font-size:12.5px;cursor:pointer;color:var(--muted)}}.catpick input{{accent-color:var(--accent)}}
.catpick label.mo{{opacity:.35}}</style>""".format(
        lich_su=escape(lich_su), msg=msg, token=escape(token), kid=escape(key.id),
        prov=escape(key.provider), ten=escape(key.name or ""),
        pv=escape(key.key_preview or ""), boxes=boxes, goi_y=goi_y,
        base=escape(key.base_url or ""),
        sup=escape(", ".join(key.supported_models or [])),
        dm=escape(key.default_model or ""), pri=int(key.priority))


class ApiKeyActionView(_AnTrongMenuSqlAdmin, BaseView):
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
        body = f"""<div class="adm-content adm-hep-640">
<div class="pagehead"><div><h1>Test key</h1>
<p>{_prov_dot(key.provider)} {escape(key.provider)} · <span class="mono">{escape(key.key_preview)}</span></p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; Provider Credentials</a></div></div>
<div class="ui-card"><p class="adm-mb8">{badge}</p>
<p class="muted mono adm-chi-tiet-loi">{escape(str(detail))}</p></div></div>"""
        return HTMLResponse(_admin_shell("Test key", "provider_test", body))

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
                # ⭐ Đặt lại CẢ `health_score`. Thiếu dòng này thì "Reset" chỉ xoá
                #    bộ đếm lỗi, còn điểm sức khoẻ vẫn thấp — và `chon_key` xếp
                #    hạng theo `health_score`, nên khoá đã hồi phục vẫn bị đẩy
                #    xuống cuối mãi mãi. Người vận hành bấm Reset, thấy trạng thái
                #    về `active`, và tưởng đã xong.
                key.health_score = 100
                key.last_error = ""
            elif op == "refresh":
                # Làm mới model sống từ provider -> ghi supported_models (H8 Pha 2).
                from platform_core import providers, providers_live
                prov = providers.get(key.provider)
                try:
                    models = providers_live.lay_models_song(prov, api_keys.lay_credential(db, key))
                    api_keys.cap_nhat_supported_models(db, key, models)
                except providers_live.ProviderLiveError as e:
                    # ⛔ TRƯỚC ĐÂY LÀ `pass`. Người vận hành bấm nút, trang tải
                    #    lại, và **không có gì cho biết nó đã hỏng** — họ kết luận
                    #    provider không có model nào. Không làm sập trang là đúng;
                    #    nuốt luôn lý do thì không.
                    db.rollback()
                    _log.warning("refresh models that bai cho key %s (%s): %s",
                                key.id[:8], key.provider, e)
                    return RedirectResponse(
                        "/admin/apikeys?loi=" + quote_plus(f"Lam moi model that bai: {e}"),
                        status_code=303)
            ghi_nhat_ky(db, request, f"provider_key_{op or 'khong_ro'}", key.id,
                        f"{key.provider}")
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/apikeys", status_code=303)


class ModelsView(_AnTrongMenuSqlAdmin, BaseView):
    """Danh sách Provider + Model (registry, chỉ đọc) — H8."""

    name = "Models"
    icon = "fa-solid fa-cubes"

    @expose("/api-models", methods=["GET"])
    async def models(self, request: Request):
        from platform_core import providers
        rows = ""
        for p in providers.list_all():
            ms = " ".join(
                f'<span class="chip {"adm-chip-model" if m.is_active else "m"}">{escape(m.id)}'
                f'{"" if m.is_active else " · Soon"}</span>' for m in p.models
            ) or '<span class="muted u-fs12">chưa khai model — key nhận mọi model</span>'
            kind = ('<span class="badge b-grey"><span class="dot"></span>Bất đồng bộ</span>'
                    if p.async_poll else '<span class="badge b-ok"><span class="dot"></span>Đồng bộ</span>')
            refresh = (f'<a class="btn ghost sm" href="/admin/api-models-refresh?provider={escape(p.id)}">Làm mới</a>'
                       if p.list_models_path else '<span class="muted u-fs12">—</span>')
            rows += (f'<tr><td><span class="prov">{_prov_dot(p.id)}{escape(p.id)}</span></td>'
                     f'<td class="mono muted u-fs12">{escape(p.auth_style)}</td>'
                     f'<td>{escape(", ".join(p.categories))}</td>'
                     f'<td class="adm-o-chip">{ms}</td><td>{kind}</td><td>{refresh}</td></tr>')
        body = f"""<div class="adm-content">
<div class="pagehead"><div><h1>Nhà cung cấp &amp; model</h1>
<p>Danh mục khai sẵn trong mã nguồn (<code>platform_core/providers.py</code>) — thêm nhà cung cấp hoặc model cần một bản cập nhật.
“Làm mới” gọi endpoint sống của provider (dùng key ưu tiên nhất) để lấy model thật.</p></div>
<div class="actions"><a class="btn ghost" href="/admin/apikeys">&larr; Provider Credentials</a>
<a class="btn" href="/admin/api-key-them">＋ Thêm credential</a></div></div>
<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>
<th>Nhà cung cấp</th><th>Xác thực</th><th>Loại</th><th>Model khai sẵn</th><th>Kiểu gọi</th><th>Model sống</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>"""
        return HTMLResponse(_admin_shell("Nhà cung cấp & model", "models", body))

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
            or '<span class="muted u-fs12">—</span>'
        body = f"""<div class="adm-content adm-hep-760">
<div class="pagehead"><div><h1>Model sống — {escape(prov_id)}</h1><p>{note}</p></div>
<div class="actions"><a class="btn ghost" href="/admin/api-models">&larr; Nhà cung cấp &amp; model</a></div></div>
<div class="ui-card adm-o-chip-rong">{chips}</div></div>"""
        return HTMLResponse(_admin_shell("Model sống", "models", body))


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


def _vnd(n, don_vi: str = "đ") -> str:  # kiểu Việt: 200.000đ, 2.200 (don_vi="")
    return f"{int(n):,}".replace(",", ".") + don_vi


def _order_badge(status: str) -> str:
    cls, lbl = _ORDER_ST.get(status, ("b-grey", status))
    return f'<span class="badge {cls}"><span class="dot"></span>{escape(lbl)}</span>'


class RevenueView(_AnTrongMenuSqlAdmin, BaseView):
    """Bảng doanh thu (H9) — tổng VND đã thu, credit đã bán, số đơn."""

    name = "Doanh thu"
    icon = "fa-solid fa-chart-line"

    @expose("/doanh-thu", methods=["GET"])
    async def revenue(self, request: Request):
        from platform_core import admin_console, billing
        gen = get_session(); db = next(gen)
        try:
            dt = billing.doanh_thu(db)
            gan_day = billing.liet_ke_don(db, status="paid", limit=10)
            # Hợp đồng P4: trang này phải trả lời "đơn nào cần xử", không chỉ
            # "đã thu bao nhiêu". Trước đợt này nó có ba ô số và một bảng đơn ĐÃ
            # trả — tức thứ duy nhất còn cần làm gì đó thì không có mặt.
            cho_xu = billing.liet_ke_don(db, status="pending", limit=10)
            tien_gan_day = db.query(NhatKyAdmin).filter(
                NhatKyAdmin.hanh_dong.in_(
                    ("cap_credit", "xac_nhan_don_da_tra"))).order_by(
                NhatKyAdmin.created_at.desc()).limit(8).all()
            email_cua = admin_console.emails_cua(
                db, [o.user_id for o in gan_day] + [o.user_id for o in cho_xu])

            def _dong(o, cot_cuoi):
                _e = email_cua.get(o.user_id) or o.user_id
                return (f'<tr><td class="mono">'
                        f'<a href="/admin/don?q={o.order_code}">{o.order_code}</a></td>'
                        f'<td><a href="/admin/nguoi-dung?q={escape(o.user_id)}">'
                        f'{escape(_e)}</a></td>'
                        f'<td class="tnum">{_vnd(o.price_vnd)}</td>'
                        f'<td class="tnum">{_vnd(o.credits, " credit")}</td>'
                        f'<td class="muted u-fs12">{cot_cuoi}</td></tr>')

            rows = "".join(_dong(o, f"{o.paid_at:%d/%m %H:%M}")
                           for o in gan_day if o.paid_at)
            rows_cho = "".join(_dong(o, f"{o.created_at:%d/%m %H:%M}")
                               for o in cho_xu)
            rows_tien = "".join(
                f'<tr><td class="muted u-fs12">'
                f'{n.created_at:%d/%m %H:%M}</td>'
                f'<td>{escape(n.hanh_dong)}</td>'
                f'<td class="mono muted u-fs12">'
                f'{escape((n.doi_tuong or "")[:40])}</td>'
                f'<td class="muted u-fs12">'
                f'{escape(n.admin_email)}</td></tr>' for n in tien_gan_day)
        finally:
            try: next(gen)
            except StopIteration: pass
        cards = (
            f'<div class="grid adm-luoi-tai-chinh">'
            f'<div class="ui-card"><div class="dim">Tổng đã thu</div>'
            f'<div class="tnum adm-so-lon">{_vnd(dt["vnd"])}</div></div>'
            f'<div class="ui-card"><div class="dim">Credit đã bán</div>'
            f'<div class="tnum adm-so-lon">{_vnd(dt["credits"], "")}</div></div>'
            f'<div class="ui-card"><div class="dim">Đơn đã trả</div>'
            f'<div class="tnum adm-so-lon">{_vnd(dt["orders"], "")}</div></div></div>')
        body = (f'<div class="adm-content"><div class="pagehead"><div>'
                f'<h1>Tổng quan tài chính</h1>'
                f'<p>Chỉ tính đơn đã trả (đã ghi vào sổ credit). Tiền hiện bằng đ, '
                f'credit hiện bằng credit — hai đơn vị, không trộn.</p></div>'
                f'<div class="actions"><a class="btn ghost" href="/admin/goi">Gói nạp</a>'
                f'<a class="btn ghost" href="/admin/don">Đơn hàng</a></div></div>'
                f'{cards}'
                f'<h2 class="u-tieu-muc">Đơn cần xử lý</h2>'
                f'<p class="adm-dan">Đơn đang chờ cổng thanh toán xác nhận. Xác '
                f'nhận tay là đường dự phòng khi webhook không tới — thao tác đó '
                f'ở <a href="/admin/don?st=pending">trang Đơn hàng</a>.</p>'
                f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
                f'<th>Mã đơn</th><th>Khách</th><th>Tiền</th><th>Credit</th><th>Tạo lúc</th>'
                f'</tr></thead><tbody>{rows_cho or "<tr><td colspan=5 class='muted o-trong'><span class=o-trong-chu>Không có đơn nào đang chờ.</span></td></tr>"}'
                f'</tbody></table></div>'
                f'<h2 class="u-tieu-muc">Đơn đã trả gần đây</h2>'
                f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
                f'<th>Mã đơn</th><th>Khách</th><th>Tiền</th><th>Credit</th><th>Trả lúc</th>'
                f'</tr></thead><tbody>{rows or "<tr><td colspan=5 class='muted o-trong'><span class=o-trong-chu>Chưa có đơn nào.</span></td></tr>"}'
                f'</tbody></table></div>'
                f'<h2 class="u-tieu-muc">Hành động tiền của admin gần đây</h2>'
                f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
                f'<th>Lúc</th><th>Hành động</th><th>Đối tượng</th><th>Ai làm</th>'
                f'</tr></thead><tbody>{rows_tien or "<tr><td colspan=4 class='muted o-trong'><span class=o-trong-chu>Chưa có thao tác tiền nào của admin.</span></td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Tổng quan tài chính", "tai_chinh", body))


class PackagesView(_AnTrongMenuSqlAdmin, BaseView):
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
                    db.add(pkg)
                    db.flush()
                    ghi_nhat_ky(db, request, "them_goi_nap", pkg.id,
                                f"{pkg.name} | {price} d | {base} credit "
                                f"| bonus {bonus}%")
                    db.commit()
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
                    return (f'<form method="post" action="/admin/goi/action" class="adm-form-inline">'
                            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                            f'<input type="hidden" name="id" value="{escape(p.id)}">'
                            f'<input type="hidden" name="op" value="{op}">'
                            f'<button class="btn {"danger" if op == "delete" else "ghost"} sm">{label}</button></form>')
                rows += (f'<tr><td class="tnum">{p.sort_order}</td><td>{escape(p.name)}</td>'
                         f'<td class="tnum">{_vnd(p.price_vnd)}</td>'
                         f'<td class="tnum">{_vnd(p.credits_base, "")}</td>'
                         f'<td class="tnum">+{p.bonus_percent}%</td>'
                         f'<td class="tnum"><strong>{_vnd(total, "")}</strong></td><td>{on}</td>'
                         f'<td><div class="rowactions">'
                         f'{act("toggle", "Bật/Tắt")}{act("delete", "Xoá")}</div></td></tr>')
        finally:
            try: next(gen)
            except StopIteration: pass
        form_html = (
            f'<div class="ui-card adm-the-form"><form method="post">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<div class="field"><label for="f-name">Tên gói</label><input id="f-name" class="inp" name="name" placeholder="Gói 100k"></div>'
            f'<div class="field"><label for="f-price-vnd">Giá (VNĐ)</label><input id="f-price-vnd" class="inp tnum" name="price_vnd" type="number" required placeholder="100000"></div>'
            f'<div class="field"><label for="f-bonus-percent">Bonus (%)</label><input id="f-bonus-percent" class="inp tnum" name="bonus_percent" type="number" value="0"></div>'
            f'<div class="field"><label for="f-sort-order">Thứ tự hiện</label><input id="f-sort-order" class="inp tnum" name="sort_order" type="number" value="100"></div>'
            f'<p class="dim u-fs12 u-mb10">Tỉ giá 1 credit = 100đ → credit gốc = giá // 100. Tổng = gốc + bonus%.</p>'
            f'<button class="btn">＋ Thêm gói</button></form></div>')
        body = (f'<div class="adm-content"><div class="pagehead"><div><h1>Gói nạp</h1>'
                f'<p>Khách thấy gói bật ở trang <code>/nap</code>. Đổi giá không ảnh hưởng đơn cũ.</p></div>'
                f'<div class="actions"><a class="btn ghost" href="/admin/doanh-thu">Doanh thu</a>'
                f'<a class="btn ghost" href="/admin/don">Đơn hàng</a></div></div>{msg}{form_html}'
                f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
                f'<th>#</th><th>Tên</th><th>Giá</th><th>Gốc</th><th>Bonus</th><th>Tổng</th>'
                f'<th>Trạng thái</th><th class="u-phai">Thao tác</th></tr></thead>'
                f'<tbody>{rows or "<tr><td colspan=8 class='muted o-trong'><span class=o-trong-chu>Chưa có gói. Thêm ở trên.</span></td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("Gói nạp", "goi_nap", body), status_code=status)

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
                    ghi_nhat_ky(db, request, "goi_nap_bat_tat", p.id,
                                f"{p.name} -> {'bat' if p.active else 'tat'}")
                elif op == "delete":
                    ghi_nhat_ky(db, request, "xoa_goi_nap", p.id,
                                f"{p.name} | {p.price_vnd} d")
                    db.delete(p)
                db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        return RedirectResponse("/admin/goi", status_code=303)


class OrdersView(_AnTrongMenuSqlAdmin, BaseView):
    """Đơn hàng nạp (H9): lọc theo trạng thái + xác nhận trả tay (dự phòng)."""

    name = "Đơn hàng"
    icon = "fa-solid fa-receipt"

    @expose("/don", methods=["GET"])
    async def orders(self, request: Request):
        from platform_core import admin_console, billing
        from server.auth.csrf import issue_csrf_token
        st = request.query_params.get("st", "all")
        tim = (request.query_params.get("q") or "").strip()
        gen = get_session(); db = next(gen)
        try:
            allrows = billing.liet_ke_don(db, limit=300)
            # Bảng đơn chỉ giữ `user_id`. Hiện tám ký tự đầu của một UUID là
            # buộc người vận hành chép nó sang một trang khác để biết đó là ai —
            # đúng luồng copy-UUID mà Golden Journey 1/2 nói phải hết.
            email_cua = admin_console.emails_cua(db, [o.user_id for o in allrows])
            token = issue_csrf_token(request)
            cnt = {"all": len(allrows)}
            for s in ("pending", "paid", "expired", "cancelled", "failed"):
                cnt[s] = sum(1 for o in allrows if o.status == s)
            shown = allrows if st == "all" else [o for o in allrows if o.status == st]
            if tim:
                shown = [o for o in shown
                         if tim in str(o.order_code)
                         or tim.lower() in (email_cua.get(o.user_id) or "").lower()
                         or tim == o.user_id]
            rows = ""
            for o in shown:
                markpaid = ""
                if o.status == "pending":
                    # Xác nhận tường minh: đây là thao tác TIỀN, và nó cộng
                    # credit thật cho khách. Idempotent nên bấm hai lần không
                    # cộng đôi — nhưng "không hỏng" khác với "cố ý".
                    xn = (f"Xác nhận đơn #{o.order_code} ĐÃ ĐƯỢC TRẢ? "
                          f"Khách sẽ được cộng {o.credits:,} credit.")
                    markpaid = (f'<form method="post" action="/admin/don/action" class="adm-form-inline">'
                                f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                                f'<input type="hidden" name="order_code" value="{o.order_code}">'
                                f'<button class="btn ghost sm" '
                                f'onclick="return confirm({escape(repr(xn))})">'
                                f'Xác nhận đã trả</button></form>')
                # Email có liên kết thay vì tám ký tự đầu của UUID: cột cũ không
                # bấm được và không nói lên ai, nên muốn biết đó là ai phải chép
                # UUID sang một trang khác.
                _email = email_cua.get(o.user_id) or o.user_id
                rows += (f'<tr><td class="mono">{o.order_code}</td>'
                         f'<td><a href="/admin/nguoi-dung?q={escape(o.user_id)}">'
                         f'{escape(_email)}</a></td>'
                         f'<td class="tnum">{_vnd(o.price_vnd)}</td>'
                         f'<td class="tnum">{_vnd(o.credits, "")}{(" +%d%%" % o.bonus_percent) if o.bonus_percent else ""}</td>'
                         f'<td>{_order_badge(o.status)}</td>'
                         f'<td class="muted u-fs12">{escape(o.gateway or "-")}</td>'
                         f'<td class="muted u-fs12">{o.created_at:%m-%d %H:%M}</td>'
                         f'<td><div class="rowactions">{markpaid}'
                         + (f'<a class="btn ghost sm" href="/admin/credit-entry/list'
                            f'?search={escape(o.user_id)}">Sổ credit</a>'
                            if o.credited else '')
                         + f'</div></td></tr>')
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
                f'<div class="actions"><a class="btn ghost" href="/admin/doanh-thu">Doanh thu</a>'
                f'<a class="btn ghost" href="/admin/goi">Gói nạp</a></div></div>'
                f'<div class="tabs">{tabs}</div>'
                f'<div class="tablewrap" tabindex="0"><table class="ui-table"><thead><tr>'
                f'<th>Mã đơn</th><th>User</th><th>Tiền</th><th>Credit</th><th>Trạng thái</th>'
                f'<th>Cổng</th><th>Tạo lúc</th><th class="u-phai">Thao tác</th></tr></thead>'
                f'<tbody>{rows or "<tr><td colspan=8 class='muted o-trong'><span class=o-trong-chu>Chưa có đơn.</span></td></tr>"}'
                f'</tbody></table></div></div>')
        return HTMLResponse(_admin_shell(
            "Đơn hàng", "don_hang", body,
            thanh_cong=request.query_params.get("ok") or "",
            loi=request.query_params.get("loi") or ""))

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
            truoc = billing.lay_don_theo_code(db, code)
            da_cong_roi = bool(truoc and truoc.credited)
            don = billing.ghi_nhan_tra(db, code, by="admin")   # idempotent
            if don is None:
                tin = f"loi=Khong tim thay don #{code}."
            elif da_cong_roi:
                # Idempotent nên lần bấm thứ hai KHÔNG cộng đôi. Nhưng im lặng
                # chuyển hướng thì người bấm không biết là mình vừa không làm gì
                # — và lần sau họ sẽ bấm tiếp.
                tin = (f"ok=Don %23{code} da duoc cong credit tu truoc. "
                       f"Khong cong lan hai.")
            else:
                # ⭐ Nhật ký admin cho mark-paid. Trước đợt này thao tác TIỀN này
                #    chỉ để lại dấu vết trong `order.note` ("xac nhan boi admin")
                #    và trong bút toán credit — không có dòng nào trong nhật ký
                #    admin, nên câu "ai xác nhận đơn này, lúc nào" không tra được
                #    ở nơi người ta sẽ đi tìm. Xem `01_LIVE_EVIDENCE.md` E-03.
                ghi_nhat_ky(db, request, "xac_nhan_don_da_tra", str(code),
                            f"{don.credits} credit cho {don.user_id}")
                tin = (f"ok=Da xac nhan don %23{code}. "
                       f"Cong {don.credits:,} credit cho khach.")
            db.commit()
        finally:
            try: next(gen)
            except StopIteration: pass
        from urllib.parse import quote
        khoa, gt = tin.split("=", 1)
        return RedirectResponse(f"/admin/don?{khoa}={quote(gt)}", status_code=303)


class _AdminLTT(Admin):
    """SQLAdmin có trang chủ `/admin/` của riêng nền tảng.

    `/admin/` đã có chủ: gói đăng ký `Route("/", endpoint=self.index)` và
    `index` render `sqladmin/index.html`. Docstring của chính gói ghi
    *"Index route which can be overridden to create dashboards."* — nên đây là
    điểm mở rộng chính thức, không phải một mẹo.

    Hai phương án còn lại đều tệ hơn và đã bị loại ở
    `docs/admin_mvp_v3/04_EXTENSION_CONTRACT.md` §4: ghi đè
    `sqladmin/index.html` khiến Tổng quan thành trang DUY NHẤT đội vỏ Tabler;
    còn đặt trang ở `/admin/tong-quan` rồi chuyển hướng `/admin/` thì thêm một
    redirect mà ma trận tương thích đã chốt là 0.

    ⚠️ Đây mới là bản TỐI THIỂU của lô C0: nó chỉ điều hướng, không có một chỉ
    số nào. Hàng đợi chú ý là hợp đồng P1 và thuộc lô C10 — làm nó bây giờ là
    dựng chín liên kết sâu tới chín trang chưa chuyển xong.
    """

    @_login_required
    async def index(self, request: Request):
        from platform_core import admin_console
        from server.templating import templates

        gen = get_session(); db = next(gen)
        try:
            hang_doi = admin_console.hang_doi_chu_y(db)
            nhat_ky = db.query(NhatKyAdmin).order_by(
                NhatKyAdmin.created_at.desc()).limit(8).all()
        except Exception as exc:
            # ⭐ Một nguồn đọc không được thì ô đó nói "không lấy được" — KHÔNG
            #    hiện 0. Số 0 ở một ô chú ý nghĩa là "mọi thứ ổn", và nói điều đó
            #    trong khi thật ra ta không biết là kiểu nói dối bằng số mà
            #    `05_PAGE_CONTRACT_MATRIX.md` Phần IV cấm.
            #    Nhưng "không làm sập trang" khác với "nuốt luôn lý do": trang
            #    vẫn mở được, còn lý do đi vào log để còn sửa được.
            _log.warning("Tong quan admin: khong doc duoc hang doi chu y: %s", exc)
            hang_doi, nhat_ky = None, None
        finally:
            try: next(gen)
            except StopIteration: pass

        than = templates.env.get_template("admin/tong_quan.html").render(
            hang_doi=hang_doi, nhat_ky=nhat_ky, mien=_MIEN_TONG_QUAN)
        return HTMLResponse(_admin_shell(
            "Tổng quan", "tong_quan", than,
            tieu_de="Tổng quan",
            mo_ta="Việc gì cần bạn ngay bây giờ, và mở ở đâu để xử."))


#: Sáu miền của trang quản trị — đích, nhãn, một câu nói nó trả lời việc gì.
#: Cố ý KHÔNG có con số nào: hàng đợi chú ý là hợp đồng P1 (lô C10), và một ô
#: chỉ số không có read-model đứng sau là đúng thứ `06b` cấm.
_MIEN_TONG_QUAN = (
    ("/admin/nguoi-dung", "Khách hàng", "Tra cứu một khách và toàn cảnh của họ."),
    ("/admin/doanh-thu", "Tài chính", "Đơn nạp, sổ credit, gói nạp."),
    ("/admin/api-tong-quan", "API Platform", "Truy cập, quản trị, vận hành, giá."),
    ("/admin/apikeys", "Vận hành", "Provider credentials, model, job."),
    ("/admin/nhat-ky-admin/list", "Hệ thống", "Nhật ký admin và tình trạng."),
)


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
    admin = _AdminLTT(
        app,
        engine,
        title="LTT AI Studio — Quản trị",
        authentication_backend=AdminAuth(secret_key=session_secret),
        templates_dir=_adm_tpl,   # override sqladmin/base.html -> theme dark (UX-1)
    )
    # Trang SQLAdmin dựng bằng Jinja env RIÊNG của gói, nên nó không thấy
    # `asset_ver` của nền tảng lẫn cây điều hướng của ta. Bơm hai thứ đó vào đây
    # là cách duy nhất để nửa SQLAdmin và nửa trang tự viết dùng CÙNG một nguồn
    # điều hướng — trước đợt này nửa SQLAdmin có năm thẻ <a> viết tay riêng, và
    # nó nạp `ltt.css` KHÔNG kèm `?v=`, tức sau mỗi lần đổi CSS nó phục vụ bản
    # cũ tới hết TTL của Cloudflare (CLAUDE.md quy tắc 6).
    from server.routes.admin._chung import dieu_huong as _dh
    admin.templates.env.globals.update(asset_ver=_asset_ver(), _=__import__("server.templating").templating.templates.env.globals["_"],
                                       adm_nav=_dh("tong_quan", apps=getattr(app.state, "loaded_apps", ()))["thanh_ben"], sqladmin_ver=__import__("sqladmin").__version__)
    admin.add_view(UserAdmin)
    admin.add_view(CreditEntryAdmin)
    admin.add_view(GrantCreditView)
    admin.add_view(ApiKeysConsole)
    admin.add_view(ChiTietNguoiDungView)
    admin.add_view(NhatKyAdminView)
    admin.add_view(ApiKeyAdmin)
    admin.add_view(AddApiKeyView)
    admin.add_view(SuaApiKeyView)
    admin.add_view(ApiKeyActionView)
    admin.add_view(ModelsView)
    admin.add_view(AppAccessAdmin)
    admin.add_view(JobAdmin)
    admin.add_view(SessionAdmin)
    admin.add_view(PlatformInfoAdmin)
    # Khu API platform sống ở `server/admin_api.py`: cùng vỏ, cùng nhật ký, cùng
    # cổng quyền, nhưng là một miền khác — và file này đã đủ dài (EXT-13).
    from server.admin_api import VIEWS as _API_VIEWS

    for _view in _API_VIEWS:
        admin.add_view(_view)
    # Miền mới tự khai view của nó ở `server/routes/admin/<mien>.py` và gom vào
    # `server.routes.admin.VIEWS`. Thêm một trang KHÔNG phải sửa chỗ này.
    from server.routes.admin import VIEWS as _MIEN_VIEWS

    for _domain_view in _MIEN_VIEWS:
        admin.add_view(_domain_view)
    admin.add_view(RevenueView)
    admin.add_view(PackagesView)
    admin.add_view(OrdersView)
    return True
