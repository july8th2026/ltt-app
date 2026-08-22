"""Vé đăng nhập một-lần: từ ứng dụng LTT Nexus sang trình duyệt (B3).

## Vấn đề

Trong ứng dụng, bấm **Nạp credit** mở trình duyệt tới `/nap` — rồi bắt đăng nhập
lại. Cùng một tài khoản, cùng một máy, mà phải gõ mật khẩu lần thứ hai. Người
dùng đọc việc đó là "app và web là hai hệ khác nhau", và họ đọc đúng: chưa có
đường nào nối phiên của app sang phiên của web.

## Cách nối

Ứng dụng **đã** chứng minh được danh tính bằng chữ ký Ed25519 của thiết bị
(`agent_auth`). Vậy nó xin nền tảng một **vé** rồi mở trình duyệt tới
`/nexus-sso?ma=<vé>`; trang đó đổi vé lấy phiên trình duyệt.

## Vì sao không cần bảng mới

Vé **chính là một hàng `sessions`** với tuổi thọ ngắn. Không phải để tiết kiệm
một bảng, mà vì hai thứ đó có cùng vòng đời và cùng cách thu hồi — dựng bảng thứ
hai nghĩa là có hai chỗ phải nhớ dọn, và một trong hai sẽ bị quên.

## Ba ràng buộc, và vì sao

1. **Sống 90 giây.** Vé đi qua thanh địa chỉ nên nó nằm lại trong lịch sử trình
   duyệt. Một vé sống lâu trong lịch sử là một cánh cửa mở lâu.
2. **Dùng một lần — đổi xong là quay vòng.** Đổi vé xong, hàng vé bị **xoá** và
   một phiên MỚI (tuổi thọ bình thường) được cấp cho cookie. Nên cái còn nằm
   trong lịch sử trình duyệt là một vé đã chết, không phải cookie đang sống.
3. **Đánh dấu `user_agent`** để người dùng nhận ra nó trong danh sách phiên: một
   dòng lạ không giải thích được thì bằng không có.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import delete

from platform_core.models import Session as SessionRow
from platform_core.models import User

log = logging.getLogger(__name__)

#: Vé sống bao lâu. Đủ để mở trình duyệt và tải trang, không đủ để thành cửa sau.
VE_TTL = timedelta(seconds=90)

#: Nhãn hiện trong "các phiên đang đăng nhập" — để dòng đó tự giải thích được.
NHAN_VE = "LTT Nexus (ve dang nhap mot lan)"
NHAN_PHIEN = "LTT Nexus (dang nhap tu ung dung)"


def tao_ve(db, user: User, *, ip: str = "") -> str:
    """Phát một vé một-lần cho `user`. Trả token THÔ (chỉ lúc này mới thấy nó)."""
    from platform_core.users import tao_phien

    return tao_phien(db, user, user_agent=NHAN_VE, ip=ip, ttl=VE_TTL)


def doi_ve(db, ma: str, *, ip: str = "", user_agent: str = "") -> str | None:
    """Đổi vé lấy một phiên trình duyệt thật. Trả sid mới, hoặc None nếu vé hỏng.

    Từ chối mọi thứ **không phải vé** — kể cả một cookie phiên hợp lệ. Nếu không
    kiểm nhãn thì đường này biến thành "đưa cookie qua URL cũng đăng nhập được",
    tức là tự tay dựng thêm một cách rò phiên.

    Đổi vé là **xoá vé rồi cấp phiên mới**, không phải kéo dài vé: cái nằm lại
    trong lịch sử trình duyệt phải là một token đã chết.
    """
    from platform_core.users import _bam_sid, lay_user_tu_phien, tao_phien

    ma = str(ma or "").strip()
    if not ma:
        return None
    user = lay_user_tu_phien(db, ma)
    if user is None:
        return None

    row = db.get(SessionRow, _bam_sid(ma))
    if row is None or row.user_agent != NHAN_VE:
        # Không phải vé (hoặc đã bị đổi rồi). Không nói vì sao.
        return None

    # Tiêu vé bằng MỘT câu DELETE có điều kiện rồi xem đếm được mấy hàng, thay
    # vì `db.delete(row)`. Hai yêu cầu cùng lúc (bấm hai lần, trình duyệt nạp
    # trước) thì chỉ một cái đếm được 1; cái kia đếm 0 và bị từ chối như vé hỏng.
    # `db.delete(row)` ở đây sẽ ném StaleDataError khi thua cuộc — tức là biến
    # một cú bấm hai lần thành trang lỗi 500.
    xoa = db.execute(delete(SessionRow).where(SessionRow.id == _bam_sid(ma)))
    if (xoa.rowcount or 0) < 1:
        return None

    sid = tao_phien(db, user, user_agent=(user_agent or NHAN_PHIEN)[:255], ip=ip)
    log.info("nexus sso: doi ve thanh cong cho user=%s", user.id)
    return sid


__all__ = ["NHAN_PHIEN", "NHAN_VE", "VE_TTL", "doi_ve", "tao_ve"]
