from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from server.auth.session import require_login

router = APIRouter(tags=["mediatools"])


@router.get("")
def media_tools(_identity: str = Depends(require_login)):
    return RedirectResponse("/agent/canvas", status_code=308)
