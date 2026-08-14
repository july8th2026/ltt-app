"""server/admin_api.py — khu quản trị dành riêng cho API platform (EXT-13).

Vì sao tách khỏi `server/admin.py`
----------------------------------

`admin.py` đã 1.174 dòng và lo chuyện vận hành nền tảng: người dùng, sổ credit,
khoá provider, đơn hàng. Khu API là một miền khác — khoá của **khách**, project
của khách, độ phơi bày của tool — và nhét thêm vào cùng một file là cách một
file route trở thành nơi mọi thứ rơi vào (AGENTS.md mục 8: đã có file route
1.799 dòng vì đúng cơ chế này).

Nghiệp vụ **không** nằm ở đây. Mọi truy vấn và mọi luật nằm ở
`platform_core/public_api/admin_console.py`; file này chỉ đọc request, kiểm
CSRF, gọi service, dựng HTML và ghi nhật ký.

Ba luật của khu này
-------------------

**Không có đường nào lộ bí mật.** Không hiện lại khoá, không hiện secret
webhook, không hiện credential provider. Máy chủ chỉ giữ dấu vân tay một chiều
của khoá; một trang quản trị "tra lại được khoá" sẽ là một lời nói dối, hoặc
tệ hơn, một đường rò.

**Mọi thao tác ghi đều để lại dấu vết.** Cùng một transaction với thay đổi, qua
`ghi_nhat_ky` (F-06) — nếu không ghi được nhật ký thì thao tác cũng không nên
coi là đã xảy ra.

**Thao tác nguy hiểm phải nói lý do và phải xác nhận.** Thu hồi khoá là một
chiều: nó làm hỏng tích hợp đang chạy của một khách hàng thật. Dòng nhật ký sẽ
được đọc lại nhiều tháng sau bởi người không có mặt lúc đó, nên "đã thu hồi"
mà không kèm lý do là một sự kiện không có ý nghĩa.
"""
from __future__ import annotations

from markupsafe import escape
from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from platform_core.db import get_session
from platform_core.public_api import admin_console

_OK = "var(--ok)"
_WARN = "var(--warn)"
_ERR = "var(--err)"


def _session():
    gen = get_session()
    return gen, next(gen)


def _close(gen) -> None:
    try:
        next(gen)
    except StopIteration:
        pass


def _config():
    from platform_core.public_api.config import load_public_api_config

    return load_public_api_config()


def _int(request: Request, name: str, default: int) -> int:
    try:
        return int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        return default


def _when(value) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "—"


#: Cùng hình dạng thẻ số mà trang Doanh thu đã dùng — một admin không nên có
#: hai cách vẽ cùng một con số.
_TILES = ('<div class="grid" style="grid-template-columns:'
          'repeat(auto-fill,minmax(196px,1fr));gap:12px">')
_COLS = ('<div class="grid" style="grid-template-columns:'
         'repeat(auto-fit,minmax(320px,1fr))">')


def _stat(label: str, value, hint: str = "", colour: str = "") -> str:
    style = f';color:{colour}' if colour else ""
    note = (f'<div class="dim" style="font-size:11px">{escape(hint)}</div>'
            if hint else "")
    return (f'<div class="ui-card"><div class="dim">{escape(label)}</div>'
            f'<div class="tnum" style="font-size:24px;font-weight:700{style}">'
            f'{escape(str(value))}</div>{note}</div>')


def _pager(page, base: str) -> str:
    """Trang trước/sau + tổng số. Tổng số là con số quyết định hành động:
    "12 khoá" và "50 khoá đầu của 4.000" dẫn tới hai việc khác nhau."""
    if page.total <= page.limit:
        return f'<p class="muted">{page.total} dòng.</p>'
    join = "&" if "?" in base else "?"
    prev = (f'<a class="btn ghost sm" href="{base}{join}offset={page.prev_offset}">'
            f'← Trước</a>' if page.offset else "")
    nxt = (f'<a class="btn ghost sm" href="{base}{join}offset={page.next_offset}">'
           f'Sau →</a>' if page.has_more else "")
    first = page.offset + 1 if page.rows else 0
    return (f'<div class="rowactions" style="margin-top:12px">{prev}{nxt}'
            f'<span class="muted">{first}–{page.offset + len(page.rows)} '
            f'/ {page.total}</span></div>')


