"""Kết quả của một lượt chạy — **DẪN XUẤT** từ các node `core.output`.

⛔ KHÔNG CÓ CỘT `output_data` TRÊN `workflow_run`, và đó là một quyết định.

Một cột thứ hai giữ cùng sự thật là một chỗ để hai câu trả lời lệch nhau: ảnh
chụp nói một đằng, cột nói một nẻo, và sau một lần chạy lại thì không ai biết
cái nào đúng. Cùng lập luận với `tien.py` (*"một khoá phái sinh là một khoá có
thể lệch khỏi thứ nó trỏ tới"*) và với `api_prod_canary` (*"không bảng chép
tay"*).

Giá phải trả: một lượt đọc kết quả tốn một truy vấn lược đồ + một truy vấn ảnh
chụp cho mỗi node `core.output`. Số node `core.output` của một đồ thị là **đơn
vị**, không phải hàng trăm — nên cái giá ấy không đổi hình dạng khi đồ thị to ra.
"""
from __future__ import annotations

from typing import Any

from platform_core.models import WorkflowRun, WorkflowVersion
from platform_core.workflow import thi_hanh

LOAI_OUTPUT = "core.output"


def ten_output(graph: dict) -> dict[str, str]:
    """`{id node: tên đầu ra}` cho mọi node `core.output` của một đồ thị."""
    return {str(n["id"]): str((n.get("params") or {}).get("ten") or "")
            for n in (graph.get("nodes") or [])
            if str(n.get("type")) == LOAI_OUTPUT}


def doc(db, run_id: str) -> dict[str, Any]:
    """`{tên: giá trị}` của những `core.output` đã chạy xong.

    ⚠️ Node `core.output` **chưa** `SUCCEEDED` thì vắng mặt, không phải `None`:
       một `None` im lặng sẽ đi tiếp vào chỗ người ta tưởng là kết quả thật.
       Cùng luật với `chinh_sach.KhongGianVars`.
    """
    run = db.get(WorkflowRun, run_id)
    if run is None:
        return {}
    version = db.get(WorkflowVersion, run.version_id)
    if version is None:
        return {}
    ra: dict[str, Any] = {}
    for nid, ten in ten_output(version.graph or {}).items():
        anh = thi_hanh.anh_chup_hien_tai(db, run_id, nid)
        if anh is None or anh.execution_status != "SUCCEEDED":
            continue
        ra[ten] = (anh.output_ref or {}).get("gia_tri")
    return ra


__all__ = ["LOAI_OUTPUT", "doc", "ten_output"]
