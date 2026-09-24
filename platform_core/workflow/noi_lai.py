"""Nối lại một điểm chờ — MỘT cửa cho mọi nguồn tín hiệu từ NGOÀI động cơ.

Webhook resume (`/hooks/wp/{id}`), người duyệt (`core.human`), bộ phát sự kiện
(§8.4) và bộ quét hết hạn đều đi qua đây. Một cửa, vì ba việc phải xảy ra
**cùng nhau hoặc không xảy ra**:

    1. ghi `waitpoint_signal`   (chốt luỹ đẳng là `UNIQUE(waitpoint_id, seq)`)
    2. đóng `waitpoint`         (`status`, `output_ref`)
    3. ghi `wakeup` cho run      → động cơ quay lại và chuyển node

⛔ Bỏ bước 3 là cách im lặng nhất để một run đứng tới `TRAN_RUN` 20 giờ **với
   tiền bị giữ**: tín hiệu đã có trong bảng, nhưng không gì đánh thức động cơ
   để nó đọc.

## ⭐ Câu hỏi bắt buộc của phase này: hai vòng `foreach` có đụng nhau không?

**Không**, và chỗ đảm bảo điều đó nằm ở `node_run_waitpoint`: hàng của nó lưu
`node_id` là **ĐƯỜNG THI HÀNH** (`cho_doi.chan_node` gọi `thi_hanh.khoa_node`).
Nên `danh_thuc_node_cua()` hẹn wakeup theo **đúng** khoá đó — `f1:0/cho1` và
`f1:1/cho1` là hai `node_run_id` khác nhau, hai hàng `wakeup` khác nhau.

⛔ Đây là lý do hàm dưới gọi `danh_thuc.hen(..., node_run_id=khoa)` **trần**
   chứ không `hen_node(node_id=…)`: khoá ĐÃ là đường thi hành, và mã hoá nó
   lần thứ hai sẽ ra `f1:0/f1:0/cho1` — một khoá không ai khác sinh ra được,
   tức một wakeup không bao giờ khớp.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy.exc import IntegrityError

from platform_core.models import Waitpoint
from platform_core.workflow import cho_doi, danh_thuc
# `bam_token` định nghĩa MỘT lần ở `trigger` (nó là chủ của token webhook);
# nhập lại ở đây thay vì viết `sha256` lần thứ hai — hai công thức băm cho
# cùng một loại bí mật là hai chỗ để chúng trôi khỏi nhau.
from platform_core.workflow.trigger import bam_token

log = logging.getLogger(__name__)


class KetNoiLai(Enum):
    KHONG_CO = "khong_co"
    TOKEN_SAI = "token_sai"
    DA_DONG = "da_dong"
    DA_MO = "da_mo"


KHONG_CO = KetNoiLai.KHONG_CO
TOKEN_SAI = KetNoiLai.TOKEN_SAI
DA_DONG = KetNoiLai.DA_DONG
DA_MO = KetNoiLai.DA_MO

#: Trạng thái `waitpoint` còn nhận tín hiệu. Mọi thứ khác là đã chốt.
DANG_CHO = "PENDING"


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def danh_thuc_node_cua(db, wp: Waitpoint, *, kind: str = "waitpoint_due",
                       due_at: Optional[datetime] = None) -> int:
    """Hẹn một wakeup cho MỖI node đang bị waitpoint này chặn.

    Trả số wakeup đã ghi. Một wakeup đã có sẵn (cùng run + cùng đường + cùng
    loại + cùng hạn) **không** được đếm và **không** phải lỗi: chốt `Q4` đòi
    đường hẹn luỹ đẳng, và chỗ cưỡng chế là `uq_wakeup_khu_trung`.
    """
    luc = due_at or _bay_gio()
    dem = 0
    for khoa in cho_doi.node_dang_bi_chan(db, wp.id):
        if danh_thuc.hen_luy_dang(db, run_id=wp.run_id, kind=kind,
                                  due_at=luc, node_run_id=khoa) is not None:
            dem += 1
    if not dem:
        # Không node nào bị chặn (hoặc tất cả đã có wakeup): vẫn phải đưa run
        # quay lại động cơ, nếu không tín hiệu nằm trong bảng mà không ai đọc.
        danh_thuc.hen_luy_dang(db, run_id=wp.run_id, kind=kind, due_at=luc)
    return dem


def mo(db, wp: Waitpoint, *, status: str = "SUCCEEDED", seq: int = 1,
       ra: Optional[dict] = None, la_loi: bool = False,
       nguon: str = "") -> KetNoiLai:
    """Ghi tín hiệu + đóng waitpoint + đánh thức run. Luỹ đẳng.

    `status` là trạng thái của **tín hiệu** (`SUCCEEDED` | `FAILED` |
    `CANCELLED` | `NOT_DISPATCHED`), không phải của node — node do động cơ
    chuyển, vì chỉ động cơ giữ khoá hàng run.
    """
    if wp.status != DANG_CHO:
        return DA_DONG
    try:
        with db.begin_nested():
            cho_doi.ghi_tin_hieu(db, wp.id, seq=int(seq), status=status,
                                 ref_id=nguon[:64], result_ref=dict(ra or {}))
    except IntegrityError:
        # `UNIQUE(waitpoint_id, seq)` — cùng nguồn gửi hai lần. Không phải lỗi;
        # đi tiếp để bước đóng + đánh thức vẫn chạy (lượt trước có thể đã chết
        # giữa chừng). ⛔ Chỉ nuốt ĐÚNG lỗi này: mọi IntegrityError khác nổi lên.
        log.info("noi_lai: tin hieu seq=%s cua waitpoint %s da co", seq, wp.id)
    wp.status = "COMPLETED"
    wp.output_ref = dict(ra or {})
    wp.output_is_error = bool(la_loi)
    db.flush()
    danh_thuc_node_cua(db, wp)
    return DA_MO


def mo_bang_token(db, waitpoint_id: str, *, token: str,
                  du_lieu: Optional[dict] = None) -> KetNoiLai:
    """Cửa CÔNG KHAI: resume bằng URL một-lần (`waitpoint.token_hash`).

    ⛔ Waitpoint **không có** `token_hash` ⇒ `TOKEN_SAI`, không phải "cho qua".
       Một điểm chờ chưa phát URL không được mở bằng một request đoán đúng id.

    ⚠️ Id sai và token sai trả về hai mã khác nhau (404 / 401) — chấp nhận
       được ở đây vì id waitpoint là UUID4 (122 bit), nên 404 không phải một
       máy dò dùng được; và phân biệt được giúp người tích hợp sửa đúng lỗi.
    """
    wp = db.get(Waitpoint, str(waitpoint_id))
    if wp is None:
        return KHONG_CO
    can = str(wp.token_hash or "")
    if not can or bam_token(token) != can:
        return TOKEN_SAI
    return mo(db, wp, status="SUCCEEDED", ra=dict(du_lieu or {}),
              nguon="hooks/wp")


__all__ = ["DANG_CHO", "DA_DONG", "DA_MO", "KHONG_CO", "TOKEN_SAI",
           "KetNoiLai", "bam_token", "danh_thuc_node_cua", "mo",
           "mo_bang_token"]