def _mode_chip(mode: str) -> str:
    if str(mode) == "test":
        return '<span class="chip v">Test</span>'
    return '<span class="chip m">Live</span>'


def _key_badge(status: str) -> str:
    cls = {"active": "b-ok", "disabled": "b-grey", "revoked": "b-err",
           "expired": "b-warn"}.get(status, "b-grey")
    return f'<span class="badge {cls}"><span class="dot"></span>{escape(status)}</span>'


class ApiOverviewView(BaseView):
    """Con số đầu tiên một người vận hành nhìn vào."""

    name = "API — Tổng quan"
    icon = "fa-solid fa-gauge"

    @expose("/api-tong-quan", methods=["GET"])
    async def page(self, request: Request):
        hours = _int(request, "hours", 24)
        gen, db = _session()
        try:
            data = admin_console.overview(db, hours=hours)
            by_tool = admin_console.jobs_by_tool(db, hours=hours)
        finally:
            _close(gen)

        keys = data["keys"]
        credit = data["credit"]
        hooks = data["webhooks"]
        failed = data["requests_failed"]

        cards = "".join([
            _stat("Tài khoản có khoá", data["accounts_with_keys"]),
            _stat("Khoá live đang chạy", keys["live"],
                  f'{keys["test"]} test · {keys["revoked"]} đã thu hồi'),
            _stat("Project đang hoạt động", data["projects_active"]),
            _stat("Credit khách đã trả", credit["net_charged"],
                  f'giữ {credit["held"]} · hoàn {credit["refunded"]}'),
            _stat("Job xong", data["jobs"]["succeeded"], colour=_OK),
            _stat("Job hỏng", data["jobs"]["failed"],
                  colour=_ERR if data["jobs"]["failed"] else ""),
            _stat("Lời gọi hỏng", failed,
                  "trong số đã ghi nhật ký",
                  colour=_ERR if failed else ""),
            _stat("Webhook chết", hooks["dead"],
                  f'{hooks["pending"]} đang chờ · {hooks["subscriptions"]} đăng ký',
                  colour=_ERR if hooks["dead"] else ""),
        ])

        codes = "".join(
            f'<tr><td class="mono">{escape(code)}</td>'
            f'<td class="tnum">{count}</td></tr>'
            for code, count in data["failures_by_code"])
        codes = codes or ('<tr><td colspan="2" class="muted">Không có lời gọi '
                          'nào hỏng trong khoảng này.</td></tr>')

        tools = ""
        for row in by_tool:
            total = row["done"] + row["error"] + row["other"]
            colour = _ERR if row["error"] else _OK
            tools += (f'<tr><td class="mono">{escape(row["job_type"])}</td>'
                      f'<td class="tnum">{total}</td>'
                      f'<td class="tnum" style="color:{colour}">{row["error"]}'
                      f'</td></tr>')
        tools = tools or ('<tr><td colspan="3" class="muted">Chưa có job nào '
                          'trong khoảng này.</td></tr>')

        windows = "".join(
            f'<a class="{"on" if hours == h else ""}" '
            f'href="/admin/api-tong-quan?hours={h}">{label}</a>'
            for h, label in ((1, "1 giờ"), (24, "24 giờ"), (168, "7 ngày"),
                             (720, "30 ngày")))

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span></div>'
            f'<div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Tổng quan</h1>'
            f'<p>Số liệu {escape(str(hours))} giờ gần nhất. Nhật ký request chỉ '
            f'ghi lời gọi hỏng và lời gọi ghi dữ liệu (EXT-09), nên "lời gọi '
            f'hỏng" là số tuyệt đối chứ không phải tỉ lệ trên toàn bộ traffic.'
            f'</p></div></div>'
            f'<div class="tabs">{windows}</div>'
            f'{_TILES}{cards}</div>'
            f'{_COLS}'
            f'<section><h2 style="margin:22px 0 10px">Mã lỗi hay gặp</h2>'
            f'<div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Mã</th><th>Số lần</th>'
            f'</tr></thead><tbody>{codes}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Job theo loại</h2>'
            f'<div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Loại job</th>'
            f'<th>Tổng</th><th>Hỏng</th></tr></thead><tbody>{tools}</tbody>'
            f'</table></div></section></div></div>')
        return HTMLResponse(_admin_shell("API — Tổng quan", "api_overview",
                                         body))


