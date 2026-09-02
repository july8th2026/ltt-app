"""
su_kien.py — sự kiện canonical của ChatLTT và cách chúng ghi vào `chatltt_execution`. (H43 Phase 07)

Một hình dạng sự kiện cho **cả ba** nguồn (facade text stream, job ảnh, job
tiếng) và cho cả hai người tiêu thụ (SSE tới trình duyệt, CSDL để reload):

    response.started / response.delta / reasoning.delta / tool_call.delta
    response.completed / response.failed / response.cancelled
    execution.started / execution.progress / execution.completed / execution.failed
    artifact.ready
    usage.updated / billing.updated

`ap_dung(ex, sk)` là hàm THUẦN trên một `ChatlttExecution` — không commit. Route
quyết định nhịp commit qua `nen_ghi()`: mỗi ~1 s hoặc mỗi 200 ký tự, và luôn ở
sự kiện kết thúc. Đây là D6 của kế hoạch: sự thật ở CSDL, không ở RAM trình duyệt.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from apps.chatltt.tables import ChatlttExecution, ChatlttMessage, sinh_id

LOAI = (
    "response.started", "response.delta", "reasoning.delta", "tool_call.delta",
    "response.completed", "response.failed", "response.cancelled",
    "execution.started", "execution.progress", "execution.completed", "execution.failed",
    "artifact.ready", "usage.updated", "billing.updated",
)
KET_THUC = frozenset({"response.completed", "response.failed", "response.cancelled",
                      "execution.completed", "execution.failed"})

#: Nhịp ghi partial: giây / ký tự.
NHIP_GIAY = 1.0
NHIP_KY_TU = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def mo_execution(db, *, message: ChatlttMessage, tool_name: str, mode: str) -> ChatlttExecution:
    """Tạo một lượt thi hành gắn vào message assistant và đánh dấu message `streaming`/`queued`."""
    ex = ChatlttExecution(message_id=message.id, conversation_id=message.conversation_id,
                          user_id=message.user_id, tool_name=str(tool_name),
                          mode=str(mode), status="streaming" if mode == "stream" else "queued")
    db.add(ex)
    db.flush()
    message.execution_id = ex.id
    message.status = ex.status
    return ex


def ap_dung(ex: ChatlttExecution, sk: dict, *, message: Optional[ChatlttMessage] = None) -> bool:
    """Áp một sự kiện lên `ex` (và `message` nếu truyền). Trả True nếu là sự kiện kết thúc.

    Ném `ValueError` với loại lạ — fail-closed: một nguồn phát sự kiện ngoài
    hợp đồng là lỗi lập trình, không phải thứ để bỏ qua im lặng.
    """
    loai = str(sk.get("type") or "")
    if loai not in LOAI:
        raise ValueError(f"su kien la: {loai!r}")
    ex.seq = int(ex.seq or 0) + 1
    if loai == "response.started":
        ex.request_id = str(sk.get("request_id") or "")[:36]
        ex.credit_giu = int(sk.get("credit_giu") or 0)
        ex.status = "streaming"
    elif loai == "response.delta":
        ex.partial_text = (ex.partial_text or "") + str(sk.get("text") or "")
    elif loai == "reasoning.delta":
        ex.reasoning_text = (ex.reasoning_text or "") + str(sk.get("text") or "")
    elif loai == "tool_call.delta":
        pass                                # V1 không có tool: ghi seq, không ghi nội dung
    elif loai == "usage.updated":
        ex.usage = {k: sk.get(k) for k in ("token_vao", "token_ra", "token_cache", "do_duoc")}
    elif loai == "billing.updated":
        ex.credit_giu = int(sk.get("credit_giu") or ex.credit_giu or 0)
        ex.credit_thu = int(sk.get("credit_thu") or 0)
        ex.credit_hoan = int(sk.get("credit_hoan") or 0)
    elif loai == "execution.started":
        ex.job_id = str(sk.get("job_id") or "")[:36] or ex.job_id
        ex.status = "queued"
    elif loai == "execution.progress":
        ex.usage = dict(ex.usage or {}, progress=sk.get("progress"))
    elif loai == "artifact.ready":
        pass                                # khối artifact được thêm vào message bởi route
    elif loai == "response.completed":
        ex.status = "done"
        ex.finish_reason = str(sk.get("finish_reason") or "")[:32]
        ex.finished_at = _now()
    elif loai == "execution.completed":
        ex.status = "done"
        ex.finished_at = _now()
    elif loai in ("response.failed", "execution.failed"):
        ex.status = "failed"
        ex.error_code = str(sk.get("code") or "")[:40]
        ex.error_text = str(sk.get("ly_do") or "")[:500]
        ex.finished_at = _now()
    elif loai == "response.cancelled":
        ex.status = "cancelled"
        ex.finished_at = _now()
    ex.updated_at = _now()
    if message is not None:
        message.status = ex.status if ex.status in ("streaming", "queued", "done",
                                                    "failed", "cancelled") else message.status
        message.updated_at = ex.updated_at
    return loai in KET_THUC


def dong_bo_khoi_text(message: ChatlttMessage, ex: ChatlttExecution) -> None:
    """Đưa `partial_text`/`reasoning_text` của execution vào `blocks` của message.

    Gọi ở sự kiện kết thúc (và khi huỷ) để message tự đứng được mà không cần
    execution; giữa chừng thì `su_that()` đã trả `execution.partial_text`.
    """
    khoi = [k for k in (message.blocks or []) if k.get("type") not in ("text", "reasoning")]
    if ex.reasoning_text:
        khoi.insert(0, {"type": "reasoning", "text": ex.reasoning_text})
    if ex.partial_text or not khoi:
        khoi.append({"type": "text", "text": ex.partial_text or ""})
    if ex.status == "cancelled":
        khoi.append({"type": "status", "code": "cancelled"})
    elif ex.status == "failed":
        khoi.append({"type": "error", "code": ex.error_code, "text": ex.error_text})
    elif ex.finish_reason == "length":
        khoi.append({"type": "status", "code": "length"})
    message.blocks = khoi
    message.updated_at = _now()


def nen_ghi(*, luc_ghi_cuoi: float, bay_gio: float, ky_tu_moi: int, ket_thuc: bool) -> bool:
    """Chính sách nhịp ghi partial xuống CSDL."""
    if ket_thuc:
        return True
    return (bay_gio - luc_ghi_cuoi) >= NHIP_GIAY or ky_tu_moi >= NHIP_KY_TU


def snapshot(ex: ChatlttExecution) -> dict:
    """Ảnh chụp để client nối lại: phần đã có + seq cuối (tương đương `resumeState`)."""
    return {"execution_id": ex.id, "status": ex.status, "seq": int(ex.seq or 0),
            "partial_text": ex.partial_text or "", "reasoning_text": ex.reasoning_text or "",
            "finish_reason": ex.finish_reason or "", "usage": dict(ex.usage or {}),
            "credit": {"giu": ex.credit_giu, "thu": ex.credit_thu, "hoan": ex.credit_hoan},
            "error_code": ex.error_code or "", "job_id": ex.job_id}


__all__ = ["LOAI", "KET_THUC", "mo_execution", "ap_dung", "dong_bo_khoi_text", "nen_ghi",
           "snapshot", "sinh_id"]
