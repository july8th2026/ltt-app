"""Configuration and kill switches for the Public API (Q92).

Every switch defaults to the safest value: the surface is **off** until an
operator turns it on, and no tool is exposed until it is named explicitly. That
is the opposite of Q25 (apps default to *open*) on purpose — Q25 governs what a
logged-in customer sees in the UI, while this governs a machine-callable surface
where forgetting a flag must cost a missing feature, never leaked capability or
uncontrolled spend.

Environment variables (all optional; the defaults are production-safe):

``LTT_PUBLIC_API``
    ``1`` mounts ``/api/v1``. Default ``0`` — the router is not mounted at all,
    so an installation that never opts in has exactly today's route surface.
``LTT_PUBLIC_API_READ_ONLY``
    ``1`` keeps reads working but rejects every write with 503. This is the
    emergency switch: it stops new chargeable work without touching the UI,
    the worker or any job already queued.
``LTT_PUBLIC_API_TOOLS``
    Comma-separated allowlist of public tool names (``<domain>.<action>``, the
    names apps declare through ``ToolSpec`` — this module must not know any of
    them, see ``AGENTS.md`` 8.4).
    Empty (default) means no tool is callable. Prompt 05 layers the catalog
    policy on top; this flag is the outer switch an operator can flip fast.
``LTT_PUBLIC_API_MAX_BODY_BYTES``
    Cap for control-plane JSON bodies. Default 2 MiB (raised from 1 MiB on
    25/09/2026 after a production 413 on ``/api/v1/messages`` — see
    ``DEFAULT_MAX_BODY_BYTES`` below), clamped to [1 KiB, 100 MiB]. Uploads do
    not go through here: they use presigned PUT / staging sessions, because
    Cloudflare rejects bodies over 100 MB before they reach this process at
    all.
``LTT_PUBLIC_API_RPM`` / ``LTT_PUBLIC_API_CREATE_RPM``
    Requests and chargeable job creations allowed per minute for one key
    (default 120 and 20). ``0`` disables that layer.
``LTT_PUBLIC_API_MAX_ACTIVE_JOBS``
    Queued+running jobs one account may hold at once (default 5). This is the
    backpressure that stops one customer filling the queue everybody waits in.
``LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT``
    Total queued Public API jobs across accounts/resources (default 100).
``LTT_PUBLIC_API_RESOURCE_QUEUE_LIMITS``
    Per-admission-resource queued caps, e.g. ``llm_remote:8,gpu:20``. Empty
    means the global/account caps still apply but that resource has no tighter
    queue cap.
``LTT_PUBLIC_API_CLASS_CONCURRENCY``
    Per-resource-class ceiling, e.g. ``gpu:2,ffmpeg:4``. Empty = off.
``LTT_PUBLIC_API_DAILY_CREDIT``
    Credit one account may commit through the API per rolling day. ``0``
    (default) = no ceiling; it is a product decision, not a safety default.
``LTT_PUBLIC_API_AUTH_FAILURES`` / ``LTT_PUBLIC_API_AUTH_FAILURE_WINDOW``
    Failed credentials tolerated per source before 429 (default 20 per 300 s).
``LTT_PUBLIC_API_CORS_ORIGINS``
    Comma-separated origins allowed to call the API **from a browser**. Empty
    (default) sends no CORS headers at all, which is right for a machine API:
    a server-side integration does not need them, and a wildcard would let any
    page on the internet spend a logged-in customer's credit if a browser ever
    attached a key for them. Only set it for a first-party browser app.
``LTT_PUBLIC_API_TRUSTED_PROXIES``
    Peers whose ``CF-Connecting-IP`` header may be believed. Default
    ``127.0.0.1,::1`` because ``cloudflared`` reaches the origin over loopback
    and the origin accepts nothing else. An empty value disables header trust
    entirely and falls back to the socket peer.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

#: 🔴 NÂNG 256 KB → 1 MiB ngày 30/08, và lý do là một lỗi đã xảy ra.
#:
#:    256 KB được chọn cho "thân JSON của control plane" — đúng cho `/jobs`,
#:    `/quotes`, `/keys`. Nhưng `/v1/responses` và `/v1/messages` mang **cả hội
#:    thoại**, và một lượt agentic 96.000 token ở dạng JSON ≈ 433 KB. Trần 256 KB
#:    chặn nó ở khoảng 64.000 token — gần bằng 65.000 nên suốt một buổi ta tưởng
#:    đang chạm trần token của máy B, trong khi thủ phạm là trần **byte** của ta.
#:
#: ⛔ Hai trần không liên quan gì nhau mà cái nhỏ hơn luôn thắng, và thông điệp
#:    lỗi khi ấy không nói nó là cái nào. Nay lỗi có `limit_name` (`server/api/
#:    deps.py`), và `tests/test_334_ngan_sach_ltt_llm.py` so trần này với
#:    `ngan_sach.BODY_BYTES_TOI_THIEU` nên lệch là đỏ chứ không phải là một buổi
#:    đi truy.
#:
#: ⛔ Chỗ này từng ghi `tests/test_312` — trỏ nhầm sang khoá dịch vụ VPS, vì hai
#:    phiên cấp trùng số hiệu. Viện dẫn phép kiểm bằng **tên tệp**, không bằng
#:    số hiệu; `tests/test_980_vien_dan_phep_kiem.py` cưỡng chế.
#:
#: 🔴 NÂNG LẦN HAI 1 MiB → 2 MiB ngày 25/09/2026 — 1 MiB LÀ CÙNG MỘT LỖI, DỊCH
#:    LÊN MỘT NẤC. Production 413 thật trên `/api/v1/messages`: thân
#:    **1.150.067 B** > trần 1.048.576 B (không ghi đè), khách nén hội thoại
#:    **4 lần liên tiếp vẫn 413** — không có đường ra. `ngan_sach.py` khi ấy giả
#:    định 4,5 byte/token; đo lại trên mẫu tiếng Việt + mã nguồn thật (xem chú
#:    thích `BYTE_MOI_TOKEN_JSON`) cho thấy ca sản xuất thật ăn **5,059
#:    byte/token** — vượt giả định cũ, và biên giữa `BODY_BYTES_TOI_THIEU` (~999
#:    KB ở 4,5) với trần 1 MiB chỉ **2,4%**, mỏng hơn cả sai số làm tròn.
#:
#:    `BYTE_MOI_TOKEN_JSON` nay = 6,0 (biên ~19% trên 5,059 đo được) ⇒
#:    `BODY_BYTES_TOI_THIEU` ≈ 1.364.000 B (~1,30 MiB) cho model cửa sổ rộng
#:    nhất đang bán. 2 MiB chừa thêm ~54% trên số đó — không phải một con số
#:    tròn chọn bừa, mà là biên **thứ hai** sau biên đã có trong hằng số byte/
#:    token, để một model thứ ba hay một hình dạng hội thoại chưa đo tới không
#:    lập tức đâm lại đúng bức tường này.
#:
#: ⚠️ MẶT TRÁI CỦA MỘT TRẦN LỚN HƠN: thân request lớn hơn được NHẬN vào tiến
#:    trình trước khi bất kỳ điều gì khác (auth, rate limit) được kiểm — tốn
#:    RAM/CPU parse JSON cho mỗi yêu cầu bị từ chối sau đó, và mở rộng cửa sổ
#:    cho một request lớn cố ý làm chậm tiến trình (từng phần giảm nhẹ bởi
#:    `LTT_PUBLIC_API_RPM`/`_AUTH_FAILURES`, không phải bởi trần thân). 2 MiB
#:    vẫn nhỏ — một lần parse JSON 2 MB tốn dưới chục mili giây — nhưng đây là
#:    sự đánh đổi thật, không phải "cứ nâng cho chắc".
#:
#: ⛔ VẪN KHÔNG ĐỦ CHO ẢNH. `apps/ltt_llm/ngan_sach.py` công bố `ANH_BYTE_TOI_DA`
#:    = 12 MiB/ảnh (base64 ~16,4 MiB), `SO_ANH_TOI_DA` = 4 ảnh/yêu cầu — MỘT
#:    ảnh đơn đã vượt xa 2 MiB. Trần này chỉ chừa đủ cho HỘI THOẠI CHỮ ở cửa sổ
#:    ngữ cảnh rộng nhất; nếu `/api/v1/messages` thật sự nhận ảnh base64 INLINE
#:    (không qua staging) thì đó là một khoảng trống hợp đồng riêng — chưa sửa
#:    ở đây — cần đo xem ảnh có thật sự đi đường này trước khi chọn số.
#:
#: ⭐ Vẫn cách trần 100 MB của Cloudflare rất xa, nên đây không phải lời hứa suông.
DEFAULT_MAX_BODY_BYTES = 2 * 1024 * 1024
MIN_MAX_BODY_BYTES = 1024
# Cloudflare Free/Pro rejects a larger body before the origin sees it, so a
# higher value here would only be a lie told to the caller.
MAX_MAX_BODY_BYTES = 100 * 1024 * 1024
DEFAULT_TRUSTED_PROXIES = ("127.0.0.1", "::1")

_TRUE = {"1", "true", "yes", "on"}


def _flag(values, name: str, *, default: bool = False) -> bool:
    raw = values.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in _TRUE


def _csv(values, name: str, default: tuple = ()) -> tuple:
    raw = values.get(name)
    if raw is None:
        return tuple(default)
    items = [part.strip() for part in str(raw).split(",")]
    return tuple(item for item in items if item)


def _int(values, name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(str(values.get(name, default)).strip())
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _pairs(values, name: str) -> dict:
    """``gpu:2,ffmpeg:4`` -> ``{"gpu": 2, "ffmpeg": 4}``; junk entries ignored.

    Ignoring a malformed entry rather than refusing to boot is deliberate: a
    typo in an optional capacity hint must not take the platform down, and the
    resulting behaviour (no limit for that class) is the same as not setting it.
    """
    out: dict = {}
    for item in _csv(values, name):
        resource, _, raw = item.partition(":")
        resource = resource.strip()
        if not resource:
            continue
        try:
            out[resource] = max(0, int(raw))
        except (TypeError, ValueError):
            continue
    return out


@dataclass(frozen=True)
class PublicApiConfig:
    """Resolved switches for one process. Immutable: read once at app build."""

    enabled: bool = False
    read_only: bool = False
    exposed_tools: frozenset = frozenset()
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES
    trusted_proxies: tuple = DEFAULT_TRUSTED_PROXIES
    cors_origins: tuple = ()
    api_version: str = "v1"
    prefix: str = "/api/v1"

    request_rpm: int = 120
    create_rpm: int = 20
    max_active_jobs: int = 5
    class_concurrency: dict = field(default_factory=dict)
    global_queue_limit: int = 100
    resource_queue_limits: dict = field(default_factory=dict)
    daily_credit_limit: int = 0
    auth_failure_limit: int = 20
    auth_failure_window_s: int = 300

    def tool_exposed(self, tool_name: str) -> bool:
        """Outer kill switch for one tool. Catalog policy still applies later."""
        return str(tool_name or "") in self.exposed_tools

    def writes_allowed(self) -> bool:
        return self.enabled and not self.read_only


def load_public_api_config(env: dict | None = None) -> PublicApiConfig:
    """Read the switches from ``env`` (defaults to the process environment)."""
    values = os.environ if env is None else env
    return PublicApiConfig(
        enabled=_flag(values, "LTT_PUBLIC_API"),
        read_only=_flag(values, "LTT_PUBLIC_API_READ_ONLY"),
        exposed_tools=frozenset(_csv(values, "LTT_PUBLIC_API_TOOLS")),
        max_body_bytes=_int(values, "LTT_PUBLIC_API_MAX_BODY_BYTES",
                            DEFAULT_MAX_BODY_BYTES, MIN_MAX_BODY_BYTES,
                            MAX_MAX_BODY_BYTES),
        trusted_proxies=_csv(values, "LTT_PUBLIC_API_TRUSTED_PROXIES",
                             DEFAULT_TRUSTED_PROXIES),
        cors_origins=_csv(values, "LTT_PUBLIC_API_CORS_ORIGINS"),
        request_rpm=_int(values, "LTT_PUBLIC_API_RPM", 120, 0, 100_000),
        create_rpm=_int(values, "LTT_PUBLIC_API_CREATE_RPM", 20, 0, 100_000),
        max_active_jobs=_int(values, "LTT_PUBLIC_API_MAX_ACTIVE_JOBS", 5, 0, 10_000),
        class_concurrency=_pairs(values, "LTT_PUBLIC_API_CLASS_CONCURRENCY"),
        global_queue_limit=_int(
            values, "LTT_PUBLIC_API_GLOBAL_QUEUE_LIMIT", 100, 0, 1_000_000),
        resource_queue_limits=_pairs(
            values, "LTT_PUBLIC_API_RESOURCE_QUEUE_LIMITS"),
        daily_credit_limit=_int(values, "LTT_PUBLIC_API_DAILY_CREDIT", 0, 0,
                                1_000_000_000),
        auth_failure_limit=_int(values, "LTT_PUBLIC_API_AUTH_FAILURES", 20, 0,
                                100_000),
        auth_failure_window_s=_int(values, "LTT_PUBLIC_API_AUTH_FAILURE_WINDOW",
                                   300, 10, 86_400),
    )
