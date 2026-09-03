"""
_p_media.py — tao anh/tieng trong hoi thoai, va cua DUY NHAT phuc vu tai san.

    POST /chatltt/api/bao-gia            {nang_luc, tham_so} -> {credit, …}
    POST /chatltt/api/hoi-thoai/{id}/tao {nang_luc, tham_so, credit}
    GET  /chatltt/api/luot/{id}/trang-thai   dong bo job -> snapshot
    GET  /chatltt/tai-san/{key:path}     anh/tieng, KIEM SO HUU
"""
from __future__ import annotations

import io
import logging

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse, StreamingResponse

from apps.chatltt.routes._chung import doc_json, json_ok, kiem_csrf, loi, router, uid
from apps.chatltt.services import chinh_sach
from apps.chatltt.services import hoi_thoai as H
from apps.chatltt.services import tao_media as TM
from server.auth.session import require_login
from server.deps import get_db

log = logging.getLogger("apps.chatltt.media")

#: Kieu MIME theo duoi tep. Bao sai kieu thi trinh duyet tu choi phat/ve, va
#: trieu chung la mot o trong im lang chu khong phai mot loi.
KIEU = {
    "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "webp": "image/webp", "wav": "audio/wav", "mp3": "audio/mpeg",
}


@router.post("/api/bao-gia")
async def bao_gia(request: Request, _=Depends(require_login), db=Depends(get_db)):
    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        return json_ok(TM.bao_gia(str(than.get("nang_luc") or ""),
                                  dict(than.get("tham_so") or {}),
                                  db=db, user_id=uid(request)))
    except chinh_sach.KhongDuocPhep as e:
        return loi(403, "khong_duoc_phep", str(e))
    except TM.ThamSoSai as e:
        return loi(400, "tham_so", str(e))


@router.post("/api/hoi-thoai/{conv_id}/tao")
async def tao(request: Request, conv_id: str, _=Depends(require_login), db=Depends(get_db)):
    from platform_core import credit

    than = await doc_json(request)
    if not kiem_csrf(request, than):
        return loi(403, "csrf")
    try:
        return json_ok(TM.tao(
            db, user_id=uid(request), conv_id=conv_id,
            ten=str(than.get("nang_luc") or ""),
            params=dict(than.get("tham_so") or {}),
            credit_da_bao=(int(than["credit"]) if than.get("credit") is not None else None),
        ), 202)
    except chinh_sach.KhongDuocPhep as e:
        return loi(403, "khong_duoc_phep", str(e))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")
    except TM.ThamSoSai as e:
        return loi(400, "tham_so", str(e))
    except credit.ThieuCreditError as e:
        db.rollback()
        return loi(402, "het_credit", str(e))


@router.get("/api/luot/{execution_id}/trang-thai")
def trang_thai(request: Request, execution_id: str,
               _=Depends(require_login), db=Depends(get_db)):
    """Nhip hoi cua client cho job (Q87). An toan goi nhieu lan."""
    try:
        return json_ok(TM.dong_bo(db, user_id=uid(request), execution_id=execution_id))
    except H.KhongTimThay:
        return loi(404, "khong_tim_thay")


@router.post("/api/anh-vao")
async def anh_vao_tai_len(request: Request, _=Depends(require_login)):
    """Tai mot anh len de gui cho model vision.

    ⛔ `multipart/form-data`, KHONG phai JSON base64. Mot anh 8 MB thanh ~10,7 MB
       khi base64 hoa, va no phai nam tron trong bo nho ca o phia trinh duyet lan
       phia may chu truoc khi kiem duoc byte dau tien. `multipart` cho ta doc
       stream va tu choi som.

    ⚠️ CSRF di qua header `X-CSRF-Token` chu khong qua than JSON: than o day la
       tep, khong phai mot dict ta doc duoc trong khi van con muon stream no.
       Van la `kiem_csrf` — MOT cua duy nhat cho ca app (`test_628` chot).
    """
    from apps.chatltt.services import anh_vao as AV

    if not kiem_csrf(request):
        return loi(403, "csrf")
    try:
        form = await request.form()
    except Exception as e:                                      # noqa: BLE001
        log.info("khong doc duoc form anh-vao: %s", type(e).__name__)
        return loi(400, "tham_so", "khong doc duoc tep")
    tep = form.get("anh")
    if tep is None or not hasattr(tep, "read"):
        return loi(400, "tham_so", "thieu tep `anh`")
    data = await tep.read()
    try:
        kq = AV.luu(data, str(getattr(tep, "content_type", "") or ""),
                    user_id=uid(request))
    except AV.LoiAnhVao as e:
        return loi(400, "tham_so", str(e))
    return json_ok(kq, 201)


@router.get("/tai-san/{key:path}")
def tai_san(request: Request, key: str, _=Depends(require_login)):
    """Anh/tieng cua CHINH nguoi dang dang nhap.

    ⛔ MOT cua duy nhat, va phep kiem so huu nam trong `tao_media` chu khong
       phai o day: mot ban chep thu hai cua phep kiem la ban se lech.

    ⚠️ Khoa khong hop le va khoa cua nguoi khac tra CUNG mot 404 — khac nhau se
       noi cho nguoi do biet khoa nao co that.
    """
    from platform_core import storage

    if not TM.kiem_so_huu_khoa(key, uid(request)):
        return loi(404, "khong_tim_thay")
    kho = storage.get_storage()
    thang = kho.try_url_for(key)
    if thang:
        # R2: chuyen thang toi CDN, khong keo byte qua may nay.
        return RedirectResponse(thang, status_code=302)
    try:
        with kho.open(key) as f:
            data = f.read()
    except Exception as e:                                      # noqa: BLE001
        # Khach van nhan 404 — khong noi cho ho biet la "co tep nhung doc hong".
        # Nhung ta thi PHAI biet: mot kho doc khong duoc la su co ha tang, con
        # mot khoa khong ton tai la chuyen thuong. Hai thu do trong y het nhau
        # tu phia khach, nen chi log moi phan biet duoc.
        log.info("khong doc duoc tai san %s: %s", key[:80], type(e).__name__)
        return loi(404, "khong_tim_thay")
    duoi = key.rsplit(".", 1)[-1].lower()
    return StreamingResponse(io.BytesIO(data),
                             media_type=KIEU.get(duoi, "application/octet-stream"),
                             headers={"Cache-Control": "private, max-age=3600"})