class ApiAccountsView(BaseView):
    """Ai đang dùng API, và một trang gom mọi thứ về một người trong số họ."""

    name = "API — Tài khoản"
    icon = "fa-solid fa-users"

    @expose("/api-tai-khoan", methods=["GET"])
    async def page(self, request: Request):
        user_id = request.query_params.get("user", "")
        if user_id:
            return await self._detail(request, user_id)

        query = request.query_params.get("q", "")
        limit, offset = admin_console.clamp_page(
            request.query_params.get("limit"),
            request.query_params.get("offset"))
        gen, db = _session()
        try:
            page = admin_console.accounts_page(db, query=query, limit=limit,
                                               offset=offset)
        finally:
            _close(gen)

        rows = ""
        for row in page.rows:
            user = row["user"]
            rows += (
                f'<tr><td><a href="/admin/api-tai-khoan?user={escape(user.id)}">'
                f'{escape(user.email)}</a></td>'
                f'<td class="tnum">{row["keys"]}</td>'
                f'<td class="tnum">{row["projects"]}</td>'
                f'<td class="tnum">{row["held_in_window"]}</td>'
                f'<td class="muted">{_when(row["newest_key_at"])}</td>'
                f'<td><a class="btn ghost sm" '
                f'href="/admin/api-khoa?q={escape(user.email)}">Khoá</a></td>'
                f'</tr>')
        rows = rows or ('<tr><td colspan="6" class="muted" '
                        'style="padding:26px;text-align:center">'
                        'Chưa có tài khoản nào cấp khoá API.</td></tr>')

        base = f'/admin/api-tai-khoan?q={escape(query)}'
        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span></div>'
            f'<div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Tài khoản</h1>'
            f'<p>Chỉ những tài khoản đã cấp ít nhất một khoá API. Danh sách '
            f'người dùng đầy đủ ở trang Người dùng.</p></div></div>'
            f'<form method="get" class="job-filters">'
            f'<input name="q" value="{escape(query)}" placeholder="email…">'
            f'<button class="btn ghost sm">Tìm</button></form>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Tài khoản</th><th>Khoá</th><th>Project</th>'
            f'<th>Credit đã giữ (7 ngày)</th><th>Khoá mới nhất</th><th></th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
            f'{_pager(page, base)}</div>')
        return HTMLResponse(_admin_shell("API — Tài khoản", "api_accounts",
                                         body))

    async def _detail(self, request: Request, user_id: str):
        gen, db = _session()
        try:
            data = admin_console.account_detail(db, user_id=user_id)
        finally:
            _close(gen)
        if data is None:
            return HTMLResponse("Không thấy tài khoản.", status_code=404)

        user = data["user"]
        projects = "".join(
            f'<tr><td>{escape(p.name)}</td><td class="mono">{escape(p.slug)}'
            f'</td><td>{escape(p.status)}</td>'
            f'<td class="muted">{_when(p.created_at)}</td></tr>'
            for p in data["projects"]) or (
            '<tr><td colspan="4" class="muted">Chưa có project.</td></tr>')

        keys = "".join(
            f'<tr><td class="mono">'
            f'<a href="/admin/api-khoa?key={escape(k.key_id)}">'
            f'{escape(k.key_id[:12])}…</a></td>'
            f'<td>{escape(k.name or "—")}</td>'
            f'<td>{_mode_chip(getattr(k, "mode", "live"))}</td>'
            f'<td>{_key_badge(k.status())}</td>'
            f'<td class="muted">{_when(k.last_used_at)}</td></tr>'
            for k in data["keys"]) or (
            '<tr><td colspan="5" class="muted">Chưa có khoá.</td></tr>')

        requests = "".join(
            f'<tr><td class="muted">{_when(r.created_at)}</td>'
            f'<td class="mono">{escape(r.method)} {escape(r.route)}</td>'
            f'<td class="tnum">{r.status}</td>'
            f'<td class="mono muted">{escape(r.code or "")}</td>'
            f'<td class="mono muted">{escape(r.request_id[:12])}</td></tr>'
            for r in data["recent_requests"]) or (
            '<tr><td colspan="5" class="muted">Chưa có lời gọi nào được '
            'ghi.</td></tr>')

        budgets = "".join(
            f'<tr><td>{escape(b.scope)}</td><td class="tnum">{b.amount}</td>'
            f'<td>{escape(b.period)}</td>'
            f'<td>{"cứng" if b.hard_cap else "mềm"}</td></tr>'
            for b in data["budgets"]) or (
            '<tr><td colspan="4" class="muted">Khách chưa đặt ngân sách '
            'nào.</td></tr>')

        hooks = "".join(
            f'<tr><td class="mono">{escape(s.url)}</td>'
            f'<td>{"bật" if s.enabled else "tắt"}</td>'
            f'<td class="muted">{_when(s.created_at)}</td></tr>'
            for s in data["subscriptions"]) or (
            '<tr><td colspan="3" class="muted">Không có webhook.</td></tr>')

        cards = "".join([
            _stat("Số dư", data["balance"]),
            _stat("Khoá", len(data["keys"])),
            _stat("Project", len(data["projects"])),
            _stat("Lời gọi hỏng (7 ngày)", data["failures_in_window"],
                  colour=_ERR if data["failures_in_window"] else ""),
        ])

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>{escape(user.email)}</h1>'
            f'<p class="mono muted">{escape(user.id)}</p></div>'
            f'<div class="actions">'
            # `q`, not `id`: trang chi tiết người dùng nhận "email hoặc user id"
            # qua đúng một tham số. Đặt sai tên thì nút vẫn mở ra một trang 200
            # — chỉ là trang tìm kiếm rỗng, nên hỏng mà không ai thấy hỏng.
            f'<a class="btn ghost" href="/admin/nguoi-dung?q={escape(user.id)}">'
            f'Hồ sơ đầy đủ</a>'
            f'<a class="btn ghost" href="/admin/api-tai-khoan">← Danh sách</a>'
            f'</div></div>'
            f'{_TILES}{cards}</div>'
            f'<section><h2 style="margin:22px 0 10px">Project</h2><div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Tên</th><th>Slug</th>'
            f'<th>Trạng thái</th><th>Tạo lúc</th></tr></thead>'
            f'<tbody>{projects}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Khoá</h2><div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Mã khoá</th><th>Tên</th>'
            f'<th>Môi trường</th><th>Trạng thái</th><th>Dùng lần cuối</th>'
            f'</tr></thead><tbody>{keys}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Ngân sách khách tự đặt</h2><div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Phạm vi</th><th>Mức</th>'
            f'<th>Chu kỳ</th><th>Kiểu</th></tr></thead><tbody>{budgets}</tbody>'
            f'</table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Webhook</h2><div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>URL</th><th>Trạng thái</th>'
            f'<th>Tạo lúc</th></tr></thead><tbody>{hooks}</tbody></table>'
            f'</div></section>'
            f'<section><h2 style="margin:22px 0 10px">20 lời gọi gần nhất được ghi</h2>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Lúc</th><th>Route</th><th>HTTP</th><th>Mã</th>'
            f'<th>Correlation ID</th></tr></thead><tbody>{requests}</tbody>'
            f'</table></div></section></div>')
        return HTMLResponse(_admin_shell(user.email, "api_accounts", body))


