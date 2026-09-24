"""Bộ nhớ bền của piece connector — `ctx.store` phía Python (spec §11.4).

Runner giữ store **trong bộ nhớ** suốt một lệnh và trả lại một danh sách
`store_ops`; tệp này là nơi duy nhất áp chúng xuống CSDL.

⭐ **Vì sao không để runner tự ghi CSDL.** Mã piece là mã của bên thứ ba và nó
   chạy trong AppContainer **không có mạng** — kể cả tới PostgreSQL. Cho nó một
   đường ghi CSDL là mở đúng cánh cửa mà cả phase này đóng lại.

⛔ **`pham_vi` phải là một ĐƯỜNG, không phải một id trần.** `trigger:<id>` /
   `run:<id>`. Phase 4 đã trả giá ba lần cho đúng lỗi này ở ba bảng khác nhau
   (`wakeup`, `node_run`, `dedupe_key` khoá theo `node_id` trần): khoá thiếu
   ngữ cảnh thì hai chủ thể khác nhau đụng nhau, im lặng.
"""
from __future__ import annotations

from sqlalchemy import delete, select

from platform_core.models import ConnectorStore

#: Trần số khoá một phạm vi được giữ. ⭐ Có trần vì `ctx.store.put` là một
#: đường ghi do **bên thứ ba** điều khiển: một piece lỗi ghi một khoá mới mỗi
#: lần poll sẽ làm bảng này phình vô hạn, và không ai nhìn thấy cho tới khi
#: đĩa đầy. Chạm trần ⇒ ném, ⛔ không âm thầm bỏ ghi.
TRAN_KHOA = 200

#: Trần kích thước một giá trị (byte của JSON). Con trỏ poll là một danh sách
#: id, không phải một kho dữ liệu.
TRAN_GIA_TRI_BYTE = 256 * 1024


class LoiStore(ValueError):
    """Piece vượt trần store. Lỗi có mã, ⛔ không phải một lần ghi bị nuốt."""


def pham_vi_trigger(trigger_id: str) -> str:
    return f"trigger:{trigger_id}"


def pham_vi_run(run_id: str) -> str:
    return f"run:{run_id}"


def doc(db, *, owner_id: str, pham_vi: str) -> dict:
    """`{khoa: gia_tri}` của một phạm vi — thứ đi vào `vao.json`."""
    hang = db.execute(
        select(ConnectorStore.khoa, ConnectorStore.gia_tri).where(
            ConnectorStore.owner_id == owner_id,
            ConnectorStore.pham_vi == pham_vi)).all()
    return {k: (v or {}).get("v") if isinstance(v, dict) and "v" in v else v
            for k, v in hang}


def ap(db, *, owner_id: str, pham_vi: str, ops) -> int:
    """Áp `store_ops` do runner trả về. Trả số thao tác đã áp.

    ⭐ Gói giá trị trong `{"v": ...}`: cột là JSON, và một piece trả về một
       **danh sách** hay một **số** thì `JSON` của SQLAlchemy vẫn lưu được
       nhưng `default=dict` của cột nói rằng hình dạng mong đợi là dict. Bọc
       lại cho **một** hình dạng duy nhất trong bảng, thay vì bốn hình dạng
       tuỳ piece.
    """
    so = 0
    for op in ops or []:
        cach = str((op or {}).get("op") or "")
        khoa = str((op or {}).get("key") or "")[:200]
        if not khoa:
            continue
        if cach == "delete":
            db.execute(delete(ConnectorStore).where(
                ConnectorStore.owner_id == owner_id,
                ConnectorStore.pham_vi == pham_vi,
                ConnectorStore.khoa == khoa))
            so += 1
            continue
        if cach != "put":
            raise LoiStore(f"store op khong biet: {cach!r}")
        import json as _json
        gia = op.get("value")
        if len(_json.dumps(gia, default=str)) > TRAN_GIA_TRI_BYTE:
            raise LoiStore(
                f"gia tri store vuot tran {TRAN_GIA_TRI_BYTE} byte (khoa {khoa!r})")
        hang = db.execute(select(ConnectorStore).where(
            ConnectorStore.owner_id == owner_id,
            ConnectorStore.pham_vi == pham_vi,
            ConnectorStore.khoa == khoa)).scalars().first()
        if hang is None:
            dem = db.execute(select(ConnectorStore.id).where(
                ConnectorStore.owner_id == owner_id,
                ConnectorStore.pham_vi == pham_vi)).all()
            if len(dem) >= TRAN_KHOA:
                raise LoiStore(
                    f"pham vi {pham_vi!r} da co {len(dem)} khoa (tran {TRAN_KHOA})")
            db.add(ConnectorStore(owner_id=owner_id, pham_vi=pham_vi,
                                  khoa=khoa, gia_tri={"v": gia}))
        else:
            hang.gia_tri = {"v": gia}
        so += 1
    db.flush()
    return so


def xoa_pham_vi(db, *, owner_id: str, pham_vi: str) -> int:
    """Xoá cả phạm vi. Gọi khi trigger bị xoá / run kết sổ.

    🔴 Xoá con trỏ poll **không phải** dọn rác: lần poll kế tiếp sẽ coi MỌI
       bản ghi là mới ⇒ tạo lại run cho cả lịch sử ⇒ **tiêu credit thật**.
       Nên chỉ gọi khi chủ thể của phạm vi thật sự biến mất.
    """
    kq = db.execute(delete(ConnectorStore).where(
        ConnectorStore.owner_id == owner_id,
        ConnectorStore.pham_vi == pham_vi))
    db.flush()
    return int(kq.rowcount or 0)


__all__ = ["LoiStore", "TRAN_GIA_TRI_BYTE", "TRAN_KHOA", "ap", "doc",
           "pham_vi_run", "pham_vi_trigger", "xoa_pham_vi"]
