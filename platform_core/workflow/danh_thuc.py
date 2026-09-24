"""Đánh thức: bảng `wakeup` là nguồn chân lý, `NOTIFY` chỉ rút ngắn độ trễ.

Chốt `Q4` (`docs/architecture/workflow_v2_audit/23_24 §3`).

🔴 Vì sao bảng chứ không phải `LISTEN/NOTIFY` — một con số đo được, không phải
   một sở thích kiến trúc: worker restart **13,6 lần/ngày** (`01 §A.6`). Một
   `NOTIFY` phát đúng lúc worker đang khởi động lại **biến mất không dấu vết**.

⇒ Đây là *"polling như dự phòng, không phải cơ chế chính"* của `WF-402`: quét
  mỗi **5 giây** (không phải 2 như hôm nay), vì `NOTIFY` lo phần tức thì.
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from platform_core.models import Wakeup

#: Chu kỳ quét. 5 giây là con số của chốt `Q4` — `NOTIFY` lo phần tức thì, nên
#: bảng chỉ cần là lưới an toàn. Rút ngắn nó là làm dày vòng quay mà không rút
#: ngắn được độ trễ thực tế.
CHU_KY_QUET_S = 5.0

#: Bề rộng THẬT của `Wakeup.node_run_id` (`models.py`). Không phải một con số
#: tự chọn: PostgreSQL ném `StringDataRightTruncation` ở ký tự thứ 65, còn
#: SQLite nuốt im lặng — nên một đường quá dài chỉ lộ trên production.
TRAN_NODE_RUN_ID = 64

#: Ký tự `#` KHÔNG nằm trong tập id hợp lệ (`bien_dich._ID`), nên một khoá băm
#: không bao giờ đụng một khoá đường-thật.
_TIEN_TO_BAM = "#"
_ID_VONG = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def duong_thi_hanh(node_id: str,
                   *, vong: Sequence[tuple[str, int]] = ()) -> str:
    """Khoá nhận dạng của MỘT lần node chạy — `foreach1:0/delay1`.

    🔴 VÌ SAO KHÔNG PHẢI `node_id` TRẦN

    `UNIQUE(run_id, node_run_id, kind, due_at)` (`models.py`) là chỗ khử trùng
    wakeup. Với `node_id` trần, hai vòng lặp của một `foreach` có `delay` trong
    thân sinh **cùng một khoá**: vòng 2 va vào timer vòng 1, và run đứng chờ
    tới hạn cuối cùng thay vì hạn của nó.

    ⭐ NGUỒN — không phải suy luận. Activepieces dính đúng lỗi này với khoá
       `UNIQUE(flow_run_id, step_name)` và sửa bằng **đường thi hành đầy đủ**;
       `brain/knowledge/decisions/000015-fan-in-is-an-event-driven-waitpoint-barrier.md`
       (activepieces@`17e2ac0b`) viết: *"Identity is path-keyed… The engine
       sends `loop_1:3/loop_2:0/approval` in the existing `stepName` field…
       a delay or approval inside a loop used to reuse one waitpoint row across
       every iteration"*. Ta lấy cùng hình dạng khoá.

    ⛔ NƠI TA PHẢI ĐI XA HƠN HỌ. `stepName` của họ không có trần; cột của ta có
       (`TRAN_NODE_RUN_ID`). Vượt trần thì **băm**, không **cắt cụt**: cắt cụt
       là cách im lặng nhất để hai đường khác nhau thành một khoá — đúng lỗi
       hàm này tồn tại để chặn, chỉ đổi nguyên nhân.

    ⚠️ Khoá phải **lặp lại được**: cùng node + cùng vòng ⇒ cùng chuỗi. Đó là
       điều kiện để `hen()` giữ được tính luỹ đẳng của nó (hai đường cùng hẹn
       một lần đánh thức là trạng thái bình thường, không phải sự cố).
    """
    if not _ID_VONG.match(str(node_id or "")):
        raise ValueError(f"node_id khong hop le: {str(node_id)[:70]!r}")
    phan: list[str] = []
    for ten, chi_so in vong:
        if not _ID_VONG.match(str(ten or "")):
            raise ValueError(f"ten vong lap khong hop le: {str(ten)[:70]!r}")
        if isinstance(chi_so, bool) or not isinstance(chi_so, int) or chi_so < 0:
            raise ValueError(f"chi so vong lap phai la int >= 0, nhan {chi_so!r}")
        phan.append(f"{ten}:{chi_so}")
    phan.append(str(node_id))
    duong = "/".join(phan)
    if len(duong) <= TRAN_NODE_RUN_ID:
        return duong
    return _TIEN_TO_BAM + hashlib.sha256(duong.encode("utf-8")).hexdigest()[:40]


def hen_node(db, *, run_id: str, node_id: str, kind: str, due_at: datetime,
             vong: Sequence[tuple[str, int]] = ()) -> Wakeup:
    """`hen()` cho một node — khoá theo ĐƯỜNG THI HÀNH, không theo node_id.

    ⭐ Mọi chỗ hẹn thay cho MỘT NODE phải đi qua đây. `hen()` trần vẫn còn cho
       hai ca không thuộc về một node: `tick`/`start` của cả run
       (`node_run_id=""`) và wakeup theo **job id** (`cau_noi.bao_ket_thuc`,
       khoá đã duy nhất sẵn vì mỗi lượt thử là một job mới).
    """
    return hen(db, run_id=run_id, kind=kind, due_at=due_at,
               node_run_id=duong_thi_hanh(node_id, vong=vong))


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


def hen_luy_dang(db, *, run_id: str, kind: str, due_at: datetime,
                 node_run_id: str = "") -> Optional[Wakeup]:
    """`hen()` nhưng nuốt ĐÚNG một lỗi: trùng `uq_wakeup_khu_trung`.

    ⭐ Vì sao cần bản này bên cạnh `hen()`: `hen()` để ràng buộc NỔI LÊN, và
       điều đó đúng cho bên gọi đang ở trong một transaction mà một wakeup
       trùng là bất thường. Nhưng bên gọi của `noi_lai` thì ngược lại — tín
       hiệu tới hai lần (webhook gửi lại, hai worker cùng thấy) là ca BÌNH
       THƯỜNG, và để nó ném sẽ cuộn mất cả lần đóng waitpoint.

    ⚠️ `begin_nested()` chứ không `try` trần: sau khi một câu lệnh vỡ,
       transaction PostgreSQL ở trạng thái abort và mọi câu sau đều hỏng cho
       tới khi cuộn về một savepoint (cùng bài học `tao_run.danh_thuc_dong_co`).

    ⛔ Bắt HẸP: chỉ `IntegrityError`. Mất kết nối, khoá ngoại thiếu, lỗi
       serialization vẫn phải nổ.
    """
    try:
        with db.begin_nested():
            return hen(db, run_id=run_id, kind=kind, due_at=due_at,
                       node_run_id=node_run_id)
    except IntegrityError:
        return None


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
