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


def xuat_ban_draft(db, workflow_id: str, *, created_by: str,
                   cong_cu: Optional[dict] = None) -> WorkflowVersion:
    """Draft → biên dịch → báo giá → version bất biến (spec §4.2, §7.2).

    Ném `bien_dich.LoiBienDich` / `bao_gia.KhongBaoGiaDuoc` — bên gọi đổi thành
    422 có `ma`. Không commit.
    """
    from platform_core.workflow import bao_gia, bien_dich

    draft = db.get(WorkflowDraft, workflow_id)
    if draft is None:
        raise bien_dich.LoiBienDich("do_thi_rong", "chua co ban nhap")
    graph = bien_dich.bien_dich(draft.document or {}, cong_cu=cong_cu)
    _kiem_credential(db, workflow_id, graph)
    _ghim_subworkflow(db, workflow_id, graph)
    gia = bao_gia.bao_gia_do_thi(graph, cong_cu=cong_cu)
    return xuat_ban(db, workflow_id, graph, created_by=created_by,
                    estimated_max=gia.toi_da)


def _kiem_credential(db, workflow_id: str, graph: dict) -> None:
    """Moi `credential_ref` trong do thi phai **dung duoc** (spec §9.1).

    🔴 CHAN O PUBLISH, KHONG PHAI LUC CHAY. Mot ref cua nguoi khac phat hien
       luc chay la mot run da tieu tien roi moi FAILED; phat hien luc publish
       la mot thong bao truoc khi khach bam Chay lan nao.

    ⛔ **Khong giai ma gi o day.** `credential.kiem_ref` chi hoi ba cau: ref co
       thuoc chu workflow khong, con hieu luc khong, `kieu` co nam trong
       `NodeDefinition.credential` khong. Dong co, validator va API khong bao
       gio cham ban ro (spec §9.4).
    """
    from platform_core import credential as kho
    from platform_core.models import Workflow
    from platform_core.workflow import bien_dich, nut

    refs = [(str(n.get("id", "")), str(n.get("type", "")),
             str(n.get("credential_ref") or ""))
            for n in (graph.get("nodes") or [])]
    refs = [r for r in refs if r[2]]
    if not refs:
        return
    wf = db.get(Workflow, workflow_id)
    owner = str(getattr(wf, "owner_id", "") or "")
    so = nut.tat_ca()
    for nid, loai, ref in refs:
        nd = so.get(loai)
        try:
            kho.kiem_ref(db, ref, owner_id=owner,
                         kieu_cho_phep=tuple(getattr(nd, "credential", ()) or ()))
        except kho.LoiCredential as loi:
            # ⛔ MOT ma cho ca ba ca (khong thay / da thu hoi / sai kieu): phan
            #    biet chung o bề mat publish la mot may dem cho nguoi ngoai biet
            #    id nao ton tai — cung bai voi `credential._hang`. Ly do that
            #    di vao `chi_tiet`, thu chi chu workflow doc.
            raise bien_dich.LoiBienDich(
                "credential_khong_hop_le",
                f"node {nid!r}: credential khong dung duoc ({loi.ma})",
                nid) from loi


def _ghim_subworkflow(db, workflow_id: str, graph: dict) -> None:
    """Ghim `version_id` của mọi `core.call_workflow`, và ghi `gia_con`.

    Spec §5.10: *"`version_id` … ghim lúc **publish cha**: compiler thay
    `"latest"` bằng id version publish hiện tại, ghi vào graph cha"*.

    🔴 BA THỨ ĐƯỢC CHỐT Ở ĐÂY, VÀ CHỈ Ở ĐÂY

    1. **`version_id` ghim** ⇒ một lần publish lại workflow con không đổi hành
       vi của cha đang chạy. Cùng bất biến `WorkflowRun.version_id` giữ cho run.
    2. **`gia_con` do NỀN TẢNG ghi**, đọc từ `WorkflowVersion.estimated_max`
       của con. ⛔ Client không khai được (`additionalProperties: false` từ chối
       `gia_con` trong draft) — *"một trường trong body của người gọi không thể
       là nguồn của một con số nền tảng dùng để giữ tiền của chính người gọi
       ấy"* (`bao_gia.py`).
    3. **Độ sâu** (`graph["do_sau_goi"]`) tính TĨNH: mọi `version_id` đã ghim và
       version là **bất biến**, nên cây gọi hữu hạn và đo được lúc publish. Chặn
       ở publish rẻ hơn chặn lúc chạy đúng một lượt tiêu tiền.
    """
    from platform_core.models import Workflow, WorkflowVersion
    from platform_core.workflow import bien_dich, run_con

    sau_nhat = 0
    for node in graph.get("nodes") or []:
        if str(node.get("type")) != run_con.LOAI_GOI:
            continue
        nid = str(node.get("id", ""))
        p = node.setdefault("params", {})
        wid = str(p.get("workflow_id") or "")
        if wid == workflow_id:
            raise bien_dich.LoiBienDich(
                "goi_de_quy",
                f"node {nid!r} goi chinh workflow nay -- mot cay goi phai huu "
                "han moi tinh duoc tran chi phi", nid)
        con = db.get(Workflow, wid)
        if con is None or con.owner_id != db.get(Workflow, workflow_id).owner_id:
            raise bien_dich.LoiBienDich(
                "workflow_con_khong_ton_tai",
                f"node {nid!r}: khong co workflow {wid!r} cua cung nguoi dung",
                nid)
        xin = str(p.get("version_id") or "latest")
        vid = con.published_version_id if xin == "latest" else xin
        ver = db.get(WorkflowVersion, vid) if vid else None
        if ver is None or ver.workflow_id != wid:
            raise bien_dich.LoiBienDich(
                "workflow_con_chua_publish",
                f"node {nid!r}: workflow {wid!r} chua co ban publish nao de "
                "ghim", nid)
        p["version_id"] = ver.id
        p["gia_con"] = int(ver.estimated_max or 0)
        sau_nhat = max(sau_nhat,
                       1 + int((ver.graph or {}).get("do_sau_goi", 0) or 0))
    if sau_nhat > run_con.DO_SAU_TOI_DA:
        raise bien_dich.LoiBienDich(
            "qua_sau_subworkflow",
            f"cay goi sau {sau_nhat} tang > tran {run_con.DO_SAU_TOI_DA} "
            "(spec §10)")
    graph["do_sau_goi"] = sau_nhat


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
