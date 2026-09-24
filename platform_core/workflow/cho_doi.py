"""Waitpoint: node chờ cái gì, và khi nào thì hết chờ.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §4.3`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, tuple_

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


def theo_khoa(db, owner_id: str, khoa: str) -> Optional[Waitpoint]:
    """Điểm chờ theo khoá khử trùng, hoặc `None`.

    ⚠️ Tra theo ĐÚNG cặp cột của chỉ mục `ux_waitpoint_idem`
       (`owner_id, idempotency_key`) — không tra theo `idempotency_key` một
       mình. Cùng bài học với route API `/runs` (spec §8.1): tra lệch chỉ mục
       thì hai người dùng khác nhau va vào nhau, và câu trả lời sai là một
       điểm chờ **của người khác**.
    """
    if not khoa:
        return None
    return db.execute(
        select(Waitpoint).where(Waitpoint.owner_id == owner_id,
                                Waitpoint.idempotency_key == khoa)
    ).scalars().first()


def chan_node(db, *, run_id: str, node_id: str, waitpoint_id: str,
              vong=()) -> None:
    """Gắn một node vào một waitpoint. Luỹ đẳng — gọi hai lần vẫn một hàng.

    ⚠️ `node_id` lưu ở đây là ĐƯỜNG THI HÀNH (`thi_hanh.khoa_node`), cùng
       khoá với `node_run`: hai vòng `foreach` chờ hai waitpoint khác nhau,
       và một khoá chung sẽ làm vòng 2 "đã bị chặn" ngay khi vòng 1 bị chặn.
    """
    from platform_core.workflow.thi_hanh import khoa_node

    node_id = khoa_node(node_id, vong)
    khoa = (run_id, node_id, waitpoint_id)
    if db.get(NodeRunWaitpoint, khoa) is not None:
        return
    db.add(NodeRunWaitpoint(run_id=run_id, node_id=node_id,
                            waitpoint_id=waitpoint_id))
    db.flush()


def het_han_den_han(db, *, moc: Optional[datetime] = None,
                    con_tro: Optional[tuple] = None,
                    gioi_han: int = 200) -> list[Waitpoint]:
    """Điểm chờ ĐÃ QUÁ HẠN, một TRANG, đi bằng **keyset cursor**.

    🔴 VÌ SAO KEYSET CHỨ KHÔNG `OFFSET`

    `OFFSET k` vẫn bắt CSDL đi qua k hàng đầu rồi vứt đi, nên một bộ quét chạy
    mỗi 5 giây trên một bảng lớn dần sẽ chậm dần **theo số hàng nó đã bỏ qua** —
    đúng hình dạng `O(N²)` mà làn p3b vừa đo được ở `foreach`
    (`docs/superpowers/reports/p3b-do-tai/report.md`: 127 000 hàng đọc cho
    N=1000). Keyset đọc đúng `gioi_han` hàng cho mỗi trang, mãi mãi.

    ⚠️ Con trỏ là **một CẶP** `(het_han_luc, id)`, không phải `het_han_luc` một
       mình: hai điểm chờ hết hạn cùng một micro-giây là chuyện thường (một run
       mở nhiều điểm chờ trong cùng transaction), và một con trỏ chỉ có thời
       gian sẽ **bỏ sót** hàng thứ hai hoặc **lặp** hàng thứ nhất mãi mãi.

    ⭐ `ix_waitpoint_het_han` là `(het_han_luc, id)` theo đúng thứ tự này —
       thiếu cột thứ hai thì điều kiện cặp vẫn chạy nhưng phải sắp lại.
    """
    luc = moc or datetime.now(timezone.utc).replace(tzinfo=None)
    dk = [Waitpoint.status == "PENDING",
          Waitpoint.het_han_luc.is_not(None),
          Waitpoint.het_han_luc <= luc]
    if con_tro is not None:
        dk.append(tuple_(Waitpoint.het_han_luc, Waitpoint.id)
                  > tuple_(con_tro[0], con_tro[1]))
    return list(db.execute(
        select(Waitpoint).where(*dk)
        .order_by(Waitpoint.het_han_luc, Waitpoint.id)
        .limit(max(1, int(gioi_han)))).scalars())


def node_dang_bi_chan(db, waitpoint_id: str) -> list[str]:
    return list(db.execute(
        select(NodeRunWaitpoint.node_id)
        .where(NodeRunWaitpoint.waitpoint_id == waitpoint_id)
        .order_by(NodeRunWaitpoint.node_id)).scalars())


def waitpoint_cua_node(db, run_id: str, node_id: str, vong=()) -> list[str]:
    from platform_core.workflow.thi_hanh import khoa_node

    node_id = khoa_node(node_id, vong)
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
