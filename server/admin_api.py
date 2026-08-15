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

import logging

from markupsafe import escape
from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from platform_core.db import get_session
from platform_core.public_api.tables import (PRICE_ACTIVE,
                                             PRICE_DRAFT,
                                             PRICE_SCHEDULED)
from platform_core import leases
from platform_core.public_api import (admin_console, anomalies, costing,
                                      metrics, policy, pricing)

_log = logging.getLogger("ltt.admin.api")

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
            # Bộ đếm sống trong tiến trình, nên trước đây chúng mất khi khởi
            # động lại và mỗi tiến trình giữ một bản riêng không ai cộng. Đây là
            # đường đọc: cộng mọi tiến trình trong cửa sổ thời gian.
            do = metrics.aggregate(db, hours=hours)
            ai_bao_tri = leases.current_holder(db, name=leases.MAINTENANCE)
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

        dem = do["counters"]
        loi_5xx = dem.get("responses_5xx", 0)
        xac_thuc_hong = dem.get("auth_failure", 0)
        cho_hang_doi = do["latency"].get("queue_pickup_ms", {})
        van_hanh = "".join([
            _stat("Lỗi 5xx", loi_5xx, "nền tảng, không phải khách",
                  colour=_ERR if loi_5xx else ""),
            _stat("Xác thực hỏng", xac_thuc_hong, "khoá sai hoặc đã thu hồi",
                  colour=_ERR if xac_thuc_hong else ""),
            _stat("Bị chặn nhịp", dem.get("rate_limited", 0)),
            _stat("Bị công tắc chặn", dem.get("kill_switch_refused", 0)),
            _stat("Hết chỗ tài nguyên", dem.get("capacity_refused", 0)),
            _stat("Webhook gửi hỏng", dem.get("webhook_failed", 0),
                  colour=_ERR if dem.get("webhook_failed") else ""),
            _stat("Chờ vào hàng đợi",
                  f'{cho_hang_doi.get("avg_ms", 0)} ms',
                  f'cao nhất {cho_hang_doi.get("max_ms", 0)} ms'),
            _stat("Tiến trình đã gộp", do["processes"],
                  f'bảo trì: {escape(ai_bao_tri or "chưa ai giữ")}'),
            # Ràng buộc này trước đây chỉ nằm trong docstring của `limits.py`,
            # nên người mở tiến trình web thứ hai sẽ không bao giờ đọc tới nó.
            # Bộ đếm nhịp sống TRONG tiến trình: hai tiến trình web nghĩa là mỗi
            # khách được gấp đôi hạn mức, im lặng.
            _stat("Tiến trình web", do["web_processes"],
                  "phải là 1 — trần nhịp đếm trong tiến trình"
                  if do["web_processes"] > 1 else "worker: "
                  f'{do["worker_processes"]}',
                  colour=_ERR if do["web_processes"] > 1 else ""),
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
            f'<section><h2 style="margin:22px 0 10px">Vận hành</h2>'
            f'<p class="muted" style="margin:0 0 10px">Cộng từ mọi tiến trình '
            f'web và worker. Bộ đếm sống trong tiến trình và được xả xuống CSDL '
            f'mỗi phút, nên số ở đây tồn tại qua khởi động lại.</p>'
            f'{_TILES}{van_hanh}</section>'
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


def _error_note(request: Request) -> str:
    """Biểu ngữ lỗi sau một lần chuyển hướng. Rỗng khi không có gì để nói."""
    message = request.query_params.get("err", "")
    if not message:
        return ""
    return (f'<p class="badge b-err" style="display:block;padding:10px">'
            f'{escape(message)}</p>')


def _reason_form(action: str, token: str, op: str, label: str, *,
                 danger: bool = False, extra: dict | None = None) -> str:
    """Một nút thao tác luôn đi kèm ô lý do.

    Cùng khuôn với trang Khoá (EXT-13): thao tác ghi nào cũng phải để lại lý do,
    vì dòng nhật ký sẽ được đọc lại bởi người không có mặt lúc đó.
    """
    hidden = "".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in (extra or {}).items())
    cls = "btn btn-danger sm" if danger else "btn sm"
    return (f'<form method="post" action="{action}" '
            f'style="display:flex;gap:6px;align-items:center">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<input type="hidden" name="op" value="{escape(op)}">{hidden}'
            f'<input name="reason" required minlength="{policy.MIN_REASON}" '
            f'placeholder="Lý do (≥ {policy.MIN_REASON})">'
            f'<button class="{cls}">{escape(label)}</button></form>')


class ApiPolicyView(BaseView):
    """Hạn mức: ai được gọi bao nhiêu, và con số đó đến từ đâu."""

    name = "API - Chinh sach"
    icon = "fa-solid fa-sliders"

    @expose("/api-chinh-sach", methods=["GET"])
    async def page(self, request: Request):
        from server.auth.csrf import issue_csrf_token

        gen, db = _session()
        try:
            rows = policy.list_policies(db)
            data = [{"policy": row,
                     "assignments": policy.assignments_for(db, row.id)}
                    for row in rows]
            # Mức nền khi KHÔNG có ai cụ thể: đó là con số mọi tài khoản nhận
            # được, và là thứ đầu tiên người vận hành cần thấy.
            baseline = policy.resolve(db, config=_config())
        finally:
            _close(gen)

        token = issue_csrf_token(request)
        note = _error_note(request)

        def cell(value) -> str:
            return ('<span class="muted">kế thừa</span>' if value is None
                    else f'<span class="tnum">{value}</span>')

        rows_html = ""
        for item in data:
            row = item["policy"]
            targets = " ".join(
                f'<code>{escape(a.scope)}:{escape(a.subject_id[:8])}</code>'
                for a in item["assignments"]) or (
                    '<span class="muted">chưa gán</span>')
            default = ('<span class="chip i">mặc định</span>'
                       if row.is_default else "")
            rows_html += (
                f'<tr><td><b>{escape(row.name)}</b> {default}<br>'
                f'<span class="muted">{escape(row.description or "")}</span>'
                f'</td>'
                f'<td>{cell(row.rpm_read)}</td><td>{cell(row.rpm_write)}</td>'
                f'<td>{cell(row.rpm_create)}</td>'
                f'<td>{cell(row.max_active_jobs)}</td>'
                f'<td>{cell(row.daily_credit)}</td>'
                f'<td>{targets}</td>'
                f'<td>{_reason_form("/admin/api-chinh-sach-action", token, "delete", "Xoá", danger=True, extra={"policy_id": row.id})}</td>'
                f'</tr>')
        rows_html = rows_html or (
            '<tr><td colspan="8" class="muted" style="padding:26px;'
            'text-align:center">Chưa có chính sách nào — mọi tài khoản dùng '
            'mức nền của deployment.</td></tr>')

        baseline_rows = "".join(
            f'<tr><td class="mono">{escape(field)}</td>'
            f'<td class="tnum">{getattr(baseline, field)}</td>'
            f'<td class="muted">{escape(baseline.sources.get(field, ""))}</td>'
            f'</tr>' for field in policy.LIMIT_FIELDS)

        fields = "".join(
            f'<label style="display:inline-block;margin:0 12px 8px 0">'
            f'{escape(field)}<br><input name="{field}" inputmode="numeric" '
            f'placeholder="kế thừa" style="width:130px"></label>'
            for field in policy.LIMIT_FIELDS)

        choices = "".join(
            f'<option value="{escape(item["policy"].id)}">'
            f'{escape(item["policy"].name)}</option>' for item in data)

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Chính sách</h1>'
            f'<p>Chuỗi ưu tiên: <code>global → tier → user → project → '
            f'credential → tool</code>. Ô trống nghĩa là <b>kế thừa</b> bước '
            f'trước, không phải 0 — 0 là một hạn mức thật (nhịp 0 = từ chối tất '
            f'cả).</p></div></div>{note}'
            f'<section><h2 style="margin:22px 0 10px">Mức nền đang áp dụng</h2>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Hạn mức</th><th>Giá trị</th><th>Đến từ</th></tr></thead>'
            f'<tbody>{baseline_rows}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Chính sách</h2>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Tên</th><th>rpm read</th><th>rpm write</th>'
            f'<th>rpm create</th><th>job đồng thời</th><th>credit/ngày</th>'
            f'<th>Đã gán</th><th></th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Tạo chính sách</h2>'
            f'<form method="post" action="/admin/api-chinh-sach-action">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<input type="hidden" name="op" value="create">'
            f'<p><input name="name" placeholder="tên (vd: pro)" required> '
            f'<input name="description" placeholder="mô tả" size="40"> '
            f'<label><input type="checkbox" name="is_default" value="1"> '
            f'dùng làm tier mặc định</label></p><p>{fields}</p>'
            f'<p><input name="reason" size="46" required '
            f'minlength="{policy.MIN_REASON}" '
            f'placeholder="Lý do (bắt buộc, ≥ {policy.MIN_REASON} ký tự)"> '
            f'<button class="btn btn-primary sm">Tạo</button></p></form>'
            f'</section>'
            f'<section><h2 style="margin:22px 0 10px">Gán chính sách</h2>'
            f'<form method="post" action="/admin/api-chinh-sach-action">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<input type="hidden" name="op" value="assign">'
            f'<p><select name="policy_id">{choices}</select> '
            f'<select name="scope"><option value="user">user</option>'
            f'<option value="project">project</option>'
            f'<option value="key">key</option></select> '
            f'<input name="subject_id" placeholder="id của đối tượng" required> '
            f'<input name="reason" required minlength="{policy.MIN_REASON}" '
            f'placeholder="Lý do (≥ {policy.MIN_REASON})"> '
            f'<button class="btn sm">Gán</button></p></form></section></div>')
        return HTMLResponse(_admin_shell("API - Chinh sach", "api_policy",
                                         body))

    @expose("/api-chinh-sach-action", methods=["POST"])
    async def action(self, request: Request):
        from server.admin import ghi_nhat_ky
        from server.auth.csrf import verify_csrf_token

        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)

        op = str(form.get("op") or "")
        reason = str(form.get("reason") or "")
        back = "/admin/api-chinh-sach"
        if len(reason.strip()) < policy.MIN_REASON:
            return _redirect(back, "Phải ghi lý do cho thao tác này.")

        gen, db = _session()
        try:
            try:
                detail = _apply_policy_op(db, op, form)
            except policy.PolicyError as exc:
                db.rollback()
                return _redirect(back, str(exc))
            except KeyError:
                return HTMLResponse("Thao tác không hợp lệ.", status_code=400)
            ghi_nhat_ky(db, request, f"api_chinh_sach_{op}", doi_tuong=detail,
                        chi_tiet=f"ly do: {reason.strip()}")
            db.commit()
        finally:
            _close(gen)
        return RedirectResponse(back, status_code=303)


