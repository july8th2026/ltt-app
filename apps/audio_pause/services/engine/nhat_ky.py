"""Cầu nối `info/debug` của bot legacy sang `logging` — như App `transcript`.

Engine chuyển vào đây **nguyên vẹn**; thứ duy nhất đổi là dòng import, vì
`utils/` của bot không đi theo.
"""
from __future__ import annotations

import logging

log = logging.getLogger("apps.audio_pause.engine")


def info(event: str, **kw) -> None:
    log.info("%s %s", event, kw if kw else "")


def debug(event: str, **kw) -> None:
    log.debug("%s %s", event, kw if kw else "")


def exc(event: str, err: Exception, **kw) -> None:
    log.warning("%s %s: %s %s", event, type(err).__name__, err, kw if kw else "")
