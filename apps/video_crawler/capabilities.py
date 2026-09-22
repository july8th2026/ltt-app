from dataclasses import dataclass
from typing import List


@dataclass
class Capability:
    id: str
    slug: str
    display_name: str
    requires: tuple[str, ...]
    login_required: bool
    login_type: str = "none"
    search: bool = True
    link: bool = True
    channel: bool = True
    preview: bool = True
    dedup: bool = True


PLATFORM_CAPABILITIES: List[Capability] = [
    Capability(
        id="video_crawler.douyin",
        slug="douyin",
        display_name="Douyin",
        requires=("browser",),
        login_required=True,
        login_type="qr_code",
    ),
    Capability(
        id="video_crawler.youtube",
        slug="youtube",
        display_name="YouTube",
        requires=("api",),
        login_required=False,
    ),
]
