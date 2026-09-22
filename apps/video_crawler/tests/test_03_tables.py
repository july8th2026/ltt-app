def test_crawl_result_orm():
    from video_crawler.tables import CrawlResult
    
    assert CrawlResult.__tablename__ == "video_crawler_results"