def _apply_policy_op(db, op: str, form) -> str:
    """Chạy một thao tác chính sách; trả mô tả để ghi nhật ký."""
    from platform_core.public_api.tables import ApiPolicy

    if op == "create":
        numbers = {field: str(form.get(field) or "").strip()
                   for field in policy.LIMIT_FIELDS
                   if str(form.get(field) or "").strip()}
        made = policy.create_policy(
            db, name=str(form.get("name") or ""),
            description=str(form.get("description") or ""),
            is_default=str(form.get("is_default") or "") == "1", **numbers)
        return f"{made.name} ({made.id})"
    if op == "assign":
        target = db.get(ApiPolicy, str(form.get("policy_id") or ""))
        if target is None:
            raise policy.PolicyError("Không thấy chính sách.")
        scope = str(form.get("scope") or "")
        subject = str(form.get("subject_id") or "")
        policy.assign(db, policy=target, scope=scope, subject_id=subject)
        return f"{target.name} -> {scope}:{subject}"
    if op == "delete":
        target = db.get(ApiPolicy, str(form.get("policy_id") or ""))
        if target is None:
            raise policy.PolicyError("Không thấy chính sách.")
        name = target.name
        policy.delete_policy(db, target)
        return f"{name} (da xoa)"
    raise KeyError(op)


