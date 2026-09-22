from fastapi import APIRouter, Request, Depends, Form
from server.auth.session import require_login


router = APIRouter(tags=["video_crawler"])


@router.get("")
def trang_chinh(request: Request, user: str = Depends(require_login)):
    return {"message": "Video Crawler home"}


@router.post("/jobs")
def tao_job(
    request: Request,
    user: str = Depends(require_login),
    platform: str = Form(...),
    query: str = Form(...),
    limit: int = Form(20)
):
    return {"message": "Job submitted"}
