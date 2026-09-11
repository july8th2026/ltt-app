"""Màn Dự án: danh sách · khối · sinh tiếng theo khối · xuất.

⛔ CHỈ LO HTTP. Nghiệp vụ ở `du_an.py`. Mọi handler ở đây làm đúng bốn việc:
   kiểm CSRF, tra dự án **kèm chủ sở hữu**, gọi `du_an.*`, dựng phản hồi.

🔴 KHÔNG CÓ LOẠI JOB MỚI. Sinh một khối là một `ltt_voice.synthesize` bình
   thường + `nguon="du_an"`. Xem lý do đầy đủ ở đầu `du_an.py`.
"""
from __future__ import annotations

from ._chung import (MANIFEST, SO_LAN_THU_JOB, TRAN_MOI_LUOT_SINH, Depends, Form,
                     HTMLResponse, JSONResponse, Request, _db, _het_phien,
                     _t, _uid, du_an, features, giong_mau, require_login,
                     router, templates, tham_chieu, user_hien_tai,
                     verify_csrf_token, vo, lan_ngon_ngu, nghe_thu,
                     so_viet)
from ._p_tao import _loi_400

#: Mã lỗi CỦA RIÊNG màn Dự án — không đụng `lan_ngon_ngu.MA_LOI` (những mã đó
#: chỉ được khai TRONG `lan_ngon_ngu.py`, `tests/test_522` chốt việc đó).
#: Lỗi lệch làn ném ra từ `_nop_mot_khoi` đã tự mang `ma_loi` riêng của nó
#: (`features.LoiGiongNoi.ma`, xem `_loi_400`) — bốn mã dưới đây chỉ cho
#: những cửa của CHÍNH tệp này không đi qua một exception có `.ma`.
MA_LOI_KHOI_RONG = "khoi_rong"
MA_LOI_KHOI_DANG_TAO = "khoi_dang_tao"
MA_LOI_VAN_BAN_QUA_DAI = "van_ban_qua_dai"
MA_LOI_LUOT_KHONG_CON_VAN_BAN = "luot_khong_con_van_ban"


def _mo_du_an(db, request, user, public_id: str):
    """Tra dự án theo `public_id` **và** chủ. Trả `None` nếu không phải của họ.

    ⛔ Một hàm, dùng ở mọi handler. Viết lại phép tra ở từng chỗ là mời một chỗ
       quên mất vế `owner_id` — và vế đó là toàn bộ phép kiểm quyền của màn này.
    """
    return du_an.tim(db, public_id, owner_id=_uid(user))


def _ngu_canh_giong(*, owner_id: str = "", **them) -> dict:
    """Bộ khoá mà `_voice_chon.html` cần. Ba màn dùng chung nên gom một chỗ.

    ⭐ `duong_nghe` TÍNH Ở ĐÂY chứ không để từng route tự gọi.

       Bộ chọn giọng xuất hiện ở ba màn của mảng này cộng màn Tạo tiếng nói.
       Bản đầu chỉ nối đường nghe thử cho màn Tạo — hệ quả là cùng một bộ chọn
       có nút nghe ở một màn và không có ở ba màn kia, không lỗi nào báo (partial
       `_voice_chon_nghe.html` tự im khi thiếu biến).

       Đó đúng là hình dạng lỗi mà `du_an.duong_tieng()` đã trả giá: nhiều chỗ
       tự dựng đường, và sửa cho đúng nghĩa là phải nhớ đủ mọi chỗ. Gom vào
       hàm dựng ngữ cảnh thì màn thứ năm sau này **được nối sẵn**.

    ⚠️ `nghe_thu.duong_cho_trang` chỉ hỏi KHO, không chạm CSDL — nên gọi được ở
       đây, sau khi phiên CSDL đã đóng.
    """
    d = {"giong_mau": giong_mau.DANH_SACH,
         "nhan_gioi": giong_mau.NHAN_GIOI,
         "nhan_vung": giong_mau.NHAN_VUNG,
         "nhan_phong_cach": giong_mau.NHAN_PHONG_CACH,
         # LÀN: nhãn cho `ngon_ngu`, xem chú thích ở `_p_tao.py`.
         "nhan_lan": lan_ngon_ngu.NHAN_LAN,
         "mac_dinh": giong_mau.MAC_DINH}
    d.update(them)
    d["duong_nghe"] = nghe_thu.duong_cho_trang(
        duong_audio=f"{MANIFEST.route_prefix}/audio", owner_id=owner_id,
        ma_mau=[g.ma for g in giong_mau.DANH_SACH],
        rieng=[g.public_id for g in (d.get("giong") or ())])
    return d


