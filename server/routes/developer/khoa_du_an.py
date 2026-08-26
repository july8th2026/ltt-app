"""Khoa API va du an."""
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

from server.routes.developer._chung import (  # noqa: F401
    _expiry_from_days, _keys_page, _kiem_cau_hinh_khoa, _projects_context, _redirect, _render, _split_ips, require_account, router)


@router.get("/projects", response_class=HTMLResponse)
def developer_projects(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "projects", "dev_projects.html",
                   **_projects_context(db, user))


@router.get("/keys", response_class=HTMLResponse)
def developer_keys(request: Request, user=Depends(require_account),
                   db: Session = Depends(get_db)):
    return _keys_page(request, db, user)


@router.get("/settings", response_class=HTMLResponse)
def developer_settings(request: Request, user=Depends(require_account),
                       db: Session = Depends(get_db)):
    return _render(request, db, user, "settings", "dev_settings.html")


@router.post("/keys", response_class=HTMLResponse)
def create_key(request: Request, name: str = Form(""),
               scopes: list[str] = Form(default=[]),
               allowed_tools: list[str] = Form(default=[]),
               project_id: str = Form(""), allowed_ips: str = Form(""),
               expires_in_days: str = Form(""), mode: str = Form("live"),
               csrf_token: str = Form(""), user=Depends(require_account),
               db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    loi_may_chu = _kiem_cau_hinh_khoa()
    if loi_may_chu:
        return _keys_page(request, db, user, error=loi_may_chu)
    try:
        project = (projects.get_owned(db, user_id=user.id, project_id=project_id)
                   if project_id else projects.default_for(db, user_id=user.id))
        if project is None or not project.is_active():
            # Ownership is resolved from the session user, so a forged id
            # simply does not resolve — it never reaches the key.
            return _keys_page(request, db, user,
                              error=_t("Không tìm thấy project."))
        expiry = _expiry_from_days(expires_in_days)
        key, token = devkeys.issue(
            db, user_id=user.id, name=name, scopes=scopes,
            allowed_tools=allowed_tools, project_id=project.id,
            allowed_ips=_split_ips(allowed_ips), expires_at=expiry,
            mode=(sandbox.MODE_TEST if mode == sandbox.MODE_TEST
                  else sandbox.MODE_LIVE))
    except Exception as exc:  # noqa: BLE001 - message is for this one customer
        from platform_core.public_api.scopes import ScopeError

        if not isinstance(exc, (devkeys.DeveloperKeyError, ScopeError,
                                projects.ProjectError)):
            raise
        db.rollback()
        return _keys_page(request, db, user, error=str(exc))
    # The plaintext exists only in this response. Nothing stores it, and the
    # page below says so — a customer who closes the tab must create a new key.
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


@router.post("/keys/{key_id}/revoke")
def revoke_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/keys", status_code=303)
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is not None:
        devkeys.revoke(db, key)
    # Same redirect whether or not the key existed: a portal must not become a
    # way to find out which key ids belong to somebody else.
    return RedirectResponse("/developers/keys", status_code=303)


@router.post("/keys/{key_id}/rotate", response_class=HTMLResponse)
def rotate_key(request: Request, key_id: str, csrf_token: str = Form(""),
               user=Depends(require_account), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/keys")
    key = devkeys.get_owned(db, user_id=user.id, key_id=key_id)
    if key is None:
        return _keys_page(request, db, user, error=_t("Không tìm thấy khóa."))
    try:
        token = devkeys.rotate(db, key)
    except devkeys.DeveloperKeyError as exc:
        return _keys_page(request, db, user, error=str(exc))
    return _keys_page(request, db, user, revealed=token,
                      created_key=key.key_id)


@router.post("/projects", response_class=HTMLResponse)
def create_project(request: Request, name: str = Form(""),
                   csrf_token: str = Form(""), user=Depends(require_account),
                   db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise _redirect("/developers/projects")
    try:
        projects.create(db, user_id=user.id, name=name)
    except projects.ProjectError as exc:
        db.rollback()
        return _render(request, db, user, "projects", "dev_projects.html",
                       error=str(exc), **_projects_context(db, user))
    db.commit()
    raise _redirect("/developers/projects")


@router.post("/projects/{project_id}/archive")
def archive_project(request: Request, project_id: str,
                    csrf_token: str = Form(""), user=Depends(require_account),
                    db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/developers/projects", status_code=303)
    project = projects.get_owned(db, user_id=user.id, project_id=project_id)
    if project is not None:
        # Archiving revokes the project's keys and touches nothing else: jobs,
        # ledger entries and usage rows record money that moved, and retiring an
        # integration cannot make them untrue.
        projects.archive(db, project)
        db.commit()
    return RedirectResponse("/developers/projects", status_code=303)
