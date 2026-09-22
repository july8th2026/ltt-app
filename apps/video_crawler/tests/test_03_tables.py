def test_crawl_result_orm():
    from apps.video_crawler.tables import CrawlResult
    
    assert CrawlResult.__tablename__ == "video_crawler_results"
