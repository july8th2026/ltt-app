"""Phục vụ tệp tiếng — cửa duy nhất đọc kho của khách."""
from __future__ import annotations

from platform_core import phat_media

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON)


def _giong_chung_dang_hop_le(public_id: str) -> bool:
    """`public_id` CÓ ĐANG là một giọng KHO CHUNG hợp lệ không — dùng làm cổng
    đọc cho `voice/chung/…` trong `audio()` (fix round 2/5, xem chú thích ở
    chỗ gọi).

    Điều kiện = ĐÚNG điều kiện của chính catalog kho chung
    (`tham_chieu._dieu_kien_kho_chung`: `dung_chung` + `license_status`) CỘNG
    `trang_thai == "active"` — một giọng đã tắt/thu hồi không còn đáng phục vụ
    bản demo của nó dù hai cột kia còn nguyên.

    ⭐ DÙNG LẠI `tham_chieu.tim_profile(..., cho_dung_chung=True)` — MỘT lượt
       SELECT theo index `public_id`, cùng hàm mà mọi cửa ĐỌC kho chung khác
       (`routes/_p_giong.py`, `routes/_p_tao.py`, …) đã đi qua, không phải một
       truy vấn mới viết riêng cho cửa này. `owner_id=""` vì ở đây không có
       khách nào để so — câu hỏi chỉ là "giọng này CÓ ĐANG công khai không".

    ⛔ KHÔNG NÉM. Một lỗi CSDL tạm thời ở đây phải đọc thành "không phục vụ
       được" (`False` → 404 ở nơi gọi), không phải 500 — cùng kỷ luật
       "không phát được thì nói KHÔNG PHÁT ĐƯỢC, không sập trang" xuyên suốt
       `nghe_thu.py`.
    """
    gen = _db()
    db = next(gen)
    try:
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id="",
                                       cho_dung_chung=True)
        return ho_so is not None and ho_so.trang_thai == "active"
    except Exception as e:  # noqa: BLE001 - xem docstring: khong nem
        import logging
        logging.getLogger(__name__).warning(
            "khong tra duoc giong kho chung %s: %s", public_id, e)
        return False
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Phục vụ tệp tiếng ────────────────────────────────────────────────────────

