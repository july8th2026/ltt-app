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
CSRF, gọi service, chọn template và ghi nhật ký.

⭐ **HTML cũng không còn nằm ở đây (29/08).** Mười hai thân trang từng là
f-string trong chính file này — 1.894 dòng — nay ở `server/templates/admin/`,
và tám hàm sinh HTML bằng chuỗi đã gỡ hẳn. Còn 846 dòng.

Đó không chỉ là gọn hơn: bánh cóc **nội dung cấm** (`test_317`) chỉ quét
`server/templates/admin`, nên chữ nằm trong f-string ở đây là chữ **vô hình**
với nó. Lần chuyển đổi làm lộ ngay hai lỗi chữ đã sống nhiều tháng — một lời
hứa "đối soát" ngân hàng không tồn tại, và "Địa chỉ" làm tiêu đề cột IP trong
khi nền tảng không có trường địa chỉ. Bánh cóc chỉ bảo vệ được thứ nó nhìn thấy.

⛔ Nên đừng dựng lại HTML bằng chuỗi ở đây. Thêm trang mới thì thêm một template
và một `_render(...)`.

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

from server.routes.admin._chung import (
    AnTrongMenuSqlAdmin as _AnTrongMenuSqlAdmin)
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
    return value.strftime("%d/%m/%Y %H:%M") if value else "—"


def _render(ten: str, **bien) -> str:
    """Dựng thân một trang khu API từ template.

    ⭐ Đây là đường thay cho HTML nối bằng f-string. Hai màu trạng thái được
       bơm sẵn vào mọi template để không template nào tự đặt một mã màu mới —
       ba màu này là bảng màu vận hành, không phải lựa chọn của từng trang.
    """
    from server.templating import templates

    return templates.env.get_template(ten).render(
        OK=_OK, WARN=_WARN, ERR=_ERR, **bien)


def _cua_so(hours: int) -> str:
    """Đuôi `?hours=` để đích giữ nguyên cửa sổ thời gian người ta đang xem.

    Bỏ nó đi thì bấm từ ô "7 ngày" sẽ rơi vào một danh sách 24 giờ, và con số
    không khớp với con số vừa bấm — đúng kiểu làm người ta mất lòng tin vào cả
    trang."""
    return f"hours={int(hours)}"


class ApiOverviewView(_AnTrongMenuSqlAdmin, BaseView):
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

        # Điền sẵn 0 cho mọi bộ đếm template đọc tới. Jinja trả `Undefined` cho
        # khoá thiếu và render nó thành chuỗi rỗng — một ô chỉ số trống nhìn
        # giống "chưa đo được" chứ không giống "bằng không", và hai thứ đó dẫn
        # tới hai hành động khác nhau.
        dem = {ten: do["counters"].get(ten, 0) for ten in (
            "responses_5xx", "auth_failure", "rate_limited",
            "kill_switch_refused", "capacity_refused", "webhook_failed")}
        cho = do["latency"].get("queue_pickup_ms", {})
        cho_hang_doi = {"avg_ms": cho.get("avg_ms", 0),
                        "max_ms": cho.get("max_ms", 0)}

        return HTMLResponse(_admin_shell(
            "API — Tổng quan", "api_overview",
            _render("admin/api_tong_quan.html",
                    hours=hours, data=data, by_tool=by_tool, do=do, dem=dem,
                    cho_hang_doi=cho_hang_doi, ai_bao_tri=ai_bao_tri,
                    cs=_cua_so(hours),
                    cua_so_chon=((1, "1 giờ"), (24, "24 giờ"),
                                 (168, "7 ngày"), (720, "30 ngày")))))


class ApiAccountsView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Tài khoản", "api_access",
            _render("admin/api_tai_khoan.html", page=page, q=query, luc=_when,
                    base=f"/admin/api-tai-khoan?q={escape(query)}")))

    async def _detail(self, request: Request, user_id: str):
        gen, db = _session()
        try:
            data = admin_console.account_detail(db, user_id=user_id)
        finally:
            _close(gen)
        if data is None:
            return HTMLResponse("Không thấy tài khoản.", status_code=404)

        return HTMLResponse(_admin_shell(
            data["user"].email, "api_access",
            _render("admin/api_tai_khoan_chi_tiet.html",
                    data=data, user=data["user"], luc=_when)))


