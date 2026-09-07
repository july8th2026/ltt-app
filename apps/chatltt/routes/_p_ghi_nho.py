"""_p_ghi_nho.py — bề mặt HTTP của kho ghi nhớ. (H44 B4 bước 4)

    GET    /api/ghi-nho            liet ke (loc theo pham vi neu khai)
    POST   /api/ghi-nho            them
    PATCH  /api/ghi-nho/{id}       sua noi dung
    DELETE /api/ghi-nho/{id}       xoa

⛔ Tệp này **chỉ lo HTTP**. Mọi quy tắc ở `services/ghi_nho.py` — hợp đồng app
   (`AGENTS.md` §8.1).

## Ở đây NGƯỜI DÙNG được nêu phạm vi, khác hẳn model

`ghi_nho.ghi_boi_model()` không nhận địa chỉ, và lý do là kẻ tấn công điều khiển
được đối số của model bằng nội dung một tệp đính kèm. Người dùng thì **là** chủ
thể quyền: họ nêu phạm vi qua thân request, và `services._kiem_so_huu` kiểm mục
tiêu ấy có phải của họ không.

⭐ Cùng một dữ liệu, hai đường vào, hai luật — và đó là điều đúng, không phải
   một bất nhất. Ranh giới không nằm ở *"tham số này có nguy hiểm không"* mà ở
   *"ai điều khiển được nó"*.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request

from apps.chatltt.routes._chung import (cong_ghi_nho, json_ok, kiem_csrf, loi,
                                        router, uid)
from apps.chatltt.services import ghi_nho as GN
from server.auth.session import require_login
from server.deps import get_db

log = logging.getLogger(__name__)


def _bay(mau) -> dict:
    """Một mẩu → JSON. **Không** trả `bam`: nó là khoá nội bộ, không phải dữ liệu."""
    return {"id": mau.id, "pham_vi": mau.pham_vi,
            "muc_tieu_id": mau.muc_tieu_id, "nguon": mau.nguon,
            "noi_dung": mau.noi_dung, "meta": mau.meta or {},
            "created_at": mau.created_at.isoformat() if mau.created_at else "",
            "updated_at": mau.updated_at.isoformat() if mau.updated_at else ""}


@router.get("/api/ghi-nho")
async def liet_ke(request: Request, pham_vi: str = "", muc_tieu_id: str = "",
                  __=Depends(cong_ghi_nho), _=Depends(require_login),
                  db=Depends(get_db)):
    """Ghi nhớ của người đang đăng nhập.

    ⭐ Trả kèm `da_dung`/`tran` để giao diện nói được *"còn bao nhiêu chỗ"*
       **trước** khi người dùng gõ xong một mẩu rồi mới bị từ chối.
    """
    user_id = uid(request)
    mau = GN.liet_ke(db, user_id=user_id,
                     pham_vi=pham_vi or None,
                     muc_tieu_id=muc_tieu_id if pham_vi else None)
    return json_ok({
        "ghi_nho": [_bay(m) for m in mau],
        "tran_moi_pham_vi": GN.TRAN_KY_TU_MOI_PHAM_VI,
        "tran_mot_ban": GN.TRAN_KY_TU_MOT_BAN,
    })


@router.post("/api/ghi-nho")
async def them(request: Request, __=Depends(cong_ghi_nho),
               _=Depends(require_login), db=Depends(get_db)):
    """Thêm một mẩu. Trùng ⇒ **201 với `trang_thai: "bo_qua"`**, không phải lỗi.

    ⛔ Trùng không phải một sự cố: người dùng dạy lại máy một điều nó đã biết là
       việc bình thường. Trả 4xx ở đây biến một thao tác vô hại thành một thông
       báo đỏ (hành vi `status='skipped'` của Open WebUI).
    """
    if not kiem_csrf(request):
        return loi(403, "csrf")
    try:
        than = await request.json()
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Bat rong nhung KHONG nuot: mot than hong co the la loi cua khach
        #    (JSON sai) hoac cua ta (proxy cat giua chung), va hai ca do trong
        #    y het nhau tu phia nguoi dung. Log kieu ngoai le la thu duy nhat
        #    phan biet duoc chung ve sau.
        log.info("than khong doc duoc: %s", type(e).__name__)
        return loi(400, "tham_so", "than khong phai JSON")
    if not isinstance(than, dict):
        return loi(400, "tham_so", "than phai la doi tuong JSON")

    try:
        mau, trang_thai = GN.them(
            db, user_id=uid(request),
            pham_vi=str(than.get("pham_vi") or GN.NGUOI_DUNG),
            muc_tieu_id=str(than.get("muc_tieu_id") or ""),
            noi_dung=str(than.get("noi_dung") or ""),
            nguon=GN.NGUOI)
    except GN.ThamSoSai as e:
        return loi(400, "tham_so", str(e))
    except GN.KhongDuocPhep:
        # 404, khong 403 — cung luat `kho_tep.mot`: phan biet hai ca la tu khai
        # rang id ay ton tai.
        return loi(404, "khong_thay", "khong tim thay muc tieu")
    except GN.KhoDay as e:
        # ⭐ 409, khong 400: than request HOP LE, chi la kho day. Hai ma khac
        #    nhau vi giao dien phai xu ly khac nhau — mot cai bao "sua lai di",
        #    cai kia bao "xoa bot di".
        return loi(409, "kho_day", str(e))
    return json_ok({"ghi_nho": _bay(mau), "trang_thai": trang_thai}, 201)


@router.patch("/api/ghi-nho/{ghi_nho_id}")
async def sua(ghi_nho_id: str, request: Request, __=Depends(cong_ghi_nho),
              _=Depends(require_login), db=Depends(get_db)):
    """Sửa nội dung. Người dùng sửa được **cả mẩu do model ghi** — đó là lời hứa."""
    if not kiem_csrf(request):
        return loi(403, "csrf")
    try:
        than = await request.json()
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Bat rong nhung KHONG nuot: mot than hong co the la loi cua khach
        #    (JSON sai) hoac cua ta (proxy cat giua chung), va hai ca do trong
        #    y het nhau tu phia nguoi dung. Log kieu ngoai le la thu duy nhat
        #    phan biet duoc chung ve sau.
        log.info("than khong doc duoc: %s", type(e).__name__)
        return loi(400, "tham_so", "than khong phai JSON")
    if not isinstance(than, dict):
        return loi(400, "tham_so", "than phai la doi tuong JSON")

    try:
        mau = GN.thay(db, user_id=uid(request), ghi_nho_id=ghi_nho_id,
                      noi_dung=str(than.get("noi_dung") or ""), boi=GN.NGUOI)
    except GN.ThamSoSai as e:
        return loi(400, "tham_so", str(e))
    except GN.KhongDuocPhep:
        return loi(404, "khong_thay", "khong tim thay mau ghi nho")
    except GN.KhoDay as e:
        return loi(409, "kho_day", str(e))
    return json_ok({"ghi_nho": _bay(mau)})


@router.delete("/api/ghi-nho/{ghi_nho_id}")
async def xoa(ghi_nho_id: str, request: Request, __=Depends(cong_ghi_nho),
              _=Depends(require_login), db=Depends(get_db)):
    if not kiem_csrf(request):
        return loi(403, "csrf")
    if not GN.quen(db, user_id=uid(request), ghi_nho_id=ghi_nho_id):
        return loi(404, "khong_thay", "khong tim thay mau ghi nho")
    return json_ok({"da_xoa": True})
