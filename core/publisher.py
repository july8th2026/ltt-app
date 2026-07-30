"""
publisher.py — Platform-agnostic Publisher interface.

Every platform (Facebook, TikTok, …) implements Publisher and returns a
PublishResult from publish().  Callers (SheetRunner) use this interface
exclusively — no platform-specific imports leak into the orchestrator.

Usage:
    from core.publisher import Publisher, PublishResult
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PublishResult:
    """Uniform result returned by every Publisher.publish() call."""

    success: bool
    # Platform-specific post / video identifier (e.g. FB video_id, TikTok publish_id)
    external_post_id: str = ""
    # Shareable URL to the published post
    external_post_url: str = ""
    # "published" | "draft" | "scheduled" | "error"
    status: str = "published"
    # Human-readable error description (only set when success=False)
    error_message: str = ""


class Publisher(ABC):
    """
    Abstract base for all platform publishers.

    Contract:
    - publish() MUST raise an exception on failure.
    - Do NOT catch exceptions inside publish() and return success=False.
    - The caller (SheetRunner._tick) owns retry / error-mark logic.
    """

    #: Lowercase platform identifier, e.g. "facebook", "tiktok"
    platform_name: str = ""

    @abstractmethod
    def publish(self, task: dict) -> PublishResult:
        """
        Upload and publish the task to the platform.

        Args:
            task: Dict with at minimum:
                  video_path, page/account identifier, title, description,
                  post_type, schedule, comment.

        Returns:
            PublishResult(success=True, external_post_url=..., external_post_id=...)

        Raises:
            Any exception on failure (InterruptedError, RuntimeError, …).
            The caller maps exceptions to retry or permanent-error handling.
        """
        ...