class ApiKeysAdminView(BaseView):
    """Mọi credential của khách, và hai thao tác một người vận hành cần."""

    name = "API — Khoá"
    icon = "fa-solid fa-key"

    @expose("/api-khoa", methods=["GET"])
    async def page(self, request: Request):
        key_id = request.query_params.get("key", "")
        if key_id:
            return await self._detail(request, key_id)

        query = request.query_params.get("q", "")
        status = request.query_params.get("status", "")
        mode = request.query_params.get("mode", "")
        limit, offset = admin_console.clamp_page(
            request.query_params.get("limit"),
            request.query_params.get("offset"))
        gen, db = _session()
        try:
            page = admin_console.keys_page(db, query=query, status=status,
                                           mode=mode, limit=limit,
                                           offset=offset)
        finally:
            _close(gen)

        rows = ""
        for row in page.rows:
            key, user = row["key"], row["user"]
            project = row["project"]
            rows += (
                f'<tr><td class="mono">'
                f'<a href="/admin/api-khoa?key={escape(key.key_id)}">'
                f'{escape(key.key_id[:12])}…</a></td>'
                f'<td>{escape(key.name or "—")}</td>'
                f'<td><a href="/admin/api-tai-khoan?user={escape(user.id)}">'
                f'{escape(user.email)}</a></td>'
                f'<td>{escape(project.name if project else "—")}</td>'
                f'<td>{_mode_chip(getattr(key, "mode", "live"))}</td>'
                f'<td>{_key_badge(row["status"])}</td>'
                f'<td class="muted">{_when(key.last_used_at)}</td></tr>')
        rows = rows or ('<tr><td colspan="7" class="muted" '
                        'style="padding:26px;text-align:center">'
                        'Không có khoá nào khớp bộ lọc.</td></tr>')

        def option(name: str, value: str, label: str, chosen: str) -> str:
            sel = " selected" if value == chosen else ""
            return f'<option value="{value}"{sel}>{label}</option>'

        status_options = "".join(
            option("status", value, label, status)
            for value, label in (("", "Mọi trạng thái"), ("active", "Đang chạy"),
                                 ("disabled", "Đã tắt"), ("revoked", "Đã thu hồi"),
                                 ("expired", "Hết hạn")))
        mode_options = "".join(
            option("mode", value, label, mode)
            for value, label in (("", "Cả hai môi trường"), ("live", "Live"),
                                 ("test", "Test")))

        base = (f'/admin/api-khoa?q={escape(query)}&status={escape(status)}'
                f'&mode={escape(mode)}')
        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Khoá</h1>'
            f'<p>Máy chủ chỉ giữ dấu vân tay một chiều của khoá, nên không có '
            f'đường nào xem lại được chuỗi bí mật — kể cả từ đây. Khách mất '
            f'khoá thì tạo khoá mới.</p></div></div>'
            f'<form method="get" class="job-filters">'
            f'<input name="q" value="{escape(query)}" '
            f'placeholder="email, mã khoá hoặc tên…">'
            f'<select name="status">{status_options}</select>'
            f'<select name="mode">{mode_options}</select>'
            f'<button class="btn ghost sm">Lọc</button></form>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Mã khoá</th><th>Tên</th><th>Chủ</th><th>Project</th>'
            f'<th>Môi trường</th><th>Trạng thái</th><th>Dùng lần cuối</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>'
            f'{_pager(page, base)}</div>')
        return HTMLResponse(_admin_shell("API — Khoá", "api_keys", body))

    async def _detail(self, request: Request, key_id: str):
        from server.auth.csrf import issue_csrf_token

        gen, db = _session()
        try:
            key = admin_console.key_by_id(db, key_id)
            if key is None:
                return HTMLResponse("Không thấy khoá.", status_code=404)
            usage = admin_console.key_usage(db, key_id=key.key_id)
            from platform_core.models import User

            owner = db.get(User, key.user_id)
            status = key.status()
            snapshot = {
                "key_id": key.key_id, "name": key.name or "",
                "mode": getattr(key, "mode", "live"),
                "scopes": list(key.scopes or ()),
                "allowed_tools": list(key.allowed_tools or ()),
                "allowed_ips": list(key.allowed_ips or ()),
                "created_at": key.created_at, "expires_at": key.expires_at,
                "last_used_at": key.last_used_at,
                "email": owner.email if owner else "",
                "user_id": key.user_id,
            }
        finally:
            _close(gen)

        token = issue_csrf_token(request)
        error = request.query_params.get("err", "")
        note = (f'<p class="badge b-err" style="display:block;padding:10px">'
                f'{escape(error)}</p>' if error else "")

        recent = "".join(
            f'<tr><td class="muted">{_when(r.created_at)}</td>'
            f'<td class="mono">{escape(r.method)} {escape(r.route)}</td>'
            f'<td class="tnum">{r.status}</td>'
            f'<td class="mono muted">{escape(r.code or "")}</td></tr>'
            for r in usage["recent"]) or (
            '<tr><td colspan="4" class="muted">Khoá này chưa có lời gọi nào '
            'được ghi.</td></tr>')

        def action_form(op: str, label: str, danger: bool) -> str:
            confirm = ""
            if danger:
                confirm = ('<label class="muted" style="display:block;'
                           'margin:6px 0"><input type="checkbox" '
                           'name="confirm" value="1"> Tôi hiểu thao tác này '
                           'không đảo ngược được và sẽ làm hỏng tích hợp đang '
                           'chạy của khách.</label>')
            cls = "btn btn-danger" if danger else "btn ghost"
            return (
                f'<form method="post" action="/admin/api-khoa-action" '
                f'style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px">'
                f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
                f'<input type="hidden" name="key_id" '
                f'value="{escape(snapshot["key_id"])}">'
                f'<input type="hidden" name="op" value="{op}">'
                f'<input name="reason" placeholder="Lý do (bắt buộc, '
                f'≥ {admin_console.MIN_REASON} ký tự)" '
                f'minlength="{admin_console.MIN_REASON}" required>'
                f'{confirm}<button class="{cls} sm">{escape(label)}</button>'
                f'</form>')

        if status == "revoked":
            actions = ('<p class="muted">Khoá đã thu hồi. Không còn thao tác '
                       'nào — thu hồi là một chiều.</p>')
        elif status == "disabled":
            actions = action_form("enable", "Bật lại", False) + action_form(
                "revoke", "Thu hồi vĩnh viễn", True)
        else:
            actions = action_form("disable", "Tắt tạm thời", False) + action_form(
                "revoke", "Thu hồi vĩnh viễn", True)

        cards = "".join([
            _stat("Lời gọi (7 ngày)", usage["calls"]),
            _stat("Trong đó hỏng", usage["failed"],
                  colour=_ERR if usage["failed"] else ""),
            _stat("Credit đã tiêu", usage["credit_spent"]),
        ])

        def chips(values) -> str:
            return " ".join(f'<code>{escape(v)}</code>' for v in values) or "—"

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1 class="mono">{escape(snapshot["key_id"])}</h1>'
            f'<p>{escape(snapshot["name"] or "không đặt tên")} · '
            f'<a href="/admin/api-tai-khoan?user={escape(snapshot["user_id"])}">'
            f'{escape(snapshot["email"])}</a> · '
            f'{_mode_chip(snapshot["mode"])} {_key_badge(status)}</p></div>'
            f'<div class="actions">'
            f'<a class="btn ghost" href="/admin/api-khoa">← Danh sách</a>'
            f'</div></div>{note}'
            f'{_TILES}{cards}</div>'
            f'<section><h2 style="margin:22px 0 10px">Thông tin</h2><div class="tablewrap">'
            f'<table class="ui-table"><tbody>'
            f'<tr><th>Phạm vi</th><td>{chips(snapshot["scopes"])}</td></tr>'
            f'<tr><th>Giới hạn công cụ</th>'
            f'<td>{chips(snapshot["allowed_tools"])}</td></tr>'
            f'<tr><th>Giới hạn IP</th>'
            f'<td>{chips(snapshot["allowed_ips"])}</td></tr>'
            f'<tr><th>Tạo lúc</th><td>{_when(snapshot["created_at"])}</td></tr>'
            f'<tr><th>Hết hạn</th><td>{_when(snapshot["expires_at"])}</td></tr>'
            f'<tr><th>Dùng lần cuối</th>'
            f'<td>{_when(snapshot["last_used_at"])}</td></tr>'
            f'</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Thao tác</h2>{actions}</section>'
            f'<section><h2 style="margin:22px 0 10px">10 lời gọi gần nhất</h2><div class="tablewrap">'
            f'<table class="ui-table"><thead><tr><th>Lúc</th><th>Route</th>'
            f'<th>HTTP</th><th>Mã</th></tr></thead><tbody>{recent}</tbody>'
            f'</table></div></section></div>')
        return HTMLResponse(_admin_shell(snapshot["key_id"], "api_keys", body))

    @expose("/api-khoa-action", methods=["POST"])
    async def action(self, request: Request):
        from server.admin import ghi_nhat_ky
        from server.auth.csrf import verify_csrf_token

        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)

        key_id = str(form.get("key_id") or "")
        op = str(form.get("op") or "")
        reason = str(form.get("reason") or "")
        confirmed = str(form.get("confirm") or "") == "1"
        back = f"/admin/api-khoa?key={key_id}"

        if op == "revoke" and not confirmed:
            return _redirect(back, "Thu hồi cần tích ô xác nhận.")

        gen, db = _session()
        try:
            key = admin_console.key_by_id(db, key_id)
            if key is None:
                return HTMLResponse("Không thấy khoá.", status_code=404)
            try:
                {"disable": admin_console.disable_key,
                 "enable": admin_console.enable_key,
                 "revoke": admin_console.revoke_key}[op](db, key, reason=reason)
            except KeyError:
                return HTMLResponse("Thao tác không hợp lệ.", status_code=400)
            except admin_console.AdminActionError as exc:
                db.rollback()
                return _redirect(back, str(exc))
            # Cùng transaction với thay đổi: một thao tác đã xảy ra mà nhật ký
            # thì không là đúng cái lỗ hổng F-06 sinh ra để bịt.
            ghi_nhat_ky(db, request, f"api_khoa_{op}",
                        doi_tuong=f"{key.key_id} ({key.user_id})",
                        chi_tiet=f"lý do: {reason.strip()}")
            db.commit()
        finally:
            _close(gen)
        return RedirectResponse(back, status_code=303)


