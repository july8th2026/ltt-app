"""Một chỗ tra ToolSpec cho workflow: tên → (app, job_type, version, giá).

Dùng lại `platform_core.registry.discover()` — không quét manifest lần hai.
Plan 02 dựng `NodeDefinition` (spec §4.4) TRÊN mô-đun này.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from platform_core.registry import ToolSpec


@dataclass(frozen=True)
class CongCu:
    ten: str
    app_slug: str
    job_type: str
    type_version: int
    params_schema: dict
    side_effect: str
    idempotency_fields: tuple[str, ...]
    tinh_gia: Callable[[dict], int]
    # `ToolSpec` thật của registry (Task 9 fix round 1, controller-found). Mặc
    # định `None` để `CongCu` giả trong test (khong qua `tat_ca()`) vẫn dựng
    # được không cần biết `registry.ToolSpec`. Cầu nối (`cau_noi.nop_job`)
    # dùng nó để gọi ĐÚNG con đường nộp canonical
    # (`registry.admission_luc_nop`/`ToolSpec.lane_for`,
    # `public_api/invocation.py:~500-560`) thay vì tự suy diễn một bản khác —
    # `spec is None` thì bỏ qua admission (hành vi cũ nguyên vẹn).
    spec: Optional["ToolSpec"] = None

    # ── Trường plan 02 (spec §4.4). TẤT CẢ có mặc định: `CongCu` dựng tay
    #    trong test của plan 01a phải tiếp tục dựng được không sửa một chữ.
    returns: dict = field(default_factory=dict)
    mo_ta: str = ""
    # Tên ngắn tuỳ chọn app tự khai trên `ToolSpec.ten_ngan` (xem đó để biết vì
    # sao). Rỗng = app chưa khai, `nut._tieu_de` tự lùi về hành vi cũ.
    ten_ngan: str = ""
    icon: str = ""
    app_name: str = ""
    customer_visible: bool = True
    workflow: bool = True
    cong: dict = field(default_factory=dict)
    resource: dict = field(default_factory=dict)
    timeout_expr: str = ""
    so_lan_thu: int = 0
    mock: Optional[Callable[[dict], dict]] = None


def _ham_gia(job_type: str) -> Callable[[dict], int]:
    def gia(params: dict) -> int:
        from platform_core import registry
        return int(registry.credit_for(job_type, params))
    return gia


def tat_ca() -> dict[str, CongCu]:
    from platform_core import registry

    ra: dict[str, CongCu] = {}
    for item in registry.discover():
        if item.error or not item.manifest.enabled:
            continue
        for t in item.manifest.tools:
            jt = t.job_type
            ra[t.name] = CongCu(
                ten=t.name, app_slug=item.slug, job_type=jt,
                type_version=int(getattr(t, "type_version", 1) or 1),
                params_schema=dict(t.params_schema or {}),
                side_effect=str(getattr(t, "side_effect", "external")
                                or "external"),
                idempotency_fields=tuple(
                    (getattr(t, "idempotency", None) or {}).get("key_fields", ())),
                tinh_gia=_ham_gia(jt),
                spec=t,
                returns=dict(t.returns or {}),
                mo_ta=str(t.description or ""),
                ten_ngan=str(getattr(t, "ten_ngan", "") or ""),
                # Biểu tượng + tên hiển thị đến từ AppManifest — nền tảng
                # KHÔNG giữ bảng nhãn thứ hai (bài học `test_967`).
                icon=str(item.manifest.icon or ""),
                app_name=str(item.manifest.display_name or item.slug),
                customer_visible=bool(t.customer_visible),
                workflow=bool(getattr(t, "workflow", True)),
                cong=dict(getattr(t, "cong", None) or {}),
                resource=dict(getattr(t, "resource", None) or {}),
                timeout_expr=str(getattr(t, "timeout_expr", "") or ""),
                so_lan_thu=item.manifest.so_lan_thu_for(jt),
                mock=getattr(t, "mock_result", None))
    return ra


__all__ = ["CongCu", "tat_ca"]
