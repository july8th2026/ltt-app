"""Màn API của Voice: mã giọng để dán vào mã nguồn, và trạng thái cửa thật.

⛔ MÀN NÀY KHÔNG PHẢI MỘT BẢN SAO CỦA `/developers`. Nó không có bảng giá, không
   có danh sách khoá, không có nhật ký — ba thứ đó khu Lập trình viên đã làm và
   làm cho **mọi** công cụ. Ở đây chỉ có thứ chỉ đúng với giọng nói: mã giọng
   của chính khách, tên giọng dựng sẵn hợp lệ, và trần ký tự cùng lý do của nó.

🔴 TRẠNG THÁI ĐỌC TỪ CẤU HÌNH ĐANG CHẠY, mỗi lần dựng trang. Xem đầu
   `doc_man_api.py` — hai lần trong dự án này một tài liệu đã nói sai về chính
   khu API, và cả hai lần đều sai về phía nguy hiểm.
"""
from __future__ import annotations

from ._chung import (TRAN_KY_TU_CONG_KHAI, Depends, HTMLResponse,
                     Request, giong_mau, require_login, router, templates,
                     user_hien_tai, vo, _db, _uid)


@router.get("/api", response_class=HTMLResponse)
def trang_api(request: Request, user=Depends(user_hien_tai),
              _=Depends(require_login)):
    from .. import doc_man_api

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        hang_doi = vo.dem_dang_chay(db, uid)
        ma_giong = doc_man_api.ma_giong_cua_toi(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    return templates.TemplateResponse(
        request, "ltt_voice_api.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_API, hang_doi=hang_doi,
                    trang_thai=doc_man_api.trang_thai_tool(),
                    ten_tool=doc_man_api.TEN_TOOL,
                    ma_giong=ma_giong,
                    giong_mau=giong_mau.DANH_SACH,
                    mac_dinh=giong_mau.MAC_DINH,
                    nhan_gioi=giong_mau.NHAN_GIOI,
                    nhan_vung=giong_mau.NHAN_VUNG,
                    vi_du=doc_man_api.vi_du_van_ban(),
                    tran_ky_tu=TRAN_KY_TU_CONG_KHAI))