# ── Danh sách dự án ──────────────────────────────────────────────────────────

@router.get("/du-an", response_class=HTMLResponse)
def trang_du_an(request: Request, user=Depends(user_hien_tai),
                _=Depends(require_login)):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        ds = du_an.danh_sach(db, uid)
        # Đếm khối cho từng dự án trong MỘT vòng, không một truy vấn mỗi thẻ.
        #
        # 🔴 `duong_tieng` PHẢI ĐƯỢC TRUYỀN VÀO `tom_tat`, không thì huy hiệu
        #    lại đọc đúng cái cột trôi mà D005/SC-11 tồn tại để sửa: khối
        #    "xong" theo cột nhưng tệp đã mất (xoá ở Lịch sử, hết hạn 30 ngày)
        #    sẽ vẫn được `trang_thai_suy` tính là "xong" nếu thiếu bước này.
        dem = {}
        for d in ds:
            khoi = du_an.cac_khoi(db, d.id)
            duong = du_an.duong_tieng(db, khoi, MANIFEST.route_prefix)
            tt = du_an.tom_tat(khoi, duong_tieng=duong)
            tt["trang_thai"] = du_an.trang_thai_suy(tt)
            dem[d.public_id] = tt
        hang_doi = vo.dem_dang_chay(db, uid)
        # `gom_dung_chung=True`: DU AN la cua DUNG, nen kho giong chung
        # cua nen tang phai thay duoc — giong nhu `_p_tao` va `_p_giong`.
        # Thieu no thi o chon giong mac dinh VA o chon giong tung khoi
        # deu chi con 20 giong mau, va 25 giong kho chung bien mat khong
        # mot loi giai thich. Cua SUA (`_p_giong` ghi danh) thi van dong.
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid,
                                       gom_dung_chung=True)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_du_an.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_DU_AN, hang_doi=hang_doi,
                    **_ngu_canh_giong(owner_id=uid, du_an_ds=ds, dem=dem,
                                      giong=cua_toi,
                                      giong_chon="")))


