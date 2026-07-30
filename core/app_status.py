"""
Meta App status monitor (Sprint B3).

Why this exists:
  If your Meta App gets disabled (TOS violation, app review fails, billing
  issue) you'll start getting cryptic 400/403 errors. Without a status
  check, the bot keeps retrying and burns through every account it has.
  Detecting "app disabled" → halt all uploads → notify user is a 30-line
  fix that saves hours of debugging.

This module exposes:
  • check_app_status(config) → AppStatusReport
  • is_app_disabled(report) → bool

It tries a cheap, side-effect-free call against the Graph API and
classifies the response. Designed to run periodically (every hour from
the MaintenanceDaemon).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class AppStatus(Enum):
    OK              = "ok"            # App responding normally
    DISABLED        = "disabled"      # App has been disabled by Meta
    SUSPENDED       = "suspended"     # Temporary suspension (still might recover)
    UNKNOWN         = "unknown"       # Couldn't determine (network down, etc.)
    NOT_CONFIGURED  = "not_configured" # Missing app_id / app_secret


@dataclass(frozen=True)
class AppStatusReport:
    """Result of one health probe against the Meta App."""
    app_id:      str
    status:      AppStatus
    error_code:  str
    message:     str
    checked_at:  str


def check_app_status(config: dict) -> AppStatusReport:
    """Probe Graph API with the app token to detect disabled/suspended state.

    The cheapest possible call is `GET /{app_id}?fields=name` with an
    APP access token (app_id|app_secret). It returns app metadata when
    healthy, and a specific error code when disabled.
    """
    app_id     = str(config.get("meta_app_id",     "")).strip()
    app_secret = str(config.get("meta_app_secret", "")).strip()
    now_iso    = datetime.now(timezone.utc).isoformat()

    if not app_id or not app_secret:
        return AppStatusReport(
            app_id=app_id, status=AppStatus.NOT_CONFIGURED,
            error_code="missing_credentials",
            message="meta_app_id hoặc meta_app_secret chưa cấu hình",
            checked_at=now_iso,
        )

    try:
        from core.graph_client import GraphClient
        from core.utils import graph_api_version
        client = GraphClient(version=graph_api_version(config), timeout=10, max_retries=0)
        app_token = f"{app_id}|{app_secret}"   # standard FB app-access-token format
        resp = client.get(app_id, params={"fields": "name,namespace"}, token=app_token)
        if resp.get("name"):
            return AppStatusReport(
                app_id=app_id, status=AppStatus.OK, error_code="",
                message=f"App '{resp.get('name')}' đang hoạt động bình thường",
                checked_at=now_iso,
            )
        return AppStatusReport(
            app_id=app_id, status=AppStatus.UNKNOWN, error_code="",
            message="Phản hồi không có 'name' field — không rõ trạng thái",
            checked_at=now_iso,
        )
    except Exception as exc:
        return _classify_error(exc, app_id, now_iso)


def _classify_error(exc: Exception, app_id: str, now_iso: str) -> AppStatusReport:
    """Map exception → AppStatus. The interesting case is Graph error codes."""
    code     = str(getattr(exc, "code", "") or "")
    subcode  = str(getattr(exc, "subcode", "") or "")
    message  = str(exc)[:300]

    # Documented disabled-app codes:
    #   190: token errors (often disabled app)
    #   368: app suspension for spam
    #   200: missing perm — likely app review revoked
    #   459: app blocked
    if code in ("190", "200", "459"):
        return AppStatusReport(
            app_id=app_id, status=AppStatus.DISABLED,
            error_code=code, message=message, checked_at=now_iso,
        )
    if code in ("368", "322"):
        return AppStatusReport(
            app_id=app_id, status=AppStatus.SUSPENDED,
            error_code=code, message=message, checked_at=now_iso,
        )

    # Network / unknown
    return AppStatusReport(
        app_id=app_id, status=AppStatus.UNKNOWN,
        error_code=code or type(exc).__name__,
        message=message, checked_at=now_iso,
    )


def is_app_disabled(report: AppStatusReport) -> bool:
    """Convenience predicate. DISABLED or SUSPENDED → bot should halt."""
    return report.status in (AppStatus.DISABLED, AppStatus.SUSPENDED)


# ─── TikTok app status probe (Sprint TT-1.5) ─────────────────────────────────

def check_tiktok_app_status(config: dict) -> AppStatusReport:
    """Probe TikTok client credentials by requesting a client_credentials
    token. A healthy app returns an access_token; a disabled app returns
    a documented error.

    Endpoint: POST https://open.tiktokapis.com/v2/oauth/token/
    Auth:     client_id + client_secret in body
    """
    import time as _time
    import requests as _requests

    now_iso = datetime.now(timezone.utc).isoformat()

    # Pick the first healthy client from the pool, falling back to legacy keys
    try:
        from core.tiktok.multi_client import TikTokClientPool
        pool = TikTokClientPool.from_config(config)
        rec  = pool.next_healthy()
        if rec is not None:
            client_key, client_secret = rec.client_key, rec.client_secret
        else:
            client_key    = str(config.get("tiktok_client_key", "")).strip()
            client_secret = str(config.get("tiktok_client_secret", "")).strip()
    except Exception:
        client_key    = str(config.get("tiktok_client_key", "")).strip()
        client_secret = str(config.get("tiktok_client_secret", "")).strip()

    if not client_key or not client_secret:
        return AppStatusReport(
            app_id=client_key, status=AppStatus.NOT_CONFIGURED,
            error_code="missing_credentials",
            message="TikTok client_key hoặc client_secret chưa cấu hình",
            checked_at=now_iso,
        )

    try:
        url  = "https://open.tiktokapis.com/v2/oauth/token/"
        # TikTok's docs accept form-encoded body for client_credentials.
        body = {
            "client_key":    client_key,
            "client_secret": client_secret,
            "grant_type":    "client_credentials",
        }
        resp = _requests.post(
            url, data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        # Healthy: HTTP 200 + access_token field
        if resp.status_code == 200:
            try:
                j = resp.json()
            except Exception:
                j = {}
            if j.get("access_token"):
                return AppStatusReport(
                    app_id=client_key, status=AppStatus.OK, error_code="",
                    message="TT client_credentials grant OK",
                    checked_at=now_iso,
                )
            # 200 without token → server confused, treat unknown
            return AppStatusReport(
                app_id=client_key, status=AppStatus.UNKNOWN,
                error_code="no_token_in_200",
                message=f"200 OK nhưng không có token: {str(j)[:200]}",
                checked_at=now_iso,
            )

        # Documented error codes:
        #   400 invalid_request / invalid_client → app disabled or key wrong
        #   401 unauthorized → key revoked
        #   403 forbidden → app suspended
        try:
            err_json = resp.json()
            err_code = str(err_json.get("error", "")) or str(err_json.get("error_code", ""))
            err_desc = str(err_json.get("error_description", ""))[:200]
        except Exception:
            err_code = f"http_{resp.status_code}"
            err_desc = resp.text[:200]

        if resp.status_code in (401, 403) or err_code in ("invalid_client", "unauthorized_client"):
            return AppStatusReport(
                app_id=client_key, status=AppStatus.DISABLED,
                error_code=err_code, message=err_desc, checked_at=now_iso,
            )
        if resp.status_code == 400 and err_code in ("invalid_request",):
            # Could be wrong credentials or rate limit
            return AppStatusReport(
                app_id=client_key, status=AppStatus.UNKNOWN,
                error_code=err_code, message=err_desc, checked_at=now_iso,
            )
        # Fall-through: treat unknown HTTP status as suspended (defensive)
        return AppStatusReport(
            app_id=client_key, status=AppStatus.UNKNOWN,
            error_code=err_code or f"http_{resp.status_code}",
            message=err_desc, checked_at=now_iso,
        )
    except _requests.RequestException as exc:
        return AppStatusReport(
            app_id=client_key, status=AppStatus.UNKNOWN,
            error_code="network_error", message=str(exc)[:200],
            checked_at=now_iso,
        )
    except Exception as exc:
        return AppStatusReport(
            app_id=client_key, status=AppStatus.UNKNOWN,
            error_code=type(exc).__name__, message=str(exc)[:200],
            checked_at=now_iso,
        )
