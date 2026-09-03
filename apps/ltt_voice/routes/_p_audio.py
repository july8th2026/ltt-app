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
def audio(key: str, mp3: int = 0,
          user=Depends(user_hien_tai), _=Depends(require_login)):
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

    # ── NGHE THỬ — tiền tố thứ ba, và nó có luật đọc RIÊNG ────────────────────
    #
    # ⭐ `voice/mau/…` KHÔNG mang `owner_id`, và đó là chủ ý chứ không phải sơ
    #    suất: giọng dựng sẵn không thuộc về ai. Hai mươi tệp ấy là **cùng một
    #    tệp cho mọi khách** — nhân bản chúng theo từng chủ sở hữu là nhân hai
    #    mươi lượt chiếm GPU lên bằng số người dùng, để bảo vệ một thứ không có
    #    gì riêng tư: một câu chào cố định đọc bằng một giọng đăng trong tài liệu.
    #
    # ⛔ Nhưng vẫn **đòi đăng nhập** (`require_login` ở chữ ký). Không phải để
    #    giấu nội dung, mà để đường này không thành một CDN mở cho người lạ.
    la_nghe_thu_mau = key.startswith("voice/mau/") and ten_tep.endswith(".wav")

    # Nghe thử giọng nhân bản thì NGƯỢC LẠI — nó là giọng của một người thật,
    # nên nó đi qua đúng phép kiểm sở hữu của clip gốc: cùng thư mục, và cửa mở
    # theo TÊN TỆP để `repr-*.npz` nằm cạnh đó không bao giờ lọt ra.
    la_nghe_thu_rieng = (key.startswith(f"voice/{uid}/")
                         and ten_tep.startswith("preview-"))

    if not (la_ket_qua or la_clip_goc or la_nghe_thu_mau or la_nghe_thu_rieng):
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

    # ── ?mp3=1 — xuất MP3 ────────────────────────────────────────────────────
    #
    # ⭐ CÙNG MỘT CỬA, không phải một route thứ hai. Phép kiểm sở hữu ở trên
    #    dựa vào **hình dạng khoá** và nó là thứ đang giữ an toàn cho cả đường
    #    này; một route riêng nghĩa là một bản chép thứ hai của phép kiểm ấy, và
    #    bản chép thứ hai là bản sẽ lệch.
    #
    # ⛔ CHỈ cho tệp KẾT QUẢ. Clip gốc của khách vốn đã là wav/mp3/m4a tuỳ họ
    #    tải lên; chuyển đổi nó không phục vụ ai và chỉ mở thêm một bề mặt.
    #
    # ⚠️ Chuyển ĐÚNG LÚC TẢI chứ không lưu sẵn bản thứ hai. Lưu sẵn nghĩa là mỗi
    #    lượt đọc chiếm gấp đôi kho, và bản MP3 ấy phải được `job_content.py`
    #    dọn theo — tức một thứ nữa để quên. Một lượt tải là hiếm; một lượt
    #    chuyển đổi mất dưới một giây.
    if mp3 and la_ket_qua:
        chuyen = _sang_mp3(data)
        if chuyen is not None:
            return StreamingResponse(
                io.BytesIO(chuyen), media_type="audio/mpeg",
                headers={"Content-Disposition":
                         'attachment; filename="tieng.mp3"'})
        # Không chuyển được thì trả WAV — khách vẫn có tệp nghe được. Ném ở đây
        # là biến "thiếu một tiện nghi" thành "không tải được gì".

    return StreamingResponse(io.BytesIO(data), media_type=kieu)


#: Chất lượng MP3. 192 kbps VBR cho giọng nói ở 48 kHz là dư — nhưng đây là tệp
#: khách mang đi dựng video, nên đừng tiết kiệm ở chỗ họ không sửa lại được.
_MP3_BITRATE = "192k"


def _sang_mp3(wav: bytes):
    """WAV -> MP3. Trả `None` nếu không chuyển được, KHÔNG ném.

    ⛔ Không ném vì nơi gọi có một đường lui tử tế (trả WAV). Biến một tiện nghi
       hỏng thành một lượt tải hỏng là đổi một phiền toái nhỏ lấy một lỗi thật.
    """
    import logging
    import os
    import subprocess
    import tempfile

    log = logging.getLogger(__name__)
    d_vao = d_ra = ""
    try:
        from platform_core.media import ffmpeg_bin

        f = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        d_vao = f.name
        f.write(wav)
        f.close()
        f2 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        d_ra = f2.name
        f2.close()

        kq = subprocess.run(
            [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error",
             "-i", d_vao, "-codec:a", "libmp3lame", "-b:a", _MP3_BITRATE,
             "-ac", "1", d_ra],
            capture_output=True, text=True, timeout=120)
        if kq.returncode != 0:
            raise RuntimeError((kq.stderr or "")[:300])
        with open(d_ra, "rb") as fh:
            ra = fh.read()
        return ra or None
    except Exception:  # noqa: BLE001
        log.warning("khong chuyen duoc sang mp3", exc_info=True)
        return None
    finally:
        for pth in (d_vao, d_ra):
            if pth:
                try:
                    os.unlink(pth)
                except OSError:
                    pass
