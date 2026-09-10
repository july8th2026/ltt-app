"""Thi hành workflow: `workflow_run` + chuỗi ảnh chụp bất biến của mỗi node.

Mô hình **C** (chốt `Q3`, `12_19 §16.2`). Nguồn thiết kế: `23_24 §4.2`.

⛔ Đợt 2 **chưa nối vào đường chạy nào** — đây là tầng lưu trữ và các phép đổi
   trạng thái, không phải scheduler. Scheduler là Đợt 3 (`27_29 §28`).
"""
from __future__ import annotations

from typing import Optional

from platform_core.models import NodeRun, NodeRunSnapshot, WorkflowRun


def tao_run(db, *, workflow_id: str, version_id: str, owner_id: str,
            trigger_kind: str = "manual", idempotency_key: str = "",
            estimated_max: int = 0) -> WorkflowRun:
    """Mở một lượt chạy, GHIM `version_id`.

    ⚠️ KHÔNG có `SELECT` chống trùng `idempotency_key` ở đây, và đó là chủ ý:
       chống trùng do chỉ mục bộ phận `ux_workflow_run_idem` cưỡng chế. Một
       `SELECT` trước `INSERT` để lại đúng cửa sổ tranh chấp mà `c9d4e1a77b02`
       sinh ra để đóng — hai request song song cùng thấy "chưa có", cùng chèn.

    ⇒ Bên gọi bắt `IntegrityError` và trả về lượt cũ. Thua ở CSDL rẻ hơn thắng
      ở một câu truy vấn không có khoá.

    ⚠️ Lỗi ấy nổi lên ở **`flush()` bên trong hàm này**, KHÔNG phải ở `commit()`
       của bên gọi — `tao_run` phải `flush()` để có `id`, và `flush()` chính là
       lúc `INSERT` chạm CSDL. Nên `try` phải bọc **lời gọi `tao_run`**, không
       chỉ bọc `commit()`. `test_951` ghim đúng chỗ này.
    """
    run = WorkflowRun(
        workflow_id=workflow_id, version_id=version_id, owner_id=owner_id,
        trigger_kind=trigger_kind, idempotency_key=idempotency_key or "",
        estimated_max=max(0, int(estimated_max or 0)))
    db.add(run)
    db.flush()
    return run


def ghi_chuyen(db, run_id: str, node_id: str, *, execution_status: str,
               description: str, run_status: str = "",
               attempt_number: int = 1, is_valid: bool = True,
               error: str = "", job_id: str = "",
               output_ref: Optional[dict] = None,
               cost_credit: int = 0) -> NodeRunSnapshot:
    """Ghi MỘT lần chuyển trạng thái của MỘT node. Không sửa gì đã ghi.

    Đây là toàn bộ đường ghi của mô hình C, và nó có đúng hai thao tác:

      1. `INSERT` một hàng `node_run_snapshot`  — luôn luôn, kể cả khi bị từ chối;
      2. `UPDATE` con trỏ `node_run`            — **chỉ khi** `is_valid`.

    ⇒ `M1` đạt được ở đây: chi phí là `O(node đổi)`, không phụ thuộc số node
      của đồ thị. Một run 31 node tiến một node vẫn ghi đúng một hàng.

    ## ⭐ Vì sao lần chuyển BỊ TỪ CHỐI vẫn được ghi

    `is_valid=False` là hàng ghi lại một lần chuyển **không được chấp nhận** —
    worker chậm chân quay lại tiến một node đã xong, hai worker cùng giành. Ghi
    nó tốn một hàng; **không** ghi nó tốn một buổi điều tra không kết luận
    được, vì thứ duy nhất còn lại sẽ là "trạng thái cuối", thứ không nói ai đã
    thử gì (`G19`).

    ⛔ Nhưng ghi lại **không phải** chấp nhận: con trỏ đứng yên.
    """
    truoc = db.get(NodeRun, (run_id, node_id))
    snapshot = NodeRunSnapshot(
        run_id=run_id, node_id=node_id,
        previous_snapshot_id=(truoc.latest_snapshot_id if truoc else ""),
        execution_status=execution_status, run_status=run_status,
        attempt_number=max(1, int(attempt_number or 1)),
        is_valid=bool(is_valid), error=error, description=description,
        job_id=job_id, output_ref=dict(output_ref or {}),
        cost_credit=int(cost_credit or 0))
    db.add(snapshot)
    db.flush()

    if not is_valid:
        return snapshot

    if truoc is None:
        db.add(NodeRun(run_id=run_id, node_id=node_id,
                       latest_snapshot_id=snapshot.id))
    else:
        truoc.latest_snapshot_id = snapshot.id
    db.flush()
    return snapshot


def anh_chup_hien_tai(db, run_id: str, node_id: str
                      ) -> Optional[NodeRunSnapshot]:
    """Trạng thái ĐANG CÓ của một node — một lần đọc con trỏ, không quét lịch sử."""
    con_tro = db.get(NodeRun, (run_id, node_id))
    if con_tro is None:
        return None
    return db.get(NodeRunSnapshot, con_tro.latest_snapshot_id)
