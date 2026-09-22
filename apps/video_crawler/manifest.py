from platform_core.registry import AppManifest, NavEntry


def _gia(params: dict) -> int:
    return int(params.get("duration_s", 60) * 5)


MANIFEST = AppManifest(
    slug="video_crawler",
    display_name="Video Crawler",
    route_prefix="/video-crawler",
    summary="Crawl videos from multiple platforms",
    icon="🔍",
    nav=(NavEntry("Video Crawler", "/video-crawler", "🔍", "video_crawler"),),
    job_types=("video_crawler.search",),
    requires=("api",),
    credit_cost=_gia,
    table_prefix="video_crawler",
    capabilities=(),
    enabled=False,
    public=False,
    surface="customer",
)
