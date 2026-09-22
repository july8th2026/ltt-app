def test_capabilities_registered():
    from apps.video_crawler.capabilities import PLATFORM_CAPABILITIES
    
    assert len(PLATFORM_CAPABILITIES) == 2
    youtube_cap = next(c for c in PLATFORM_CAPABILITIES if c.slug == "youtube")
    assert youtube_cap.requires == ("api",)
    douyin_cap = next(c for c in PLATFORM_CAPABILITIES if c.slug == "douyin")
    assert douyin_cap.requires == ("browser",)
