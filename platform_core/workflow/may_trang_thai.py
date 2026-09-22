"""Máy trạng thái của run và node — và việc GHI LẠI lần chuyển bị từ chối.

Nguồn thiết kế: `docs/architecture/workflow_v2_audit/23_24 §5`.

⭐ Cưỡng chế bằng **bảng chuyển**, không bằng một chuỗi `if` rải trong
   scheduler. Bảng đọc được, so sánh được với tài liệu, và thêm một trạng thái
   là sửa **một** chỗ.
"""
from __future__ import annotations

from datetime import datetime, timezone

from platform_core.models import NodeRun, NodeRunSnapshot, WorkflowRun
from platform_core.workflow import thi_hanh


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Run ───────────────────────────────────────────────────────────────────────

#: ⭐ `SYSTEM_FAILURE` TÁCH khỏi `FAILED` — hai chuyện khác nhau về **hoàn tiền**
#: và **cảnh báo vận hành**. LTT hôm nay gộp hết vào `AGENT_ERROR` (`G21`), nên
#: không phân biệt được "khách làm sai" với "ta hỏng".
RUN_KET_THUC = frozenset({
    "SUCCEEDED", "FAILED", "SYSTEM_FAILURE", "CANCELLED", "TIMED_OUT",
})

#: Lỗi **của ta** — không được bắt khách trả tiền cho nó.
RUN_LOI_CUA_TA = frozenset({"SYSTEM_FAILURE"})

RUN_CHUYEN: dict[str, frozenset[str]] = {
    # Validate chạy lúc PUBLISH (spec §4.2) — tạo run chỉ kiểm tiền + quyền.
    "CREATED": frozenset({"QUEUED", "FAILED", "CANCELLED"}),
    "QUEUED": frozenset({"RUNNING", "CANCELLED", "TIMED_OUT",
                         "SYSTEM_FAILURE"}),
    # `RUNNING ⇄ WAITING` qua lại được: một run có thể chờ rồi chạy tiếp nhiều lần.
    "RUNNING": frozenset({"WAITING", "SUCCEEDED", "FAILED", "SYSTEM_FAILURE",
                          "CANCELLED", "TIMED_OUT"}),
    "WAITING": frozenset({"RUNNING", "SUCCEEDED", "FAILED", "SYSTEM_FAILURE",
                          "CANCELLED", "TIMED_OUT"}),
}


# ── Node ──────────────────────────────────────────────────────────────────────

#: ⭐ `ABANDONED` — provider **có thể đã nhận**. Kế thừa `provider_state =
#: ambiguous` đã đúng của LTT. `AmbiguousProviderError` xảy ra **10 lần / 28
#: ngày** (`01 §A.4`) ⇒ đây là trạng thái có thật, không phải phòng xa.
NODE_KET_THUC = frozenset({
    "SUCCEEDED", "FAILED", "SKIPPED", "ABANDONED", "CANCELLED",
})

#: Node đang chiếm một suất song song của run (spec §5.9).
NODE_DANG_CHAY = frozenset({"QUEUED", "RUNNING", "WAITING"})

#: ⭐ `RESUMING` KHÔNG phải trạng thái lưu (spec §5.3): resume là MỘT transaction
#:    (nhặt wakeup → đọc tín hiệu → chuyển), không có khoảng nào quan sát được.
#: ⭐ `QUEUED → SUCCEEDED/FAILED/…` hợp lệ: job có thể xong trước khi động cơ kịp
#:    thấy nó chạy — động cơ không có hook lúc job bắt đầu (spec §5.8).
NODE_CHUYEN: dict[str, frozenset[str]] = {
    "PENDING": frozenset({"READY", "SKIPPED", "CANCELLED"}),
    "READY": frozenset({"QUEUED", "RUNNING", "WAITING", "SKIPPED",
                        "CANCELLED"}),
    "QUEUED": frozenset({"RUNNING", "SUCCEEDED", "FAILED", "ABANDONED",
                         "RETRY_SCHEDULED", "CANCELLED"}),
    "RUNNING": frozenset({"SUCCEEDED", "FAILED", "WAITING", "RETRY_SCHEDULED",
                          "ABANDONED", "CANCELLED"}),
    "WAITING": frozenset({"RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"}),
    "RETRY_SCHEDULED": frozenset({"READY", "CANCELLED"}),
}

