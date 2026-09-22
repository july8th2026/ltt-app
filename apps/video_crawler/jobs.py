from platform_core import jobs as ltt_jobs
from platform_core.models import Job


def submit_job(db, user_id, job_type, params, dedupe_key=None):
    job = ltt_jobs.submit(
        db, user_id=user_id, app_slug="video_crawler",
        job_type=job_type, params=params, dedupe_key=dedupe_key
    )
    return job.id


def cancel_job(db, job_id):
    from sqlalchemy import select
    
    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if job:
        return ltt_jobs.cancel(db, job)
    return False
