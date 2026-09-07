"""Màn Tạo tiếng nói: dựng trang, xem trước cách đọc, nộp job,
theo dõi kết quả."""
from __future__ import annotations

from ._chung import (MANIFEST, SO_LAN_THU_JOB, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, du_an, features,
                     gia, giong_mau, io, lan_ngon_ngu, nghe_thu,
                     require_login,
                     router, templates,
                     tham_chieu, tu_dien_rieng, user_hien_tai,
                     verify_csrf_token, vo,
                     NHAN_NGUON, so_viet)


# ── Tạo tiếng nói ────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def trang_tao(request: Request, giong: str = "", user=Depends(user_hien_tai),
              _=Depends(require_login)):
    """Màn tạo tiếng nói.

    `?giong=` cho phép màn Giọng gửi thẳng một lựa chọn sang đây — một cú bấm từ
    chỗ chọn tới chỗ dùng, thay vì bắt khách tự tìm lại cái tên vừa xem trong
    một ô chọn hai mươi mục.

    ⛔ Tham số này là **chuỗi khách gửi**, nên nó không được tin. Nó chỉ dùng để
       *chọn sẵn* một mục trong danh sách máy chủ đã dựng; giá trị không khớp
       mục nào thì bỏ qua, im lặng và an toàn. Quyền sở hữu vẫn kiểm ở cửa nộp
       (`features.giai_giong`) như cũ — chỗ này không phải một cửa.
    """
    from platform_core import job_history

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        # Bộ chọn giọng: giọng của khách + kho chung của nền tảng.
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid, gom_dung_chung=True)
        hang_doi = vo.dem_dang_chay(db, uid)
        # "Gần đây" chỉ ba dòng: nó là một lối quay lại, không phải màn Lịch sử
        # thu nhỏ. Nhiều hơn thì cột giữa dài ra và đẩy ô kịch bản lên trên.
        gan_day, _cur = job_history.list_owned(
            db, uid, app_slug=MANIFEST.slug, limit=3)

        # ── PHIÊN BẢN của MỘT văn bản ───────────────────────────────────────
        #
        # 🔴 Ảnh tham chiếu có `V3 / V2 / V1`, và chú thích cũ ở template bỏ nó
        #    với lý do *"phiên bản là khái niệm của KHỐI trong một dự án"*. Lý
        #    do ấy đúng cho **khối**, và nó không trả lời câu hỏi ở đây: một
        #    người đọc đi đọc lại CÙNG một câu để chọn bản ưng nhất thì ba lượt
        #    ấy có phải phiên bản của nhau không? Có — và đó chính là cảnh ảnh
        #    mẫu vẽ.
        #
        # ⭐ Nhóm theo **văn bản đã chuẩn hoá** (`result.text`), không theo văn
        #    bản thô: hai lượt chỉ khác nhau một dấu cách thừa là cùng một bài
        #    đọc, và người dùng coi chúng là hai lần thử của một thứ.
        #
        # ⛔ KHÔNG gom ba job bất kỳ rồi gắn nhãn V1/V2/V3 — đó đúng là thứ §22
        #    cấm. Không đủ hai lượt cùng văn bản thì danh sách RỖNG, và cột phải
        #    hiện trạng thái rỗng thật thà.
        #
        # ⚠️ Lấy trong một cửa sổ gần đây (không quét cả lịch sử): nhãn vì thế là
        #    "trong các lượt gần đây", và template nói đúng như vậy.
        _lich, _ = job_history.list_owned(
            db, uid, app_slug=MANIFEST.slug, limit=25)
        _xong = [j for j in _lich
                 if j.status == "done" and (j.result or {}).get("audio_key")]
        phien_ban = []
        nhan_pb = {}
        if _xong:
            _chuan = ((_xong[0].result or {}).get("text") or "").strip()
            if _chuan:
                cung = [j for j in _xong
                        if ((j.result or {}).get("text") or "").strip() == _chuan]
                if len(cung) > 1:
                    # `cung` mới nhất trước; nhãn V lớn nhất cho bản mới nhất.
                    n = len(cung)
                    phien_ban = [{"job": j, "nhan": f"V{n - i}"}
                                 for i, j in enumerate(cung)]
        # Bản đồ `job_id -> nhãn` để dòng `Gần đây` gắn chip mà không phải dò
        # lại. Dòng nào không thuộc nhóm nào thì KHÔNG có chip — chứ không gắn
        # bừa `V1` cho một lượt đứng một mình.
        nhan_pb = {pb["job"].id: pb["nhan"] for pb in phien_ban}
        # ⚠️ TÍNH Ở ĐÂY, không ở chỗ dựng template. `finally` ngay bên dưới
        #    đóng phiên CSDL, nên một lời gọi ORM đặt sau đó chạm vào một
        #    session đã đóng — và nó hỏng ở tận Jinja, một chỗ không ai nghĩ
        #    tới khi đọc lỗi. Danh sách dự án cho nút `Lưu vào dự án`.
        du_an_ds = [{"public_id": d.public_id, "ten": d.ten}
                    for d in du_an.danh_sach(db, uid)]
        # Đường nghe thử cho bộ chọn giọng. CÙNG thẩm quyền với màn Giọng
        # (`nghe_thu.duong_cho_trang`) — hai chỗ tự ghép URL là hai chỗ
        # sẽ lệch, và bài học đó đã trả giá ở `du_an.duong_tieng()`.
        duong_nghe = nghe_thu.duong_cho_trang(
            duong_audio=f"{MANIFEST.route_prefix}/audio", owner_id=uid,
            ma_mau=[g.ma for g in giong_mau.DANH_SACH],
            rieng=[g.public_id for g in cua_toi])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    xin = (giong or "").strip()
    hop_le = (giong_mau.hop_le(xin)
              or any(g.public_id == xin and g.trang_thai == "active"
                     for g in cua_toi))
    # ⚠️ BÍ DANH `_toc_do`, không phải `toc_do`. Hàm POST ở dưới có một
    #    THAM SỐ FORM tên `toc_do`, và một cái tên mang hai nghĩa trong
    #    cùng một tệp là đúng lớp bẫy đã từng ghi SAI một bút toán credit
    #    (`$So`/`$so` trong PowerShell, 31/08). Ở Python nó không nổ —
    #    nó chỉ chờ tới lần ai đó cần module trong hàm kia.
    from .. import toc_do as _toc_do

    return templates.TemplateResponse(
        request, "ltt_voice_studio.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_STUDIO, hang_doi=hang_doi,
                    giong=cua_toi, giong_mau=giong_mau.DANH_SACH,
                    nhan_gioi=giong_mau.NHAN_GIOI,
                    nhan_vung=giong_mau.NHAN_VUNG,
                    nhan_phong_cach=giong_mau.NHAN_PHONG_CACH,
                    # LÀN: nhãn hiển thị cho `ngon_ngu`. Truyền ở MỌI màn dựng
                    # `_voice_chon.html` — thiếu một chỗ thì Jinja ném
                    # `UndefinedError` ngay trên trang đó, và nó chỉ lộ ra khi
                    # ai đó mở đúng màn ấy.
                    nhan_lan=lan_ngon_ngu.NHAN_LAN,
                    giong_chon=(xin if hop_le else ""),
                    mac_dinh=giong_mau.MAC_DINH,
                    # Các nấc tốc độ lấy từ `toc_do.CAC_NAC` chứ không gõ lại
                    # trong template: một danh sách chép ra hai chỗ sẽ lệch, và
                    # chỗ lệch là chỗ giao diện mời một giá trị mà `hop_le` ép
                    # về giá trị khác — im lặng.
                    cac_nac_toc_do=_toc_do.CAC_NAC,
                    du_an_ds=du_an_ds,
                    duong_nghe=duong_nghe,
                    gan_day=gan_day,
                    phien_ban=phien_ban,
                    nhan_pb=nhan_pb))