class ApiToolsView(BaseView):
    """Tool nào đang mở, mở theo luật nào, và nó đang chạy ra sao."""

    name = "API — Công cụ"
    icon = "fa-solid fa-screwdriver-wrench"

    @expose("/api-cong-cu", methods=["GET"])
    async def page(self, request: Request):
        hours = _int(request, "hours", 168)
        config = _config()
        gen, db = _session()
        try:
            tools = admin_console.tools_page(db, config, hours=hours)
        finally:
            _close(gen)

        rows = ""
        for row in tools:
            if row["published"]:
                state = ('<span class="badge b-ok"><span class="dot"></span>'
                         'đang mở</span>')
            else:
                state = ('<span class="badge b-grey"><span class="dot"></span>'
                         'app khai nhưng deployment chưa mở</span>')
            dep = (f'<span class="chip v">{escape(row["deprecated"])}</span>'
                   if row["deprecated"] else "")
            colour = _ERR if row["failed"] else ""
            failed = (f'<span style="color:{colour}">{row["failed"]}</span>'
                      if colour else str(row["failed"]))
            rows += (f'<tr><td class="mono">{escape(row["name"])} {dep}</td>'
                     f'<td>{escape(row["app"])}</td>'
                     f'<td class="mono muted">{escape(row["execution_mode"])}'
                     f'</td><td>{state}</td>'
                     f'<td class="tnum">{row["calls"]}</td>'
                     f'<td class="tnum">{failed}</td></tr>')
        rows = rows or ('<tr><td colspan="6" class="muted" '
                        'style="padding:26px;text-align:center">'
                        'Chưa app nào khai tool ra API công khai.</td></tr>')

        exposed = sorted(config.exposed_tools)
        allowlist = " ".join(f'<code>{escape(name)}</code>'
                             for name in exposed) or "<em>rỗng</em>"

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Công cụ</h1>'
            f'<p>Hai điều kiện phải cùng đúng thì một tool mới gọi được: app '
            f'khai <code>api_exposed</code>, <b>và</b> deployment liệt kê nó '
            f'trong <code>LTT_PUBLIC_API_TOOLS</code>. Mặc định là đóng.</p>'
            f'</div></div>'
            f'<section><h2 style="margin:22px 0 10px">Allowlist của deployment này</h2>'
            f'<p>{allowlist}</p>'
            f'<p class="muted">Sửa ở <code>secrets/app.env</code> rồi khởi '
            f'động lại dịch vụ. Bật/tắt ngay tại chỗ (kill switch) là việc của '
            f'EXT-14, chưa có ở đây — nên trang này không hứa cái nút đó.</p>'
            f'</section>'
            f'<section><h2 style="margin:22px 0 10px">Tool ({escape(str(hours))} giờ gần nhất)</h2>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Tên công khai</th><th>App</th><th>Chế độ chạy</th>'
            f'<th>Phơi bày</th><th>Lời gọi</th><th>Hỏng</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div></section></div>')
        return HTMLResponse(_admin_shell("API — Công cụ", "api_tools", body))


