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
                    nhan_nguon=NHAN_NGUON,
                    f_tt=tt, f_nguon=nguon, f_giong=giong))


