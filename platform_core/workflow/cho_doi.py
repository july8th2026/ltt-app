"""Waitpoint: node chờ cái gì, và khi nào thì hết chờ.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.3`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select

from platform_core.models import (NodeRunWaitpoint, Waitpoint,
                                  WaitpointSignal)

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


def dem_tin_hieu(db, waitpoint_id: str) -> dict[str, int]:
    """`{status: số lượng}` bằng **MỘT** câu `GROUP BY`.

    ⭐ 000015: *"Counts are taken once, from a single `GROUP BY status`, and
       handed to a pure predicate… one `GROUP BY status` replaces up to three
       round-trips and the policy matrix is unit-testable without a database."*

    ⛔ Bản cũ nạp **mọi hàng** tín hiệu vào bộ nhớ để trả về một `bool`. Với
       một barrier 10 000 nhánh (con số Activepieces khai là có thật) đó là
       10 000 đối tượng ORM cho một câu hỏi có/không.
    """
    return {str(tt): int(n) for tt, n in db.execute(
        select(WaitpointSignal.status, func.count())
        .where(WaitpointSignal.waitpoint_id == waitpoint_id)
        .group_by(WaitpointSignal.status)).all()}


def da_mo(db, waitpoint_id: str) -> bool:
    """Waitpoint này đã hết chờ chưa?

    ⭐ Luật nằm ở `join.nen_mo_barrier` — hàm THUẦN, PORT từ
       `shouldReleaseBarrier` của Activepieces. Hàm này chỉ làm một việc:
       **quy trạng thái CSDL của ta về `dem[PENDING]` mà hàm kia cần**.

    Ta không tạo sẵn một hàng `PENDING` cho mỗi nhánh như họ, nên "còn bao
    nhiêu chưa về" được trả lời bằng hai đường:

      - `so_nguon > 0` (Join — mẫu số **biết lúc dựng đồ thị**):
        `PENDING = so_nguon − số tín hiệu đã xong`.
      - `so_nguon == 0` (barrier ĐỘNG — ForEach sinh nhánh lúc chạy): mẫu số
        chỉ biết khi đã `sealed`. Chưa niêm phong ⇒ coi như còn một nhánh chưa
        về, và `nen_mo_barrier` tự trả `False` ở luật sàn.

    ⛔ `so_nguon == 0` và chưa `sealed` KHÔNG có nghĩa "chưa đủ" — nó có nghĩa
       **"chưa biết"**. Hai thứ ấy khác nhau, và gộp chúng lại chính là khiếm
       khuyết mà `sealed`/`so_nguon` sinh ra để đóng.
    """
    # ⚠️ Import CỤC BỘ: `join` import `cho_doi` (nó dựng waitpoint), nên một
    #    import ở đầu tệp là một vòng — và vòng import là cách im lặng nhất để
    #    một trong hai mô-đun nạp dở.
    from platform_core.workflow import join

    wp = db.get(Waitpoint, waitpoint_id)
    if wp is None:
        return False
    dem = dem_tin_hieu(db, waitpoint_id)
    xong = sum(n for tt, n in dem.items() if tt in _DA_XONG)
    if wp.so_nguon > 0:
        con_cho = max(0, int(wp.so_nguon) - xong)
        sealed = True          # mẫu số đã biết ⇒ luật sàn kết luận được
    else:
        con_cho = 0 if wp.sealed else 1
        sealed = bool(wp.sealed)
    dem[join.TIN_HIEU_CHO] = con_cho
    return join.nen_mo_barrier(
        sealed=sealed, dem=dem,
        can_thanh_cong=int(wp.required_successes or 0),
        mo_khi_hong_dau_tien=bool(wp.release_on_first_failure))
