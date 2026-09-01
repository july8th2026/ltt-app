"""Health/readiness/version endpoints (P3). No authentication required —
these are meant to be probed by the reverse proxy / service manager."""
from __future__ import annotations

from fastapi import APIRouter, Request, Response

from platform_core import to_tien

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

    ⭐ Từ 2026-08-25 hàm này **không còn đọc tệp cấu hình nào**. Trước đó nó trả
       503 "config not loaded" khi `data/config.json` hỏng — mà tệp đó là cấu
       hình của app socialbot, nay đã gỡ. Nghĩa là suốt thời gian ấy một app
       đóng băng quyết định được nền tảng có sẵn sàng hay không, và nssm khởi
       động lại tiến trình theo câu trả lời đó. Sự cố BOM ghi ở `AGENTS.md`
       mục 5 đi đúng đường này.

       Hồ sơ môi trường nay lấy từ `LTT_ENV` (đã nằm sẵn trong
       `server_settings`, không phải một lượt đọc đĩa), nên "sẵn sàng" chỉ còn
       đúng một nghĩa: **CSDL nối được**.
    """
    server_settings = getattr(request.app.state, "server_settings", None)
    environment = (server_settings.environment.value
                   if server_settings is not None else "unknown")

    db_ok, db_reason = _kiem_tra_csdl()
    if not db_ok:
        response.status_code = 503
        return {
            "status": "not_ready",
            "reason": f"database: {db_reason}",
            "environment": environment,
        }

    return {
        "status": "ready",
        "environment": environment,
        "database": "ok",
        # 🔴 "Sẵn sàng" trả lời *"tôi có phục vụ được không"*. Trường này trả lời
        #    một câu KHÁC: *"tôi có NÊN đang chạy không"* — và hai câu đó tách ra
        #    khi tiến trình sống sót mồ côi sau khi vỏ bọc NSSM chết.
        #
        #    Đo trên máy B 01/09: `/health` trả 200 suốt **99 giây** trong khi
        #    `Get-Service` nói `Stopped` và không ai dựng dậy nữa. Máy A đo cùng
        #    ngày có **cùng lỗ** (không dịch vụ nào có `FAILURE_ACTIONS`), chỉ
        #    khác là ở đây nó nằm trên máy đang phục vụ khách thật.
        #
        # ⛔ CỐ Ý KHÔNG đổi `status` thành `not_ready` khi mồ côi. Tiến trình mồ
        #    côi **vẫn phục vụ được**; trả 503 sẽ khiến proxy ngắt một dịch vụ
        #    đang chạy tốt và biến một sự cố vận hành thành một sự cố ngừng
        #    dịch vụ. Việc của trường này là làm sự cố **nhìn thấy được**.
        "duoi_dich_vu": to_tien.trang_thai(),
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
