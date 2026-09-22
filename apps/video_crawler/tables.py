from platform_core.db import Base
from sqlalchemy.orm import mapped_column
from platform_core.models import DateTimeTZ, UUID
from sqlalchemy import String, Integer, func
import uuid


class CrawlResult(Base):
    __tablename__ = "video_crawler_results"
    
    id = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    job_id = mapped_column(UUID, nullable=False)
    platform = mapped_column(String(100), nullable=False)
    url = mapped_column(String(1000), nullable=False)
    title = mapped_column(String(1000))
    duration_s = mapped_column(Integer)
    created_at = mapped_column(DateTimeTZ, server_default=func.now())
