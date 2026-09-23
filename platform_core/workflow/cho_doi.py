"""Waitpoint: node chờ cái gì, và khi nào thì hết chờ.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.3`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from platform_core.models import (NodeRunWaitpoint, Waitpoint, WaitpointSignal)

# Tín hiệu nào KHÔNG còn phải chờ nữa. `NOT_DISPATCHED` nằm ở đây có chủ ý:
# nhánh ấy sẽ không bao giờ gửi gì, nên coi nó là "đang chờ" là treo vĩnh viễn.
_DA_XONG = frozenset({"SUCCEEDED", "FAILED", "CANCELLED", "NOT_DISPATCHED"})
_THANH_CONG = "SUCCEEDED"
_THAT_BAI = frozenset({"FAILED", "CANCELLED"})


def tao_waitpoint(db, *, run_id: str, owner_id: str, kind: str,
                  required_successes: int = 0,
                  release_on_first_failure: bool = False,
                  due_at: Optional[datetime] = None,
                  idempotency_key: str = "") -> Waitpoint:
    """Mở một điểm chờ.

    `required_successes=0` nghĩa là **ALL** — và ALL chỉ kết luận được sau khi
    `niem_phong()`. Xem `da_mo()`.
    """
    wp = Waitpoint(
        run_id=run_id, owner_id=owner_id, kind=kind,
        required_successes=max(0, int(required_successes or 0)),
        release_on_first_failure=bool(release_on_first_failure),
        due_at=due_at, idempotency_key=idempotency_key or "")
    db.add(wp)
    db.flush()
    return wp


def chan_node(db, *, run_id: str, node_id: str, waitpoint_id: str) -> None:
    """Gắn một node vào một waitpoint. Luỹ đẳng — gọi hai lần vẫn một hàng."""
    khoa = (run_id, node_id, waitpoint_id)
    if db.get(NodeRunWaitpoint, khoa) is not None:
        return
    db.add(NodeRunWaitpoint(run_id=run_id, node_id=node_id,
                            waitpoint_id=waitpoint_id))
    db.flush()


def node_dang_bi_chan(db, waitpoint_id: str) -> list[str]:
    return list(db.execute(
        select(NodeRunWaitpoint.node_id)
        .where(NodeRunWaitpoint.waitpoint_id == waitpoint_id)
        .order_by(NodeRunWaitpoint.node_id)).scalars())


def waitpoint_cua_node(db, run_id: str, node_id: str) -> list[str]:
    return list(db.execute(
        select(NodeRunWaitpoint.waitpoint_id)
        .where(NodeRunWaitpoint.run_id == run_id,
               NodeRunWaitpoint.node_id == node_id)).scalars())


def ghi_tin_hieu(db, waitpoint_id: str, *, seq: int, status: str,
                 ref_id: str = "",
                 result_ref: Optional[dict] = None) -> WaitpointSignal:
    """Ghi một tín hiệu của MỘT nhánh.

    ⚠️ Không có `SELECT` chống trùng: `UNIQUE(waitpoint_id, seq)` cưỡng chế.
       Hai lần gửi cùng một nhánh không được cộng đôi vào số thành công, và một
       ràng buộc CSDL là chỗ duy nhất đảm bảo điều đó dưới chạy song song.
    """
    sig = WaitpointSignal(
        waitpoint_id=waitpoint_id, seq=int(seq), status=status,
        ref_id=ref_id, result_ref=dict(result_ref or {}))
    db.add(sig)
    db.flush()
    return sig


def niem_phong(db, waitpoint_id: str) -> None:
    """Khai "sẽ không còn tín hiệu nào nữa" — điều kiện để `ALL` có nghĩa."""
    wp = db.get(Waitpoint, waitpoint_id)
    if wp is not None:
        wp.sealed = True
        db.flush()


def da_mo(db, waitpoint_id: str) -> bool:
    """Waitpoint này đã hết chờ chưa?

    Ba luật, theo đúng thứ tự — và thứ tự là một phần của ngữ nghĩa:

      1. `release_on_first_failure` → hỏng một nhánh là thả ngay. Đứng trước vì
         nó là quyết định "đừng bắt chờ nữa", không phụ thuộc đếm đủ hay chưa.
      2. `required_successes > 0` → N-of-M: đếm `SUCCEEDED`, đủ N thì mở.
      3. `required_successes == 0` (**ALL**) → nếu `so_nguon > 0` (Join, mẫu số
         biết lúc dựng đồ thị) thì đếm số tín hiệu đã xong so với `so_nguon`.
         Nếu không (barrier động — ForEach) thì chỉ kết luận được khi `sealed`.

    ⛔ `so_nguon == 0` và chưa `sealed` KHÔNG có nghĩa "chưa đủ" — nó có nghĩa
       **"chưa biết"**. Hai thứ ấy khác nhau, và gộp chúng lại chính là
       khiếm khuyết mà `sealed`/`so_nguon` sinh ra để đóng: không có mẫu số
       thì "đủ tất cả" là một câu hỏi không trả lời được.
    """
    wp = db.get(Waitpoint, waitpoint_id)
    if wp is None:
        return False
    tin_hieu = list(db.execute(
        select(WaitpointSignal)
        .where(WaitpointSignal.waitpoint_id == waitpoint_id)).scalars())

    if wp.release_on_first_failure and any(
            s.status in _THAT_BAI for s in tin_hieu):
        return True

    if wp.required_successes > 0:
        thanh_cong = sum(1 for s in tin_hieu if s.status == _THANH_CONG)
        return thanh_cong >= wp.required_successes

    xong = [s for s in tin_hieu if s.status in _DA_XONG]
    if wp.so_nguon > 0:
        return len(xong) >= wp.so_nguon
    # Barrier động (ForEach): mẫu số chỉ biết khi đã niêm phong.
    return bool(wp.sealed) and len(xong) == len(tin_hieu)
