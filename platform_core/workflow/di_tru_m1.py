"""`M-1` — chuyển bản nháp Canvas v2 (`agent_workflows`) sang lược đồ V2.

Nguồn: `docs/architecture/workflow_v2_audit/27_29 §27.2`.

## 🔴 HẠNG MỤC NÀY TỪNG ĐƯỢC XẾP LÀ "GẦN NHƯ KHÔNG TỒN TẠI"

`§27.1` viết vậy dựa trên một phép đo **đúng**: `0 job agent.advance / 28 ngày`.
Kết luận rút ra: *"không có khách đứng trên đường cũ ⇒ thay thẳng, gỡ bản cũ"*.

⚠️ Đo `D2` ngày 08/09/2026 trên chính CSDL production:

    agent_workflows 10 · agent_runs 4 · agent_workflow_snapshots 83
    doi chung: users 27 · jobs 1770 · credit_entries 5500

⇒ `0 run` **đúng**, nhưng nó nói **KHÔNG AI CHẠY** — không nói **KHÔNG AI ĐÃ
  DỰNG**. Đó là hai mệnh đề khác nhau, và cả tài liệu lẫn `CLAUDE.md` đã đọc
  mệnh đề thứ nhất thành mệnh đề thứ hai.

## ⭐ HÌNH DẠNG THẬT quyết cách làm, không phải con số tổng

Đo tiếp (chỉ đọc, 08/09):

    10/10 mang ten mac dinh "Workflow moi"   khong ai doi ten
    toi da 3 node, toi da 2 canh             khong do thi nao that su
    4/10 `document` RONG                     khong co Canvas v2 de chuyen
    6/10 `document` 5 khoa                   active_page_id · budget_max_credit
                                             · goal · pages · version
    3 `validated` · 7 `draft` · tat ca `plan_version = 1`

⇒ `M-1` **có thật** nhưng **nhỏ**, và nó phải xử **ba lớp** chứ không một.

## ⛔ HAI TÍNH CHẤT BẮT BUỘC

**Mặc định là CHẠY THỬ.** Một script di trú mặc định ghi là một script chỉ cần
gõ nhầm một lần. Mặc định chạy thử biến "lỡ tay" thành một **báo cáo**.

**Luỹ đẳng.** Một script chạy lại vì hoảng không được biến thành một sự cố
thật.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from platform_core.models import AgentWorkflow, Workflow, WorkflowDraft

#: Khoá của Canvas v2 mang **ý nghĩa nghiệp vụ** — phải sang v3 nguyên vẹn.
#: `budget_max_credit` là một con số về TIỀN: mất nó là mất trần chi phí.
_GIU_NGUYEN = ("goal", "budget_max_credit", "active_page_id")


def _canh_v3(canh: dict) -> dict:
    """Cạnh v2 → v3, **giữ lại** `sourceHandle`/`targetHandle`.

    ⭐ Đây là toàn bộ giá trị của `M-1`. `27_29 §27.2`:

        "du lieu de dung canh co kieu DA CO SAN — hom nay `canvas_to_plan()`
         VUT NO DI. Script chuyen GIU LAI thu dang bi vut."

    Tức việc này không phải chép dữ liệu sang chỗ mới, mà **cứu phần thông tin
    mà đường cũ đang đánh rơi**. Sau khi Plan v1 bị gỡ, thứ đã rơi không lấy
    lại được.
    """
    return {
        "id": str(canh.get("id", "")),
        "source_node": str(canh.get("source", "")),
        "target_node": str(canh.get("target", "")),
        "source_port": str(canh.get("sourceHandle") or "out"),
        "target_port": str(canh.get("targetHandle") or "in"),
        "kind": "DATA",
    }


def _trang_v3(trang: dict) -> dict:
    return {
        "id": str(trang.get("id", "p1")),
        "name": str(trang.get("name", "")),
        "nodes": list(trang.get("nodes") or []),
        "edges": [_canh_v3(c) for c in (trang.get("edges") or [])],
    }


def _tu_document(doc: dict) -> Optional[dict]:
    trang = doc.get("pages") or []
    if not trang:
        return None
    ra: dict[str, Any] = {"version": 3,
                          "pages": [_trang_v3(t) for t in trang]}
    for k in _GIU_NGUYEN:
        if k in doc:
            ra[k] = doc[k]
    return ra


def _tu_nodes_edges(cu: AgentWorkflow) -> Optional[dict]:
    """Đường dự phòng cho **4/10** bản ghi production có `document` rỗng.

    ⛔ Bỏ qua chúng là bỏ mất **40 %** thứ cần chuyển, và bỏ theo cách im lặng:
       script báo *"đã chuyển 6"* và không ai hỏi *6 trên mấy*.
    """
    nodes = list(cu.nodes or [])
    edges = list(cu.edges or [])
    if not nodes and not edges:
        return None
    return {
        "version": 3,
        "goal": cu.goal or "",
        "budget_max_credit": int(cu.budget_max or 0),
        "active_page_id": "p1",
        "pages": [{"id": "p1", "name": "", "nodes": nodes,
                   "edges": [_canh_v3(c) for c in edges]}],
    }


def chuyen(db, *, chay_that: bool = False) -> dict:
    """Chuyển mọi `AgentWorkflow` sang `workflow` + `workflow_draft`.

    Trả một báo cáo **cộng lại được**:

        da_chuyen + rong + da_co == tong so ban ghi

    ⭐ Bất biến ấy là thứ làm báo cáo kiểm được: không có nó, một nhánh
       `continue` bị bỏ quên sẽ làm vài bản ghi biến mất khỏi **mọi** con số,
       và một báo cáo không cộng lại được là một báo cáo không ai kiểm được.
    """
    cu_ds = list(db.execute(select(AgentWorkflow)).scalars())
    ra: dict[str, Any] = {
        "chay_that": bool(chay_that), "tong": len(cu_ds),
        "da_chuyen": 0, "rong": 0, "da_co": 0, "se_chuyen": 0,
        "anh_xa": {},
    }

    for cu in cu_ds:
        # Luỹ đẳng theo `source_workflow_id`: một lần chạy lại tìm thấy bản cũ
        # thay vì tạo bản thứ hai.
        da = db.execute(
            select(Workflow).where(Workflow.name == cu.name,
                                   Workflow.owner_id == cu.user_id)).scalars()
        trung = [w for w in da if w.published_version_id == f"m1:{cu.id}"]
        if trung:
            ra["da_co"] += 1
            ra["anh_xa"][cu.id] = trung[0].id
            continue

        doc = cu.document if isinstance(cu.document, dict) else {}
        moi = _tu_document(doc) or _tu_nodes_edges(cu)
        if moi is None:
            # Rỗng hoàn toàn. Vẫn đếm — gộp nó vào `da_chuyen` là nói dối một
            # cách dễ chịu: con số đẹp hơn, và người đọc tưởng có 10 đồ thị
            # được cứu.
            ra["rong"] += 1
            continue

        if not chay_that:
            ra["se_chuyen"] += 1
            continue

        # ⚠️ GIỮ NGUYÊN tên: 10/10 bản ghi production mang tên mặc định
        #    "Workflow mới". Đặt tên mới cho chúng là **bịa** một thông tin mà
        #    không người dùng nào cung cấp.
        wf = Workflow(owner_id=cu.user_id, name=cu.name)
        # Dấu nguồn, để lần chạy thứ hai nhận ra. Không thêm cột mới cho một
        # script chạy một lần.
        wf.published_version_id = f"m1:{cu.id}"
        db.add(wf)
        db.flush()
        db.add(WorkflowDraft(workflow_id=wf.id, document=moi, revision=1))
        db.flush()
        ra["da_chuyen"] += 1
        ra["anh_xa"][cu.id] = wf.id

    return ra
