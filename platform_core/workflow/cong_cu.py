"""Một chỗ tra ToolSpec cho workflow: tên → (app, job_type, version, giá).

Dùng lại `platform_core.registry.discover()` — không quét manifest lần hai.
Plan 02 dựng `NodeDefinition` (spec §4.4) TRÊN mô-đun này.
"""
from __future__ import annotations

from dataclasses import dataclass
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
                spec=t)
    return ra


__all__ = ["CongCu", "tat_ca"]
