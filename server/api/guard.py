"""Surface-wide guards for ``/api/v1``: the read-only switch and the size cap.

These run as middleware on the public sub-application rather than as route
dependencies, and that is the whole point: an emergency switch has to hold for
every route the surface serves — including the ones added by later prompts, and
including a route whose author forgot the dependency. A kill switch you can
forget to attach is not a kill switch.

Because a middleware short-circuits above the exception handlers, it renders the
problem document itself instead of raising :class:`ApiError`, and stamps the
correlation id on the response so a refused request is still traceable.
"""
from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from platform_core.public_api import metrics, protocol
from platform_core.public_api.config import PublicApiConfig
from platform_core.public_api.errors import ApiError
from server.api.context import client_ip, request_id
from server.api.deps import enforce_body_limit, enforce_read_only
from server.api.errors import problem_response

log = logging.getLogger("ltt.public_api.access")


class PublicApiGuardMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, config: PublicApiConfig):
        super().__init__(app)
        self._config = config

    async def dispatch(self, request, call_next):
        correlation_id = request_id(request)
        started = time.perf_counter()
        try:
            enforce_read_only(request, self._config)
            enforce_body_limit(request, self._config)
        except ApiError as exc:
            response = problem_response(exc.problem(
                instance=request.url.path, request_id=correlation_id))
            self._stamp(response, request, correlation_id)
            self._record(request, response.status_code, started, correlation_id)
            return response
        response = await call_next(request)
        self._stamp(response, request, correlation_id)
        self._record(request, response.status_code, started, correlation_id)
        self._schedule_log(response, request, response.status_code,
                           (time.perf_counter() - started) * 1000.0,
                           correlation_id)
        return response

    def _stamp(self, response, request, correlation_id: str) -> None:
        """Correlation id and API version on **every** response.

        Until EXT-02 the correlation id was only stamped on responses this
        middleware refused itself. A caller whose successful-then-mysterious
        request needed support had nothing to quote, and the audit found it: the
        id existed in the server's log and nowhere the customer could see.
        """
        response.headers[protocol.HEADER_CORRELATION_ID] = correlation_id
        response.headers[protocol.HEADER_API_VERSION] = protocol.API_VERSION
        route = _declared_route(request)
        # RFC 8594. Nothing is deprecated today; the hook exists so that
        # retiring an endpoint is a data change in the inventory rather than a
        # code change here, at the moment when getting it right matters.
        if route is not None and route.deprecated_on:
            response.headers[protocol.HEADER_DEPRECATION] = route.deprecated_on
            if route.sunset_on:
                response.headers[protocol.HEADER_SUNSET] = route.sunset_on

    def _record(self, request, status: int, started: float,
                correlation_id: str) -> None:
        """One structured line per request, and the counters behind it.

        Every field here is either public (a route, a status, a duration) or a
        public identifier (`key_id`, the owner's account id). The bearer token,
        the request body and any provider text are not logged — and cannot be,
        because they are never passed in.
        """
        latency_ms = (time.perf_counter() - started) * 1000.0
        principal = getattr(request.state, "api_principal", None)
        metrics.increment(metrics.REQUESTS)
        metrics.observe(metrics.LATENCY_REQUEST, latency_ms)
        if 400 <= status < 500:
            metrics.increment(metrics.RESPONSES_4XX)
        elif status >= 500:
            metrics.increment(metrics.RESPONSES_5XX)
        if status == 429:
            metrics.increment(metrics.RATE_LIMITED)

        log.info(
            "api request_id=%s method=%s route=%s status=%s latency_ms=%.1f "
            "key_id=%s owner=%s tool=%s job_id=%s credit_delta=%s ip=%s",
            correlation_id, request.method,
            # The templated path, not the filled-in one: a job id in a log line
            # is fine, but grouping by route is what makes the log usable.
            _route_of(request), status, latency_ms,
            getattr(principal, "key_id", "-") or "-",
            getattr(principal, "user_id", "-") or "-",
            getattr(request.state, "api_tool", "-") or "-",
            getattr(request.state, "api_job_id", "-") or "-",
            getattr(request.state, "api_credit_delta", 0) or 0,
            client_ip(request, getattr(self._config, "trusted_proxies", ())),
        )

    def _schedule_log(self, response, request, status: int, latency_ms: float,
                      correlation_id: str) -> None:
        """Queue the database row to be written once the response is out.

        Not inline: the request's own session is still finishing at this point,
        and a second connection writing at the same moment deadlocks SQLite and
        doubles connection use on PostgreSQL. A background task runs after the
        response is sent, when the request's session is definitively closed.
        """
        from starlette.background import BackgroundTask

        principal = getattr(request.state, "api_principal", None)
        if principal is None or not getattr(principal, "user_id", ""):
            return
        if not _worth_recording(request, status):
            return
        fields = {
            "request_id": correlation_id,
            "user_id": principal.user_id,
            "key_id": getattr(principal, "key_id", ""),
            "project_id": getattr(principal, "project_id", ""),
            "method": request.method,
            "route": _route_of(request),
            "status": int(status),
            "code": str(getattr(request.state, "api_error_code", "") or ""),
            "latency_ms": latency_ms,
            "tool": getattr(request.state, "api_tool", "") or "",
            "job_id": getattr(request.state, "api_job_id", "") or "",
            # ⛔ CHO TRONG. Gia tri THAT duoc doc LUC CHAY task, khong phai bay
            #    gio — xem `_write_request_log_muon` ngay duoi.
            "credit_delta": 0,
        }
        task = BackgroundTask(_write_request_log_muon, fields, request.state)
        if response.background is None:
            response.background = task
        else:
            existing = response.background
            response.background = BackgroundTask(
                _run_both, existing, task)