def _redirect(path: str, message: str):
    from urllib.parse import quote

    join = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{join}err={quote(message)}",
                            status_code=303)


def _admin_shell(title: str, active: str, body: str) -> str:
    """Vỏ quản trị dùng chung. Import muộn để tránh vòng import với admin.py."""
    from server.admin import _admin_shell as shell

    return shell(title, active, body)


#: Đăng ký ở `server/admin.py`. Giữ danh sách ở đây để thêm một trang là sửa
#: một file, không phải hai.
VIEWS = (ApiOverviewView, ApiAccountsView, ApiKeysAdminView, ApiToolsView)

#: Mục điều hướng cho vỏ quản trị, chèn vào `_ADM_NAV`.
#: Hai chữ cái là thứ người ta nhận ra trước khi đọc nhãn, nên chúng phải khác
#: nhau: "AK" đã là APIKEYS (khoá của NỀN TẢNG) — dùng lại nó cho khoá của
#: KHÁCH là đúng hai thứ dễ nhầm nhất lại trông giống nhau nhất.
NAV = (
    ("__grp__", "", "API platform", ""),
    ("/admin/api-tong-quan", "AT", "API — Tổng quan", "api_overview"),
    ("/admin/api-tai-khoan", "TK", "API — Tài khoản", "api_accounts"),
    ("/admin/api-khoa", "KH", "API — Khoá", "api_keys"),
    ("/admin/api-cong-cu", "CC", "API — Công cụ", "api_tools"),
)
