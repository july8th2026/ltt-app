"""`info/warn/error/exc` kiểu sự kiện + khoá — chữ ký của bot legacy."""
from __future__ import annotations

import logging

log = logging.getLogger("apps.video_assembly.engine")


def info(event: str, **kw) -> None:
    log.info("%s %s", event, kw if kw else "")


def warn(event: str, **kw) -> None:
    log.warning("%s %s", event, kw if kw else "")


def error(event: str, **kw) -> None:
    log.error("%s %s", event, kw if kw else "")


def debug(event: str, **kw) -> None:
    log.debug("%s %s", event, kw if kw else "")


def exc(event: str, err: Exception, **kw) -> None:
    log.warning("%s %s: %s %s", event, type(err).__name__, err, kw if kw else "")
