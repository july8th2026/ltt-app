"""kho_tep.py — gắn tệp đã tải lên vào một hội thoại ChatLTT. (H44 P06 bước 2)

## Nó làm gì, và nó CỐ TÌNH không làm gì

Nó nối `upload_sessions` (vé tải lên của nền tảng, nơi byte thật sự nằm) với
`chatltt_conversation`. Nó **không** đọc byte, **không** ghi byte, **không**
trích văn bản. Trích là bước 3 và là một **job**, vì trích một PDF dài vượt trần
100 giây của Cloudflare.

## Mọi hàm ở đây nhận `user_id`, và đó là điều kiện chứ không phải tham số

Không hàm nào tin rằng người gọi đã kiểm quyền. Route có thể quên; một hàm tự
kiểm thì không quên. `test_822` chốt cả **hai** chiều — sở hữu tệp mà không sở
hữu hội thoại cũng bị chặn, vì kiểm một chiều là để hở chiều kia.

⛔ `mot()` trả `None` cho người lạ chứ không ném. Ném một lỗi *"cấm"* khác với
   ném một lỗi *"không có"* là tự khai rằng id ấy có tồn tại — một rò rỉ nhỏ
   nhưng có thật khi id đoán được từ một lần chia sẻ màn hình.

## Vì sao đòi upload đã `promoted`

`upload_sessions.py` viết thẳng lý do cửa credit tồn tại: *"để không ai biến
input của job thành kho lưu trữ miễn phí"*. Cho gắn một vé còn `pending` là mở
đúng đường vòng mà cửa ấy sinh ra để chặn. P06 §7 vì thế chấm: **tải một tài
liệu lên để hỏi là tốn credit**, và giá phải hiện **trước** khi bấm, đi qua đúng
đường duyệt của P04.
"""
from __future__ import annotations

import logging

from sqlalchemy import select

from apps.chatltt.tables import ChatlttConversation, ChatlttTep
from platform_core.models import UPLOAD_ATTACHED, UPLOAD_PROMOTED, UploadSession

log = logging.getLogger(__name__)

MOI = "moi"
DANG_TRICH = "dang_trich"
XONG = "xong"
LOI = "loi"

#: Vé phải qua cửa credit rồi mới gắn được. `attached` cũng tính: nó nghĩa là vé
#: đã gắn vào một job có giữ credit — cùng một cửa, khác một nhịp.
SAN_SANG = (UPLOAD_PROMOTED, UPLOAD_ATTACHED)


class KhongDuocPhep(Exception):
    """Người gọi không sở hữu hội thoại, hoặc không sở hữu vé upload."""


class ChuaSanSang(Exception):
    """Vé upload chưa qua cửa credit — chưa `promoted`/`attached`."""


def gan(db, *, user_id: str, conversation_id: str, upload_id: str) -> ChatlttTep:
    """Gắn một tệp đã tải lên vào một hội thoại. Gọi lại lần hai trả về hàng cũ.

    ⭐ Idempotent ở **tầng hàm** vì bấm hai lần / F5 giữa chừng là ca thường; và
       `ux_chatltt_tep_conv_upload` chặn thêm một lần nữa ở **tầng CSDL**, cho ca
       hai tiến trình cùng lọt qua một `if`.
    """
    hoi_thoai = db.get(ChatlttConversation, conversation_id)
    if hoi_thoai is None or hoi_thoai.user_id != user_id:
        raise KhongDuocPhep("hoi thoai khong thuoc nguoi goi")

    ve = db.get(UploadSession, upload_id)
    if ve is None or ve.user_id != user_id:
        raise KhongDuocPhep("ve upload khong thuoc nguoi goi")
    if ve.status not in SAN_SANG:
        raise ChuaSanSang(f"ve upload dang {ve.status!r}, chua qua cua credit")

    cu = db.execute(
        select(ChatlttTep).where(ChatlttTep.conversation_id == conversation_id,
                                 ChatlttTep.upload_id == upload_id)
    ).scalar_one_or_none()
    if cu is not None:
        return cu

    tep = ChatlttTep(user_id=user_id, conversation_id=conversation_id,
                     upload_id=upload_id, ten_tep=ve.filename or "",
                     content_type=ve.content_type or "",
                     kich_thuoc=int(ve.actual_size or 0))
    db.add(tep)
    db.flush()
    return tep


def cua_hoi_thoai(db, *, user_id: str, conversation_id: str) -> list[ChatlttTep]:
    """Các tệp của một hội thoại. Người lạ nhận danh sách rỗng.

    ⛔ Lọc theo **cả hai** `user_id` và `conversation_id`. Lọc riêng hội thoại là
       đủ *hôm nay* (chủ hội thoại = chủ tệp), nhưng nó dựa vào một bất biến ở
       nơi khác. Một cửa quyền không được vay bất biến của bảng bên cạnh.
    """
    return list(db.execute(
        select(ChatlttTep)
        .where(ChatlttTep.conversation_id == conversation_id,
               ChatlttTep.user_id == user_id)
        .order_by(ChatlttTep.created_at)
    ).scalars())


def mot(db, *, user_id: str, tep_id: str) -> ChatlttTep | None:
    """Một tệp theo id. `None` cho người lạ — xem ghi chú đầu tệp về rò rỉ id."""
    tep = db.get(ChatlttTep, tep_id)
    return tep if tep is not None and tep.user_id == user_id else None


def danh_dau(db, *, user_id: str, tep_id: str, trang_thai: str,
             job_id: str = "", so_doan: int = 0, ly_do: str = "") -> bool:
    """Đổi trạng thái trích. Trả `False` khi không được phép — **không** ném.

    🔴 Đây là cửa **GHI**. Một kẻ không đọc được vẫn phá được nếu hàm ghi tin
       rằng người gọi đã kiểm quyền. `test_822` chốt đúng ca ấy.

    Trả `bool` chứ không ném vì người gọi chính là worker trích (bước 3): tệp
    đã bị xoá giữa chừng là chuyện bình thường của một job chạy sau, không phải
    một sự cố cần dựng ngược ngăn xếp.
    """
    tep = mot(db, user_id=user_id, tep_id=tep_id)
    if tep is None:
        log.info("danh_dau bi tu choi: tep=%r nguoi=%r", tep_id, user_id)
        return False
    tep.trang_thai_trich = trang_thai
    if job_id:
        tep.job_id = job_id
    if so_doan:
        tep.so_doan = int(so_doan)
    if ly_do:
        tep.ly_do_loi = ly_do
    db.flush()
    return True
