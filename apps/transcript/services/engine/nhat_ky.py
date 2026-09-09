"""Cầu nối `info(event, **kw)` của bot legacy sang `logging` của nền tảng.

Engine được chuyển vào đây **nguyên vẹn** — đó là điểm chính: mọi ngưỡng, mọi
hằng số, mọi nhánh rẽ giữ y như bản đã chạy một năm. Thứ duy nhất phải đổi là
`from utils.log import info`, vì `utils/` của bot không đi theo.

⛔ Đừng "cải tiến" chữ ký thành `info(msg, *args)` cho giống phần còn lại của
   kho: 17 tệp gọi nó theo kiểu sự kiện + khoá (`info("vad_done", segments=3)`),
   và một chữ ký khác sẽ làm 17 tệp ấy hỏng lúc chạy chứ không lúc nạp.
"""
from __future__ import annotations

import logging

log = logging.getLogger("apps.transcript.engine")


def info(event: str, **kw) -> None:
    log.info("%s %s", event, kw if kw else "")


def exc(event: str, err: Exception, **kw) -> None:
    log.warning("%s %s: %s %s", event, type(err).__name__, err, kw if kw else "")


def debug(event: str, **kw) -> None:
    log.debug("%s %s", event, kw if kw else "")
