"""Bốn hệ con còn lại của scheduler — `enqueue` · `dequeue` · `attempt` · `ttl`.

`23_24 §6` khai **tám** hệ con; bốn cái kia đã có (`snapshot` = `thi_hanh`,
`waitpoint` = `cho_doi`, `finally` = `ket_so`, kho dữ liệu `foreach`).

🔴 **CHẠY SAU CỜ** (`27_29 §28` đặt tên Đợt 3 đúng như vậy). Cờ không phải một
   tuỳ chọn tiện nghi: nó là điều kiện để thứ này tồn tại **cạnh** đường cũ mà
   không ai phải chọn giữa hai đường trong lúc chưa đo được cái nào tốt hơn.

⛔ **`G23` — KHÔNG I/O ngoài trong transaction.** Đây là lỗi LTT đang mắc mà
   chính `job_runner` đã cấm cho handler: `verifier.verify()` gọi model **bên
   trong** transaction, nên một lần model treo là một transaction treo, và một
   transaction treo **giữ khoá hàng**. Ở quy mô một suất `llm_remote` thì đó là
   cả hàng đợi đứng.

   ⇒ Mô-đun này **không import gì gọi ra ngoài**, và `test_962` cấm điều đó ở
     tầng **AST**: cấm lúc import bắt được **mọi** đường, kể cả đường chưa ai
     viết; một phép kiểm lúc chạy chỉ bắt được đường mà bài kiểm đi qua.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from platform_core.models import (Artifact, NodeRunSnapshot, Waitpoint,
                                  WorkflowRun)
from platform_core.workflow import cho_doi, may_trang_thai

#: Cờ bật scheduler mới. **Mặc định TẮT.**
BIEN_CO = "LTT_WORKFLOW_V2"

#: Chỉ những giá trị này là BẬT. Mọi thứ khác — kể cả rác — là TẮT.
#: Fail-closed: một giá trị không hiểu được nghĩa là người đặt nó **không chắc**
#: họ đang bật cái gì, và một scheduler bật vì nhầm là một đường chạy đổi mà
#: không ai bấm nút.
_BAT = frozenset({"1", "true", "yes", "on", "bat"})

#: Trần thời gian một run được phép chạy. `TIMED_OUT` là trạng thái **kết thúc**,
#: nên nó kéo theo `finally` — đó là điểm của `M10`.
TRAN_RUN = timedelta(hours=24)


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def dang_bat() -> bool:
    return (os.environ.get(BIEN_CO) or "").strip().lower() in _BAT


# ── enqueue ───────────────────────────────────────────────────────────────────

def enqueue(db, run_id: str) -> bool:
    """Run mới → hàng đợi. Trả `False` nếu nó đã ở đó (hoặc đi xa hơn).

    Luỹ đẳng, vì trigger, API và người dùng đều có thể gọi — và một run vào
    hàng đợi hai lần là một run chạy hai lần.
    """
    run = db.get(WorkflowRun, run_id)
    if run is None:
        return False
    if run.status not in ("queued", "CREATED"):
        return False
    if not may_trang_thai.chuyen_run(db, run_id, sang="VALIDATING"):
        return False
    return may_trang_thai.chuyen_run(db, run_id, sang="QUEUED")


# ── dequeue ───────────────────────────────────────────────────────────────────

def _con_cho_chay(db, run: WorkflowRun) -> bool:
    """Run này còn chờ waitpoint nào chưa mở không?"""
    wps = list(db.execute(
        select(Waitpoint).where(Waitpoint.run_id == run.id,
                                Waitpoint.status == "PENDING")).scalars())
    return any(not cho_doi.da_mo(db, wp.id) for wp in wps)


def dequeue(db, gioi_han: int = 50) -> list[WorkflowRun]:
    """Run sẵn sàng tiến. ⭐ **LỌC TRƯỚC KHI CHỌN**, không nhặt-rồi-nhả.

    🔴 Nhặt một run rồi phát hiện nó đang chờ là **đúng khiếm khuyết** mà `F2`
    đo được ở tầng job:

        9.833 / 10.663 = 92,2 %  luot nhat ket thuc bang "hoan: tai nguyen ban"

    Mỗi lượt nhặt-rồi-nhả tốn một vòng truy vấn, một lượt ghi sự kiện, và một
    khoảng chờ **khách nhìn thấy**. Ở `jobs.claim()` ta đã sửa bằng cách hỏi
    trước; đây là cùng phép sửa ở tầng run.

    ⚠️ Vẫn là **bộ lọc cơ hội, không phải khoá** — giống hệt
       `jobs._con_cho_tai_nguyen`. Hai worker vẫn có thể cùng thấy một run sẵn
       sàng. Lớp giành thật thuộc về Đợt sau (`FOR UPDATE SKIP LOCKED` trên
       PostgreSQL); bộ lọc này chỉ làm chuyện nhặt-rồi-nhả thành **hiếm** thay
       vì **thường trực**.
    """
    if not dang_bat():
        return []
    ung_vien = list(db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.status.in_(("QUEUED", "RUNNING", "WAITING")))
        .order_by(WorkflowRun.created_at, WorkflowRun.id)
        .limit(max(1, int(gioi_han)) * 4)).scalars())
    ra = [r for r in ung_vien if not _con_cho_chay(db, r)]
    return ra[:max(1, int(gioi_han))]


# ── attempt ───────────────────────────────────────────────────────────────────

def attempt(db, run_id: str, node_id: str) -> int:
    """Số thứ tự lượt thử KẾ TIẾP của MỘT node.

    ⚠️ Đếm **theo node**, không theo run. Một run có node A thử ba lần và node B
       thử một lần; một bộ đếm chung nói *"lượt thứ 4"* cho B — và `cost_credit`
       ghi theo attempt sẽ vào sai chỗ, tức **sổ tiền sai**, không chỉ nhãn sai.

    Đếm từ chính chuỗi ảnh chụp: không cần một cột đếm nào, và không có cột đếm
    nào để lệch khỏi lịch sử.
    """
    da_co = db.query(NodeRunSnapshot).filter_by(run_id=run_id,
                                                node_id=node_id).count()
    lan = da_co + 1
    may_trang_thai.chuyen_node(db, run_id, node_id, sang="READY",
                               mo_ta=f"luot thu {lan}", attempt_number=lan)
    return lan


# ── ttl ───────────────────────────────────────────────────────────────────────

def ttl(db) -> dict[str, int]:
    """Hết hạn run · waitpoint · artifact. Trả số lượng đã đóng mỗi loại.

    ⭐ `TIMED_OUT` là một trạng thái **kết thúc**, nên `chuyen_run()` kéo theo
       `ket_so()` trong **cùng transaction**. Đó chính là hình dạng của `M10`:
       đường `SUCCEEDED` có người kết sổ, còn `TIMED_OUT` thì rơi vào một bộ dọn
       nền — và giữ chỗ nằm lại.

    ⛔ **Không xoá artifact ở đây**, chỉ đếm. Backend nào có vòng đời riêng (R2
       lifecycle) thì ta không tự xoá; việc xoá thuộc về `artifact.ta_tu_xoa()`
       và một bước riêng, không phải một vòng quét chung.
    """
    if not dang_bat():
        return {"bo_qua": 0}
    luc = _bay_gio()
    dem = {"run": 0, "waitpoint": 0, "artifact": 0}

    han = luc - TRAN_RUN
    for run in db.execute(
            select(WorkflowRun)
            .where(WorkflowRun.status.in_(("QUEUED", "RUNNING", "WAITING")),
                   WorkflowRun.started_at.is_not(None),
                   WorkflowRun.started_at <= han)).scalars():
        if may_trang_thai.chuyen_run(db, run.id, sang="TIMED_OUT",
                                     ly_do="qua tran thoi gian"):
            dem["run"] += 1

    for wp in db.execute(
            select(Waitpoint)
            .where(Waitpoint.status == "PENDING",
                   Waitpoint.due_at.is_not(None),
                   Waitpoint.due_at <= luc)).scalars():
        wp.status = "EXPIRED"
        dem["waitpoint"] += 1

    dem["artifact"] = len(db.execute(
        select(Artifact.id)
        .where(Artifact.ttl_class != "PERMANENT",
               Artifact.expires_at.is_not(None),
               Artifact.expires_at <= luc)).scalars().all())

    db.flush()
    return dem


# ── Một vòng ─────────────────────────────────────────────────────────────────

def mot_vong(db, gioi_han: int = 50) -> dict:
    """Một lượt của vòng điều phối. KHÔNG commit — bên gọi quyết ranh giới.

    ⛔ Không commit ở đây là chủ ý: `ket_so()` phải nằm **cùng transaction** với
       lần chuyển sang trạng thái kết thúc (`M10`), và chỉ bên gọi mới biết
       ranh giới ấy nên đóng ở đâu.
    """
    if not dang_bat():
        return {"bo_qua": "co tat"}
    san_sang = dequeue(db, gioi_han=gioi_han)
    return {"san_sang": [r.id for r in san_sang], "ttl": ttl(db)}

