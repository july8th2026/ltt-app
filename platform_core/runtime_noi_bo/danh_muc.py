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
    #: Alias được chọn sẵn. **Đọc từ `default` đã khai trong `input_schema`**,
    #: không phải phần tử đầu của `models`.
    #:
    #: 🔴 VÌ SAO PHẢI LÀ MỘT TRƯỜNG RIÊNG. Giao diện trước đây lấy
    #:    `Object.keys(models)[0]` — tức mặc định là **thứ tự khai trong một
    #:    dict**. Nó cho ra `ltt_llm`, đúng thứ ta muốn, nhưng đúng một cách
    #:    tình cờ: đảo hai dòng trong `apps/ltt_llm/manifest.py` là mặc định
    #:    lặng lẽ thành `ltt_llm_vision` — model có ngữ cảnh **28K thay vì 89K**,
    #:    tức mọi hội thoại dài của mọi khách bỗng chạm trần sớm gấp ba.
    #:
    #: ⛔ Và không có gì bắt được: bộ test không đọc thứ tự dict, phép kiểm giao
    #:    diện chỉ hỏi "có chọn sẵn cái gì không". Một hằng số đúng nhờ may mắn
    #:    thì không phải một hằng số.
    #:
    #: ⭐ Hợp đồng ĐÃ nói mặc định là gì (`input_schema.properties.model.default`).
    #:    Việc cần làm không phải chọn hộ, mà là **chuyển câu trả lời đã có**
    #:    tới nơi cần nó.
    model_mac_dinh: str = ""
    tuy_chon: dict = field(default_factory=dict) # tham số → [{value,label}] theo NGƯỜI DÙNG
    gia: dict = field(default_factory=dict)      # `AppManifest.bang_gia()` của app sở hữu
    duong_dan_app: str = ""  # route_prefix của app sở hữu (deep-link "quản lý giọng")
    san_sang: str = "san_sang"   # "san_sang" | "ban" | "chua_san_sang" (từ `AppManifest.suc_khoe`)


def _mac_dinh(pt, models: dict) -> str:
    """Alias mặc định theo hợp đồng, chỉ lùi về phần tử đầu khi hợp đồng câm.

    ⛔ Lùi về `next(iter(models))` là **có chủ ý**, không phải cẩu thả: một năng
       lực không khai `default` vẫn phải chọn được một cái gì đó, nếu không giao
       diện mở ra với ô model trống và không gửi được gì. Nhưng nó chỉ là lưới
       đỡ — và `test_632` chốt rằng `text.chat` **không** rơi vào lưới đó.
    """
    try:
        cho = ((pt.input_schema or {}).get("properties") or {}).get("model") or {}
    except AttributeError:
        cho = {}
    khai = str(cho.get("default") or "")
    if khai and khai in models:
        return khai
    return next(iter(models), "")


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


#: Đệm kết quả `suc_khoe()` theo slug: (thời điểm, giá trị). Một trang catalog
#: không được thăm dò ba dịch vụ mỗi lần vẽ.
_DEM_SUC_KHOE: dict = {}
DEM_SUC_KHOE_GIAY = 10.0
TRANG_THAI_HOP_LE = ("san_sang", "ban", "chua_san_sang")


def suc_khoe_cua(manifest, *, now=None) -> str:
    """`manifest.suc_khoe()` có đệm; không khai ⇒ chỉ biết `enabled`; ném ⇒ `chua_san_sang`.

    Fail-closed có chủ ý: một hook ném hay trả giá trị lạ nghĩa là ta **không
    biết** dịch vụ sống hay chết — và "không biết" phải hiện ra là "chưa sẵn
    sàng", không phải chip xanh (bài học `ltt_voice` 02/09).
    """
    import time

    if not manifest.enabled:
        return "chua_san_sang"
    if manifest.suc_khoe is None:
        return "san_sang"
    t = time.monotonic() if now is None else now
    dem = _DEM_SUC_KHOE.get(manifest.slug)
    if dem and t - dem[0] < DEM_SUC_KHOE_GIAY:
        return dem[1]
    try:
        gia_tri = str(manifest.suc_khoe() or "")
    except Exception:                                           # noqa: BLE001
        log.exception("suc_khoe cua %s nem", manifest.slug)
        gia_tri = "chua_san_sang"
    if gia_tri not in TRANG_THAI_HOP_LE:
        log.warning("suc_khoe cua %s tra gia tri la %r", manifest.slug, gia_tri)
        gia_tri = "chua_san_sang"
    _DEM_SUC_KHOE[manifest.slug] = (t, gia_tri)
    return gia_tri


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
                model_mac_dinh=_mac_dinh(pt, models),
                ten=tool.name,
                phuong_thuc=phuong_thuc_cua(tool),
                che_do="stream" if getattr(tool, "sync_executor", "") else "job",
                nhan=pt.description,
                hop_dong=pt.to_public_dict(),
                models=models,
                tuy_chon=_tuy_chon(tool, db, user_id),
                gia=_gia(m),
                duong_dan_app=m.route_prefix,
                san_sang=suc_khoe_cua(m),
            ))
    ra.sort(key=lambda n: n.ten)
    return ra
