"""
danh_muc.py — catalog cho một client **nội bộ**, lọc bằng allowlist của sản phẩm.

## Ba cổng khác nhau, đừng trộn

  `ToolSpec.customer_visible`   palette Agent/Canvas
  `ToolSpec.api_exposed` + `LTT_PUBLIC_API_TOOLS`   bán qua `/api/v1`
  **allowlist của sản phẩm** (tham số `cho_phep`)   thứ MỘT sản phẩm web mời

Hàm này chỉ nhìn cổng thứ ba, và **fail-closed**: tên không có trong `cho_phep`,
tool của app tắt/lỗi nạp, hay tool chưa có hợp đồng công khai — đều không hiện.

## Vì sao mượn `catalog.project_tool`

Phép chiếu ấy đã làm đúng việc khó: bỏ id model nội bộ, chỉ giữ alias
(test_212), ẩn tham số máy chủ tự quyết, giữ đúng kiểu số/chuỗi của enum. Viết
một phép chiếu thứ hai cho sản phẩm web là mời hai bản hợp đồng lệch nhau.
`project_tool(manifest, tool)` không cần `config` hay `Principal` — chỉ
`build_catalog`/`require_tool` (ba cổng của `/api/v1`) mới cần.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import FrozenSet, Iterable, Optional

from platform_core import registry as _reg
from platform_core.public_api.catalog import project_tool
from platform_core.registry import tai_tham_chieu

log = logging.getLogger("platform_core.runtime_noi_bo.danh_muc")


@dataclass(frozen=True)
class NangLuc:
    """Một năng lực như sản phẩm web nhìn thấy. Không có id nội bộ, không có URL máy."""

    ten: str                 # "text.chat"
    phuong_thuc: str         # "text" | "image" | "audio" | "video"
    che_do: str              # "stream" (có sync_executor) | "job"
    nhan: str                # mô tả cho khách (từ api_contract)
    hop_dong: dict           # `PublicTool.to_public_dict()`: input/output schema…
    models: dict = field(default_factory=dict)   # alias → {description, stability, constraints}
    tuy_chon: dict = field(default_factory=dict) # tham số → [{value,label}] theo NGƯỜI DÙNG
    gia: dict = field(default_factory=dict)      # `AppManifest.bang_gia()` của app sở hữu
    duong_dan_app: str = ""  # route_prefix của app sở hữu (deep-link "quản lý giọng")
    san_sang: str = "san_sang"   # "san_sang" | "chua_san_sang"


def phuong_thuc_cua(tool) -> str:
    """Suy phương thức từ **kiểu cổng ra** đã khai, không từ tên app hay tên tool."""
    kieu = {str(v).rstrip("[]") for v in (tool.returns or {}).values()}
    for ung_vien in ("audio", "video", "image"):
        if ung_vien in kieu:
            return ung_vien
    return "text"


def _tuy_chon(tool, db, user_id: str) -> dict:
    ra: dict = {}
    for param, ref in (getattr(tool, "tuy_chon_dong", None) or {}).items():
        try:
            chon = tai_tham_chieu(ref)(db, user_id)
            ra[param] = [{"value": str(c["value"]),
                          "label": str(c.get("label", c["value"]))}
                         for c in (chon or ()) if isinstance(c, dict) and "value" in c]
        except Exception:                                       # noqa: BLE001
            # Một app hỏng danh sách tuỳ chọn không được làm rỗng catalog của
            # mọi app khác — cùng luật với `bang_gia`/`bao_tri`. Nhưng phải ồn.
            log.exception("khong lay duoc tuy chon %s cua %s", param, tool.name)
            ra[param] = []
    return ra


def _gia(manifest) -> dict:
    if manifest.bang_gia is None:
        return {}
    try:
        return dict(manifest.bang_gia() or {})
    except Exception:                                           # noqa: BLE001
        log.exception("bang_gia cua %s nem", manifest.slug)
        return {}


def danh_muc(db, *, user_id: str, cho_phep: Iterable[str],
             apps: Optional[Iterable] = None) -> list:
    """Các `NangLuc` trong `cho_phep` mà người dùng này gọi được, xếp theo tên."""
    duoc: FrozenSet[str] = frozenset(str(t) for t in cho_phep)
    ra: list = []
    for loaded in (_reg.discover() if apps is None else apps):
        if loaded.error:
            continue
        m = loaded.manifest
        for tool in m.tools:
            if tool.name not in duoc:
                continue
            if not tool.api_contract:
                # Không có hợp đồng công khai = không có phép chiếu an toàn nào
                # để đưa ra một bề mặt khách. Fail-closed, và nói ra.
                log.warning("tool %s trong allowlist nhung chua co api_contract",
                            tool.name)
                continue
            pt = project_tool(m, tool)
            models = {alias: {k: v for k, v in dict(spec).items() if k != "id"}
                      for alias, spec in pt.model_aliases.items()}
            ra.append(NangLuc(
                ten=tool.name,
                phuong_thuc=phuong_thuc_cua(tool),
                che_do="stream" if getattr(tool, "sync_executor", "") else "job",
                nhan=pt.description,
                hop_dong=pt.to_public_dict(),
                models=models,
                tuy_chon=_tuy_chon(tool, db, user_id),
                gia=_gia(m),
                duong_dan_app=m.route_prefix,
                san_sang="san_sang" if m.enabled else "chua_san_sang",
            ))
    ra.sort(key=lambda n: n.ten)
    return ra
