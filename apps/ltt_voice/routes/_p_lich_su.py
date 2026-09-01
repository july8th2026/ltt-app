"""Màn Lịch sử: lọc và liệt kê các lượt đọc."""
from __future__ import annotations

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON)


# ── Lịch sử ──────────────────────────────────────────────────────────────────

@router.get("/lich-su", response_class=HTMLResponse)
def trang_lich_su(request: Request, tt: str = "", nguon: str = "",
                  giong: str = "", user=Depends(user_hien_tai),
                  _=Depends(require_login)):
    """Lịch sử tạo tiếng, lọc theo trạng thái · nguồn · giọng.

    ⛔ Ba tham số lọc là **chuỗi khách gửi**, nhưng chúng không chạm SQL: chúng
       chỉ đi vào một phép so bằng trong Python (`doc_man_lich_su.loc`). Giá trị
       lạ thì không khớp gì và trả danh sách rỗng — an toàn, và đúng nghĩa.
    """
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        goi = doc_man_lich_su.doc(db, uid, MANIFEST.slug,
                                  trang_thai=tt, nguon=nguon, giong=giong)
        hang_doi = vo.dem_dang_chay(db, uid)
        # ── Mã giọng -> tên hiển thị ──────────────────────────────────────
        #
        # ⛔ Trước 01/09/2026 màn này in thẳng `vc_fceeabc694124a51921c7558a…`
        #    ra ba chỗ: ô lọc, dòng của mỗi lượt, và "Giọng dùng nhiều nhất".
        #    Không có bước tra tên nào cả — kể cả với giọng do CHÍNH khách đặt
        #    tên. Khách nhìn một chuỗi băm và không biết mình đã đọc bằng giọng
        #    nào, trong khi cái tên họ gõ đang nằm sẵn trong CSDL.
        #
        # ⭐ `gom_dung_chung=True` vì lịch sử có thể trỏ tới một giọng kho chung
        #    — cửa thi hành (`features.py`) cho phép dùng chúng, nên lịch sử
        #    chắc chắn có chúng.
        ten_giong = {g.public_id: g.ten_hien_thi
                     for g in tham_chieu.danh_sach(db, owner_id=uid,
                                                   gom_dung_chung=True)}
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    duong_audio = f"{MANIFEST.route_prefix}/audio"
    return templates.TemplateResponse(
        request, "ltt_voice_lich_su.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_LICH_SU, hang_doi=hang_doi,
                    dong=[doc_man_lich_su.dong_cho_trang(j, duong_audio)
                          for j in goi["dong"]],
                    tom_tat=goi["tom_tat"], bi_cat=goi["bi_cat"],
                    tran=goi["tran"],
                    giong_da_dung=goi["giong_da_dung"],
                    nguon_da_dung=goi["nguon_da_dung"],
                    nhan_nguon=NHAN_NGUON, ten_giong=ten_giong,
                    f_tt=tt, f_nguon=nguon, f_giong=giong))