class ApiKillSwitchView(BaseView):
    """Công tắc sự cố: tắt cái gì, vì sao, và tới bao giờ."""

    name = "API - Kill switch"
    icon = "fa-solid fa-power-off"

    @expose("/api-kill-switch", methods=["GET"])
    async def page(self, request: Request):
        from platform_core.public_api.tables import KILL_SCOPES
        from server.auth.csrf import issue_csrf_token

        gen, db = _session()
        try:
            rows = policy.active_switches(db)
        finally:
            _close(gen)

        token = issue_csrf_token(request)
        note = _error_note(request)

        rows_html = ""
        for row in rows:
            rows_html += (
                f'<tr><td><code>{escape(row.scope)}</code></td>'
                f'<td class="mono">{escape(row.subject or "—")}</td>'
                f'<td>{escape(row.reason)}</td>'
                f'<td class="muted">{escape(row.created_by or "—")}</td>'
                f'<td class="muted">{_when(row.created_at)}</td>'
                f'<td class="muted">{_when(row.expires_at)}</td>'
                f'<td>{_reason_form("/admin/api-kill-switch-action", token, "release", "Bật lại", extra={"switch_id": row.id})}</td>'
                f'</tr>')
        rows_html = rows_html or (
            '<tr><td colspan="7" class="muted" style="padding:26px;'
            'text-align:center">Không có công tắc nào đang bật. Đó là trạng '
            'thái bình thường.</td></tr>')

        options = "".join(f'<option value="{scope}">{scope}</option>'
                          for scope in KILL_SCOPES)
        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Kill switch</h1>'
            f'<p>Công tắc <b>không phải</b> hạn mức đặt về 0. Hạn mức là chính '
            f'sách thường trực; công tắc là công cụ xử lý sự cố — có người bật, '
            f'có lý do, và nên có hạn dùng. Phạm vi của mọi công tắc ở đây là '
            f'<code>/api/v1</code>; giao diện web không bị ảnh hưởng.</p>'
            f'</div></div>{note}'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Phạm vi</th><th>Đối tượng</th><th>Lý do</th><th>Ai bật</th>'
            f'<th>Bật lúc</th><th>Hết hiệu lực</th><th></th></tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>'
            f'<section><h2 style="margin:22px 0 10px">Bật một công tắc</h2>'
            f'<form method="post" action="/admin/api-kill-switch-action">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<input type="hidden" name="op" value="engage">'
            f'<p><select name="scope">{options}</select> '
            f'<input name="subject" size="46" placeholder="đối tượng (bỏ trống '
            f'với global_writes / maintenance)"></p>'
            f'<p><input name="reason" size="60" required '
            f'minlength="{policy.MIN_REASON}" placeholder="Lý do (bắt buộc, '
            f'≥ {policy.MIN_REASON} ký tự) — sẽ hiện cho khách"> '
            f'<input name="minutes" inputmode="numeric" style="width:180px" '
            f'placeholder="tự tắt sau (phút)"></p>'
            f'<p><label><input type="checkbox" name="confirm" value="1"> '
            f'Tôi hiểu thao tác này chặn lời gọi của khách hàng thật ngay lập '
            f'tức.</label></p>'
            f'<button class="btn btn-danger sm">Bật</button></form>'
            f'<p class="muted">Không đặt "tự tắt sau" thì công tắc là vĩnh viễn '
            f'cho tới khi có người tắt tay. Lỗi thường gặp nhất của một công tắc '
            f'sự cố là không ai nhớ tắt nó đi.</p></section></div>')
        return HTMLResponse(_admin_shell("API - Kill switch", "api_kill", body))

    @expose("/api-kill-switch-action", methods=["POST"])
    async def action(self, request: Request):
        from datetime import datetime, timedelta, timezone

        from server.admin import _email_admin, ghi_nhat_ky
        from server.auth.csrf import verify_csrf_token

        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)

        op = str(form.get("op") or "")
        reason = str(form.get("reason") or "")
        back = "/admin/api-kill-switch"
        if op == "engage" and str(form.get("confirm") or "") != "1":
            return _redirect(back, "Bật công tắc cần tích ô xác nhận.")
        if len(reason.strip()) < policy.MIN_REASON:
            return _redirect(back, "Phải ghi lý do cho thao tác này.")

        expires = None
        raw_minutes = str(form.get("minutes") or "").strip()
        if raw_minutes:
            try:
                expires = (datetime.now(timezone.utc)
                           + timedelta(minutes=max(1, int(raw_minutes))))
            except (TypeError, ValueError):
                return _redirect(back, "Số phút không hợp lệ.")

        gen, db = _session()
        try:
            try:
                if op == "engage":
                    row = policy.engage(
                        db, scope=str(form.get("scope") or ""),
                        subject=str(form.get("subject") or ""), reason=reason,
                        created_by=_email_admin(request), expires_at=expires)
                    detail = f"{row.scope}:{row.subject or '*'}"
                elif op == "release":
                    row = policy.switch_by_id(
                        db, str(form.get("switch_id") or ""))
                    if row is None:
                        return HTMLResponse("Không thấy công tắc.",
                                            status_code=404)
                    detail = f"{row.scope}:{row.subject or '*'}"
                    policy.release(db, row)
                else:
                    return HTMLResponse("Thao tác không hợp lệ.",
                                        status_code=400)
            except policy.PolicyError as exc:
                db.rollback()
                return _redirect(back, str(exc))
            ghi_nhat_ky(db, request, f"api_kill_{op}", doi_tuong=detail,
                        chi_tiet=f"ly do: {reason.strip()}")
            db.commit()
        finally:
            _close(gen)
        return RedirectResponse(back, status_code=303)


