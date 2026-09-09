"""Đánh thức: bảng `wakeup` là nguồn chân lý, `NOTIFY` chỉ rút ngắn độ trễ.

Chốt `Q4` (`docs/architecture/workflow_v2_audit/23_24 §3`).

🔴 Vì sao bảng chứ không phải `LISTEN/NOTIFY` — một con số đo được, không phải
   một sở thích kiến trúc: worker restart **13,6 lần/ngày** (`01 §A.6`). Một
   `NOTIFY` phát đúng lúc worker đang khởi động lại **biến mất không dấu vết**.

⇒ Đây là *"polling như dự phòng, không phải cơ chế chính"* của `WF-402`: quét
  mỗi **5 giây** (không phải 2 như hôm nay), vì `NOTIFY` lo phần tức thì.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from platform_core.models import Wakeup

#: Chu kỳ quét. 5 giây là con số của chốt `Q4` — `NOTIFY` lo phần tức thì, nên
#: bảng chỉ cần là lưới an toàn. Rút ngắn nó là làm dày vòng quay mà không rút
#: ngắn được độ trễ thực tế.
CHU_KY_QUET_S = 5.0


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hen(db, *, run_id: str, kind: str, due_at: datetime,
        node_run_id: str = "") -> Wakeup:
    """Hẹn một lần đánh thức.

    ⚠️ Không có `SELECT` chống trùng, và đó là chủ ý:
       `UNIQUE(run_id, node_run_id, kind, due_at)` cưỡng chế. Hai đường cùng
       hẹn một lần đánh thức — bảng **và** `NOTIFY`, hoặc hai worker cùng thấy
       một job xong — là trạng thái **bình thường**, không phải sự cố. Chốt
       `Q4` đòi cả hai đường luỹ đẳng; chỗ cưỡng chế điều đó là ràng buộc, chứ
       không phải một câu truy vấn cẩn thận ở tầng trên.
    """
    w = Wakeup(run_id=run_id, node_run_id=node_run_id or "", kind=kind,
               due_at=due_at)
    db.add(w)
    db.flush()
    return w


def den_han(db, gioi_han: int = 200) -> list[Wakeup]:
    """Những lần đánh thức đã tới hạn và chưa ai nhặt. CHỈ ĐỌC.

    🔴 `M2` sống ở đây: **một** câu SQL cho **toàn hệ thống**, không phải một
    câu mỗi run. Hai trăm run đang chờ vẫn là một truy vấn, đi thẳng vào chỉ số
    bộ phận `ix_wakeup_due (due_at) WHERE claimed_at IS NULL`.

    ⛔ Đừng thêm một vòng lặp nào quanh hàm này — `test_953` đếm câu SQL thật
       bằng `before_cursor_execute`, nên một vòng lặp ẩn sẽ hiện ra thành con
       số, không phải thành một nhận xét.

    Sắp theo `due_at` tăng dần: quá hạn lâu nhất được phục vụ trước, để một run
    không bị đói mãi sau những run tới hạn liên tục.
    """
    return list(db.execute(
        select(Wakeup)
        .where(Wakeup.claimed_at.is_(None), Wakeup.due_at <= _bay_gio())
        .order_by(Wakeup.due_at, Wakeup.id)
        .limit(max(1, int(gioi_han)))).scalars())


def nhat(db, gioi_han: int = 200,
         bay_gio: Optional[datetime] = None) -> list[Wakeup]:
    """Nhặt và đánh dấu `claimed_at` — hai worker không cùng đánh thức một run.

    ⚠️ Đây là **bộ lọc cơ hội ở tầng đọc**, không phải khoá. Lớp giành thật khi
       hai worker chạy song song vẫn là transaction của bên gọi: nhặt rồi
       `commit()` ngay, và bên thua sẽ thấy `claimed_at` đã có ở lượt sau.
       Trên PostgreSQL, bên gọi nên bọc bằng `FOR UPDATE SKIP LOCKED` giống
       `jobs.claim()` — Đợt 3 làm việc đó cùng scheduler.
    """
    luc = bay_gio or _bay_gio()
    ra = den_han(db, gioi_han=gioi_han)
    for w in ra:
        w.claimed_at = luc
    if ra:
        db.flush()
    return ra
