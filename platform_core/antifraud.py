"""
antifraud.py — chống lạm dụng đăng ký (Q9).

Tự đăng ký + credit dùng thử (Q7) nghĩa là **ai cũng tạo được tài khoản mới để
lấy credit miễn phí**. Với API tính tiền thật, đây là cách chắc chắn nhất để
mất tiền. Hai lớp chặn ở đây, cộng với xác thực email (route) và Turnstile
(server/auth/turnstile.py):

1. **Chặn tên miền email dùng-một-lần.** Phần lớn lạm dụng dùng hộp thư tạm
   (10-phút-mail...). Chặn được đa số người lạm dụng phổ thông.
2. **Giới hạn số tài khoản mới trên mỗi IP mỗi ngày.** Chặn tạo hàng loạt từ
   một máy.

Không lớp nào chặn được kẻ quyết tâm (mail riêng + VPN xoay IP). Mục tiêu là
nâng chi phí lạm dụng lên cao hơn giá trị credit dùng thử, không phải bất khả
xâm phạm.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from platform_core.models import User

# Số tài khoản mới tối đa trên mỗi IP trong 24 giờ. Đổi qua env nếu cần.
GIOI_HAN_IP_MOI_NGAY = int(os.environ.get("LTT_MAX_DANGKY_IP_NGAY", "3") or "3")

# Tên miền email TIN CẬY — không bị đếm theo IP.
#
# Vì sao theo tên miền chứ không theo IP: IP văn phòng là IP **động**, dùng chung
# sau NAT, và đổi được bằng một VPN trong năm giây. Nó vừa chặn nhầm người thật
# (nhân viên ngồi cùng mạng, 2026-08-07) vừa không chặn được kẻ có chủ ý. Tên
# miền email thì cố định, và chỉ ai có hộp thư trong miền đó mới qua được.
#
# Đây KHÔNG phải là nới lỏng cho Internet: người lạ không có `@lttstudios.com`.
MIEN_TIN_CAY = frozenset(
    m.strip().lower()
    for m in (os.environ.get("LTT_DANGKY_MIEN_TIN_CAY") or "").split(",")
    if m.strip())


def la_mien_tin_cay(email: str) -> bool:
    """True nếu email thuộc một tên miền đã khai là tin cậy."""
    e = (email or "").strip().lower()
    return "@" in e and e.rsplit("@", 1)[1] in MIEN_TIN_CAY

# Danh sách tên miền mail dùng-một-lần phổ biến. Cố ý là danh sách tĩnh nhỏ,
# không phải một gói phụ thuộc: gói dữ liệu này thay đổi hằng ngày và kéo theo
# một phụ thuộc phải cập nhật. Danh sách cốt lõi này chặn phần lớn; mở rộng qua
# LTT_DISPOSABLE_EXTRA (ngăn cách bằng dấu phẩy) khi phát hiện tên miền mới.
_DISPOSABLE_CORE = {
    "10minutemail.com", "guerrillamail.com", "guerrillamail.net", "mailinator.com",
    "tempmail.com", "temp-mail.org", "throwawaymail.com", "yopmail.com",
    "getnada.com", "trashmail.com", "sharklasers.com", "grr.la", "maildrop.cc",
    "dispostable.com", "fakeinbox.com", "mailnesia.com", "mohmal.com",
    "emailondeck.com", "mytemp.email", "moakt.com", "tempinbox.com",
    "spamgourmet.com", "mailcatch.com", "tmail.ws", "10mail.org", "burnermail.io",
    "tempmailo.com", "1secmail.com", "inboxkitten.com", "harakirimail.com",
}


def _disposable_domains() -> set[str]:
    extra = (os.environ.get("LTT_DISPOSABLE_EXTRA") or "").strip()
    if not extra:
        return _DISPOSABLE_CORE
    them = {d.strip().lower() for d in extra.split(",") if d.strip()}
    return _DISPOSABLE_CORE | them


def la_email_dung_mot_lan(email: str) -> bool:
    """True nếu email thuộc tên miền dùng-một-lần đã biết."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1]
    return domain in _disposable_domains()


def _bay_gio() -> datetime:
    return datetime.now(timezone.utc)


def vuot_gioi_han_ip(db: DbSession, ip: str, email: str = "") -> bool:
    """True nếu IP này đã tạo đủ số tài khoản cho phép trong 24 giờ qua.

    Đếm theo cột `registration_ip` của bảng users. IP rỗng (không xác định được)
    không bị giới hạn ở đây — chặn theo IP rỗng sẽ chặn nhầm mọi người khi
    reverse proxy cấu hình sai; các lớp khác (email, Turnstile) vẫn còn.
    """
    # Miền tin cậy: bỏ qua trần IP hoàn toàn. Nhân viên ngồi chung một mạng
    # (một IP công cộng, lại còn động) không được coi là hành vi farm.
    if email and la_mien_tin_cay(email):
        return False
    ip = (ip or "").strip()
    if not ip:
        return False
    tu = _bay_gio() - timedelta(hours=24)
    so = db.execute(
        select(func.count()).select_from(User).where(
            User.registration_ip == ip, User.created_at >= tu
        )
    ).scalar_one()
    return so >= GIOI_HAN_IP_MOI_NGAY
