"""
publisher_registry.py — Registry mapping platform names to Publisher classes.

Usage:
    from core.publisher_registry import get_publisher

    publisher = get_publisher(
        platform     = "facebook",   # or "tiktok"
        config       = config,
        stop_event   = stop_event,
        on_log       = on_log,
        on_status    = on_status,
        rate_limiter = rate_limiter,
    )
    result = publisher.publish(task)

New platforms are added by calling register() before get_publisher() is
invoked, or by extending _ensure_defaults_registered().
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from core.publisher import Publisher

# ── Internal registry ─────────────────────────────────────────────────────────
# Maps lower-case platform name → Publisher subclass (not instance)
_registry: dict[str, type] = {}


def register(platform: str, cls: type) -> None:
    """
    Register a Publisher subclass for the given platform name.

    Typically called once at import time by each platform module:
        from core.publisher_registry import register
        from core.tiktok.publisher_service import TikTokPublisher
        register("tiktok", TikTokPublisher)
    """
    _registry[platform.lower()] = cls


def get_publisher(
    platform: str,
    config: dict,
    stop_event: threading.Event,
    on_log: Optional[Callable] = None,
    on_status: Optional[Callable] = None,
    rate_limiter=None,
) -> Publisher:
    """
    Instantiate and return the Publisher for *platform*.

    Built-in platforms (facebook) are auto-registered on first call.
    Raises ValueError for unknown platforms.
    """
    _ensure_defaults_registered()

    key = (platform or "facebook").lower().strip()
    cls = _registry.get(key)
    if cls is None:
        supported = ", ".join(sorted(_registry.keys()))
        raise ValueError(
            f"Không tìm thấy publisher cho platform '{platform}'. "
            f"Hỗ trợ: {supported or '(chưa có platform nào được đăng ký)'}"
        )

    return cls(
        config       = config,
        stop_event   = stop_event,
        on_log       = on_log,
        on_status    = on_status,
        rate_limiter = rate_limiter,
    )


# ── Lazy default registration ──────────────────────────────────────────────────

def _ensure_defaults_registered() -> None:
    """
    Lazily register built-in publishers to avoid circular imports at module load.
    Called automatically by get_publisher().
    """
    if "facebook" not in _registry:
        from core.facebook.publisher_service import FacebookPublisher
        register("facebook", FacebookPublisher)

    # TikTok publisher — all tiktok_* post_types share one class.
    if "tiktok" not in _registry:
        from core.tiktok.publisher_service import TikTokPublisher
        register("tiktok",        TikTokPublisher)
        register("tiktok_draft",  TikTokPublisher)
        register("tiktok_direct", TikTokPublisher)
