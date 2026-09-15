"""Thin app-local operator HTTP surface, registered under the VPS router."""
from pathlib import Path
from html import escape

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

import apps.vps as vps_app
from apps.vps.profiles import ProfileNotReady
from apps.vps.services import admin_profiles
from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.deps import audit_operator_action, get_db, require_operator
from server.templating import render_admin_shell


def _enabled():
    if not vps_app.enabled():
        raise HTTPException(status_code=404)


router = APIRouter(prefix="/admin", tags=["vps-admin"], dependencies=[Depends(_enabled)])
_templates = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
    autoescape=select_autoescape(("html",)),
)
_templates.globals["_"] = _t


@router.get("", response_class=HTMLResponse)
@router.get("/cong-ha-tang", response_class=HTMLResponse)
def profile_list(request: Request, _operator=Depends(require_operator), db=Depends(get_db)):
    body = _templates.get_template("admin_profiles.html").render(
        profiles=admin_profiles.list_profiles(db), csrf_token=issue_csrf_token(request))
    return HTMLResponse(render_admin_shell(
        _t("Cổng hạ tầng"), "app_vps_profiles", body,
        tieu_de=_t("Cổng hạ tầng"), mo_ta=_t(
            "Profile đã ghim không đổi khi chuyển default. Preflight phải đạt trước khi nhận máy mới.")))


@router.post("/profiles/{profile_id}/action")
def profile_action(
    request: Request, profile_id: str, _operator=Depends(require_operator),
    db=Depends(get_db), action: str = Form(""), csrf_token: str = Form(""),
    config_version: int = Form(0),
):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403, detail=_t("CSRF không hợp lệ"))
    try:
        result = admin_profiles.apply_action(db, profile_id, action, config_version=config_version)
    except LookupError:
        raise HTTPException(status_code=404) from None
    except (admin_profiles.AdminProfileConflict, ProfileNotReady):
        raise HTTPException(status_code=409, detail=_t(
            "Profile chưa sẵn sàng hoặc phiên bản đã đổi. Chạy preflight và tải lại trang.")) from None
    except ValueError:
        raise HTTPException(status_code=400, detail=_t("Thao tác không hợp lệ")) from None
    except Exception:
        # No raw credential/provider/SSH exception is exposed to the browser.
        raise HTTPException(status_code=409, detail=_t(
            "Không xác minh được preflight. Kiểm tra cấu hình canonical.")) from None
    row = result.profile
    audit_action = f"vps_profile_{action}" + ("_blocked" if not result.applied else "")
    audit_operator_action(db, request, audit_action, row.id,
                          f"status={row.status}; version={row.config_version}")
    if not result.applied:
        # Return a response, not HTTPException: get_db must commit failure
        # evidence and closed acceptance instead of rolling them back.
        return HTMLResponse(render_admin_shell(
            _t("Cổng hạ tầng"), "app_vps_profiles", "",
            tieu_de=_t("Cổng hạ tầng"), loi=(
                _t("Kiểm tra kết nối chưa đạt; profile đã ngừng nhận máy mới.")
                if action == "test_connection" else
                _t("Preflight chưa đạt; không đổi activation/default. Profile đã ngừng nhận máy mới."))),
            status_code=409)
    if action == "reconcile":
        items = "".join(
            f"<li><strong>{escape(finding.code)}</strong> — "
            f"{escape(finding.instance_id or finding.resource_id or '')}</li>"
            for finding in result.findings)
        body = (_t("<p>Đối chiếu read-only hoàn tất: {count} finding.</p>").format(
            count=len(result.findings)) +
            f"<ul>{items}</ul><p><a href='/vps/admin/cong-ha-tang'>" +
            _t("Quay lại") + "</a></p>")
        return HTMLResponse(render_admin_shell(
            _t("Cổng hạ tầng"), "app_vps_profiles", body,
            tieu_de=_t("Kết quả đối chiếu hạ tầng")))
    return RedirectResponse("/vps/admin/cong-ha-tang", status_code=303)


@router.post("/profiles/save")
def profile_save(request: Request, _operator=Depends(require_operator), db=Depends(get_db),
                 csrf_token: str = Form(""), profile_id: str = Form(""),
                 config_version: int = Form(0), name: str = Form(""), slug: str = Form(""),
                 region: str = Form(""), ip_backend: str = Form(""),
                 credential_ref: str = Form(""), compute_ref: str = Form(""),
                 runtime_ref: str = Form(""), gateway_ref: str = Form(""),
                 router_ref: str = Form(""), mapping_strategy: str = Form("")):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=403)
    try:
        row = admin_profiles.save_profile(
            db, profile_id, config_version=config_version, name=name, slug=slug, region=region,
            ip_backend=ip_backend, credential_ref=credential_ref, compute_ref=compute_ref,
            runtime_ref=runtime_ref, gateway_ref=gateway_ref, router_ref=router_ref,
            mapping_strategy=mapping_strategy)
    except LookupError:
        raise HTTPException(status_code=404) from None
    except admin_profiles.AdminProfileConflict:
        raise HTTPException(status_code=409, detail=_t(
            "Cấu hình đã đổi hoặc đang gắn tài nguyên. Tải lại trang.")) from None
    except ValueError:
        raise HTTPException(status_code=400, detail=_t(
            "Cấu hình không hợp lệ; chỉ nhập tên biến canonical, không nhập bí mật.")) from None
    audit_operator_action(db, request, "vps_profile_save", row.id,
                          f"version={row.config_version}; accept_new=false")
    return RedirectResponse("/vps/admin/cong-ha-tang", status_code=303)
