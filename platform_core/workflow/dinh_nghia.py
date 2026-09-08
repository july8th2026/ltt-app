"""Định nghĩa workflow: draft (sửa được) · version (bất biến) · hash tất định.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.1`.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import func, select

from platform_core.i18n import N_

from platform_core.models import (Workflow, WorkflowDraft, WorkflowVersion,
                                  WorkflowVersionEdge, WorkflowVersionNode)


class XungDotRevision(RuntimeError):
    """Draft đã đổi kể từ lúc client đọc. Bên gọi HTTP nên trả 409.

    ⚠️ Thông điệp của nó là **chẩn đoán cho lập trình viên**, viết ASCII có chủ
    ý. Chữ hiện cho người dùng do tầng HTTP dựng và phải đi qua `_()`; một
    thông điệp tiếng Việt ở đây trông như chữ giao diện nhưng không bao giờ
    được trích dịch — tệ hơn cả không có.
    """


# ⚠️ Trường CHỈ phục vụ trình bày — không được vào hash. Không khai tường minh
#    thì `position` lọt vào, và **kéo một node sang phải sinh một version mới**:
#    lịch sử đầy version giả, và `UNIQUE(workflow_id, graph_hash)` mất tác dụng
#    vì không lần xuất bản nào trùng lần nào.
#
#    Bài học Kestra (`07+08 §1.4`). `test_950` ghim tập này; thu hẹp nó thì gate
#    đỏ — cố ý, vì thu hẹp lặng lẽ chính là cách khiếm khuyết trên quay lại.
LOAI_TRU_KHOI_HASH = frozenset({
    "position", "label", "summary", "_ui", "created_at", "updated_at",
})


def _loc(gia_tri: Any) -> Any:
    """Bỏ đệ quy các khoá trình bày khỏi một cấu trúc lồng nhau."""
    if isinstance(gia_tri, dict):
        return {k: _loc(v) for k, v in gia_tri.items()
                if k not in LOAI_TRU_KHOI_HASH}
    if isinstance(gia_tri, list):
        return [_loc(v) for v in gia_tri]
    return gia_tri


def bam_do_thi(graph: dict) -> str:
    """sha256 **tất định** của phần nội dung trong `graph`.

    Hai chuẩn hoá, và cả hai đều cần thiết:

    - **bỏ trường trình bày** (`LOAI_TRU_KHOI_HASH`) — kéo node không đổi nội dung;
    - **sắp xếp `nodes` theo `id`** — Canvas trả chúng theo thứ tự dựng, và thứ
      tự dựng không phải nội dung. `sort_keys=True` của `json.dumps` chỉ sắp
      khoá của dict, **không** sắp phần tử của list.

    ⛔ `edges` thì KHÔNG sắp, và đó không phải một thiếu sót.

    `25_26 §7` khai cổng `multiple: True` — **một cổng nhận nhiều cạnh**. Không
    có trường thứ tự tường minh nào trên cạnh, nên thứ tự mảng `edges` là thứ
    **duy nhất** mang được thứ tự nối vào một node kiểu `text.join`. Sắp nó đi
    là quyết định lặng lẽ rằng thứ tự ấy không tồn tại.

    ⭐ Hai chiều hỏng KHÔNG đối xứng (phiên ASV chỉ ra, ca đối chứng của họ:
    `che_do_render.van_tay_che_do`, nơi các vùng che chồng nhau nối tiếp):

        thieu sorted() khi thu tu KHONG co nghia -> van tay gia -> lam viec thua
        thua  sorted() khi thu tu CO   co nghia -> hai ket qua KHAC dung chung
                                                   mot van tay -> PHUC VU LAI
                                                   MOT KET QUA SAI

    ⇒ Khi phân vân thì **giữ thứ tự** — ngược với phản xạ "chuẩn hoá cho sạch".
       Nếu sau này Đợt 4 đưa vào số thứ tự tường minh trên cạnh
       (`23_24 §4.2`, cardinality), khi ấy sắp `edges` mới an toàn.
    """
    goi = _loc(graph)
    muc = goi.get("nodes")
    if isinstance(muc, list):
        goi["nodes"] = sorted(muc, key=lambda m: str(m.get("id", "")))
    canonical = json.dumps(goi, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def tao_workflow(db, *, owner_id: str, name: str = "") -> Workflow:
    """Tạo danh tính workflow. KHÔNG commit — caller commit cùng việc của mình."""
    wf = Workflow(owner_id=owner_id, name=name or N_("Workflow mới"))
    db.add(wf)
    db.flush()
    return wf


def luu_draft(db, workflow_id: str, *, document: dict,
              revision: int) -> WorkflowDraft:
    """Ghi bản đang soạn với khoá lạc quan.

    `revision` là số mà client ĐANG GIỮ. Khớp thì ghi và tăng lên; lệch thì
    `XungDotRevision` — người đến sau phải đọc lại, không được ghi đè.
    """
    draft = db.get(WorkflowDraft, workflow_id)
    if draft is None:
        if revision != 0:
            raise XungDotRevision(
                f"draft chua ton tai nhung client giu revision={revision}")
        draft = WorkflowDraft(workflow_id=workflow_id, document=document,
                              revision=1)
        db.add(draft)
        db.flush()
        return draft

    if draft.revision != revision:
        raise XungDotRevision(
            f"draft dang o revision {draft.revision}, client giu {revision}")
    draft.document = document
    draft.revision = draft.revision + 1
    db.flush()
    return draft


def xuat_ban(db, workflow_id: str, graph: dict, *, created_by: str,
             estimated_max: int = 0) -> WorkflowVersion:
    """Đóng băng `graph` thành một version bất biến.

    ⭐ Xuất bản lại **cùng nội dung** trả về đúng version cũ, không tạo bản mới.
       Đó là hành vi của `UNIQUE (workflow_id, graph_hash)`; hàm này chỉ tránh
       đi vào ràng buộc chứ không phải nơi cưỡng chế nó — cưỡng chế nằm ở CSDL,
       nên hai request song song cũng không lách được.
    """
    h = bam_do_thi(graph)
    cu: Optional[WorkflowVersion] = db.execute(
        select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.graph_hash == h)
    ).scalars().first()
    if cu is not None:
        return cu

    seq_cuoi = db.execute(
        select(func.max(WorkflowVersion.seq))
        .where(WorkflowVersion.workflow_id == workflow_id)
    ).scalar()
    version = WorkflowVersion(
        workflow_id=workflow_id, seq=int(seq_cuoi or 0) + 1,
        graph=graph, graph_hash=h,
        estimated_max=max(0, int(estimated_max or 0)), created_by=created_by)
    db.add(version)
    db.flush()
    _sinh_chi_muc(db, version)
    return version


def _sinh_chi_muc(db, version: WorkflowVersion) -> None:
    """Trải `graph` ra hai bảng phẳng để truy vấn được bằng SQL.

    Dẫn xuất thuần: mất chúng thì dựng lại được từ `graph`; lệch chúng thì
    `graph` đúng.
    """
    for node in version.graph.get("nodes", []) or []:
        db.add(WorkflowVersionNode(
            version_id=version.id, node_id=str(node.get("id", "")),
            node_type=str(node.get("type", "")),
            type_version=int(node.get("type_version", 1) or 1)))
    for edge in version.graph.get("edges", []) or []:
        db.add(WorkflowVersionEdge(
            version_id=version.id, edge_id=str(edge.get("id", "")),
            source_node=str(edge.get("source_node", "")),
            source_port=str(edge.get("source_port", "")),
            target_node=str(edge.get("target_node", "")),
            target_port=str(edge.get("target_port", "")),
            kind=str(edge.get("kind", "DATA")),
            condition=edge.get("condition") or {}))
    db.flush()
