from platform_core.models import Job
from sqlalchemy import select


def lay_runs(db, user_id):
    """Trả lại tất cả jobs video_crawler của user."""
    result = db.execute(
        select(Job).where(Job.app_slug == "video_crawler", Job.user_id == user_id)
    )
    return list(result.scalars().all())


def get_jobs(db, user_id, job_type=None):
    """Trả lại jobs video_crawler của user, có filter job_type."""
    query = select(Job).where(Job.app_slug == "video_crawler", Job.user_id == user_id)
    if job_type:
        query = query.where(Job.job_type == job_type)
    result = db.execute(query)
    return list(result.scalars().all())
