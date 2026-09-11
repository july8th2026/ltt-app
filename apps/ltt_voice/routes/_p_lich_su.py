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

    # Hạn lưu trữ nội dung — LẤY từ nguồn chân lý, không gõ tay: màn Lịch sử nói
    # với khách "bản ghi đã hết hạn sau bao nhiêu ngày", và con số ấy phải khớp
    # đúng hạn mà `job_content.purge_expired` thi hành. Gõ tay thì hai chỗ trôi.
    from platform_core import job_content
    duong_audio = f"{MANIFEST.route_prefix}/audio"
    return templates.TemplateResponse(
        request, "ltt_voice_lich_su.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_LICH_SU, hang_doi=hang_doi,
                    retention_ngay=job_content.RETENTION_DAYS,
                    dong=[doc_man_lich_su.dong_cho_trang(
                              j, duong_audio,
                              da_tai=goi["nd"].get(str(j.id), {}).get("da_tai", False),
                              da_xoa=goi["nd"].get(str(j.id), {}).get("da_xoa", False))
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
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

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

        # 🔴 KIỂM LẠI TRƯỚC KHI GIỮ CREDIT — và đây là cửa DỄ SÓT NHẤT, không
        #    phải cửa ít quan trọng nhất.
        #
        #    Ba cửa kia (`_p_tao`, `_p_du_an`, `_p_phat_dan`) đều gọi
        #    `features.giai_giong` trước khi tiêu tiền. Cửa này thì không, và
        #    nó **tái tạo đúng sự cố production 31/08/2026** mà ba cửa kia được
        #    sửa để tránh: *"job vẫn được giữ credit, vẫn xếp hàng, và bị thử
        #    lại — cho một câu trả lời mà cửa vào đã biết ngay từ đầu."*
        #
        # ⭐ Và nó là cửa **có nhiều khả năng mang tham chiếu ôi nhất**, theo
        #    đúng thiết kế: nó phát lại `params` CŨ. Giữa lần chạy đầu và lần
        #    bấm "đọc lại", ba thứ có thể đã đổi:
        #      · giọng nhân bản bị **tắt / thu hồi** (`trang_thai != active`);
        #      · làn ngôn ngữ được khai lại, biến một cặp từng hợp lệ thành
        #        lệch làn (Q121);
        #      · engine nâng cấp, một `preset` cũ không còn tồn tại.
        #
        #    Đo thật 2026-09-11 trên `studio_dev`, cùng một cặp văn-bản/giọng:
        #        POST /ltt-voice/tao            -> 400 voice_language_mismatch
        #        POST /ltt-voice/lich-su/…/doc-lai -> 200, job queued, so du 500 -> 499
        #
        # ⛔ KIỂM bằng `chuan_hoa`, nhưng vẫn NỘP `p` GỐC. Dựng lại params từ
        #    `YeuCau` sẽ đánh rơi mọi khoá mà `YeuCau` không biết (`nguon`,
        #    `project_id`, `block_id`, và khoá tiếp theo ai đó thêm) — đúng thứ
        #    docstring trên đã cảnh báo, chỉ theo chiều ngược lại. Hai việc
        #    khác nhau: `chuan_hoa` là **phép kiểm**, `p` là **tải trọng**.
        try:
            yc = features.chuan_hoa(p)
            features.giai_giong(db, yc)
        except features.LoiGiongNoi as e:
            db.rollback()
            return JSONResponse(
                {"ok": False, "loi": str(e),
                 "ma_loi": str(getattr(e, "ma", "") or "")}, status_code=400)

        tool = MANIFEST.tools[0]
        try:
            # 🔴 DEDUPE — chặn double-submit / F5 / hai tab bấm "Đọc lại" cùng
            #    một lượt trong khi bản đầu còn `queued`/`running`. Khoá KHÔNG
            #    hash `p` (params ĐẦY ĐỦ bên trên): hai lượt "đọc lại" job A
            #    trong hai lần bấm khác nhau phải cùng một khoá dù `p` mang
            #    những khoá `YeuCau` không biết (`project_id`…) — băm nguyên
            #    `p` thì một trường lạ thêm sau này âm thầm đổi khoá. Băm
            #    `(owner, job_id_gốc)` là đúng thứ cần: "đọc lại ĐÚNG lượt này".
            #    `jobs.submit` chỉ gộp job CHƯA kết thúc nên tính năng phiên bản
            #    (V1/V2/V3) không bị phá — đọc lại SAU khi job trước `done` vẫn
            #    ra job mới. Cùng khuôn `_p_tao.py` (test_502/test_519).
            #
            #    ⚠️ `str(cu.id)`, KHÔNG phải `job_id` thô từ path: `cu` đã đi
            #    qua `job_history.get_owned` (id đã được CSDL xác nhận và
            #    chuẩn hoá). `job_id` là chuỗi khách gõ trên URL — khoảng
            #    trắng/hoa-thường thừa (nếu route ever nới lỏng kiểm tra) sẽ
            #    băm ra một khoá KHÁC cho cùng một job, làm dedupe không gộp.
            # ⚠️ Tính khoá lặp TRƯỚC, ngoài lời gọi `submit_with_credit` —
            #    `str(cu.id)` lồng bên trong lời gọi làm mẫu quét của
            #    `test_501` (khớp một lớp ngoặc lồng) không khớp được, và cửa
            #    này biến mất khỏi tầm nhìn của nó.
            khoa_lap = dedupe_key_for(
                "ltt_voice.synthesize", {"owner": uid, "doc_lai": str(cu.id)})
            job = submit_with_credit(
                db, user_id=uid, app_slug=MANIFEST.slug,
                job_type="ltt_voice.synthesize", params=p,
                dedupe_key=khoa_lap,
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


@router.get("/lich-su/{job_id}/anh-huong")
def anh_huong(request: Request, job_id: str,
             user=Depends(user_hien_tai), _=Depends(require_login)):
    """Khối Dự án nào đang dùng audio của lượt này — TRƯỚC khi khách xoá (D005).

    ⭐ Đây là lý do hộp xác nhận XOÁ không hỏi ngay ở `voice.js`: một khách xoá
       một lượt Studio bình thường thì không mất gì ngoài chính tệp đó, nhưng
       nếu lượt ấy đã được "Lưu vào dự án" thì xoá nó cũng làm khối đó mất
       tiếng — và khách cần biết TRƯỚC khi bấm, không phải sau khi dự án đã vỡ.

    ⛔ Vẫn kiểm sở hữu: hỏi hậu quả của job người khác vẫn là một câu hỏi cần
       quyền, dù nội dung câu trả lời (tên dự án) không phải bí mật tài chính.
    """
    from platform_core import job_history

    from .. import lich_su_nd
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        cu = job_history.get_owned(db, uid, (job_id or "").strip())
        if cu is None or cu.app_slug != MANIFEST.slug:
            return JSONResponse({"ok": False, "loi": _t(
                "Không tìm thấy lượt đọc này.")}, status_code=404)
        khoi = lich_su_nd.khoi_bi_anh_huong(db, owner_id=uid, job_id=str(cu.id))
        return JSONResponse({"ok": True, "khoi": khoi})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/lich-su/{job_id}/da-tai")
def danh_dau_tai(request: Request, job_id: str, csrf_token: str = Form(""),
                 user=Depends(user_hien_tai), _=Depends(require_login)):
    """Đánh dấu một lượt là **đã tải**. Khách bấm liên kết tải thì giao diện gọi
    đây (bắn-rồi-quên) — tải vẫn chạy dù ghi dấu hỏng.

    ⭐ Tải là một sự thật về VÒNG ĐỜI, không phải một lần phát. Ghi ở CSDL (bền,
       theo tài khoản) để backend phân biệt được trạng thái, không ở localStorage.

    ⛔ Vẫn kiểm CSRF + sở hữu: một dấu vết ghi vào CSDL cho một job của người
       khác vẫn là một phép ghi cần quyền, dù nó vô hại về nội dung.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from platform_core import job_history

    from .. import lich_su_nd
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        cu = job_history.get_owned(db, uid, (job_id or "").strip())
        if cu is None or cu.app_slug != MANIFEST.slug:
            return JSONResponse({"ok": False, "loi": _t(
                "Không tìm thấy lượt đọc này.")}, status_code=404)
        lich_su_nd.danh_dau_tai(db, uid, str(cu.id))
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/lich-su/{job_id}/xoa")
def xoa_luot(request: Request, job_id: str, csrf_token: str = Form(""),
             user=Depends(user_hien_tai), _=Depends(require_login)):
    """Xoá một lượt khỏi Lịch sử — dọn TỆP sớm, giữ hàng làm bằng chứng.

    🔴 KHÁC HẲN hard-delete. Hàng `jobs` là bằng chứng mà sổ credit trỏ về
       (`credit_entries` khoá ngoài RESTRICT); xoá cứng nó là làm mồ côi một
       bút toán. Nên xoá ở đây = `job_content.expire_content` (xoá tệp, dọn
       `params`/`result`, đặt `content_expired_at`) + đánh dấu `da_xoa_luc` —
       và (T-11) thử dọn thêm khoá lưu trữ CŨ nếu job sinh trước 31/08/2026
       (xem `lich_su_nd._khoa_cu`). Dòng vẫn hiện trong lịch sử dưới trạng thái
       "Đã xoá", đối chiếu được.

    ⛔ CHỈ job đã KẾT THÚC. Một job đang chờ/đang chạy còn cần `params` để chạy;
       dọn giữa chừng là bẻ gãy worker. Cùng lý do `job_content.purge_expired`
       chỉ đụng job terminal.

    ⛔ Không hoàn tác được (tệp mất thật). Giao diện hỏi xác nhận — và liệt kê
       khối Dự án bị ảnh hưởng qua `/anh-huong` — trước khi gọi cửa này.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from platform_core import job_history
    from platform_core.storage import get_storage

    from .. import lich_su_nd
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        cu = job_history.get_owned(db, uid, (job_id or "").strip())
        if cu is None or cu.app_slug != MANIFEST.slug:
            return JSONResponse({"ok": False, "loi": _t(
                "Không tìm thấy lượt đọc này.")}, status_code=404)
        if cu.status not in lich_su_nd.TRANG_THAI_XOA_DUOC:
            return JSONResponse({"ok": False, "loi": _t(
                "Lượt đang xử lý chưa xoá được. Chờ nó xong hoặc huỷ trước.")},
                status_code=400)
        try:
            lich_su_nd.xoa(db, get_storage(), cu)
        except Exception as e:  # noqa: BLE001 - kho co the nem nhieu loai loi
            db.rollback()
            import logging
            logging.getLogger(__name__).warning(
                "khong xoa duoc luot %s: %s", job_id, e)
            return JSONResponse({"ok": False, "loi": _t(
                "Không xoá được lượt này. Thử lại sau.")}, status_code=500)
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
