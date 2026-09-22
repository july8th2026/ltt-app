import uuid

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import mapped_column

from platform_core.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class CrawlResult(Base):
    __tablename__ = "video_crawler_results"
    
    id = mapped_column(String(36), primary_key=True, default=_uuid)
    job_id = mapped_column(String(36), nullable=False)
    platform = mapped_column(String(100), nullable=False)
    url = mapped_column(String(1000), nullable=False)
    title = mapped_column(String(1000))
    duration_s = mapped_column(Integer)
    created_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
