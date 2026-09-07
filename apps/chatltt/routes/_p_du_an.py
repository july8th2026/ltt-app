"""_p_du_an.py — bề mặt HTTP của dự án. (H44 B5 bước 5)

    GET    /api/du-an                     liet ke, gan dung nhat truoc
    POST   /api/du-an                     tao
    PATCH  /api/du-an/{id}                doi ten (can `revision`)
    DELETE /api/du-an/{id}                xoa — hoi thoai O LAI
    GET    /api/du-an/{id}/hoi-thoai      hoi thoai trong du an
    POST   /api/hoi-thoai/{conv}/du-an    gan / go (`du_an_id` rong = go)

⛔ Tệp này **chỉ lo HTTP**. Mọi quy tắc ở `services/du_an.py`.

## Một route cho CẢ gán lẫn gỡ, và đó là chủ đích

`POST /api/hoi-thoai/{conv}/du-an` với `du_an_id` rỗng nghĩa là **gỡ**. Hai
route riêng nghe sạch hơn, nhưng giao diện chỉ có **một** ô chọn dự án, và
"chọn — không thuộc dự án nào —" là cùng một thao tác với "chọn dự án khác".
Tách đôi ở tầng HTTP là bắt giao diện tự chọn động từ, rồi một ngày nó chọn sai.

## `PATCH` đòi `revision` — khoá lạc quan của lõi

`platform_core.app_projects.save` so `revision` trong `WHERE`. Hai tab sửa cùng
lúc thì tab thứ hai nhận **409**, không ghi đè im lặng. Đó là hành vi của lõi;
tệp này chỉ chuyển nó thành mã HTTP đúng.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request

from apps.chatltt.routes._chung import (cong_du_an, json_ok, kiem_csrf, loi,
                                        router, uid)
from apps.chatltt.services import du_an as DA
from platform_core import app_projects as AP
from server.auth.session import require_login
from server.deps import get_db

log = logging.getLogger(__name__)


def _bay(d) -> dict:
    """Một dự án → JSON. `payload` **không** ra ngoài: bản v1 rỗng, và một
    trường rỗng trên đường dây là một trường ai đó sẽ nhét thứ gì vào."""
    return {"id": d.id, "ten": d.name, "revision": int(d.revision),
            "created_at": d.created_at.isoformat() if d.created_at else "",
            "updated_at": d.updated_at.isoformat() if d.updated_at else ""}


async def _than(request: Request):
    try:
        t = await request.json()
    except Exception as e:                                      # noqa: BLE001
        log.info("than khong doc duoc: %s", type(e).__name__)
        return None
    return t if isinstance(t, dict) else None


@router.get("/api/du-an")
async def liet_ke(request: Request, __=Depends(cong_du_an),
                  _=Depends(require_login), db=Depends(get_db)):
    return json_ok({"du_an": [_bay(d) for d in
                              DA.liet_ke(db, user_id=uid(request))]})


@router.post("/api/du-an")
async def tao(request: Request, __=Depends(cong_du_an),
              _=Depends(require_login), db=Depends(get_db)):
    if not kiem_csrf(request):
        return loi(403, "csrf")
    than = await _than(request)
    if than is None:
        return loi(400, "tham_so", "than phai la doi tuong JSON")
    try:
        d = DA.tao(db, user_id=uid(request), ten=str(than.get("ten") or ""))
    except AP.ProjectError as e:
        return loi(400, "tham_so", str(e))
    return json_ok({"du_an": _bay(d)}, 201)


@router.patch("/api/du-an/{du_an_id}")
async def doi_ten(du_an_id: str, request: Request, __=Depends(cong_du_an),
                  _=Depends(require_login), db=Depends(get_db)):
    if not kiem_csrf(request):
        return loi(403, "csrf")
    than = await _than(request)
    if than is None:
        return loi(400, "tham_so", "than phai la doi tuong JSON")
    try:
        rev = int(than.get("revision"))
    except (TypeError, ValueError):
        # ⛔ Thieu `revision` KHONG duoc mac dinh thanh mot so: mot mac dinh o
        #    day la tat khoa lac quan di, va hai tab lai ghi de nhau im lang.
        return loi(400, "tham_so", "thieu `revision`")
    try:
        d = DA.doi_ten(db, user_id=uid(request), du_an_id=du_an_id,
                       ten=str(than.get("ten") or ""), revision=rev)
    except DA.KhongDuocPhep:
        return loi(404, "khong_thay", "khong tim thay du an")
    except AP.ProjectConflict as e:
        # 409: than HOP LE, chi la co nguoi sua truoc. Giao dien phai tai lai
        # roi hoi nguoi dung, khong phai bao "tham so sai".
        return loi(409, "xung_dot", str(e))
    except AP.ProjectError as e:
        return loi(400, "tham_so", str(e))
    return json_ok({"du_an": _bay(d)})


@router.delete("/api/du-an/{du_an_id}")
async def xoa(du_an_id: str, request: Request, __=Depends(cong_du_an),
              _=Depends(require_login), db=Depends(get_db)):
    """Xoá một dự án. **Hội thoại trong nó ở lại**, chỉ mất cái nhãn."""
    if not kiem_csrf(request):
        return loi(403, "csrf")
    if not DA.xoa(db, user_id=uid(request), du_an_id=du_an_id):
        return loi(404, "khong_thay", "khong tim thay du an")
    return json_ok({"da_xoa": True})


@router.get("/api/du-an/{du_an_id}/hoi-thoai")
async def hoi_thoai_cua(du_an_id: str, request: Request, __=Depends(cong_du_an),
                        _=Depends(require_login), db=Depends(get_db)):
    ds = DA.hoi_thoai_cua(db, user_id=uid(request), du_an_id=du_an_id)
    return json_ok({"hoi_thoai": [{"id": h.id, "title": h.title} for h in ds]})


@router.post("/api/hoi-thoai/{conv_id}/du-an")
async def gan(conv_id: str, request: Request, __=Depends(cong_du_an),
              _=Depends(require_login), db=Depends(get_db)):
    """Gán hội thoại vào một dự án. `du_an_id` rỗng ⇒ **gỡ** — xem docstring."""
    if not kiem_csrf(request):
        return loi(403, "csrf")
    than = await _than(request)
    if than is None:
        return loi(400, "tham_so", "than phai la doi tuong JSON")
    user_id = uid(request)
    da_id = str(than.get("du_an_id") or "").strip()
    ok = (DA.gan(db, user_id=user_id, conv_id=conv_id, du_an_id=da_id) if da_id
          else DA.go(db, user_id=user_id, conv_id=conv_id))
    if not ok:
        # 404 cho ca "khong co" lan "khong phai cua ban" — cung luat `kho_tep`.
        return loi(404, "khong_thay", "khong tim thay hoi thoai hoac du an")
    return json_ok({"du_an_id": da_id})