class ApiPricingView(BaseView):
    """Giá hiện tại, giá sắp tới, giá đã qua — và một chỗ thử không tốn tiền."""

    name = "API - Gia"
    icon = "fa-solid fa-tags"

    @expose("/api-gia", methods=["GET"])
    async def page(self, request: Request):
        from platform_core.public_api.catalog import build_catalog
        from server.auth.csrf import issue_csrf_token

        config = _config()
        catalog = build_catalog(config)
        chosen = request.query_params.get("tool", "")
        tool = next((item for item in catalog if item.name == chosen),
                    catalog[0] if catalog else None)

        gen, db = _session()
        try:
            line = (pricing.timeline(db, tool=tool.name)
                    if tool is not None else None)
            preview = (pricing.simulate(db, tool=tool,
                                        params=_example_input(tool))
                       if tool is not None else None)
        finally:
            _close(gen)

        token = issue_csrf_token(request)
        note = _error_note(request)

        tabs = "".join(
            f'<a class="{"on" if tool is not None and item.name == tool.name else ""}" '
            f'href="/admin/api-gia?tool={escape(item.name)}">{escape(item.name)}</a>'
            for item in catalog) or '<span class="muted">Chưa mở công cụ nào.</span>'

        def row(version, *, actions: bool) -> str:
            window = (f'{_when(version.effective_from)} → '
                      f'{_when(version.effective_until)}')
            bounds = " / ".join(str(x) for x in (
                version.min_credit if version.min_credit is not None else "—",
                version.max_credit if version.max_credit is not None else "—"))
            rounding = (f'{version.rounding} ({escape(version.rounding_mode)})'
                        if version.rounding else "—")
            buttons = ""
            if actions:
                if version.status in (PRICE_DRAFT,):
                    buttons += _reason_form(
                        "/admin/api-gia-action", token, "publish", "Phát hành",
                        extra={"version_id": version.id})
                if version.status in (PRICE_ACTIVE, PRICE_SCHEDULED):
                    buttons += _reason_form(
                        "/admin/api-gia-action", token, "retire", "Ngừng",
                        danger=True, extra={"version_id": version.id})
            return (f'<tr><td><b>{escape(version.label)}</b>'
                    f'{" · " + escape(version.model) if version.model else ""}'
                    f'<br><span class="muted">{escape(version.formula_ref or "")}'
                    f'</span></td>'
                    f'<td>{escape(version.status)}</td>'
                    f'<td class="muted">{window}</td>'
                    f'<td class="tnum">{bounds}</td>'
                    f'<td class="tnum">{rounding}</td>'
                    f'<td class="muted">{escape(version.published_by or "—")}'
                    f'</td><td>{buttons}</td></tr>')

        if line is None:
            body_rows = ('<tr><td colspan="7" class="muted">Chưa có công cụ '
                         'nào được mở.</td></tr>')
            upcoming = history = ""
        else:
            body_rows = (row(line.current, actions=True) if line.current
                         else '<tr><td colspan="7" class="muted">Chưa phát '
                              'hành phiên bản nào — giá vẫn do app tính, và '
                              'quote mang nhãn "unversioned".</td></tr>')
            upcoming = "".join(row(v, actions=True) for v in line.upcoming) or (
                '<tr><td colspan="7" class="muted">Không có gì đang chờ.</td></tr>')
            history = "".join(row(v, actions=False) for v in line.history) or (
                '<tr><td colspan="7" class="muted">Chưa có lịch sử.</td></tr>')

        head = ('<thead><tr><th>Nhãn</th><th>Trạng thái</th><th>Cửa sổ</th>'
                '<th>Sàn / trần</th><th>Làm tròn</th><th>Ai phát hành</th>'
                '<th></th></tr></thead>')

        sim = ""
        if preview is not None:
            sim = (f'<p>Cùng công thức mà báo giá thật dùng, với đầu vào ví dụ: '
                   f'<b class="tnum">{preview.credit}</b> credit'
                   f'{" (app tính " + str(preview.raw_credit) + ", bị chặn bởi "
                      + escape(preview.pricing_version) + ")" if preview.bounded else ""}'
                   f'. Không sinh báo giá, không trừ credit.</p>')

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Giá</h1>'
            f'<p>Phiên bản giá <b>không</b> tính giá. Giá vẫn do '
            f'<code>credit_cost()</code> của app tính; phiên bản ghi lại chế độ '
            f'nào đang có hiệu lực, kèm sàn/trần/làm tròn, rồi được đóng dấu '
            f'lên báo giá và job. Phát hành bản mới là <b>thêm dòng</b> và đóng '
            f'cửa sổ bản cũ — không sửa số của bản cũ, nên không có đường nào '
            f'đổi giá hồi tố.</p></div></div>{note}'
            f'<div class="tabs">{tabs}</div>'
            f'<section><h2 style="margin:22px 0 10px">Đang áp dụng</h2>'
            f'<div class="tablewrap"><table class="ui-table">{head}'
            f'<tbody>{body_rows}</tbody></table></div>{sim}</section>'
            f'<section><h2 style="margin:22px 0 10px">Sắp tới</h2>'
            f'<div class="tablewrap"><table class="ui-table">{head}'
            f'<tbody>{upcoming}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Lịch sử</h2>'
            f'<div class="tablewrap"><table class="ui-table">{head}'
            f'<tbody>{history}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Tạo phiên bản</h2>'
            f'<form method="post" action="/admin/api-gia-action">'
            f'<input type="hidden" name="csrf_token" value="{escape(token)}">'
            f'<input type="hidden" name="op" value="create">'
            f'<input type="hidden" name="tool" '
            f'value="{escape(tool.name if tool else "")}">'
            f'<p><input name="label" placeholder="nhãn (vd 2026-09-a)" required> '
            f'<input name="model" placeholder="model (bỏ trống = mọi model)"> '
            f'<input name="min_credit" inputmode="numeric" placeholder="sàn" '
            f'style="width:110px"> '
            f'<input name="max_credit" inputmode="numeric" placeholder="trần" '
            f'style="width:110px"> '
            f'<input name="rounding" inputmode="numeric" '
            f'placeholder="làm tròn" style="width:130px"> '
            f'<select name="rounding_mode">'
            + "".join(f'<option value="{m}">{m}</option>'
                      for m in pricing.ROUNDING_MODES) +
            f'</select></p>'
            f'<p><input name="starts_in_hours" inputmode="numeric" '
            f'style="width:190px" placeholder="bắt đầu sau (giờ, trống = ngay)"> '
            f'<input name="notes" size="40" placeholder="ghi chú"></p>'
            f'<p><input name="reason" size="50" required '
            f'minlength="{pricing.MIN_REASON}" '
            f'placeholder="Lý do (bắt buộc, ≥ {pricing.MIN_REASON} ký tự)"> '
            f'<button class="btn btn-primary sm">Tạo bản nháp</button></p>'
            f'<p class="muted">Bản nháp chưa có hiệu lực. Phải bấm Phát hành, '
            f'và cả hai thao tác đều ghi nhật ký.</p></form></section></div>')
        return HTMLResponse(_admin_shell("API - Gia", "api_pricing", body))

    @expose("/api-gia-action", methods=["POST"])
    async def action(self, request: Request):
        from datetime import datetime, timedelta, timezone

        from server.admin import _email_admin, ghi_nhat_ky
        from server.auth.csrf import verify_csrf_token

        form = await request.form()
        if not verify_csrf_token(request, (form.get("csrf_token") or "")):
            return HTMLResponse("CSRF", status_code=400)

        op = str(form.get("op") or "")
        reason = str(form.get("reason") or "")
        back = f'/admin/api-gia?tool={str(form.get("tool") or "")}'
        if len(reason.strip()) < pricing.MIN_REASON:
            return _redirect(back, "Phải ghi lý do cho thao tác này.")

        gen, db = _session()
        try:
            try:
                if op == "create":
                    hours = str(form.get("starts_in_hours") or "").strip()
                    starts = None
                    if hours:
                        starts = (datetime.now(timezone.utc)
                                  + timedelta(hours=max(0, int(hours))))
                    version = pricing.create_version(
                        db, tool=str(form.get("tool") or ""),
                        label=str(form.get("label") or ""),
                        model=str(form.get("model") or ""),
                        effective_from=starts,
                        min_credit=_maybe_int(form.get("min_credit")),
                        max_credit=_maybe_int(form.get("max_credit")),
                        rounding=_maybe_int(form.get("rounding")),
                        rounding_mode=str(form.get("rounding_mode")
                                          or "nearest"),
                        notes=str(form.get("notes") or ""),
                        created_by=_email_admin(request))
                    detail = f"{version.tool}:{version.label} (nhap)"
                elif op in ("publish", "retire"):
                    version = pricing.version_by_id(
                        db, str(form.get("version_id") or ""))
                    if version is None:
                        return HTMLResponse("Không thấy phiên bản.",
                                            status_code=404)
                    if op == "publish":
                        pricing.publish(db, version,
                                        published_by=_email_admin(request))
                    else:
                        pricing.retire(db, version)
                    detail = f"{version.tool}:{version.label}"
                    back = f"/admin/api-gia?tool={version.tool}"
                else:
                    return HTMLResponse("Thao tác không hợp lệ.",
                                        status_code=400)
            except (pricing.PricingError, ValueError) as exc:
                db.rollback()
                return _redirect(back, str(exc))
            ghi_nhat_ky(db, request, f"api_gia_{op}", doi_tuong=detail,
                        chi_tiet=f"ly do: {reason.strip()}")
            db.commit()
        finally:
            _close(gen)
        return RedirectResponse(back, status_code=303)