@router.post("/xem-truoc")
def xem_truoc(request: Request, text: str = Form(""),
              csrf_token: str = Form(""), user=Depends(user_hien_tai),
              _=Depends(require_login)):
    """Văn bản này máy sẽ đọc thành gì, và tốn khoảng bao nhiêu.

    ⭐ VÌ SAO NÓ ĐÁNG CÓ MỘT ROUTE RIÊNG.

       `text_pipeline.chuan_hoa` quyết định **cả tiền lẫn âm thanh**:
       `manifest._gia()` đếm ký tự **sau** chuẩn hoá, nên số ký tự bị tính tiền
       không phải số ký tự khách gõ. Trước ô này khách không có cách nào thấy
       điều đó trước khi bấm — họ chỉ gặp nó dưới dạng một hoá đơn không giải
       thích được.

    ⚠️ ĐỘ LỚN CỦA CHÊNH LỆCH PHỤ THUỘC MỘT CỜ ĐANG TẮT — nói cho đúng, vì bản
       đầu của chú thích này nói quá và một phiên sau sẽ tin nó:

         hôm nay (`doc_so_tran=False`)  "15%"        -> "15 phần trăm"   (+9)
                                        "1.250.000"  -> "1250000"        (−2)
         khi cờ được bật               "1.250.000"  -> "một triệu hai trăm
                                                       năm mươi nghìn"  (+30)

       Tức hôm nay chênh lệch nhỏ và có thể âm; nó sẽ lớn khi `doc_so_tran` được
       bật. `text_pipeline` để nó tắt **có chủ ý**: chưa đo được `sea-g2p` có tự
       đọc số đúng chưa, và bật bừa thì có thể sinh ra đọc hai lần.
       ⇒ Ô này có giá trị ở **cả hai** trạng thái, vì nó hiện thứ máy **sẽ đọc**,
         không hiện một con số ước.

    ⛔ THUẦN TÍNH TOÁN. Không chạm CSDL, không chạm mạng, không chạm GPU, không
       giữ credit. Đó là điều kiện để nó gọi được ở mỗi lần khách tò mò mà không
       tốn gì — và nếu ngày nào đó nó cần một trong bốn thứ trên thì nó phải
       thôi là một "xem trước".
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from .. import text_pipeline
    from ..tham_so_cong_khai import TRAN_MOI_LUOT_SINH

    tho = (text or "").strip()
    if not tho:
        return JSONResponse({"ok": False, "loi": _t("Chưa có văn bản để đọc.")},
                            status_code=400)
    if len(tho) > TRAN_KY_TU_CONG_KHAI:
        return JSONResponse({"ok": False, "loi": _t(
            "Văn bản dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
        ).format(n=so_viet(len(tho)), t=so_viet(TRAN_KY_TU_CONG_KHAI))}, status_code=400)

    # 🔴 TỪ ĐIỂN RIÊNG PHẢI CÓ Ở ĐÂY, và thiếu nó biến bảng xem trước thành
    #    một lời nói dối.
    #
    #    Bảng "Máy sẽ đọc thành" tồn tại để khách thấy trước máy đọc ra sao
    #    **trước khi trả tiền**. Nếu worker áp từ điển mà xem trước thì không,
    #    hai bên cho hai kết quả khác nhau — và bên khách nhìn thấy là bên SAI.
    #
    # ⚠️ Đây đúng lớp lỗi "một cửa có, cửa kia không" mà `features.py` cảnh báo,
    #    và tôi vừa mắc nó ngay trong lượt thêm chính tính năng này: nối vào
    #    `jobs.py` rồi quên `xem_truoc`.
    gen = _db()
    db = next(gen)
    try:
        tu_rieng = tu_dien_rieng.nhu_dict(db, _uid(user))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    chuan = text_pipeline.chuan_bi(tho, tran_moi_doan=TRAN_MOI_LUOT_SINH,
                                   tu_dien_rieng=tu_rieng)
    da = chuan.da_chuan_hoa
    return JSONResponse({
        "ok": True,
        "da_chuan_hoa": da,
        "so_ky_tu_tho": len(tho),
        "so_ky_tu": len(da),
        "so_doan": len(chuan.doan),
        # Cùng một hàm mà `manifest.credit_cost` gọi — nên con số hiện ra ở đây
        # là con số sẽ bị tạm giữ, không phải một ước lượng thứ hai.
        "uoc_credit": gia.uoc_tran(so_ky_tu=len(da)),
        "doi_khac": da != tho,
    })


@router.get("/ket-qua/{job_id}")
def ket_qua(job_id: str, user=Depends(user_hien_tai), _=Depends(require_login)):
    """Trạng thái + kết quả của một lượt, dạng JSON, cho màn Studio poll.

    🔴 VÌ SAO KHÔNG DÙNG `/api/jobs/{id}` CỦA NỀN TẢNG.

       `job_history.customer_payload` cố tình **không** trả `result` lẫn `error`
       — nó là gói dùng chung cho mọi app, và `result` mỗi app một hình dạng.
       Studio thì cần đúng ba thứ trong đó: khoá tệp tiếng, thời lượng, credit.

    ⛔ Quyền đọc đi qua `job_history.get_owned`, tức lọc theo `user_id` **trong
       chính câu truy vấn**. Không tra job rồi so chủ ở bước sau: giữa hai bước
       đó có một khoảng trống mà một bản vá sau này rất dễ quên.

    ⚠️ Thông điệp lỗi lấy từ **sự kiện công khai**, không từ `job.error`.
       `job_events.public_message` là câu đã được duyệt để hiện cho chủ job;
       `job.error` là chuỗi thô của ngoại lệ và có thể mang chi tiết nội bộ.
    """
    from platform_core import job_history

    gen = _db()
    db = next(gen)
    try:
        job = job_history.get_owned(db, _uid(user), job_id)
        if job is None:
            return JSONResponse({"ok": False}, status_code=404)

        kq = (job.result or {}) if job.status == "done" else {}
        ra = {
            "ok": True,
            "trang_thai": job.status,
            "tien_do": max(0, min(100, int(job.progress or 0))),
            "audio_url": (f"{MANIFEST.route_prefix}/audio/{kq['audio_key']}"
                          if kq.get("audio_key") else ""),
            "giay": kq.get("duration_s"),
            "credit": kq.get("credit_cost"),
            "so_doan": kq.get("so_doan"),
        }
        if job.status == "error":
            from platform_core import job_events
            cau = [e.public_message for e in job_events.timeline(db, job.id)
                   if e.level == "error" and e.public_message]
            ra["loi"] = cau[-1] if cau else _t(
                "Không tạo được tiếng nói. Bạn có thể thử lại.")
        return JSONResponse(ra)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/tao")
def tao(request: Request, text: str = Form(""), voice_id: str = Form(""),
        preset: str = Form(""), toc_do: str = Form("1.0"),
        # `features.chuan_hoa` kep gia tri la ve "auto" — cua khong tu kiem,
        # vi Public API di THANG xuong job va khong qua day.
        ngon_ngu: str = Form("auto"),
        csrf_token: str = Form(""),
        user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from platform_core.job_submit import submit_with_credit

    # Nghiệp vụ ở `features`, kể cả phép kiểm "không được vừa voice_id vừa preset".
    try:
        # ⛔ KHÔNG kiểm `toc_do` ở đây. `features.chuan_hoa` ép nó về khoảng
        #    và biến giá trị vô nghĩa thành 1.0 — và phép kiểm ấy phải nằm ở
        #    `features` vì Public API đi THẲNG xuống job, không qua route này.
        yc = features.chuan_hoa({"text": text, "voice_id": voice_id,
                                 "preset": preset, "owner_id": _uid(user),
                                 "toc_do": toc_do, "ngon_ngu": ngon_ngu})
    except features.LoiGiongNoi as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

    if len(yc.text) > TRAN_KY_TU_CONG_KHAI:
        return JSONResponse({"ok": False, "loi": _t(
            "Văn bản dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
        ).format(n=so_viet(len(yc.text)), t=so_viet(TRAN_KY_TU_CONG_KHAI))}, status_code=400)

    tool = MANIFEST.tools[0]
    gen = _db()
    db = next(gen)
    try:
        # 🔴 KIỂM QUYỀN NGAY TẠI CỬA, trước khi giữ credit.
        #
        #    Phép kiểm này cũng chạy trong worker (`jobs.py` gọi `giai_giong`),
        #    và nó PHẢI ở lại đó — worker mới là cửa thật, vì Public API không
        #    đi qua route này. Nhưng chỉ có ở worker thì chưa đủ:
        #
        #    Đo thật 31/08/2026 trên production: tài khoản B gửi `voice_id` của
        #    tài khoản A và nhận **HTTP 200 kèm job_id**. Giọng không bị dùng —
        #    worker chặn đúng — nhưng job vẫn được giữ credit, vẫn xếp hàng, và
        #    bị thử lại **ba lần**. Khách chờ 31 giây để nghe một câu trả lời mà
        #    cửa vào đã biết ngay từ đầu.
        #
        #    Gọi `features.giai_giong` ở đây KHÔNG phá quy tắc "nghiệp vụ ở
        #    features": vẫn là features quyết định, route chỉ hỏi sớm hơn.
        try:
            features.giai_giong(db, yc)
        except features.LoiGiongNoi as e:
            db.rollback()
            return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

        job = submit_with_credit(
            db, user_id=_uid(user), app_slug=MANIFEST.slug,
            job_type="ltt_voice.synthesize",
            # 🔴 `nguon` GHI NGAY TỪ BÂY GIỜ, dù màn Lịch sử chưa dùng tới.
            #
            #    Ảnh tham chiếu 05 lọc lịch sử theo nguồn (Studio · Dự án · Lô ·
            #    API) — và đó là thứ **không thể bù lại sau**. Thêm cột lọc thì
            #    làm lúc nào cũng được; nhưng một job đã chạy mà không ghi nó
            #    đến từ đâu thì mãi mãi không biết. Ghi ở P1 tốn một dòng; ghi
            #    sau P6 tốn một dòng Y HỆT **cộng với** một khoảng lịch sử
            #    khuyết mà không lệnh nào vá được.
            params={"text": yc.text, "voice_id": yc.voice_id,
                    "preset": yc.preset, "owner_id": _uid(user),
                    "toc_do": yc.toc_do, "nguon": "studio"},
            # Một GPU = một việc, và cả ba cửa giành cùng một slot (Q114).
            admission_resource=tool.admission_resource,
            admission_slots=tool.admission_slots,
            # ⛔ 5 chứ không phải mặc định 3. Ba lần thử là một cửa sổ ~30 giây,
            #    còn riêng phần nạp model khi deploy đã đo 39,9–73,1 giây — nên
            #    mọi lượt đang bay lúc deploy đều chết. Xem `SO_LAN_THU_JOB`.
            max_attempts=SO_LAN_THU_JOB)
        db.commit()
        return JSONResponse({"ok": True, "job_id": str(job.id)})
    except Exception as e:  # noqa: BLE001 - thiếu credit cũng đi đường này
        db.rollback()
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass




# ── Từ điển phát âm riêng ────────────────────────────────────────────────────
#
# ⭐ Ở `_p_tao.py` chứ không phải một tệp riêng: nó là một điều khiển của màn
#    Tạo tiếng nói (ảnh 01 vẽ nó ở mục ⑤ `PRONUNCIATION`, ngay cột trái), và
#    `AGENTS.md` mục 8 nói route chia theo MÀN, không theo bảng.

@router.get("/tu-dien")
def xem_tu_dien(request: Request, user=Depends(user_hien_tai),
                _=Depends(require_login)):
    """Danh sách mục của khách. Dùng cho hộp từ điển ở màn Tạo tiếng nói."""
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        return JSONResponse({"ok": True, "muc": [
            {"id": m.id, "tu": m.tu, "thay": m.thay, "ghi_chu": m.ghi_chu}
            for m in tu_dien_rieng.danh_sach(db, uid)
        ], "tran": tu_dien_rieng.TRAN_SO_MUC})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/tu-dien/them")
def them_tu_dien(request: Request, tu: str = Form(""), thay: str = Form(""),
                 ghi_chu: str = Form(""), csrf_token: str = Form(""),
                 user=Depends(user_hien_tai), _=Depends(require_login)):
    """Thêm hoặc SỬA một mục.

    ⭐ Gõ lại cùng một từ = sửa cách đọc, không phải lỗi trùng. Bắt khách xoá
       rồi thêm lại là một bước thừa cho thao tác họ làm nhiều nhất.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        try:
            m = tu_dien_rieng.them(db, uid, tu=tu, thay=thay, ghi_chu=ghi_chu)
        except features.LoiGiongNoi as e:
            db.rollback()
            return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
        db.commit()
        return JSONResponse({"ok": True, "muc": {
            "id": m.id, "tu": m.tu, "thay": m.thay, "ghi_chu": m.ghi_chu}})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/tu-dien/{muc_id}/xoa")
def xoa_tu_dien(request: Request, muc_id: int, csrf_token: str = Form(""),
                user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        if not tu_dien_rieng.xoa(db, uid, muc_id):
            return JSONResponse({"ok": False}, status_code=404)
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