@router.post("/du-an/tao")
def tao_du_an(request: Request, ten: str = Form(""), giong: str = Form(""),
              csrf_token: str = Form(""), user=Depends(user_hien_tai),
              _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = du_an.tao(db, owner_id=_uid(user), ten=ten, giong=giong)
        db.commit()
        return JSONResponse({"ok": True, "id": d.public_id})
    except du_an.LoiDuAn as e:
        db.rollback()
        return _loi_400(e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/{public_id}/xoa")
def xoa_du_an(request: Request, public_id: str, csrf_token: str = Form(""),
              user=Depends(user_hien_tai), _=Depends(require_login)):
    """Xoá một dự án và các khối của nó.

    ⭐ Xoá THẬT ở đây là đúng, khác `voice_profile` (chỉ tắt). Dự án là một tài
       liệu soạn thảo — nó không mang danh tính công khai nào và không bị lịch
       sử tính tiền trỏ tới. Các **job** đã sinh vẫn còn nguyên trong lịch sử
       cùng tệp tiếng của chúng; thứ mất đi chỉ là cách gom chúng lại.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    from sqlalchemy import delete

    from ..tables_du_an import VoiceBlock, VoiceProject
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        db.execute(delete(VoiceBlock).where(VoiceBlock.project_id == d.id))
        db.execute(delete(VoiceProject).where(VoiceProject.id == d.id))
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Một dự án ────────────────────────────────────────────────────────────────

@router.get("/du-an/{public_id}", response_class=HTMLResponse)
def trang_mot_du_an(request: Request, public_id: str,
                    user=Depends(user_hien_tai), _=Depends(require_login)):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            # 404 chứ không 403: phân biệt "không có" với "không phải của bạn"
            # là cho phép dò xem `public_id` nào có thật.
            return templates.TemplateResponse(
                request, "ltt_voice_thongbao.html",
                vo.ngu_canh(request, user, nav_key=vo.NAV_DU_AN,
                            man={"tieu_de": _t("Không tìm thấy dự án"),
                                 "mo_ta": _t("Dự án này không tồn tại, hoặc "
                                             "không thuộc tài khoản của bạn.")}),
                status_code=404)
        khoi = du_an.cac_khoi(db, d.id)
        duong = du_an.duong_tieng(db, khoi, MANIFEST.route_prefix)
        # `duong_tieng=duong`: cùng lý do ở `trang_du_an` — không truyền thì
        # `tt["khoi"]` (badge suy theo D005) suy theo `bool(audio_key)`, bỏ
        # sót ca tệp đã hết hạn/bị xoá dù khoá vẫn còn trên cột.
        tt = du_an.tom_tat(khoi, duong_tieng=duong)
        hang_doi = vo.dem_dang_chay(db, uid)
        # `gom_dung_chung=True`: DU AN la cua DUNG, nen kho giong chung
        # cua nen tang phai thay duoc — giong nhu `_p_tao` va `_p_giong`.
        # Thieu no thi o chon giong mac dinh VA o chon giong tung khoi
        # deu chi con 20 giong mau, va 25 giong kho chung bien mat khong
        # mot loi giai thich. Cua SUA (`_p_giong` ghi danh) thi van dong.
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid,
                                       gom_dung_chung=True)
        # Cột điều hướng bên trái. CHỈ tên + mã, không đếm khối: đếm khối
        # cho mọi dự án là một truy vấn cho mỗi dòng, để trang trí một cột điều
        # hướng. Trang danh sách đã có con số ấy và nó có chỗ ở đó.
        du_an_ds = [{"public_id": x.public_id, "ten": x.ten}
                    for x in du_an.danh_sach(db, uid)]
        # Bản sao phẳng cho template — tránh chạm ORM trong Jinja.
        #
        # 🔴 Fix round 1/5 — `"trang_thai"` PHẢI LÀ `trang_thai_hien()`, không
        #    phải cột thô. Trước bản vá này, một khối "xong" theo cột nhưng
        #    tệp đã hết hạn/bị xoá hiện badge XANH "Đã đọc" NGAY TRÊN dòng
        #    "Tệp tiếng đã hết hạn…" bên dưới nó — hai câu mâu thuẫn trên cùng
        #    một màn hình (INV-TRANG-THAI-1). `duong.get(k.id)` đã có sẵn ở
        #    đây (dùng cho `audio_url`) nên không tốn thêm một truy vấn nào.
        ds_khoi = [{
            "id": k.id, "thu_tu": k.thu_tu, "text": k.text, "giong": k.giong,
            "trang_thai": du_an.trang_thai_hien(k, bool(duong.get(k.id))),
            "job_id": k.job_id,
            "giay": k.giay, "credit": k.credit,
            "audio_url": duong.get(k.id, ""),
        } for k in khoi]
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_mot_du_an.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_DU_AN, hang_doi=hang_doi,
                    **_ngu_canh_giong(du_an=d, khoi=ds_khoi, tom_tat=tt,
                                      owner_id=uid, giong=cua_toi,
                                      du_an_ds=du_an_ds,
                                      giong_chon=d.giong_mac_dinh)))


@router.post("/du-an/{public_id}/sua")
def sua_du_an(request: Request, public_id: str, ten: str = Form(""),
              giong: str = Form(""), csrf_token: str = Form(""),
              user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        if ten.strip():
            d.ten = ten.strip()[:200]
        d.giong_mac_dinh = (giong or "")[:64]
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Khối ─────────────────────────────────────────────────────────────────────

@router.post("/du-an/{public_id}/khoi/them")
def them_khoi(request: Request, public_id: str, text: str = Form(""),
              sau: str = Form(""), csrf_token: str = Form(""),
              user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        try:
            vi_tri = float(sau) if sau.strip() else None
        except ValueError:
            vi_tri = None
        k = du_an.them_khoi(db, d, text=text, sau=vi_tri)
        db.commit()
        return JSONResponse({"ok": True, "id": k.id})
    except du_an.LoiDuAn as e:
        db.rollback()
        return _loi_400(e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/{public_id}/khoi/{block_id}/sua")
def sua_khoi(request: Request, public_id: str, block_id: int,
             text: str = Form(None), giong: str = Form(None),
             csrf_token: str = Form(""), user=Depends(user_hien_tai),
             _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        k = du_an.tim_khoi(db, d.id, block_id)
        if k is None:
            return JSONResponse({"ok": False}, status_code=404)
        # 🔴 `TRAN_MOI_LUOT_SINH`, KHÔNG phải `TRAN_KY_TU_CONG_KHAI`.
        #
        #    Một KHỐI là một lượt đọc — đúng một lượt `infer`. Nên trần của nó
        #    là trần CHẤT LƯỢNG của một lượt sinh, không phải trần của một yêu
        #    cầu khách gửi lên. Hai con số ấy đang bằng nhau, nên đổi chỗ này
        #    không đổi hành vi hôm nay.
        #
        # ⛔ Nhưng ngày trần yêu cầu được nới (tài liệu dài đi đường
        #    `ban_doc_dai`), một khối vẫn phải nằm trong một lượt sinh. Neo nhầm
        #    hằng số ở đây thì khối phình theo, và mỗi khối lại vượt đúng cái
        #    ngưỡng trôi giọng mà `tham_so.py` dựng trần lên để tránh — hỏng im
        #    lặng, chỉ nghe thấy chứ không đỏ ở đâu cả.
        #
        # ⭐ Cùng lớp lỗi `du_an.TRAN_KHOI_KHI_NHAP` đã ghi: 1.500 trả lời "một
        #    lượt đọc gánh được bao nhiêu", không trả lời "một đơn vị biên tập
        #    nên to bằng nào". Một hằng số đi lạc sang chỗ nó không thuộc về.
        if text is not None and len(text) > TRAN_MOI_LUOT_SINH:
            return JSONResponse({"ok": False, "loi": _t(
                "Khối dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
            ).format(n=so_viet(len(text)), t=so_viet(TRAN_MOI_LUOT_SINH)),
                                 "ma_loi": MA_LOI_VAN_BAN_QUA_DAI}, status_code=400)
        du_an.sua_khoi(db, k, text=text, giong=giong)
        db.commit()
        return JSONResponse({"ok": True, "trang_thai": k.trang_thai})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/{public_id}/khoi/{block_id}/xoa")
def xoa_khoi(request: Request, public_id: str, block_id: int,
             csrf_token: str = Form(""), user=Depends(user_hien_tai),
             _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        k = du_an.tim_khoi(db, d.id, block_id)
        if k is None:
            return JSONResponse({"ok": False}, status_code=404)
        db.delete(k)
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/{public_id}/nhap")
def nhap_van_ban(request: Request, public_id: str, text: str = Form(""),
                 csrf_token: str = Form(""), user=Depends(user_hien_tai),
                 _=Depends(require_login)):
    """Dán một kịch bản dài, cắt thành khối theo ranh giới câu."""
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        # Cùng lý do ở `sua_khoi` phía trên: cỡ một khối là cỡ một LƯỢT ĐỌC.
        so = du_an.nhap_van_ban(db, d, text,
                                tran_moi_khoi=TRAN_MOI_LUOT_SINH)
        db.commit()
        return JSONResponse({"ok": True, "so_khoi": so})
    except du_an.LoiDuAn as e:
        db.rollback()
        return _loi_400(e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Sinh tiếng ───────────────────────────────────────────────────────────────

def _nop_mot_khoi(db, user, du_an_row, khoi) -> str:
    """Nộp một job cho một khối. Trả `job_id`.

    ⛔ Kiểm quyền giọng **ngay tại cửa**, trước khi giữ credit — cùng lý do đã
       ghi ở `_p_tao.tao`: không kiểm thì job vẫn được giữ tiền, vẫn xếp hàng,
       và bị thử lại ba lần cho một câu trả lời cửa vào đã biết.

    🔴 `dedupe_key` — CHỐT THỨ HAI cho double-submit, KHÔNG THAY cho chốt thứ
       nhất. `doc_mot_khoi` đã chặn ở CỬA khi `khoi.trang_thai == "dang_tao"`
       (đọc TRƯỚC khi gọi hàm này), nhưng đó là một phép đọc-rồi-quyết: hai
       request chạm cửa đó gần như cùng lúc có thể CÙNG đọc thấy khối chưa
       `dang_tao` rồi cùng lọt qua. `dedupe_key` dựa trên `jobs.submit` —
       khoá theo (owner, khối) nên nó bắt được đúng khe hở đó, cùng khuôn
       T-06 đã áp cho Studio (`test_519`) và Lịch sử (`test_525`).
    """
    from platform_core.job_submit import dedupe_key_for, submit_with_credit

    uid = _uid(user)
    chon = khoi.giong or du_an_row.giong_mac_dinh
    voice_id, preset = du_an.tach_giong(chon)

    yc = features.chuan_hoa({"text": khoi.text, "voice_id": voice_id,
                             "preset": preset, "owner_id": uid})
    features.giai_giong(db, yc)

    tool = MANIFEST.tools[0]
    job = submit_with_credit(
        db, user_id=uid, app_slug=MANIFEST.slug,
        job_type="ltt_voice.synthesize",
        params={"text": yc.text, "voice_id": yc.voice_id, "preset": yc.preset,
                "owner_id": uid, "nguon": "du_an",
                # Hai khoá này để Lịch sử và hỗ trợ truy ngược được về đúng khối.
                "project_id": du_an_row.public_id, "block_id": khoi.id},
        dedupe_key=dedupe_key_for("ltt_voice.synthesize",
                                  {"owner": uid, "khoi": khoi.id}),
        admission_resource=tool.admission_resource,
        admission_slots=tool.admission_slots,
        max_attempts=SO_LAN_THU_JOB)
    khoi.job_id = str(job.id)
    khoi.trang_thai = "dang_tao"
    return str(job.id)


@router.post("/du-an/{public_id}/khoi/{block_id}/doc")
def doc_mot_khoi(request: Request, public_id: str, block_id: int,
                 csrf_token: str = Form(""), user=Depends(user_hien_tai),
                 _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        k = du_an.tim_khoi(db, d.id, block_id)
        if k is None:
            return JSONResponse({"ok": False}, status_code=404)
        if not (k.text or "").strip():
            return JSONResponse({"ok": False, "loi": _t(
                "Khối này chưa có văn bản."),
                                 "ma_loi": MA_LOI_KHOI_RONG}, status_code=400)
        # 🔴 T-06 — CHỐT THỨ NHẤT cho double-submit của khối này: đọc trạng
        #    thái NGAY TẠI CỬA, trước khi nộp job. `dedupe_key` trong
        #    `_nop_mot_khoi` là chốt thứ hai (đua giữa hai request gần như
        #    đồng thời) — xem chú thích ở đó. Không đợi worker: một khối
        #    đang `dang_tao` không cần thêm một job thứ hai chạy song song
        #    cho đúng một khối, kể cả khi job đầu rồi cũng bị dedupe gộp lại.
        if k.trang_thai == "dang_tao":
            return JSONResponse({"ok": False, "loi": _t(
                "Khối này đang được đọc — đợi lượt trước xong đã."),
                                 "ma_loi": MA_LOI_KHOI_DANG_TAO},
                                status_code=409)
        jid = _nop_mot_khoi(db, user, d, k)
        db.commit()
        return JSONResponse({"ok": True, "job_id": jid})
    except Exception as e:  # noqa: BLE001 - thieu credit cung di duong nay
        # `_loi_400` doc `getattr(e, "ma", "")` nen no dung chung duoc cho ca
        # `features.LoiGiongNoi` (mang `.ma`, vd "voice_language_mismatch")
        # lan moi Exception khac (thieu credit, ...) — tach rieng mot nhanh
        # `except features.LoiGiongNoi` truoc no la trung, hai than giong het.
        db.rollback()
        return _loi_400(e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/{public_id}/doc-tat-ca")
def doc_tat_ca(request: Request, public_id: str, csrf_token: str = Form(""),
               user=Depends(user_hien_tai), _=Depends(require_login)):
    """Sinh mọi khối còn thiếu.

    🔴 DỪNG Ở KHỐI ĐẦU TIÊN HỎNG, và trả về số đã nộp.

       Nếu khách hết credit ở khối thứ ba trong hai mươi, nộp tiếp mười bảy khối
       nữa chỉ để mỗi khối tự hỏng là mười bảy vòng xếp hàng vô ích — và mười
       bảy dòng lỗi giống hệt nhau che mất dòng đầu tiên, dòng duy nhất nói ra
       nguyên nhân.

    ⭐ Những khối đã nộp trước chỗ dừng **được giữ** (commit), không cuộn lại.
       Chúng là việc thật đã trả tiền và sẽ chạy xong bình thường.
    """
    gen = _db()
    db = next(gen)
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    try:
        d = _mo_du_an(db, request, user, public_id)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)

        can = du_an.khoi_can_tao(du_an.cac_khoi(db, d.id))
        if not can:
            return JSONResponse({"ok": True, "so_nop": 0, "het": True})

        da_nop, loi = 0, ""
        for k in can:
            try:
                _nop_mot_khoi(db, user, d, k)
                da_nop += 1
            except Exception as e:  # noqa: BLE001
                loi = str(e)
                break
        d.trang_thai = "dang_lam"
        db.commit()
        return JSONResponse({"ok": True, "so_nop": da_nop,
                             "con_lai": len(can) - da_nop, "loi": loi})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/du-an/{public_id}/trang-thai")
def trang_thai_du_an(public_id: str, user=Depends(user_hien_tai),
                     _=Depends(require_login)):
    """Trạng thái mọi khối, cho màn hình poll trong lúc sinh.

    ⭐ MỘT lời gọi cho cả dự án, không một lời gọi mỗi khối. Hai mươi khối đang
       chạy mà mỗi khối tự poll là hai mươi vòng mạng mỗi nhịp.
    """
    from platform_core import job_history

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        d = du_an.tim(db, public_id, owner_id=uid)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)

        khoi = du_an.cac_khoi(db, d.id)
        for k in khoi:
            if k.trang_thai == "dang_tao" and k.job_id:
                du_an.gan_ket_qua(db, k, job_history.get_owned(db, uid, k.job_id))
        db.commit()

        # `duong_tieng` TRƯỚC `tom_tat`: cùng lý do ở `trang_du_an`/
        # `trang_mot_du_an` — không truyền thì huy hiệu suy sai cho khối đã
        # mất tệp. Đây là cửa POLL nên nó chạy mỗi vài giây trong lúc sinh —
        # càng phải đúng, vì đây là chỗ giao diện cập nhật huy hiệu trực tiếp.
        duong = du_an.duong_tieng(db, khoi, MANIFEST.route_prefix)
        tt = du_an.tom_tat(khoi, duong_tieng=duong)
        tt["trang_thai"] = du_an.trang_thai_suy(tt)
        # Fix round 1/5 — cùng lý do ở `trang_mot_du_an`: đây là dữ liệu mà
        # `voice.js::motDuAn` dùng để cập nhật badge từng khối khi đang poll
        # (`datTrangThai(li, k.trang_thai)`), nên nó phải là giá trị ĐÃ SUY,
        # không phải cột thô — nếu không, trang mở sẵn sẽ tự SỬA badge đúng
        # rồi vài giây sau POLL lại GHI ĐÈ nó về sai.
        return JSONResponse({
            "ok": True,
            "tom_tat": tt,
            "khoi": [{
                "id": k.id,
                "trang_thai": du_an.trang_thai_hien(k, bool(duong.get(k.id))),
                "giay": k.giay, "credit": k.credit,
                "audio_url": duong.get(k.id, ""),
            } for k in khoi],
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/du-an/luu-tu-studio")
def luu_tu_studio(request: Request, job_id: str = Form(""),
                  du_an_id: str = Form(""), ten_moi: str = Form(""),
                  csrf_token: str = Form(""),
                  user=Depends(user_hien_tai), _=Depends(require_login)):
    """Lưu một lượt đọc ở Studio thành một khối trong Dự án.

    ## Vì sao nó tồn tại, và vì sao mãi tới giờ mới có

    Ảnh tham chiếu 01 vẽ nút `Save to Project` ở góc dưới bên phải. Chú thích
    trong `ltt_voice_studio.html` từng ghi lý do hoãn:

        · `Save to Project` — chưa có Dự án. Nút sẽ xuất hiện cùng P5, không
          sớm hơn.

    Dự án nay đã có. Đây là **một lời hứa đã đến hạn**, không phải một tính năng
    mới — nên nó không cần một quyết định nào, chỉ cần được làm.

    ## 🔴 KHÔNG SINH LẠI, VÀ KHÔNG THU TIỀN LẦN HAI

    Tiếng đã có rồi. `VoiceBlock` mang sẵn `job_id`/`audio_key`/`giay`/`credit`,
    và `du_an.gan_ket_qua` chép đúng bốn thứ đó từ job sang khối. Nên thao tác
    này là một phép **tham chiếu**, không phải một lượt sinh:

      · không nộp job mới        ⇒ không giữ credit, không quyết toán
      · không chạm GPU
      · khối vào thẳng trạng thái `xong`, nghe được ngay

    ⛔ Cám dỗ ở đây là gọi lại `submit_with_credit` cho gọn mã. Đừng — nó thu
       tiền lần thứ hai cho một tệp khách đã trả tiền và đang nghe.

    ## Quyền

    `job_history.get_owned` đã kiểm chủ sở hữu, nên một `job_id` của người khác
    trả `None` và ta dừng ở đó. Không phân biệt "không có" với "không phải của
    bạn" — phân biệt hai câu ấy là cho phép dò job nào có thật.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    from platform_core import job_history

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        job = job_history.get_owned(db, uid, (job_id or "").strip())
        if job is None or job.status != "done":
            return JSONResponse({"ok": False, "loi": _t(
                "Không tìm thấy lượt đọc này, hoặc nó chưa xong.")},
                status_code=404)

        kq = job.result or {}
        p = job.params or {}
        # Văn bản ĐÃ CHUẨN HOÁ là thứ máy thật sự đọc, và cũng là thứ khối cần
        # để đọc lại y hệt. `params["text"]` là bản khách gõ.
        van_ban = str(kq.get("text") or p.get("text") or "").strip()
        if not van_ban:
            return JSONResponse({"ok": False, "loi": _t(
                "Lượt đọc này không còn văn bản để lưu."),
                                 "ma_loi": MA_LOI_LUOT_KHONG_CON_VAN_BAN},
                                status_code=400)

        # Giọng: dựng lại chuỗi `v:`/`m:` mà khối dùng, từ params của job.
        giong = ""
        if p.get("voice_id"):
            giong = f"v:{p['voice_id']}"
        elif p.get("preset"):
            giong = f"m:{p['preset']}"

        d = None
        if du_an_id.strip():
            d = du_an.tim(db, du_an_id.strip(), owner_id=uid)
            if d is None:
                return JSONResponse({"ok": False, "loi": _t(
                    "Không tìm thấy dự án này.")}, status_code=404)
        else:
            ten = (ten_moi or "").strip() or _t("Dự án từ Studio")
            d = du_an.tao(db, owner_id=uid, ten=ten, giong=giong)

        try:
            khoi = du_an.them_khoi(db, d, text=van_ban, giong=giong)
        except du_an.LoiDuAn as e:
            db.rollback()
            return _loi_400(e)

        du_an.gan_ket_qua(db, khoi, job)
        db.commit()
        return JSONResponse({
            "ok": True, "du_an": d.public_id, "ten": d.ten,
            "duong": f"{MANIFEST.route_prefix}/du-an/{d.public_id}",
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/du-an/{public_id}/khoi/{block_id}/phien-ban")
def phien_ban_khoi(public_id: str, block_id: int,
                   user=Depends(user_hien_tai), _=Depends(require_login)):
    """Các lượt sinh đã xong của một khối — V1/V2/V3 trong ảnh 03.

    ⭐ Đọc từ lịch sử job, KHÔNG từ một bảng phiên bản. `tables_du_an.py` từ chối
       bảng ấy vì nó là nguồn chân lý thứ hai cho cùng một sự thật, và tệp này
       giữ nguyên quyết định đó. Xem `du_an.cac_phien_ban`.

    ⚠️ Đường nghe đi qua `du_an.duong_tieng`-style, tức cửa `/audio` đã kiểm sở
       hữu bằng hình dạng khoá. Không trả `audio_key` thô ra ngoài.
    """
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        d = du_an.tim(db, public_id, owner_id=uid)
        if d is None:
            return JSONResponse({"ok": False}, status_code=404)
        k = du_an.tim_khoi(db, d.id, block_id)
        if k is None:
            return JSONResponse({"ok": False}, status_code=404)

        cac = du_an.cac_phien_ban(db, uid, block_id,
                                  job_hien_tai=k.job_id or "")
        tien_to = f"{MANIFEST.route_prefix}/audio"
        return JSONResponse({
            "ok": True,
            # Đánh số NGƯỢC: lượt mới nhất là V lớn nhất, đúng như ảnh vẽ.
            "phien_ban": [{
                "ten": f"V{len(cac) - i}",
                "job_id": v["job_id"],
                "giay": round(v["giay"], 2),
                "credit": v["credit"],
                "audio_url": f"{tien_to}/{v['audio_key']}",
                "luc": v["luc"].isoformat() if v["luc"] else "",
                "dang_dung": v["job_id"] == (k.job_id or ""),
            } for i, v in enumerate(cac)],
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