def _maybe_int(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    return int(raw)


def _example_input(tool) -> dict:
    """A plausible call for the preview, from the contract's own examples."""
    from platform_core.public_api import examples

    try:
        return examples.example_input(tool)
    except Exception as exc:  # noqa: BLE001 - a preview is a convenience
        # An empty preview is acceptable; an unexplained one is not. A tool
        # whose contract cannot produce an example is a contract problem, and
        # the pricing page is where somebody would first notice.
        _log.warning("khong dung duoc vi du cho %s: %s: %s",
                     getattr(tool, "name", "?"), type(exc).__name__, exc)
        return {}


class ApiMarginView(BaseView):
    """Doanh thu từ sổ credit, chi phí là ước lượng — và nói rõ điều đó."""

    name = "API - Margin"
    icon = "fa-solid fa-scale-balanced"

    @expose("/api-margin", methods=["GET"])
    async def page(self, request: Request):
        from datetime import datetime, timedelta, timezone

        hours = _int(request, "hours", 24)
        since = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))

        gen, db = _session()
        try:
            window = costing.margin(db, since=since)
            by_tool = costing.margin_by_tool(db, since=since)
            configured = costing.rates()
        finally:
            _close(gen)

        def money(micros: int) -> str:
            return f"{micros / costing.MICROS:.2f}"

        cards = "".join([
            _stat("Doanh thu (credit)", window.revenue_credit,
                  "từ sổ credit — con số đã đối soát"),
            _stat("Chi phí ước tính", money(window.cost_micros),
                  f"{window.observations} quan sát"),
            _stat("Chênh lệch ước tính", money(window.margin_micros),
                  "ước lượng, không phải kế toán",
                  colour=_ERR if window.is_negative else _OK),
        ])

        rows = "".join(
            f'<tr><td class="mono">{escape(row["tool"])}</td>'
            f'<td class="tnum">{money(row["cost_micros"])}</td>'
            f'<td class="tnum">{row["observations"]}</td></tr>'
            for row in by_tool) or (
            '<tr><td colspan="3" class="muted">Chưa có quan sát chi phí nào '
            'trong khoảng này.</td></tr>')

        if configured:
            rates = " ".join(
                f'<code>{escape(kind)}={value}µ</code>'
                for kind, value in sorted(configured.items()))
            rate_note = (f'<p>Đơn giá đang cấu hình: {rates}. Đây là con số '
                         f'<b>giả định</b> do người vận hành nhập, không phải '
                         f'hoá đơn.</p>')
        else:
            rate_note = ('<p class="muted">Chưa cấu hình đơn giá nào '
                         f'({", ".join(sorted(costing.RATE_ENV.values()))}), '
                         'nên nền tảng không ghi quan sát chi phí. Cố ý: một '
                         'chi phí bằng 0 là một khẳng định, và khi chưa có đơn '
                         'giá thì nền tảng không có quyền khẳng định điều đó.'
                         '</p>')

        windows = "".join(
            f'<a class="{"on" if hours == h else ""}" '
            f'href="/admin/api-margin?hours={h}">{label}</a>'
            for h, label in ((24, "24 giờ"), (168, "7 ngày"), (720, "30 ngày")))

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Margin</h1>'
            f'<p><b>Doanh thu</b> lấy từ sổ credit: đó là số khách thật sự bị '
            f'tính, và là chân lý thanh toán. <b>Chi phí</b> ở đây là '
            f'<b>ƯỚC LƯỢNG</b>: nền tảng đo được thời lượng và số byte, nhưng '
            f'giá tiền của một giây GPU hay một byte lưu trữ là con số hợp đồng '
            f'do người vận hành nhập. Đừng đổi giá bán chỉ dựa vào trang này — '
            f'hãy đối chiếu hoá đơn thật trước.</p></div></div>'
            f'<div class="tabs">{windows}</div>'
            f'{_TILES}{cards}</div>'
            f'{rate_note}'
            f'<section><h2 style="margin:22px 0 10px">Chi phí ước tính theo '
            f'công cụ</h2><div class="tablewrap"><table class="ui-table">'
            f'<thead><tr><th>Công cụ</th><th>Chi phí ước tính</th>'
            f'<th>Số quan sát</th></tr></thead><tbody>{rows}</tbody></table>'
            f'</div></section></div>')
        return HTMLResponse(_admin_shell("API - Margin", "api_margin", body))


class ApiRequestsView(BaseView):
    """Lời gọi đã ghi, của mọi tài khoản."""

    name = "API - Request"
    icon = "fa-solid fa-list"

    @expose("/api-request", methods=["GET"])
    async def page(self, request: Request):
        query = request.query_params.get("q", "")
        status = request.query_params.get("status", "")
        code = request.query_params.get("code", "")
        hours = _int(request, "hours", 24)
        limit, offset = admin_console.clamp_page(
            request.query_params.get("limit"),
            request.query_params.get("offset"))

        gen, db = _session()
        try:
            page = admin_console.requests_page(
                db, query=query, status=status, code=code, hours=hours,
                limit=limit, offset=offset)
        finally:
            _close(gen)

        rows = ""
        for item in page.rows:
            row = item["row"]
            colour = _ERR if row.status >= 400 else ""
            style = f' style="color:{colour}"' if colour else ""
            rows += (
                f'<tr><td class="muted">{_when(row.created_at)}</td>'
                f'<td class="mono">'
                f'<a href="/admin/api-trace?q={escape(row.request_id)}">'
                f'{escape(row.request_id[:12])}</a></td>'
                f'<td>{escape(item["email"] or "—")}</td>'
                f'<td class="mono">{escape(row.method)} {escape(row.route)}</td>'
                f'<td class="tnum"{style}>{row.status}</td>'
                f'<td class="mono muted">{escape(row.code or "")}</td>'
                f'<td class="tnum">{row.latency_ms}</td>'
                f'<td class="tnum">{row.credit_delta}</td></tr>')
        rows = rows or ('<tr><td colspan="8" class="muted" '
                        'style="padding:26px;text-align:center">'
                        'Không có lời gọi nào khớp.</td></tr>')

        base = (f'/admin/api-request?q={escape(query)}&status={escape(status)}'
                f'&code={escape(code)}&hours={hours}')
        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Request</h1>'
            f'<p>Nhật ký này chỉ ghi <b>lời gọi hỏng</b> và <b>lời gọi ghi dữ '
            f'liệu</b> (EXT-09) — một quyết định về thông lượng, không phải '
            f'thiếu sót. Mọi con số ở đây là con số trên phần đã ghi.</p>'
            f'</div></div>'
            f'<form method="get" class="job-filters">'
            f'<input name="q" value="{escape(query)}" '
            f'placeholder="correlation id, khoá, route, tool…">'
            f'<select name="status">'
            f'<option value="">mọi kết quả</option>'
            f'<option value="failed"{" selected" if status == "failed" else ""}>'
            f'chỉ hỏng</option>'
            f'<option value="ok"{" selected" if status == "ok" else ""}>'
            f'chỉ thành công</option></select>'
            f'<input name="code" value="{escape(code)}" placeholder="mã lỗi">'
            f'<input name="hours" value="{hours}" style="width:90px">'
            f'<button class="btn ghost sm">Lọc</button></form>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Lúc</th><th>Correlation</th><th>Tài khoản</th><th>Route</th>'
            f'<th>HTTP</th><th>Mã</th><th>ms</th><th>Credit</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>'
            f'{_pager(page, base)}</div>')
        return HTMLResponse(_admin_shell("API - Request", "api_requests", body))