_NODE_BAT_DAU = "PENDING"


def trang_thai_node(db, run_id: str, node_id: str) -> str:
    """Trạng thái ĐANG CÓ của một node. Chưa có ảnh chụp nào ⇒ `PENDING`."""
    anh = thi_hanh.anh_chup_hien_tai(db, run_id, node_id)
    return anh.execution_status if anh is not None else _NODE_BAT_DAU


def chuyen_node(db, run_id: str, node_id: str, *, sang: str, mo_ta: str,
                **thong_tin) -> bool:
    """Chuyển một node sang trạng thái mới. Trả `False` nếu bị TỪ CHỐI.

    ⭐ **Lần chuyển bị từ chối vẫn ghi một ảnh chụp** (`is_valid=False`), đúng
       `23_24 §5`. Đây là thứ khiến một tranh chấp **điều tra được**: không ghi
       thì thứ duy nhất còn lại là trạng thái cuối, và trạng thái cuối không nói
       **ai đã thử gì**.

    ⛔ Nhưng ghi lại KHÔNG phải chấp nhận — con trỏ `node_run` đứng yên
       (`thi_hanh.ghi_chuyen` lo phần đó).
    """
    hien = trang_thai_node(db, run_id, node_id)
    duoc = NODE_CHUYEN.get(hien, frozenset())
    hop_le = sang in duoc

    thi_hanh.ghi_chuyen(
        db, run_id, node_id, execution_status=(sang if hop_le else hien),
        description=mo_ta, is_valid=hop_le,
        error=("" if hop_le else
               f"chuyen bi tu choi: {hien} -> {sang} khong nam trong bang"),
        **thong_tin)
    return hop_le


# ── Run ───────────────────────────────────────────────────────────────────────

def chuyen_run(db, run_id: str, *, sang: str, ly_do: str = "") -> bool:
    """Chuyển một run. Trả `False` nếu bị TỪ CHỐI.

    🔴 Khi run vào một trạng thái **kết thúc**, hệ con `finally` chạy **ngay
       trong lời gọi này** — tức cùng transaction với lần chuyển. Đó là toàn bộ
       nội dung của `M10`.

       Hôm nay việc kết sổ nằm rải: `_terminal_status` ở một chỗ, `budget.settle`
       ở chỗ khác, và giữa hai chỗ là một cửa sổ mà một lần restart (13,6
       lần/ngày) làm khoản giữ chỗ nằm lại — **145 lần / 28 ngày**.
    """
    run = db.get(WorkflowRun, run_id)
    if run is None:
        return False
    hien = run.status or "CREATED"
    if hien in RUN_KET_THUC or sang not in RUN_CHUYEN.get(hien, frozenset()):
        return False

    run.status = sang
    if sang == "RUNNING" and run.started_at is None:
        run.started_at = _bay_gio()
    if sang in RUN_KET_THUC:
        run.finished_at = _bay_gio()
    db.flush()

    if sang in RUN_KET_THUC:
        # Import trễ: `ket_so` đọc bảng chuyển ở đây, nên nạp sớm thành vòng.
        from platform_core.workflow import ket_so
        ket_so.ket_so(db, run_id, ly_do=ly_do or f"run -> {sang}")
    return True


def tong_chi_phi_hop_le(db, run_id: str) -> int:
    """Tổng `cost_credit` của các ảnh chụp **HỢP LỆ**.

    ⛔ Hàng `is_valid=False` là một lần chuyển **không xảy ra**. Tính tiền cho
       nó là thu tiền một việc chưa từng chạy — và bảng chỉ-thêm khiến sai lầm
       ấy dễ mắc, vì hàng vẫn nằm đó.
    """
    return sum(
        int(s.cost_credit or 0)
        for s in db.query(NodeRunSnapshot).filter_by(run_id=run_id).all()
        if s.is_valid)


__all__ = ["RUN_CHUYEN", "RUN_KET_THUC", "RUN_LOI_CUA_TA", "NODE_CHUYEN",
           "NODE_KET_THUC", "NODE_DANG_CHAY", "chuyen_node", "chuyen_run",
           "trang_thai_node", "tong_chi_phi_hop_le", "NodeRun"]
