"""Route TAI LEN NHIEU PHAN cua Auto Scan Video. Nghiep vu o `tai_len.py`.

Tach khoi `routes.py` vi tep do co tran 900 dong (`test_455`).

    POST /tai-len                     bat dau          -> mo ta + da_co=[]
    GET  /tai-len/{id}                trang thai       -> da_co (tiep tuc)
    POST /tai-len/{id}/phan/{so}/ve   ve cho mot phan  -> {url, method, headers}
    PUT  /tai-len/{id}/phan/{so}      nhan phan        (chi kho cuc bo)
    POST /tai-len/{id}/xong           ghep + confirm   -> dung `upload_id` o /tao
    POST /tai-len/{id}/huy            huy luot tai

🔑 Moi route: `_cong_co` TRUOC `require_login` (co tat -> 404), CSRF cho moi
   route ghi (form `csrf_token` hoac header `X-CSRF-Token` cho PUT tho), va chu
   so huu giai trong truy van (`tai_len._phien`).
"""
from __future__ import annotations

import tempfile

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from platform_core import upload_sessions
from platform_core.i18n import _ as _t
from platform_core.storage import get_storage
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai

from . import features, tai_len
from .routes import _cong_co

router = APIRouter()


def _nguoi(request: Request, csrf: str | None):
    if csrf is not None and not verify_csrf_token(request, csrf):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401)
    return u


def _ma_loi(exc: Exception) -> HTTPException:
    if isinstance(exc, features.KhongTimThay):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.post("/tai-len")
def bat_dau(request: Request, ten_tep: str = Form(...), kieu: str = Form(...),
            co: int = Form(...), csrf_token: str = Form(""),
            _g: None = Depends(_cong_co), user: str = Depends(require_login),
            db: Session = Depends(get_db)):
    u = _nguoi(request, csrf_token)
    try:
        ra = tai_len.bat_dau(db, get_storage(), owner_id=u.id, ten_tep=ten_tep,
                             kieu=kieu, co=co)
        db.commit()
    except (upload_sessions.UploadSessionError, features.AsvError) as exc:
        db.rollback()
        raise _ma_loi(exc) from exc
    return JSONResponse(ra)


@router.get("/tai-len/{upload_id}")
def trang_thai(request: Request, upload_id: str,
               _g: None = Depends(_cong_co), user: str = Depends(require_login),
               db: Session = Depends(get_db)):
    u = _nguoi(request, None)
    try:
        return JSONResponse(tai_len.trang_thai(db, get_storage(), owner_id=u.id,
                                               upload_id=upload_id))
    except features.AsvError as exc:
        raise _ma_loi(exc) from exc


@router.post("/tai-len/{upload_id}/phan/{so}/ve")
def ve_phan(request: Request, upload_id: str, so: int, md5: str = Form(...),
            csrf_token: str = Form(""),
            _g: None = Depends(_cong_co), user: str = Depends(require_login),
            db: Session = Depends(get_db)):
    u = _nguoi(request, csrf_token)
    try:
        ve = tai_len.ve_phan(db, get_storage(), owner_id=u.id,
                             upload_id=upload_id, so=so, md5_b64=md5)
        db.commit()
    except features.AsvError as exc:
        db.rollback()
        raise _ma_loi(exc) from exc
    if ve["url"] is None:
        # Kho cuc bo: phan di qua CHINH app. Co phan (16 MiB) xa duoi tran
        # 100 MB cua Cloudflare, nen duong nay cung chay qua tunnel.
        # ⛔ Token CSRF CHI di kem ve cuc bo — khong bao gio gui sang R2.
        ve["url"] = request.url_for("asv_nhan_phan", upload_id=upload_id,
                                    so=str(so)).path
        ve["headers"] = {"Content-MD5": md5, "X-CSRF-Token": csrf_token}
    return JSONResponse(ve)


@router.put("/tai-len/{upload_id}/phan/{so}", name="asv_nhan_phan")
async def nhan_phan(request: Request, upload_id: str, so: int,
                    _g: None = Depends(_cong_co), user: str = Depends(require_login),
                    db: Session = Depends(get_db)):
    u = _nguoi(request, request.headers.get("x-csrf-token", ""))
    md5 = request.headers.get("content-md5", "")
    # Doc than theo khoi, CO TRAN ngay trong vong doc — khong `await body()`.
    tran = tai_len.CO_PHAN
    with tempfile.SpooledTemporaryFile(max_size=1024 * 1024) as tam:
        da = 0
        async for khoi in request.stream():
            da += len(khoi)
            if da > tran:
                raise HTTPException(status_code=413,
                                    detail=_t('Phần lớn hơn kích thước cho phép.'))
            tam.write(khoi)
        tam.seek(0)
        try:
            tai_len.nhan_phan(db, get_storage(), owner_id=u.id,
                              upload_id=upload_id, so=so, md5_b64=md5, luong=tam)
            db.commit()
        except features.AsvError as exc:
            db.rollback()
            raise _ma_loi(exc) from exc
    return Response(status_code=204)


@router.post("/tai-len/{upload_id}/xong")
def xong(request: Request, upload_id: str, csrf_token: str = Form(""),
         _g: None = Depends(_cong_co), user: str = Depends(require_login),
         db: Session = Depends(get_db)):
    u = _nguoi(request, csrf_token)
    try:
        ra = tai_len.hoan_tat(db, get_storage(), owner_id=u.id,
                              upload_id=upload_id)
        db.commit()
    except features.AsvError as exc:
        db.rollback()
        raise _ma_loi(exc) from exc
    return JSONResponse(ra)


@router.post("/tai-len/{upload_id}/huy")
def huy(request: Request, upload_id: str, csrf_token: str = Form(""),
        _g: None = Depends(_cong_co), user: str = Depends(require_login),
        db: Session = Depends(get_db)):
    u = _nguoi(request, csrf_token)
    try:
        tai_len.huy(db, get_storage(), owner_id=u.id, upload_id=upload_id)
        db.commit()
    except features.AsvError as exc:
        db.rollback()
        raise _ma_loi(exc) from exc
    return Response(status_code=204)
