"""Một chỗ tra ToolSpec cho workflow: tên → (app, job_type, version, giá).

Dùng lại `platform_core.registry.discover()` — không quét manifest lần hai.
Plan 02 dựng `NodeDefinition` (spec §4.4) TRÊN mô-đun này.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from platform_core import registry


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


def tat_ca() -> dict[str, CongCu]:
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
                tinh_gia=lambda p, _jt=jt: int(registry.credit_for(_jt, p)))
    return ra


__all__ = ["CongCu", "tat_ca"]
