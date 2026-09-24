"""Cầu nối CSDL → môi trường §6.2 của ngôn ngữ biểu thức.

🔑 VÌ SAO LÀ MỘT TỆP RIÊNG

`chinh_sach.KhongGianNodes` nói thẳng ranh giới của nó:

    "Nhan MAP chu khong nhan doi tuong run: tang nay khong duoc biet CSDL, va
     ai nap anh chup do la viec cua tang dong co."

⇒ Đây là "ai nạp ảnh chụp đó". Máy biểu thức không được biết SQLAlchemy; động
  cơ không được biết cú pháp §6.2. Tệp này là chỗ duy nhất hai bên gặp nhau.

⛔ Không dựng một bản sao của `moi_truong_wf` — gọi thẳng nó. Một bảng namespace
   thứ hai là một bảng sẽ trôi, và ngày nó trôi thì trình soạn gợi ý một tên mà
   lúc chạy không có.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from platform_core.workflow import chinh_sach, thi_hanh

#: Khoá trong `output_ref` giữ TÊN NHÁNH mà một node rẽ (`core.if`/`core.switch`,
#: spec §5.4). Cạnh CONTROL mang `condition = "<tên nhánh>"` và chỉ cạnh khớp
#: mới được kích hoạt — nên đây là chỗ duy nhất nói "nhánh nào đã chạy".
KHOA_NHANH = "_nhanh"

#: Những khoá nội bộ động cơ ghi vào `output_ref`. Chúng KHÔNG phải cổng ra và
#: không được lộ vào `nodes.<id>.output` của người soạn biểu thức.
#:
#: ⚠️ Đây là một danh sách, tức một chỗ có thể quên. `test_1783` ghim rằng
#:    `nodes.<id>.output` không chứa khoá nào bắt đầu bằng `_`.
KHOA_NOI_BO = ("_gia_that", "_tran", "_thu_lai_luc", KHOA_NHANH)


def _cong_ra(output_ref: Optional[Mapping]) -> dict:
    return {k: v for k, v in (output_ref or {}).items()
            if not str(k).startswith("_")}


def anh_chup_nodes(db, run_id: str, node_ids) -> dict[str, dict]:
    """`{id: {"status", "output", "error"}}` cho `chinh_sach.KhongGianNodes`.

    ⚠️ CHỈ những node đã có ảnh chụp. Node chưa chạy **vắng mặt** chứ không phải
       rỗng: `KhongGianNodes` nói *"node chưa có trong run"*, còn một bản ghi
       rỗng sẽ nói *"output không có khoá đó"* — hai câu dẫn người gõ đi hai
       hướng khác nhau.
    """
    ra: dict[str, dict] = {}
    for nid in node_ids:
        anh = thi_hanh.anh_chup_hien_tai(db, run_id, str(nid))
        if anh is None:
            continue
        ra[str(nid)] = {"status": anh.execution_status,
                        "output": _cong_ra(anh.output_ref),
                        "error": str(anh.error or "")}
    return ra


def to_tien_cua(graph: dict) -> dict[str, set[str]]:
    """`{id: tập tổ tiên}` từ `graph.thu_tu` + `graph.edges`.

    ⚠️ Cùng phép tính mà `bien_dich.cau_truc` làm lúc publish, chỉ khác đầu vào
       (đồ thị đã biên dịch thay vì draft). Không phải một luật thứ hai: thứ tự
       tô-pô đã nằm sẵn trong `graph.thu_tu`, đây chỉ là lan tập theo nó.
    """
    ke: dict[str, list[str]] = {str(n["id"]): [] for n in graph.get("nodes") or []}
    for e in graph.get("edges") or []:
        if str(e["source_node"]) in ke:
            ke[str(e["source_node"])].append(str(e["target_node"]))
    ra: dict[str, set[str]] = {k: set() for k in ke}
    for k in graph.get("thu_tu") or list(ke):
        for t in ke.get(str(k), ()):
            if t in ra:
                ra[t] |= ra[str(k)] | {str(k)}
    return ra


def moi_truong_run(db, run, graph: dict, node_id: str, *, loop: Any = None,
                   params: Any = None) -> dict[str, Any]:
    """Môi trường §6.2 đầy đủ cho một lần tính **của một node** trong một run.

    `node_id` là bắt buộc vì `vars` (§6.5) là *"gộp output của mọi `core.set` là
    **tổ tiên** của node đang tính"* — một môi trường "dùng chung cho cả run"
    sẽ cho node này đọc biến của một nhánh song song chưa chắc chạy.

    `loop` chỉ có mặt khi đang ở trong thân `foreach` — truyền `None` ở ngoài,
    vì *"đọc `loop.item` ngoài thân ForEach phải báo **không có `loop`**"*
    (`chinh_sach.moi_truong_wf`).
    """
    from platform_core.workflow import bien_vars

    nodes = graph.get("nodes") or []
    anh = anh_chup_nodes(db, run.id, [n["id"] for n in nodes])
    to_tien = to_tien_cua(graph).get(str(node_id), set())
    vars_ = bien_vars.gop_vars(
        anh,
        nguoi_ghi=[str(n["id"]) for n in nodes
                   if str(n.get("type")) == bien_vars.LOAI_GHI],
        to_tien=to_tien, thu_tu=graph.get("thu_tu") or [])
    return chinh_sach.moi_truong_wf(
        trigger={"kind": str(run.trigger_kind or "")},
        workflow_input={}, vars=vars_,
        nodes=anh, loop=loop, params=params,
        run={"id": run.id, "status": run.status})


__all__ = ["KHOA_NHANH", "KHOA_NOI_BO", "anh_chup_nodes", "moi_truong_run",
           "to_tien_cua"]