class ApiJobsView(BaseView):
    """Job của khu API, kèm ba con số trang khách không bao giờ thấy."""

    name = "API - Job"
    icon = "fa-solid fa-diagram-project"

    @expose("/api-job", methods=["GET"])
    async def page(self, request: Request):
        status = request.query_params.get("status", "")
        tool = request.query_params.get("tool", "")
        hours = _int(request, "hours", 24)
        limit, offset = admin_console.clamp_page(
            request.query_params.get("limit"),
            request.query_params.get("offset"))

        gen, db = _session()
        try:
            page = admin_console.jobs_page(db, status=status, tool=tool,
                                           hours=hours, limit=limit,
                                           offset=offset)
            failing = admin_console.failing_webhooks(db, hours=hours)
        finally:
            _close(gen)

        def ms(value) -> str:
            return "—" if value is None else f"{value:,}"

        rows = ""
        for item in page.rows:
            job = item["job"]
            rows += (
                f'<tr><td class="mono">'
                f'<a href="/admin/api-trace?q={escape(job.id)}">'
                f'{escape(job.id[:12])}</a></td>'
                f'<td>{escape(item["email"] or "—")}</td>'
                f'<td class="mono">{escape(item["tool"] or "—")}</td>'
                f'<td>{escape(job.status)}</td>'
                f'<td class="tnum">{ms(item["queue_delay_ms"])}</td>'
                f'<td class="tnum">{ms(item["run_ms"])}</td>'
                f'<td class="mono muted">{escape(job.worker_id or "—")}</td>'
                f'<td class="tnum">{job.attempts}</td>'
                f'<td class="tnum">{item["held"]}</td></tr>')
        rows = rows or ('<tr><td colspan="9" class="muted" '
                        'style="padding:26px;text-align:center">'
                        'Không có job API nào trong khoảng này.</td></tr>')

        hooks = ""
        for item in failing:
            row = item["row"]
            colour = _ERR if row.status == "dead" else _WARN
            hooks += (f'<tr><td style="color:{colour}">{escape(row.status)}</td>'
                      f'<td>{escape(item["email"] or "—")}</td>'
                      f'<td class="mono">{escape(row.event_type)}</td>'
                      f'<td class="tnum">{row.attempts}</td>'
                      f'<td class="tnum">{row.last_status_code or "—"}</td>'
                      f'<td class="muted">{_when(row.created_at)}</td></tr>')
        hooks = hooks or ('<tr><td colspan="6" class="muted">Không có webhook '
                          'nào hỏng trong khoảng này.</td></tr>')

        base = (f'/admin/api-job?status={escape(status)}&tool={escape(tool)}'
                f'&hours={hours}')
        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Job</h1>'
            f'<p><b>Chờ hàng đợi</b> tách "chúng ta chậm" khỏi "hàng đợi đầy" — '
            f'ngã rẽ đầu tiên của gần như mọi khiếu nại về độ trễ. Ba cột '
            f'chờ/chạy/worker là của người vận hành; trang của khách không có '
            f'chúng.</p></div></div>'
            f'<form method="get" class="job-filters">'
            f'<input name="status" value="{escape(status)}" '
            f'placeholder="trạng thái"> '
            f'<input name="tool" value="{escape(tool)}" placeholder="tool"> '
            f'<input name="hours" value="{hours}" style="width:90px">'
            f'<button class="btn ghost sm">Lọc</button></form>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Job</th><th>Tài khoản</th><th>Tool</th><th>Trạng thái</th>'
            f'<th>Chờ (ms)</th><th>Chạy (ms)</th><th>Worker</th><th>Lần</th>'
            f'<th>Đã giữ</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'{_pager(page, base)}'
            f'<section><h2 style="margin:22px 0 10px">Webhook hỏng</h2>'
            f'<p class="muted">Dòng <b>dead</b> đứng trước: một delivery '
            f'<i>failed</i> sẽ được thử lại, một <i>dead</i> thì không — và chỉ '
            f'cái thứ hai là một khách đang lặng lẽ mất callback.</p>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Trạng thái</th><th>Tài khoản</th><th>Sự kiện</th>'
            f'<th>Lần</th><th>HTTP cuối</th><th>Lúc</th></tr></thead>'
            f'<tbody>{hooks}</tbody></table></div></section></div>')
        return HTMLResponse(_admin_shell("API - Job", "api_jobs", body))