@router.get("/audio/{key:path}")
def audio(request: Request, key: str, mp3: int = 0,
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

       ⚠️ NGOẠI LỆ DUY NHẤT: `voice/chung/…` (fix round 2/5, xem khối chú
          thích ngay tại chỗ tính `la_nghe_thu_chung` bên dưới) — hình dạng
          khoá không đổi khi một giọng thu hồi/hạ license/tắt chia sẻ, nên chỉ
          hình dạng không đủ để giữ an toàn ở ĐÚNG tiền tố này.

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

    # ── NGHE THỬ KHO CHUNG — tiền tố thứ tư, và NGOẠI LỆ DUY NHẤT trong tệp
    #    này với luật "chỉ kiểm hình dạng khoá" ──────────────────────────────
    #
    # ⭐ Luật đọc GIỐNG `voice/mau/`, và vì đúng cùng một lý do: giọng kho chung
    #    thuộc **nền tảng**, mọi tài khoản đều được đọc nó (đó là định nghĩa của
    #    "kho chung" ở `tables.VoiceProfile.dung_chung`). Một câu chào cố định
    #    đọc bằng một giọng ta chào bán không có gì riêng tư.
    #
    # ⛔ NÓ KHÔNG THAY `la_nghe_thu_rieng`. Giọng nhân bản CỦA MỘT KHÁCH vẫn đi
    #    đường cũ, vẫn khoá theo chủ sở hữu — đó là giọng của một người thật.
    #    Hai loại giọng, hai luật, và gộp chúng lại là cách một giọng riêng lọt
    #    ra ngoài.
    #
    # ⚠️ Vẫn dưới `require_login`, cùng lý do với `voice/mau/`: không phải để
    #    giấu nội dung, mà để đường này không thành một CDN mở.
    #
    # 🔴 FIX ROUND 2/5 (Task 10, 2026-09-11, controller ruling) — TẠI SAO
    #    TIỀN TỐ NÀY PHẢI TRA CSDL, KHÁC MỌI TIỀN TỐ KHÁC Ở TRÊN.
    #
    #    Ba nguyên nhân ĐỘC LẬP có thể làm một giọng không còn xứng đáng ở kho
    #    chung nữa TRONG KHI tệp nghe thử của nó vẫn còn nguyên trong kho
    #    (`Storage` không có API liệt-kê-theo-tiền-tố để dọn — xem
    #    `giong_vong_doi.khoa_can_xoa`): thu hồi, đổi làn (cả hai đã xoá tệp
    #    TẠI NGUỒN ở fix round 1/5 — `giong_vong_doi.khoa_da_biet`,
    #    `nghe_thu.dung_lai_cho_giong`), và HẠ LICENSE qua
    #    `tools/soat_giong.py` (công cụ vận hành đó không chạm kho, và sẽ
    #    KHÔNG BAO GIỜ là công cụ cuối cùng từng chạm tới cột `license_status`
    #    — không có cách nào chắc MỌI công cụ tương lai đều nhớ dọn kho).
    #
    #    ⭐ Gác cổng tại ĐÂY — nơi DUY NHẤT phục vụ tệp — đóng CẢ BA đường
    #       (và mọi đường tương lai chưa ai viết) bằng MỘT chốt, thay vì phải
    #       nhớ dọn kho ở từng nơi ghi. Tệp cũ có thể còn sót lại trong kho
    #       (residue vô hại — không đường nào phục vụ nó nữa), nhưng không
    #       còn *đọc được*, và đọc được mới là thứ gây hại.
    #
    #    ⚠️ Cái giá là ĐÚNG MỘT truy vấn theo index `public_id`
    #       (`tham_chieu.tim_profile`, hàm ĐÃ CÓ — không viết truy vấn mới),
    #       và chỉ chạy khi khoá THẬT SỰ mang tiền tố này. Không đáng giữ
    #       nguyên tắc "không CSDL" bằng giá một giọng đã thu hồi/hạ license
    #       vẫn phát được cho bất kỳ ai đoán đúng khoá.
    #
    #    ⛔ 404 CHO CẢ "không tồn tại" LẪN "không còn hợp lệ" — CÙNG MỘT PHẢN
    #       HỒI (`_giong_chung_dang_hop_le` trả `bool`, không trả lý do). Một
    #       mã khác cho "có tồn tại nhưng hết hợp lệ" là để lộ trạng thái nội
    #       bộ (license, đã thu hồi…) cho bất kỳ ai đoán đúng khoá.
    la_nghe_thu_chung = False
    if key.startswith("voice/chung/") and ten_tep.endswith(".wav"):
        doan = key.split("/")
        # `nghe_thu.khoa_chung` luôn dựng ĐÚNG bốn đoạn:
        # `voice/chung/{public_id}/{PHIEN_BAN}.wav`. Sai hình dạng ⇒ từ chối
        # thẳng, không đoán `public_id` từ một chuỗi không đúng khuôn.
        if len(doan) == 4 and doan[2]:
            la_nghe_thu_chung = _giong_chung_dang_hop_le(doan[2])

    if not (la_ket_qua or la_clip_goc or la_nghe_thu_mau or la_nghe_thu_rieng
            or la_nghe_thu_chung):
        return Response(status_code=404)
    from platform_core.storage import get_storage
    kho = get_storage()
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
    #
    # ⚠️ Và đây là đường DUY NHẤT còn đọc toàn tệp vào RAM — có lý do: `ffmpeg`
    #    cần trọn vẹn byte, và đây là một lượt TẢI XUỐNG (`attachment`), không
    #    phải một lượt phát. Trình phát không bao giờ đi qua nhánh này.
    if mp3 and la_ket_qua:
        try:
            with kho.open(key) as f:
                data = f.read()
        except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
            import logging
            logging.getLogger(__name__).warning(
                "khong doc duoc audio %s: %s", key, e)
            return Response(status_code=404)
        chuyen = _sang_mp3(data)
        if chuyen is not None:
            return StreamingResponse(
                io.BytesIO(chuyen), media_type="audio/mpeg",
                headers={"Content-Disposition":
                         'attachment; filename="tieng.mp3"'})
        # Không chuyển được thì trả WAV — khách vẫn có tệp nghe được. Ném ở đây
        # là biến "thiếu một tiện nghi" thành "không tải được gì".

    # ── Phát: đi qua `platform_core.phat_media` ──────────────────────────────
    #
    # 🔴 Trước 2026-09-05 chỗ này là `StreamingResponse(io.BytesIO(f.read()))`:
    #    toàn tệp vào RAM, **không** `Accept-Ranges`, **không** `Content-Length`,
    #    không 206, không 416.
    #
    # ⭐ Safari/WebKit quyết định một nguồn âm thanh có tua được hay không từ
    #    chính lượt 200 đầu tiên. Không thấy `Accept-Ranges` thì nó kết luận máy
    #    chủ không hỗ trợ Range và **bỏ phát** — trong khi `<a download>` vẫn tải
    #    bình thường, vì tải xuống không cần tua. Đó chính xác là hình dạng lỗi
    #    người dùng báo: *"tải về được nhưng bấm Play trên điện thoại không chạy"*.
    #    (WebKit bug 211323, Starlette #950 — xem `docs/MOBILE/02_BASELINE.md`.)
    try:
        return phat_media.phat_tu_kho(
            kho, key, kieu_noi_dung=kieu,
            dai_range=request.headers.get("range"))
    except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
        # Khong co tep la 404, khong phai 500 — nhung PHAI ghi lai. Mot khoa dung
        # dinh dang ma doc khong duoc nghia la kho lech voi CSDL, va no bien mat
        # o dung cho kho tim nhat neu ta chi tra 404 roi im.
        import logging
        logging.getLogger(__name__).warning("khong doc duoc audio %s: %s", key, e)
        return Response(status_code=404)


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
