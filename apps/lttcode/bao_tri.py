"""Việc nền của app LTTCODE — `AppManifest.bao_tri`, nền tảng gọi dưới lease.

Chỉ một việc: dọn `lttcode_auth_codes` đã hết hạn (`dang_nhap.don_ma_het_han`),
đúng lời khai ở `platform_core/public_api/governance.py`.

Import `dang_nhap` TRONG hàm: manifest được nạp lúc khám phá app, còn `dang_nhap`
kéo theo tầng khoá API — không cần trả giá đó chỉ để liệt kê app.
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def chay() -> None:
    """⛔ Không được ném (luật `bao_tri` của nền tảng) — lỗi thì ghi log rồi thôi."""
    from apps.lttcode.dang_nhap import don_ma_het_han
    from platform_core.db import get_session

    gen = get_session()
    db = next(gen)
    try:
        so = don_ma_het_han(db)
        db.commit()
        if so:
            log.info("LTTCODE bao tri: da xoa %s ma dang nhap het han", so)
    except Exception:
        db.rollback()
        log.exception("LTTCODE bao tri: don ma het han that bai")
    finally:
        next(gen, None)                         # chạy nốt `finally` đóng phiên của get_session