def _worth_recording(request, status: int) -> bool:
    """Which requests earn a row in the customer-visible log.

    Everything that failed, and everything that was not a read. What is left
    out — a successful GET — is the polling and discovery traffic, which is both
    the overwhelming majority of requests and the part a developer can already
    see: the job explains itself, and the catalog is the same for everyone.

    This is not a micro-optimisation. Measured on the load harness, a row per
    request cost 177 rps → 42.6 rps and p95 47ms → 333ms. Paying that so a
    successful `GET /jobs/{id}` poll can be listed twice is a bad trade; the
    operator's access log still has every request either way.
    """
    if status >= 400:
        return True
    return request.method != "GET"


async def _run_both(first, second) -> None:
    await first()
    await second()


def _write_request_log_muon(fields: dict, state) -> None:      # noqa: ANN001
    """Đọc `credit_delta` **muộn**, rồi mới ghi dòng.

    🔴 VÌ SAO KHÔNG CHỤP SỚM NHƯ MỌI TRƯỜNG KHÁC (P08 F-01).

       Cửa stream quyết toán tiền trong `finally` của generator — tức **sau** khi
       middleware đã đi qua. Chụp `credit_delta` ở thời điểm dựng `fields` thì
       với cửa stream nó **luôn** đọc ra `0`, dù khách bị thu bao nhiêu.

       Hệ quả không nằm ở một cột xấu xí, mà ở chỗ nó **giả làm bằng chứng**:
       `reports/06` từng chứng minh "bận thì không thu tiền" bằng câu *"89 lượt
       hỏng, credit=+0 mọi dòng"* — trên đúng cửa mà cột ấy không bao giờ khác 0.
       Một bằng chứng không thể sai thì không chứng minh gì.

       Và `platform_core/public_api/anomalies.py` cộng chính cột này để dò **bất
       thường tiền**, nên nó mù với hai cửa khách dùng nhiều nhất.

    ⭐ Đọc muộn là đúng cho MỌI cửa, không chỉ cửa stream: task nền chạy sau khi
       thân phản hồi đã đi hết, nên tới lúc đó cửa nào cũng đã chốt tiền xong.
    """
    gia_tri = getattr(state, "api_credit_delta", 0)
    # Cửa stream đặt `"cho"` lúc trả phản hồi để dòng log VĂN BẢN không nói dối
    # bằng một số `0`. Tới đây mà vẫn là `"cho"` nghĩa là quyết toán không chạy.
    fields["credit_delta"] = int(gia_tri) if isinstance(gia_tri, int) else 0
    _write_request_log(fields)


def _write_request_log(fields: dict) -> None:
    """One row, best effort.

    A request that succeeded must not be reported as failed because its
    bookkeeping row could not be written, so a failure here is logged and
    swallowed — the one place in this file where swallowing is right.
    """
    from platform_core.db import get_session
    from platform_core.public_api import request_log

    gen = get_session()
    try:
        db = next(gen)
    except Exception:                            # pragma: no cover - no database
        log.warning("request log unavailable request_id=%s",
                    fields.get("request_id"))
        return
    try:
        request_log.record(db, **fields)
        db.commit()
    except Exception:                            # noqa: BLE001 - see docstring
        db.rollback()
        log.warning("could not write request log request_id=%s",
                    fields.get("request_id"), exc_info=True)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _route_of(request) -> str:
    """The templated path as the *caller* wrote it.

    The sub-application knows its routes without the mount prefix, so a route
    object says "/me" where the customer typed "/api/v1/me". Logging the short
    form makes every line and every log row a puzzle to match against the API
    the customer sees.
    """
    from server.api.inventory import API_V1_PREFIX

    route = request.scope.get("route")
    path = getattr(route, "path", "") if route is not None else ""
    if not path:
        return request.url.path
    return path if path.startswith(API_V1_PREFIX) else API_V1_PREFIX + path


def _declared_route(request):
    """The inventory entry for this request, or None for an unmatched path."""
    from server.api.inventory import API_V1_ROUTES, API_V1_PREFIX

    path = _route_of(request)
    if not path.startswith(API_V1_PREFIX):
        path = API_V1_PREFIX + path
    for route in API_V1_ROUTES:
        if route.path == path and route.method == request.method:
            return route
    return None