class ApiSecurityView(BaseView):
    """Những lần bị từ chối trước khi kịp thành một request."""

    name = "API - Bao mat"
    icon = "fa-solid fa-shield-halved"

    @expose("/api-bao-mat", methods=["GET"])
    async def page(self, request: Request):
        from platform_core.public_api import security_log

        hours = _int(request, "hours", 24)
        kind = request.query_params.get("kind", "")

        gen, db = _session()
        try:
            data = security_log.summary(db, hours=hours)
            rows = security_log.list_recent(
                db, kind=kind, since=data["since"], limit=100)
            # Chặn được tấn công đã biết là một chuyện; **thấy** bất thường là
            # chuyện khác. Ba câu hỏi này trả lời được từ dữ liệu đã có, và
            # trước đây không ai hỏi.
            bat_thuong = anomalies.quet(db, hours=hours)
        finally:
            _close(gen)

        def _hang(cot: list) -> str:
            return "".join(f'<tr>{"".join(cot)}</tr>')

        canh_bao = ""
        for row in bat_thuong["khoa_thu_hoi"]:
            canh_bao += _hang([
                '<td><span class="chip danger">Khoá đã thu hồi</span></td>',
                f'<td class="mono">{escape(row["key_id"][:16])}</td>',
                f'<td class="tnum">{row["lan"]}</td>',
                f'<td class="muted">vẫn bị gọi từ {row["so_ip"]} địa chỉ — '
                f'thứ đang giữ khoá không phải hệ thống vừa được cập nhật</td>'])
        for row in bat_thuong["chi_tieu_vot"]:
            gap = f'gấp {row["gap"]}×' if row["gap"] else "tài khoản mới"
            canh_bao += _hang([
                '<td><span class="chip warn">Chi tiêu vọt</span></td>',
                f'<td class="mono">{escape(row["user_id"][:16])}</td>',
                f'<td class="tnum">{row["tieu"]}</td>',
                f'<td class="muted">{gap} mức thường ngày '
                f'({row["thuong_ngay"]}/ngày)</td>'])
        for row in bat_thuong["scope_bi_tu_choi"]:
            canh_bao += _hang([
                '<td><span class="chip warn">Thiếu quyền</span></td>',
                f'<td class="mono">{escape(row["key_id"][:16])}</td>',
                f'<td class="tnum">{row["lan"]}</td>',
                f'<td class="muted">trên {row["so_route"]} route — cấu hình '
                f'thiếu scope, hoặc đang dò xem với tới đâu</td>'])
        canh_bao = canh_bao or ('<tr><td colspan="4" class="muted">Không có dấu '
                                'hiệu bất thường nào trong khoảng này.</td></tr>')

        cards = "".join([
            _stat("Lần bị từ chối", data["total"],
                  colour=_ERR if data["total"] else ""),
            _stat("Khoá đã thu hồi bị dùng", data["revoked_in_use"],
                  "thường là một bản triển khai chưa ai cập nhật",
                  colour=_ERR if data["revoked_in_use"] else ""),
            _stat("Khoá lạ", data["by_kind"].get(security_log.UNKNOWN_KEY, 0),
                  "nhiều + từ một địa chỉ = đang dò"),
            _stat("Bị bóp vì dò nhiều",
                  data["by_kind"].get(security_log.THROTTLED, 0)),
        ])

        sources = "".join(
            f'<tr><td class="mono">{escape(ip)}</td>'
            f'<td class="tnum">{count}</td></tr>'
            for ip, count in data["top_ips"]) or (
            '<tr><td colspan="2" class="muted">Không có.</td></tr>')

        listed = "".join(
            f'<tr><td class="muted">{_when(row.created_at)}</td>'
            f'<td><code>{escape(row.kind)}</code></td>'
            f'<td class="mono">{escape(row.ip or "—")}</td>'
            f'<td class="mono">{escape(row.key_id or "—")}</td>'
            f'<td class="mono muted">{escape(row.route or "")}</td>'
            f'<td class="mono muted">'
            f'<a href="/admin/api-trace?q={escape(row.request_id)}">'
            f'{escape(row.request_id[:12])}</a></td></tr>'
            for row in rows) or (
            '<tr><td colspan="6" class="muted" style="padding:26px;'
            'text-align:center">Không có sự kiện nào. Đó là trạng thái bình '
            'thường.</td></tr>')

        kinds = "".join(
            f'<option value="{k}"{" selected" if k == kind else ""}>{k}</option>'
            for k in ("",) + security_log.KINDS)

        windows = "".join(
            f'<a class="{"on" if hours == h else ""}" '
            f'href="/admin/api-bao-mat?hours={h}">{label}</a>'
            for h, label in ((1, "1 giờ"), (24, "24 giờ"), (168, "7 ngày")))

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Bảo mật</h1>'
            f'<p>Những lần bị từ chối <b>trước khi</b> kịp thành một request có '
            f'chủ. Trước EXT-16 chúng chỉ vào file log, nên "có ai đang dò khoá "'
            f'"không" và "khoá đã thu hồi còn bị dùng không" không hỏi được bằng '
            f'dữ liệu. Ở đây chỉ lưu <b>nửa công khai</b> của khoá — nửa bí mật '
            f'không tồn tại ở đâu để mà hiện.</p></div></div>'
            f'<div class="tabs">{windows}</div>'
            f'{_TILES}{cards}</div>'
            f'{_COLS}'
            f'<section><h2 style="margin:22px 0 10px">Dấu hiệu bất thường</h2>'
            f'<p class="muted">Một khoá bị lộ vẫn gọi đúng scope và đúng nhịp, '
            f'nên nó không chạm vào bất kỳ hàng rào nào — cho tới khi hết tiền. '
            f'Ba câu hỏi này nhìn vào <b>thói quen</b> thay vì vào luật.</p>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Dấu hiệu</th><th>Đối tượng</th><th>Số</th><th>Nghĩa là gì</th>'
            f'</tr></thead><tbody>{canh_bao}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Địa chỉ ồn nhất</h2>'
            f'<p class="muted">Một địa chỉ hỏng 400 lần là một con bot; 400 địa '
            f'chỉ hỏng mỗi cái một lần là một bản phát hành lỗi. Cùng một tổng '
            f'số, hai việc khác nhau.</p>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Địa chỉ</th><th>Số lần</th></tr></thead>'
            f'<tbody>{sources}</tbody></table></div></section>'
            f'<section><h2 style="margin:22px 0 10px">Theo loại</h2>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Loại</th><th>Số lần</th></tr></thead><tbody>'
            + "".join(f'<tr><td><code>{escape(k)}</code></td>'
                      f'<td class="tnum">{v}</td></tr>'
                      for k, v in sorted(data["by_kind"].items()))
            + f'</tbody></table></div></section></div>'
            f'<form method="get" class="job-filters">'
            f'<select name="kind">{kinds}</select>'
            f'<input name="hours" value="{hours}" style="width:90px">'
            f'<button class="btn ghost sm">Lọc</button></form>'
            f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
            f'<th>Lúc</th><th>Loại</th><th>Địa chỉ</th><th>Khoá đã thử</th>'
            f'<th>Route</th><th>Correlation</th></tr></thead>'
            f'<tbody>{listed}</tbody></table></div></div>')
        return HTMLResponse(_admin_shell("API - Bao mat", "api_security", body))


class ApiTraceView(BaseView):
    """Một lời gọi, từ đầu đến cuối, từ bất kỳ mẩu định danh nào."""

    name = "API - Truy vet"
    icon = "fa-solid fa-magnifying-glass"

    @expose("/api-trace", methods=["GET"])
    async def page(self, request: Request):
        from platform_core.public_api import support

        query = request.query_params.get("q", "")
        gen, db = _session()
        try:
            found = support.trace(db, query) if query else support.Trace()
        finally:
            _close(gen)

        body = (
            f'<div class="adm-top"><span class="eyebrow">API platform</span>'
            f'</div><div class="adm-content"><div class="pagehead"><div>'
            f'<h1>API — Truy vết</h1>'
            f'<p>Dán vào đây bất kỳ thứ gì khách đưa: correlation id, job id, '
            f'mã khoá, id project, email — hoặc một địa chỉ IP. Tất cả dẫn về '
            f'<b>một</b> dòng thời gian.</p></div></div>'
            f'<form method="get" class="job-filters">'
            f'<input name="q" value="{escape(query)}" size="46" '
            f'placeholder="correlation id / job / khoá / project / email / IP">'
            f'<button class="btn sm">Tra</button>'
            + (f'<a class="btn ghost sm" '
               f'href="/admin/api-trace-export?q={escape(query)}">Xuất JSON</a>'
               if found.found else "")
            + f'</form>'
            + (_trace_body(found) if query else "")
            + '</div>')
        return HTMLResponse(_admin_shell("API - Truy vet", "api_trace", body))

    @expose("/api-trace-export", methods=["GET"])
    async def export(self, request: Request):
        import json

        from platform_core.public_api import support

        query = request.query_params.get("q", "")
        gen, db = _session()
        try:
            found = support.trace(db, query)
            payload = support.export(found)
        finally:
            _close(gen)

        from starlette.responses import Response

        # `Content-Disposition` so it lands as a file: a support trace is
        # something somebody attaches to a ticket, not something they read in a
        # browser tab and lose.
        return Response(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            media_type="application/json",
            headers={"Content-Disposition":
                     f'attachment; filename="trace-{query[:24]}.json"',
                     "Cache-Control": "no-store"})


