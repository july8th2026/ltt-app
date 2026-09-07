"""_p_tep.py — bề mặt HTTP để đính tài liệu vào hội thoại. (H44 B1)

    POST   /api/hoi-thoai/{conv_id}/tep            tai len, HIEN GIA, chua thu
    POST   /api/hoi-thoai/{conv_id}/tep/{up}/trich khach dong y -> giu credit
    GET    /api/hoi-thoai/{conv_id}/tep            danh sach
    DELETE /api/tep/{tep_id}                       go

⛔ Tệp này **chỉ lo HTTP**. Mọi quy tắc ở `services/dinh_tep.py` — hợp đồng app
   (`AGENTS.md` §8.1), và trần cứng 900 dòng/30 handler của
   `tools/lint_app_contract.py`.

## Vì sao TẢI LÊN và TRÍCH là hai route, không phải một

Gộp lại thì khách bấm một nút và bị trừ tiền cho một giá họ chưa thấy. P06 §7
chốt: *"giá phải nhỏ và phải hiện **trước** khi bấm"*. Hai route là cách duy
nhất để có một khoảnh khắc ở giữa cho họ đọc con số.

⭐ Giữa hai bước, vé ở trạng thái `ready`: byte đã lên `storage`, **chưa ai bị
   trừ gì**, và `upload_sessions.sweep()` tự dọn nếu khách bỏ đi.
"""
from __future__ import annotations

import logging

from fastapi import Depends, Request

from apps.chatltt.routes._chung import (cong_tep, json_ok, kiem_csrf, loi,
                                        router, uid)
from apps.chatltt.services import dinh_tep as DT
from server.auth.session import require_login
from server.deps import get_db

log = logging.getLogger(__name__)


@router.post("/api/hoi-thoai/{conv_id}/tep")
async def tai_len(conv_id: str, request: Request,
                  __=Depends(cong_tep), _=Depends(require_login), db=Depends(get_db)):
    """Tải một tài liệu lên và **hiện giá**. Chưa thu, chưa nộp job.

    ⚠️ `multipart/form-data`, không phải JSON base64 — cùng lý do đã ghi ở
       `_p_media.anh_vao_tai_len`: base64 phồng ~34 % và phải nằm trọn trong bộ
       nhớ cả hai phía trước khi kiểm được byte đầu tiên.

    ⚠️ CSRF qua header `X-CSRF-Token`: thân là tệp, không phải một dict đọc được.
    """
    if not kiem_csrf(request):
        return loi(403, "csrf")
    try:
        form = await request.form()
    except Exception as e:                                      # noqa: BLE001
        log.info("khong doc duoc form tep: %s", type(e).__name__)
        return loi(400, "tham_so", "khong doc duoc tep")
    tep = form.get("tep")
    if tep is None or not hasattr(tep, "read"):
        return loi(400, "tham_so", "thieu tep `tep`")
    du_lieu = await tep.read()
    try:
        kq = DT.nhan(db, user_id=uid(request), conversation_id=conv_id,
                     ten_tep=str(getattr(tep, "filename", "") or "tai-lieu"),
                     content_type=str(getattr(tep, "content_type", "") or ""),
                     du_lieu=du_lieu)
    except DT.LoiDinhTep as e:
        return loi(400, "tham_so", str(e))
    return json_ok(kq, 201)


@router.post("/api/hoi-thoai/{conv_id}/tep/{upload_id}/trich")
async def trich(conv_id: str, upload_id: str, request: Request,
                __=Depends(cong_tep), _=Depends(require_login), db=Depends(get_db)):
    """Khách đã đọc giá và bấm đồng ý ⇒ giữ credit, promote, gắn, nộp job."""
    if not kiem_csrf(request):
        return loi(403, "csrf")
    try:
        kq = DT.trich(db, user_id=uid(request), conversation_id=conv_id,
                      upload_id=upload_id)
    except DT.LoiDinhTep as e:
        return loi(400, "tham_so", str(e))
    except Exception as e:                                      # noqa: BLE001
        # ⛔ Bat rong CO CHU Y nhung KHONG nuot: giu credit co the hong vi so du,
        #    vi khoa, vi mot loi ta chua nghi toi — va khach phai doc duoc mot
        #    cau, khong phai mot trang 500.
        log.exception("trich tep hong: conv=%s up=%s", conv_id[:8], upload_id[:8])
        return loi(400, "khong_trich_duoc", f"{type(e).__name__}: {e}"[:200])
    return json_ok(kq, 202)


@router.get("/api/hoi-thoai/{conv_id}/tep")
async def danh_sach(conv_id: str, request: Request,
                    __=Depends(cong_tep), _=Depends(require_login), db=Depends(get_db)):
    try:
        return json_ok({"tep": DT.danh_sach(db, user_id=uid(request),
                                            conversation_id=conv_id)})
    except DT.LoiDinhTep as e:
        return loi(404, "khong_thay", str(e))


@router.delete("/api/tep/{tep_id}")
async def go(tep_id: str, request: Request,
             __=Depends(cong_tep), _=Depends(require_login), db=Depends(get_db)):
    """Gỡ một tệp: xoá liên kết **và** các đoạn đã trích.

    ⛔ Trả 404 cho cả "không có" lẫn "không phải của bạn" — phân biệt hai ca là
       tự khai rằng id ấy tồn tại. Cùng luật `kho_tep.mot`.
    """
    if not kiem_csrf(request):
        return loi(403, "csrf")
    if not DT.go(db, user_id=uid(request), tep_id=tep_id):
        return loi(404, "khong_thay", "khong tim thay tep")
    return json_ok({"da_go": True})
