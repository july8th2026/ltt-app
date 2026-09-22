def test_app_registered():
    from platform_core.registry import discover
    
    apps = list(discover())
    assert any(app.slug == "video_crawler" for app in apps)
    app = next(a for a in apps if a.slug == "video_crawler")
    assert app.manifest.requires == ("api",)
    assert app.manifest.table_prefix == "video_crawler"
