"""
workflows.py — nạp template workflow ComfyUI và thay tham số.

Template là JSON **định dạng API** của ComfyUI (`{"<node_id>": {"class_type":...,
"inputs": {...}}}`), giữ trong repo ở `render_gateway/workflows/`. Thêm một model
mới = thêm một file JSON, **không sửa mã** — đó là toàn bộ ý nghĩa của "kiến trúc
không phụ thuộc model" ở `KE_HOACH_H37.md` §2, và nó đã được thử thật một lần khi
model đích đổi từ Klein 9B sang HiDream-O1 mà không phải sửa dòng nào.

Chỗ cần thay giá trị thì viết một **thẻ** dạng chuỗi `"@ten"`. Ta duyệt cây JSON và
thay đúng những chuỗi bằng thẻ đó — không dùng thay-chuỗi trên văn bản, vì như thế
sẽ dính cả những chỗ chỉ tình cờ chứa chữ giống thẻ.

⛔ KIỂM NODE TRƯỚC KHI GỬI. ComfyUI từ chối workflow thiếu node bằng HTTP 400 —
   nhưng chỉ sau khi ta đã xếp hàng và chờ. `/object_info` trả lời câu đó trong
   một lời gọi. Đây đúng tinh thần `cong_gpu.py` của dự án video máy B:
   *"thứ gì CPU trả lời được thì không hỏi GPU"*.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Optional

#: Thư mục template — neo theo vị trí gói, KHÔNG dùng `parents[n]` (đếm sai cấp
#: ngay khi file đổi chỗ, và hỏng lặng lẽ).
THU_MUC_MAC_DINH = Path(__file__).with_name("workflows")


class WorkflowError(ValueError):
    """Template hỏng, thiếu thẻ, hoặc thiếu node — đều là lỗi của TA, không phải
    của ComfyUI. Tách riêng để không đổ lỗi nhầm cho máy chủ."""


def the(ten: str) -> str:
    """Thẻ thay-giá-trị dùng trong template JSON."""
    return f"@{ten}"


def nap(ten_file: str, *, thu_muc: Optional[Path] = None) -> dict:
    duong = (thu_muc or THU_MUC_MAC_DINH) / ten_file
    if not duong.is_file():
        raise WorkflowError(f"khong thay template: {duong}")
    try:
        data = json.loads(duong.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise WorkflowError(f"template {ten_file} khong phai JSON hop le: {e}") from None
    if not isinstance(data, dict) or not data:
        raise WorkflowError(f"template {ten_file} phai la object khong rong")
    return data


def the_con_thieu(workflow: dict, gia_tri: dict[str, Any]) -> list[str]:
    """Những thẻ còn trong template mà `gia_tri` không cấp. Trả danh sách đã sắp."""
    con: set[str] = set()
    _duyet(workflow, lambda v: con.add(v[1:]) if _la_the(v) else None)
    return sorted(con - set(gia_tri))


def thay(workflow: dict, gia_tri: dict[str, Any], *, cho_phep_thieu: bool = False) -> dict:
    """Thay mọi thẻ bằng giá trị. Trả bản sao — template gốc không bị đụng.

    Thiếu thẻ là lỗi, không phải cảnh báo: một workflow còn nguyên `"@seed"` sẽ
    được ComfyUI nhận rồi hỏng ở giữa, tốn trọn thời gian nạp model mới lộ ra.
    """
    thieu = the_con_thieu(workflow, gia_tri)
    if thieu and not cho_phep_thieu:
        raise WorkflowError(f"thieu gia tri cho the: {', '.join(thieu)}")
    return _thay_sau(copy.deepcopy(workflow), gia_tri)


def node_can(workflow: dict) -> set[str]:
    """Tập `class_type` mà workflow này cần."""
    ra: set[str] = set()
    for node in workflow.values():
        if isinstance(node, dict):
            ct = node.get("class_type")
            if isinstance(ct, str) and ct:
                ra.add(ct)
    return ra


def kiem_node(workflow: dict, node_dang_co: set[str]) -> None:
    """Ném `WorkflowError` nếu ComfyUI thiếu node mà workflow cần."""
    thieu = sorted(node_can(workflow) - node_dang_co)
    if thieu:
        raise WorkflowError(
            "ComfyUI thieu node: " + ", ".join(thieu[:8])
            + (" ..." if len(thieu) > 8 else ""))


# ── nội bộ ───────────────────────────────────────────────────────────────────
def _la_the(v: Any) -> bool:
    return isinstance(v, str) and len(v) > 1 and v.startswith("@") and not v.startswith("@@")


def _duyet(nut: Any, ham) -> None:
    if isinstance(nut, dict):
        for v in nut.values():
            _duyet(v, ham)
    elif isinstance(nut, list):
        for v in nut:
            _duyet(v, ham)
    elif isinstance(nut, str):
        ham(nut)


def _thay_sau(nut: Any, gia_tri: dict[str, Any]) -> Any:
    if isinstance(nut, dict):
        return {k: _thay_sau(v, gia_tri) for k, v in nut.items()}
    if isinstance(nut, list):
        return [_thay_sau(v, gia_tri) for v in nut]
    if _la_the(nut):
        ten = nut[1:]
        # Thẻ không có giá trị chỉ tới được đây khi caller đặt `cho_phep_thieu`.
        return gia_tri[ten] if ten in gia_tri else nut
    if isinstance(nut, str) and nut.startswith("@@"):
        # `"@@x"` là cách viết một chuỗi bắt đầu bằng `@` mà KHÔNG phải thẻ.
        return nut[1:]
    return nut