def _trace_body(found) -> str:
    """The timeline, in the order the work actually happened."""
    if not found.found:
        return ('<p class="muted" style="padding:26px">Không tìm thấy gì khớp. '
                'Correlation id chỉ được lưu cho lời gọi hỏng và lời gọi ghi '
                'dữ liệu (EXT-09).</p>')

    def line(label: str, value: str, muted: bool = False) -> str:
        cls = ' class="muted"' if muted else ""
        return f'<tr><th>{escape(label)}</th><td{cls}>{value}</td></tr>'

    who = ""
    if found.user is not None:
        who += line("Tài khoản",
                    f'<a href="/admin/api-tai-khoan?user={escape(found.user.id)}">'
                    f'{escape(found.user.email)}</a>')
    if found.project is not None:
        who += line("Project", escape(found.project.name))
    if found.key is not None:
        who += line("Khoá",
                    f'<a href="/admin/api-khoa?key={escape(found.key.key_id)}">'
                    f'<code>{escape(found.key.key_id[:16])}</code></a> '
                    f'{_mode_chip(getattr(found.key, "mode", "live"))}')

    steps = ""
    row = found.request
    if row is not None:
        steps += (f'<tr><td>1. Request</td>'
                  f'<td class="mono">{escape(row.method)} {escape(row.route)}</td>'
                  f'<td class="tnum">{row.status}</td>'
                  f'<td class="muted">{_when(row.created_at)}</td></tr>')
    job = found.job
    if job is not None:
        steps += (f'<tr><td>2. Job</td><td class="mono">{escape(job.id[:16])}</td>'
                  f'<td>{escape(job.status)}</td>'
                  f'<td class="muted">{_when(job.created_at)}</td></tr>')
        delay = found.queue_delay_ms
        steps += (f'<tr><td>3. Chờ hàng đợi</td>'
                  f'<td class="tnum">{"—" if delay is None else f"{delay:,} ms"}'
                  f'</td><td class="mono muted">{escape(job.worker_id or "—")}'
                  f'</td><td class="muted">{_when(job.started_at)}</td></tr>')
        run = found.run_ms
        steps += (f'<tr><td>4. Chạy</td>'
                  f'<td class="tnum">{"—" if run is None else f"{run:,} ms"}</td>'
                  f'<td>{escape(job.status)}</td>'
                  f'<td class="muted">{_when(job.finished_at)}</td></tr>')
    for entry in found.credit:
        steps += (f'<tr><td>5. Sổ credit</td><td>{escape(entry.kind)}</td>'
                  f'<td class="tnum">{entry.delta:+d}</td>'
                  f'<td class="muted">{_when(entry.created_at)}</td></tr>')
    for hook in found.webhooks:
        steps += (f'<tr><td>6. Webhook</td>'
                  f'<td class="mono">{escape(hook.event_type)}</td>'
                  f'<td>{escape(hook.status)} ({hook.attempts})</td>'
                  f'<td class="muted">{_when(hook.created_at)}</td></tr>')

    events = "".join(
        f'<tr><td class="tnum">{row.sequence}</td>'
        f'<td class="mono">{escape(row.event_code)}</td>'
        f'<td>{escape(row.level)}</td>'
        f'<td>{"khách" if row.visibility == "customer" else "nội bộ"}</td>'
        f'<td class="muted">{escape(str(row.details or "")[:160])}</td></tr>'
        for row in found.events) or (
        '<tr><td colspan="5" class="muted">Không có sự kiện.</td></tr>')

    recent = "".join(
        f'<tr><td class="muted">{_when(row.created_at)}</td>'
        f'<td class="mono">{escape(row.method)} {escape(row.route)}</td>'
        f'<td class="tnum">{row.status}</td>'
        f'<td class="mono muted">{escape(row.code or "")}</td>'
        f'<td class="mono muted">'
        f'<a href="/admin/api-trace?q={escape(row.request_id)}">'
        f'{escape(row.request_id[:12])}</a></td></tr>'
        for row in found.requests)

    security = "".join(
        f'<tr><td class="muted">{_when(row.created_at)}</td>'
        f'<td><code>{escape(row.kind)}</code></td>'
        f'<td class="mono">{escape(row.ip or "—")}</td>'
        f'<td class="mono">{escape(row.key_id or "—")}</td></tr>'
        for row in found.security)

    out = (f'<p class="muted">Khớp theo <code>{escape(found.matched_by)}</code>.'
           f'</p>')
    if who:
        out += (f'<section><h2 style="margin:22px 0 10px">Ai</h2>'
                f'<div class="tablewrap"><table class="ui-table"><tbody>'
                f'{who}</tbody></table></div></section>')
    if steps:
        out += (f'<section><h2 style="margin:22px 0 10px">Dòng thời gian</h2>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>Bước</th><th></th><th></th><th>Lúc</th></tr></thead>'
                f'<tbody>{steps}</tbody></table></div></section>')
    if found.job is not None:
        out += (f'<section><h2 style="margin:22px 0 10px">Sự kiện job '
                f'(gồm cả nội bộ)</h2>'
                f'<p class="muted">Trang của khách chỉ hiện dòng '
                f'<i>khách</i>. Chỗ này hiện cả hai — đó là toàn bộ lý do có '
                f'một trang truy vết cho người vận hành.</p>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>#</th><th>Mã</th><th>Mức</th><th>Ai thấy</th>'
                f'<th>Chi tiết</th></tr></thead><tbody>{events}</tbody></table>'
                f'</div></section>')
        if found.job.error:
            out += (f'<section><h2 style="margin:22px 0 10px">Lỗi thô</h2>'
                    f'<p class="muted">Khách được xem một bản đã làm sạch '
                    f'(Q76). Bản gốc ở đây.</p>'
                    f'<pre class="mono" style="white-space:pre-wrap">'
                    f'{escape(found.job.error[:2000])}</pre></section>')
    if recent:
        out += (f'<section><h2 style="margin:22px 0 10px">Lời gọi gần đây</h2>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>Lúc</th><th>Route</th><th>HTTP</th><th>Mã</th>'
                f'<th>Correlation</th></tr></thead><tbody>{recent}</tbody>'
                f'</table></div></section>')
    if security:
        out += (f'<section><h2 style="margin:22px 0 10px">Sự kiện bảo mật</h2>'
                f'<div class="tablewrap"><table class="ui-table"><thead><tr>'
                f'<th>Lúc</th><th>Loại</th><th>Địa chỉ</th><th>Khoá</th>'
                f'</tr></thead><tbody>{security}</tbody></table></div>'
                f'</section>')
    return out


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
VIEWS = (ApiOverviewView, ApiAccountsView, ApiKeysAdminView, ApiToolsView,
         ApiPolicyView, ApiKillSwitchView, ApiPricingView, ApiMarginView,
         ApiRequestsView, ApiJobsView, ApiSecurityView, ApiTraceView)

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
    ("/admin/api-chinh-sach", "CS", "API — Chính sách", "api_policy"),
    ("/admin/api-kill-switch", "KS", "API — Kill switch", "api_kill"),
    ("/admin/api-gia", "GI", "API — Giá", "api_pricing"),
    ("/admin/api-margin", "MG", "API — Margin", "api_margin"),
    ("/admin/api-request", "RQ", "API — Request", "api_requests"),
    ("/admin/api-job", "AJ", "API — Job", "api_jobs"),
    ("/admin/api-bao-mat", "BM", "API — Bảo mật", "api_security"),
    ("/admin/api-trace", "TV", "API — Truy vết", "api_trace"),
)
