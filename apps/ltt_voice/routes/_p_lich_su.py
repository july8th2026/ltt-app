"""Màn Lịch sử: lọc và liệt kê các lượt đọc."""
from __future__ import annotations

from ._chung import (MANIFEST, SO_LAN_THU_JOB, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON)


# ── Lịch sử ──────────────────────────────────────────────────────────────────

@router.get("/lich-su", response_class=HTMLResponse)
def trang_lich_su(request: Request, tt: str = "", nguon: str = "",
                  giong: str = "", ngay: str = "",
                  user=Depends(user_hien_tai), _=Depends(require_login)):
    """Lịch sử tạo tiếng, lọc theo trạng thái · nguồn · giọng.

    ⛔ Ba tham số lọc là **chuỗi khách gửi**, nhưng chúng không chạm SQL: chúng
       chỉ đi vào một phép so bằng trong Python (`doc_man_lich_su.loc`). Giá trị
       lạ thì không khớp gì và trả danh sách rỗng — an toàn, và đúng nghĩa.
    """
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        # `ngay` là chuỗi khách gửi ⇒ ép về một trong các mốc đã biết. Một số
        # lạ không được thành một truy vấn lạ.
        try:
            _n = int(ngay or 0)
        except (TypeError, ValueError):
            _n = 0
        ngay_hop_le = _n if _n in doc_man_lich_su.CAC_MOC_NGAY else 0
        goi = doc_man_lich_su.doc(db, uid, MANIFEST.slug,
                                  trang_thai=tt, nguon=nguon, giong=giong,
                                  so_ngay=ngay_hop_le)
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
                    # Tên giọng engine dùng khi khách không chọn gì.
                    # Lấy từ ảnh chụp preset, KHÔNG gõ tay — gõ tay thì
                    # ngày engine đổi mặc định, lịch sử vẫn nói cái cũ.
                    giong_mac_dinh=giong_mau.MAC_DINH,
                    cac_moc_ngay=doc_man_lich_su.CAC_MOC_NGAY,
                    f_tt=tt, f_nguon=nguon, f_giong=giong,
                    f_ngay=ngay_hop_le))




@router.post("/lich-su/{job_id}/doc-lai")
def doc_lai(request: Request, job_id: str, csrf_token: str = Form(""),
            user=Depends(user_hien_tai), _=Depends(require_login)):
    """Đọc lại một lượt cũ — ảnh 05 vẽ biểu tượng này ở mỗi dòng.

    ## 🔴 NỘP MỘT JOB MỚI, VÀ THU TIỀN NHƯ MỘT LƯỢT MỚI

    Đây là chỗ khác hẳn `Lưu vào dự án`: lưu vào dự án chỉ **tham chiếu** tệp
    đã có nên tốn 0, còn đọc lại thì **chạy engine lần nữa** — GPU làm lại toàn
    bộ việc, nên nó phải trả tiền như một lượt bình thường.

    ⛔ Cám dỗ ngược lại cũng có thật: "khách đã trả cho câu này rồi". Nhưng tệp
       cũ vẫn còn và vẫn nghe được — họ bấm đọc lại là vì muốn một BẢN KHÁC
       (model tự hồi quy cho ra khác nhau mỗi lượt), tức một lượt sinh mới.

    ⭐ Chép nguyên `params` cũ chứ không dựng lại: một bản dựng lại sẽ bỏ sót
       tham số mới thêm (như `toc_do`), và bỏ sót IM LẶNG — khách bấm đọc lại
       rồi nghe một bản 1,0× trong khi bản cũ là 1,5×.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from platform_core import job_history
    from platform_core.job_submit import submit_with_credit

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        cu = job_history.get_owned(db, uid, (job_id or "").strip())
        if cu is None or cu.app_slug != MANIFEST.slug:
            return JSONResponse({"ok": False, "loi": _t(
                "Không tìm thấy lượt đọc này.")}, status_code=404)

        p = dict(cu.params or {})
        if not str(p.get("text") or "").strip():
            return JSONResponse({"ok": False, "loi": _t(
                "Lượt đọc này không còn văn bản để đọc lại.")}, status_code=400)
        # `nguon` giữ nguyên gốc (`studio`/`du_an`/`api`) chứ không đổi thành
        # một nguồn mới: bộ lọc nguồn ở màn này dùng để trả lời "lượt ấy đến từ
        # đâu", và một lượt đọc lại vẫn đến từ chỗ cũ.
        p["owner_id"] = uid

        tool = MANIFEST.tools[0]
        try:
            job = submit_with_credit(
                db, user_id=uid, app_slug=MANIFEST.slug,
                job_type="ltt_voice.synthesize", params=p,
                admission_resource=tool.admission_resource,
                admission_slots=tool.admission_slots,
                max_attempts=SO_LAN_THU_JOB)
        except Exception as e:  # noqa: BLE001
            db.rollback()
            # Thiếu credit là câu trả lời hay gặp nhất ở đây, và nó phải tới
            # được khách nguyên văn thay vì thành một lỗi 500 vô nghĩa.
            return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
        db.commit()
        return JSONResponse({"ok": True, "job_id": str(job.id)})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