class ApiKeysAdminView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Khoá", "api_khoa",
            _render("admin/api_khoa.html", page=page, q=query, status=status,
                    mode=mode, luc=_when,
                    base=(f"/admin/api-khoa?q={escape(query)}"
                          f"&status={escape(status)}&mode={escape(mode)}"))))

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
            # Chụp lại TRƯỚC khi đóng phiên: đọc thuộc tính của một ORM object
            # sau khi phiên đóng là một truy vấn nữa, và ở đây nó sẽ nổ.
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

        return HTMLResponse(_admin_shell(
            snapshot["key_id"], "api_khoa",
            _render("admin/api_khoa_chi_tiet.html",
                    k=snapshot, dung=usage, trang_thai=status, luc=_when,
                    token=issue_csrf_token(request),
                    min_reason=admin_console.MIN_REASON,
                    loi=request.query_params.get("err", ""))))

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


class ApiToolsView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Công cụ", "api_governance",
            _render("admin/api_cong_cu.html", tools=tools, hours=hours,
                    mo_san=sorted(config.exposed_tools))))


class ApiPolicyView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Chính sách", "api_policy",
            _render("admin/api_chinh_sach.html",
                    data=data, nen=baseline, truong=policy.LIMIT_FIELDS,
                    token=issue_csrf_token(request),
                    min_reason=policy.MIN_REASON,
                    loi=request.query_params.get("err", ""))))

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


class ApiKillSwitchView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Kill switch", "api_kill",
            _render("admin/api_kill_switch.html",
                    rows=rows, pham_vi=KILL_SCOPES, luc=_when,
                    token=issue_csrf_token(request),
                    min_reason=policy.MIN_REASON,
                    loi=request.query_params.get("err", ""))))

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


class ApiPricingView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Giá", "api_economics",
            _render("admin/api_gia.html",
                    catalog=catalog, tool=tool, line=line, preview=preview,
                    luc=_when, che_do_tron=pricing.ROUNDING_MODES,
                    NHAP=PRICE_DRAFT, DANG=PRICE_ACTIVE, LEN_LICH=PRICE_SCHEDULED,
                    token=issue_csrf_token(request),
                    min_reason=pricing.MIN_REASON,
                    loi=request.query_params.get("err", ""))))

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


class ApiMarginView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Margin", "api_margin",
            _render("admin/api_margin.html",
                    hours=hours, window=window, by_tool=by_tool,
                    tien=lambda micros: f"{micros / costing.MICROS:.2f}",
                    don_gia=sorted(configured.items()),
                    bien_moi_truong=", ".join(sorted(costing.RATE_ENV.values())),
                    cua_so_chon=((24, "24 giờ"), (168, "7 ngày"),
                                 (720, "30 ngày")))))


class ApiRequestsView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Request", "api_ops",
            _render("admin/api_request.html",
                    page=page, query=query, status=status, code=code,
                    hours=hours, luc=_when,
                    base=(f"/admin/api-request?q={escape(query)}"
                          f"&status={escape(status)}&code={escape(code)}"
                          f"&hours={hours}"))))


class ApiJobsView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Job", "api_job",
            _render("admin/api_job.html",
                    page=page, failing=failing, status=status, tool=tool,
                    hours=hours, luc=_when,
                    ms=lambda v: "—" if v is None else f"{v:,}",
                    base=(f"/admin/api-job?status={escape(status)}"
                          f"&tool={escape(tool)}&hours={hours}"))))


class ApiSecurityView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Bảo mật", "api_security",
            _render("admin/api_bao_mat.html",
                    data=data, rows=rows, bat_thuong=bat_thuong,
                    hours=hours, kind=kind, luc=_when,
                    loai_chon=("",) + security_log.KINDS,
                    UNKNOWN_KEY=security_log.UNKNOWN_KEY,
                    THROTTLED=security_log.THROTTLED)))


class ApiTraceView(_AnTrongMenuSqlAdmin, BaseView):
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

        return HTMLResponse(_admin_shell(
            "API — Truy vết", "api_trace",
            _render("admin/api_trace.html", found=found, q=query, luc=_when,
                    ms=lambda v: "—" if v is None else f"{v:,} ms")))

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

# 🔴 `NAV` ĐÃ BỊ GỠ. Mười hai mục "API — ..." từng được chèn thẳng vào
# `server/admin.py:_ADM_NAV`, tức MỘT miền chiếm 48% thanh bên quản trị và người
# xử sự cố phải tự đoán trong mười hai mục cùng tiền tố cái nào chứa câu trả
# lời. Chúng nay là MỘT mục cha "API Platform" với năm mục con
# (Overview/Access/Governance/Operations/Economics) — không route nào bị xoá,
# không URL nào đổi.
#
# Nguồn điều hướng duy nhất: `server/routes/admin/_chung.py`.
# Bố cục đã đóng băng: `docs/admin_mvp_v3/03_IA_FREEZE.md` §3b.
