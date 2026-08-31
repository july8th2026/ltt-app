"""Màn đã có tab nhưng CHƯA xây: API.

⭐ Danh sách này **co lại** mỗi khi một màn được xây thật — Dự án đã rời
   khỏi đây ở P5, Chạy lô ở P6. Một tệp giữ chỗ không co lại là một tệp sẽ
   giữ chỗ cho những màn đã tồn tại — và vì FastAPI khớp theo thứ tự đăng
   ký, một bản giữ chỗ còn sót sẽ **nuốt** đường thật nếu ai đó đổi thứ tự
   import ở `__init__.py`.
"""
from __future__ import annotations

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON)


# ── Màn chưa xây ─────────────────────────────────────────────────────────────
#
# ⭐ MỘT HANDLER CHO CẢ BA, không ba bản chép. Nội dung khác nhau là **dữ liệu**
#    (`vo.CHUA_XAY`), không phải mã — nên ngày một màn được xây thật, việc phải
#    làm là xoá một khoá trong từ điển và lật `built=True`, không phải đi tìm
#    xem còn bản chép nào sót lại.
#
# ⛔ Trang này KHÔNG vẽ giao diện giả. Nó nói sẽ có gì, không mô phỏng cái sẽ có.

def _trang_chua_xay(request: Request, user, nav_key: str):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        hang_doi = vo.dem_dang_chay(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_chua_xay.html",
        vo.ngu_canh(request, user, nav_key=nav_key, hang_doi=hang_doi,
                    man=vo.CHUA_XAY[nav_key]))


@router.get("/api", response_class=HTMLResponse)
def trang_api(request: Request, user=Depends(user_hien_tai),
              _=Depends(require_login)):
    return _trang_chua_xay(request, user, vo.NAV_API)


