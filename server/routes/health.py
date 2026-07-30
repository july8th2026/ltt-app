"""Health/readiness/version endpoints (P3). No authentication required —
these are meant to be probed by the reverse proxy / service manager."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

try:
    from version import APP_VERSION_SHORT as _APP_VERSION
except ImportError:
    _APP_VERSION = "unknown"

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict:
    """Process is up and able to answer HTTP requests. Never checks
    dependencies — that's /ready's job. A monitor that gets anything other
    than 200 here should restart the process, not wait."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict:
    """Process is up AND its dependencies are actually reachable.

    The database check is deliberately a real round-trip (`SELECT 1`), not a
    "was a connection string configured" check. A configured-but-unreachable
    database is exactly the state that makes an application look healthy while
    every request fails.

    `reason` always names *what* is wrong. Any database error passes through
    `che_mat_khau()` first — driver messages routinely embed the whole
    connection string, and this endpoint is unauthenticated by design so the
    reverse proxy can probe it.
    """
    core_settings = getattr(request.app.state, "core_settings", None)
    if core_settings is None:
        response.status_code = 503
        return {"status": "not_ready", "reason": "config not loaded"}

    db_ok, db_reason = _kiem_tra_csdl()
    if not db_ok:
        response.status_code = 503
        return {
            "status": "not_ready",
            "reason": f"database: {db_reason}",
            "environment": core_settings.environment.value,
        }

    return {
        "status": "ready",
        "environment": core_settings.environment.value,
        "database": "ok",
    }


def _kiem_tra_csdl() -> tuple[bool, str]:
    """Thử kết nối CSDL. Tách ra để test thay thế được dễ dàng.

    Chưa cấu hình CSDL **không** bị coi là lỗi trong giai đoạn chuyển tiếp:
    H1.1 vừa dựng lớp CSDL, nhưng chưa phần nào của ứng dụng phụ thuộc vào nó.
    Bắt `/health/ready` trả 503 ngay bây giờ sẽ làm dịch vụ đang chạy bị trình
    quản lý khởi động lại liên tục vì một phụ thuộc chưa ai dùng tới.

    Khi H1.2 đưa bảng người dùng vào, đổi nhánh này thành lỗi thật — và đổi cả
    test đi kèm trong cùng một lần.
    """
    try:
        from platform_core.db import DatabaseNotConfigured, kiem_tra_ket_noi
        try:
            from platform_core.db import database_url
            database_url()
        except DatabaseNotConfigured:
            return True, ""      # chua cau hinh -> chua phai loi (xem docstring)
        return kiem_tra_ket_noi()
    except Exception as exc:      # pragma: no cover - loi ngoai du kien
        return False, f"{type(exc).__name__}"


@router.get("/version")
def version() -> dict:
    return {"version": _APP_VERSION}
