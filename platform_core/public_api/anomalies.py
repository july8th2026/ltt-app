"""Dấu hiệu bất thường: hỏi những câu mà dữ liệu đã có sẵn nhưng chưa ai hỏi.

Khu API chống được các kiểu tấn công đã biết — SSRF, đọc chéo tài khoản, giả mạo
header, dò khoá — và mỗi lần chặn đều để lại một dòng. Nhưng nó **không phát
hiện** bất thường: một khoá bị lộ vẫn được dùng bình thường, đúng scope, đúng
nhịp, cho tới khi hết tiền. Nhật ký ghi đầy đủ mọi lời gọi đó và không ai đọc.

Ba câu hỏi dưới đây đều trả lời được từ `api_request_logs` và
`api_security_events` đang có, **không cần bảng mới, không cần cột mới**. Đó là
lý do chúng đáng làm trước: chi phí gần bằng không, và chúng chuyển việc phát
hiện từ "khách báo cho ta" thành "ta thấy trước".

Cố ý **chỉ đọc và chỉ báo cho người vận hành**, không tự khoá gì. Một hệ tự động
khoá dựa trên suy đoán sẽ chặn nhầm khách thật vào đúng ngày họ chạy chiến dịch
lớn — và mất một khách vì nghi oan thì đắt hơn nhiều so với xử lý muộn vài giờ.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from platform_core.public_api.tables import (ApiRequestLog, ApiSecurityEvent)

#: Bao nhiêu lần bị từ chối vì thiếu quyền trong một cửa sổ thì đáng nhìn. Một
#: tích hợp cấu hình sai cũng chạm ngưỡng này — và đó là chuyện tốt, vì khách
#: đang gọi hỏng mà chưa chắc đã biết.
SCOPE_DENIED_NGUONG = 20

#: Chi tiêu hôm nay gấp bao nhiêu lần mức thường ngày thì đáng nhìn.
CHI_TIEU_GAP = 5.0

#: Sàn để một tài khoản mới không bị coi là bất thường: gấp 5 lần của một con số
#: rất nhỏ vẫn là một con số rất nhỏ.
CHI_TIEU_SAN = 50

#: Bao nhiêu lần thử một khoá đã thu hồi thì đáng nhìn. Một lần là quên; lặp
#: lại nghĩa là **có thứ đang giữ khoá đó và vẫn chạy** — hoặc là hệ thống của
#: khách chưa cập nhật, hoặc là khoá đã ra ngoài.
KHOA_THU_HOI_NGUONG = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


def scope_bi_tu_choi(db, *, hours: int = 24, now=None) -> list:
    """Khoá nào đang bị từ chối vì thiếu quyền, nhiều lần.

    Hai nguyên nhân, và người vận hành phân biệt được ngay khi nhìn: một tích
    hợp mới cấu hình thiếu scope (rất nhiều lỗi, một route), hoặc ai đó đang dò
    xem khoá này với được tới đâu (rải khắp nhiều route).
    """
    since = (now or _now()) - timedelta(hours=max(1, int(hours)))
    rows = db.execute(
        sa.select(ApiRequestLog.key_id,
                  sa.func.count(ApiRequestLog.id).label("lan"),
                  sa.func.count(sa.distinct(ApiRequestLog.route)).label("route"))
        .where(ApiRequestLog.created_at >= since,
               ApiRequestLog.status == 403,
               ApiRequestLog.key_id != "")
        .group_by(ApiRequestLog.key_id)
        .having(sa.func.count(ApiRequestLog.id) >= SCOPE_DENIED_NGUONG)
        .order_by(sa.desc("lan"))
    ).all()
    return [{"key_id": r.key_id, "lan": int(r.lan), "so_route": int(r.route)}
            for r in rows]


def chi_tieu_vot(db, *, hours: int = 24, now=None) -> list:
    """Tài khoản nào đang tiêu vọt hẳn so với chính nó mọi ngày.

    So với **chính tài khoản đó**, không so với trung bình toàn hệ thống: một
    khách lớn tiêu nhiều là bình thường, còn một khách nhỏ đột nhiên tiêu như
    khách lớn thì không.
    """
    current = now or _now()
    since = current - timedelta(hours=max(1, int(hours)))
    truoc = current - timedelta(days=14)

    gan = dict(db.execute(
        sa.select(ApiRequestLog.user_id,
                  sa.func.coalesce(sa.func.sum(ApiRequestLog.credit_delta), 0))
        .where(ApiRequestLog.created_at >= since, ApiRequestLog.user_id != "")
        .group_by(ApiRequestLog.user_id)).all())
    if not gan:
        return []

    truoc_do = dict(db.execute(
        sa.select(ApiRequestLog.user_id,
                  sa.func.coalesce(sa.func.sum(ApiRequestLog.credit_delta), 0))
        .where(ApiRequestLog.created_at >= truoc,
               ApiRequestLog.created_at < since,
               ApiRequestLog.user_id != "")
        .group_by(ApiRequestLog.user_id)).all())

    ngay = max(1.0, (since - truoc).total_seconds() / 86400.0)
    ra = []
    for user_id, tieu in gan.items():
        tieu = abs(int(tieu or 0))
        if tieu < CHI_TIEU_SAN:
            continue
        thuong_ngay = abs(int(truoc_do.get(user_id, 0) or 0)) / ngay
        if thuong_ngay <= 0:
            # Chưa có nền để so. Chỉ báo khi con số đủ lớn để đáng nhìn dù là
            # tài khoản mới — im lặng hẳn ở đây nghĩa là một khoá bị lộ ngay
            # ngày đầu sẽ không ai thấy.
            if tieu >= CHI_TIEU_SAN * 10:
                ra.append({"user_id": user_id, "tieu": tieu,
                           "thuong_ngay": 0.0, "gap": None})
            continue
        gap = tieu / thuong_ngay
        if gap >= CHI_TIEU_GAP:
            ra.append({"user_id": user_id, "tieu": tieu,
                       "thuong_ngay": round(thuong_ngay, 1),
                       "gap": round(gap, 1)})
    return sorted(ra, key=lambda r: r["tieu"], reverse=True)


def khoa_da_thu_hoi_van_bi_dung(db, *, hours: int = 24, now=None) -> list:
    """Khoá đã thu hồi mà vẫn có thứ gì đó gọi bằng nó.

    Đây là tín hiệu trực tiếp nhất về một credential đã ra ngoài: khách thu hồi
    rồi mà vẫn có lời gọi nghĩa là **thứ đang giữ khoá không phải hệ thống mà họ
    vừa cập nhật**. Đường xác thực cố ý không phân biệt khoá sai với khoá đã thu
    hồi (để không ai dò được id hợp lệ), nên câu hỏi này chỉ trả lời được ở đây,
    lúc đọc.
    """
    from platform_core.public_api import security_log

    since = (now or _now()) - timedelta(hours=max(1, int(hours)))
    rows = db.execute(
        sa.select(ApiSecurityEvent.key_id,
                  sa.func.count(ApiSecurityEvent.id).label("lan"),
                  sa.func.count(sa.distinct(ApiSecurityEvent.ip)).label("ip"))
        .where(ApiSecurityEvent.created_at >= since,
               ApiSecurityEvent.kind == security_log.REVOKED_KEY,
               ApiSecurityEvent.key_id != "")
        .group_by(ApiSecurityEvent.key_id)
        .having(sa.func.count(ApiSecurityEvent.id) >= KHOA_THU_HOI_NGUONG)
        .order_by(sa.desc("lan"))
    ).all()
    return [{"key_id": r.key_id, "lan": int(r.lan), "so_ip": int(r.ip)}
            for r in rows]


def quet(db, *, hours: int = 24, now=None) -> dict:
    """Cả ba câu hỏi, cho trang bảo mật của người vận hành."""
    return {
        "scope_bi_tu_choi": scope_bi_tu_choi(db, hours=hours, now=now),
        "chi_tieu_vot": chi_tieu_vot(db, hours=hours, now=now),
        "khoa_thu_hoi": khoa_da_thu_hoi_van_bi_dung(db, hours=hours, now=now),
    }


__all__ = ["CHI_TIEU_GAP", "CHI_TIEU_SAN", "KHOA_THU_HOI_NGUONG",
           "SCOPE_DENIED_NGUONG", "chi_tieu_vot", "khoa_da_thu_hoi_van_bi_dung",
           "quet", "scope_bi_tu_choi"]
