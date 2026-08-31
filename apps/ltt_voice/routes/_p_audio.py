"""Phục vụ tệp tiếng — cửa duy nhất đọc kho của khách."""
from __future__ import annotations

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON)


# ── Phục vụ tệp tiếng ────────────────────────────────────────────────────────

@router.get("/audio/{key:path}")
def audio(key: str, user=Depends(user_hien_tai), _=Depends(require_login)):
    """Phục vụ tệp tiếng. **Kiểm sở hữu bằng chính hình dạng khoá.**

    Khoá có dạng `voice/out/{owner_id}/{job_id}/tieng.wav`, nên chỉ chủ mới đọc
    được tệp của mình. Đoán một `job_id` khác cũng không ra vì phần `owner_id`
    không khớp.

    ⚠️ Dấu gạch chéo sau `{job_id}` là bắt buộc, và không phải vì route này —
       `platform_core/job_content.py` chỉ dọn được tệp có job id **là một đoạn
       đường dẫn**. Xem chú thích ở `jobs.py`.

    ⭐ HAI TIỀN TỐ, VÀ CHÚNG CÓ VÒNG ĐỜI KHÁC NHAU — đó là lý do có hai chứ không
       phải vì lịch sử để lại:

         `voice/out/{uid}/{job_id}/…`   tệp KẾT QUẢ. Có `job_id` trong khoá nên
                                        `job_content.py` dọn được, và điều khoản
                                        hứa xoá sau 30 ngày.
         `voice/{uid}/{public_id}/…`    clip GỐC của khách (`tham_chieu.khoa_nguon`).
                                        **Cố ý không** có `job_id`, nên nằm ngoài
                                        tầm dọn — điều khoản hứa giữ nguyên bản để
                                        dựng lại giọng khi nâng engine, nên nó phải
                                        sống theo vòng đời của HỒ SƠ GIỌNG, không
                                        theo hạn của tệp kết quả.

    ⛔ Vẫn kiểm bằng **hình dạng khoá**, không bằng một phép tra CSDL. Một phép
       kiểm rẻ và không thể quên là thứ đang giữ an toàn cho đường này; đổi nó
       thành một truy vấn là mời một nhánh nào đó sau này quên gọi.

    🔴 VÀ ĐÂY LÀ CHỖ PHẢI CẨN THẬN NHẤT CỦA CẢ TỆP.

       Bản đầu của việc mở clip gốc cho phép nguyên tiền tố `voice/{uid}/`. Nghe
       thì đúng — đó là thư mục của chính khách đó. Nhưng **biểu diễn engine
       cũng nằm trong đó**: `tham_chieu.khoa_bieu_dien` ghi
       `voice/{owner}/{public_id}/repr-<van_tay>.npz`, và tệp ấy chứa
       `speaker_emb`. `tables.py` nói thẳng về nó: *"KHÔNG BAO GIỜ ra ngoài.
       Khách không cần biết nó tồn tại."*

       Một khách tải embedding của **chính mình** thì chưa phải thảm hoạ, nhưng
       nó phá đúng ranh giới mà cả thiết kế bảng được dựng lên để giữ: `voice_id`
       là danh tính công khai, biểu diễn là thứ nội bộ có thể thay khi đổi engine.
       Cho nó rò ra một lần là biến nó thành thứ ai đó sẽ phụ thuộc vào.

       Nên cửa này mở theo **TÊN TỆP**, không theo thư mục: chỉ `source.*`.
    """
    uid = _uid(user)
    ten_tep = key.rsplit("/", 1)[-1]
    la_ket_qua = key.startswith(f"voice/out/{uid}/")
    la_clip_goc = (key.startswith(f"voice/{uid}/")
                   and ten_tep.startswith("source."))
    if not (la_ket_qua or la_clip_goc):
        return Response(status_code=404)
    from platform_core.storage import get_storage
    try:
        with get_storage().open(key) as f:
            data = f.read()
    except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
        # Khong co tep la 404, khong phai 500 — nhung PHAI ghi lai. Mot khoa dung
        # dinh dang ma doc khong duoc nghia la kho lech voi CSDL, va no bien mat
        # o dung cho kho tim nhat neu ta chi tra 404 roi im.
        import logging
        logging.getLogger(__name__).warning("khong doc duoc audio %s: %s", key, e)
        return Response(status_code=404)
    # Kieu noi dung theo DUOI TEP, khong gan cung `audio/wav`. Tep ket qua luon
    # la WAV, nhung clip GOC cua khach thi khong: `luu_nguon` nhan ca mp3 va m4a
    # (xem bang duoi o `tham_chieu.luu_nguon`). Bao sai kieu thi trinh duyet tu
    # choi phat, va trieu chung la mot trinh phat im lang chu khong phai mot loi.
    kieu = {"wav": "audio/wav", "mp3": "audio/mpeg", "m4a": "audio/mp4"}.get(
        ten_tep.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    return StreamingResponse(io.BytesIO(data), media_type=kieu)
