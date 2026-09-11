"""Màn Giọng: lưới giọng, ghi danh giọng mới, tắt giọng."""
from __future__ import annotations

from ._chung import (MANIFEST, SO_LAN_THU_JOB, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON, lan_ngon_ngu, muc_dung, nghe_thu)
from .. import giong_vong_doi


def _loi_400_ma(loi: str, ma: str = "") -> JSONResponse:
    """Mirror TỐI GIẢN của `_loi_400` (`_p_tao.py:17`) — cùng khuôn phản hồi
    `{"ok": false, "loi": ..., "ma_loi": ...}`, nhưng nhận thẳng CÂU và MÃ thay
    vì một `LoiGiongNoi` (route này chưa có exception mang `.ma`).

    ⛔ Không import `_loi_400` từ `_p_tao.py`: nó nhận một *exception object* và
       đọc `getattr(e, "ma", "")`, còn ở đây `khai_lan_hop_le` đã trả thẳng một
       MÃ CHUỖI. Ép giá trị đó vào một exception giả chỉ để tái dùng một hàm
       nhận exception là đường vòng, không phải tái dùng."""
    return JSONResponse({"ok": False, "loi": loi, "ma_loi": ma}, status_code=400)


def _tra_loi_ngon_ngu(muon_json: bool, loi: str, ma: str, *,
                      that_bai: int = 400) -> Response:
    """Phản hồi lỗi của cửa `/ngon-ngu`: JSON khi khách xin JSON (fetch —
    `Accept: application/json`), 303 kèm câu lỗi khi đây là một `<form>` HTML
    thật (thẻ giọng, không JS) — theo đúng khuôn nội dung-thương lượng mà
    `dat_ngon_ngu_giong` (`65e099af`) đã dùng, và cùng hình dạng JSON với
    `_loi_400` (`_p_tao.py`)."""
    if muon_json:
        return JSONResponse({"ok": False, "loi": loi, "ma_loi": ma},
                            status_code=that_bai)
    from urllib.parse import quote

    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"{MANIFEST.route_prefix}/giong?loi={quote(loi)}",
                            status_code=303)


# ── Giọng của tôi ────────────────────────────────────────────────────────────

@router.get("/giong", response_class=HTMLResponse)
def trang_giong(request: Request, user=Depends(user_hien_tai),
                _=Depends(require_login)):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        # Kho chung của nền tảng hiện cùng lưới, sau giọng của chính khách.
        giong = tham_chieu.danh_sach(db, owner_id=uid, gom_dung_chung=True)
        hang_doi = vo.dem_dang_chay(db, uid)
        thong_ke = doc_man_giong.thong_ke_theo_giong(db, uid, MANIFEST.slug)
        chi_tiet = doc_man_giong.chi_tiet_cho_trang(
            db, giong, thong_ke, f"{MANIFEST.route_prefix}/audio")
        # Đường nghe thử — MỘT thẩm quyền, dùng chung với màn Tạo tiếng nói.
        # Giọng nào chưa có tệp thì **vắng mặt** khỏi dict, không phải rỗng.
        duong_nghe = nghe_thu.duong_cho_trang(
            duong_audio=f"{MANIFEST.route_prefix}/audio", owner_id=uid,
            ma_mau=[g.ma for g in giong_mau.DANH_SACH],
            rieng=[g.public_id for g in giong])
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    from ..dieu_khoan import CAM_KET, cac_dieu
    return templates.TemplateResponse(
        request, "ltt_voice_giong.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_GIONG, hang_doi=hang_doi,
                    giong=giong,
                    giong_mau=muc_dung.xep(giong_mau.DANH_SACH),  # U-12
                    nhan_gioi=giong_mau.NHAN_GIOI,
                    nhan_vung=giong_mau.NHAN_VUNG,
                    nhan_phong_cach=giong_mau.NHAN_PHONG_CACH,
                    # LÀN: nhãn hiển thị cho `ngon_ngu`. Truyền ở MỌI màn dựng
                    # `_voice_chon.html` — thiếu một chỗ thì Jinja ném
                    # `UndefinedError` ngay trên trang đó, và nó chỉ lộ ra khi
                    # ai đó mở đúng màn ấy.
                    nhan_lan=lan_ngon_ngu.NHAN_LAN,
                    thong_ke=thong_ke, chi_tiet=chi_tiet,
                    duong_nghe=duong_nghe,
                    dieu_khoan=cac_dieu(), cam_ket=CAM_KET))


@router.post("/giong/tao")
async def tao_giong(request: Request, ten: str = Form(""),
                    dong_y: str = Form(""), csrf_token: str = Form(""),
                    gioi: str = Form(""), ngon_ngu: str = Form(""),
                    tep: UploadFile = File(...),
                    user=Depends(user_hien_tai), _=Depends(require_login)):
    """Ghi danh một giọng mới. Consent lưu thành **dữ liệu**, không phải ghi chú.

    🔴 D003 (2026-09-11): `ngon_ngu` BẮT BUỘC, KHÔNG MẶC ĐỊNH `"vi"`.

       Trước RC1, ô trống rơi vào `"vi"` — nên mọi giọng nhân bản từ một clip
       tiếng Anh vẫn ghi `ngon_ngu="vi"`, một khẳng định KHÔNG hề khai. D003 bỏ
       lối lui đó: rỗng hay lạ ⇒ từ chối thẳng (`ma_loi="voice_language_required"`,
       xem `giong_vong_doi.khai_lan_hop_le`), TRƯỚC khi đọc tệp hay chạm CSDL —
       không job nào được nộp, không credit nào bị giữ cho một lượt sẽ bị từ
       chối. Xem `tests/test_521_ltt_voice_ghi_danh_ngon_ngu.py`.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)

    if not (ten or "").strip():
        return JSONResponse({"ok": False, "loi": _t("Hãy đặt tên cho giọng.")},
                            status_code=400)
    if dong_y != "1":
        # ⛔ Không có cam kết thì không ghi danh. Đây là cổng pháp lý, không phải
        #    một ô tick cho đẹp: nhân bản giọng chạm quyền nhân thân.
        return JSONResponse({"ok": False, "loi": _t(
            "Bạn cần xác nhận đây là giọng của chính bạn hoặc bạn được uỷ quyền."
        )}, status_code=400)

    # D003 — bắt khai làn TRƯỚC MỌI GHI DB/CREDIT. `lan_hien`/`nguon_hien` rỗng
    # vì đây là một hồ sơ CHƯA TỒN TẠI: không có làn hiện tại nào để so, nên
    # nhánh `voice_language_measured` của `khai_lan_hop_le` không thể trúng ở
    # đây — chỉ `voice_language_required` (rỗng/lạ) mới trúng.
    ma_loi_lan = giong_vong_doi.khai_lan_hop_le(ngon_ngu, lan_hien="", nguon_hien="")
    if ma_loi_lan:
        return _loi_400_ma(_t(
            "Hãy chọn ngôn ngữ của clip giọng: Tiếng Việt hoặc Tiếng Anh."
        ), ma_loi_lan)

    data = await tep.read()
    try:
        mo_ta = features.kiem_ghi_danh(data, tep.content_type or "")
    except features.LoiGiongNoi as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

    sha = features.hash_noi_dung(data)

    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    from sqlalchemy.exc import IntegrityError

    from ..dieu_khoan import PHIEN_BAN_DIEU_KHOAN
    from ..tables import VoiceConsent, VoiceProfile, VoiceRef

    gen = _db()
    db = next(gen)
    try:
        # ⛔ ÉP VỀ TẬP ĐÓNG, KHÔNG TIN Ô FORM. Một giá trị lạ ở `gioi` sẽ được
        #    `lui_giong.chon` đọc là "không rõ" và từ chối lùi — an toàn — nhưng
        #    nó vẫn lên thẻ giọng và vào bộ lọc, nơi nó thành một mặt lọc rác.
        _gioi = gioi.strip().lower()
        _gioi = _gioi if _gioi in ("nam", "nu") else ""
        # `ngon_ngu` đã qua `khai_lan_hop_le` phía trên nên chắc chắn hợp lệ —
        # `chuan_lan` ở đây chỉ chuẩn hoá hoa/thường, KHÔNG còn là một lối lui
        # về `"vi"` (xem docstring hàm này, D003).
        _lan = lan_ngon_ngu.chuan_lan(ngon_ngu)
        ho_so = VoiceProfile(owner_id=uid, ten_hien_thi=ten.strip(),
                             gioi=_gioi, ngon_ngu=_lan,
                             ngon_ngu_nguon=giong_vong_doi.NGUON_KHAI_BAO,
                             trang_thai="dang_ghi_danh")
        db.add(ho_so)
        # 🔴 FLUSH TRƯỚC KHI GHI KHO. `uq_voice_owner_ten` nổ ở ĐÂY khi khách đã
        #    có một giọng trùng tên, và bắt nó ở đây — trước `luu_nguon` — nghĩa
        #    là một tên trùng KHÔNG để lại một tệp mồ côi trong kho. Cho khách
        #    một câu sửa được, không phải một dòng lỗi CSDL thô (`0915f1f3`).
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            return JSONResponse({"ok": False, "loi": _t(
                "Bạn đã có một giọng tên này. Hãy đặt tên khác."
            )}, status_code=400)

        khoa = tham_chieu.luu_nguon(owner_id=uid, public_id=ho_so.public_id,
                                    data=data, mime=mo_ta["mime"])
        ref = VoiceRef(profile_id=ho_so.id, storage_key=khoa, sha256=sha,
                       mime=mo_ta["mime"], so_byte=len(data),
                       giay=float(mo_ta.get("giay") or 0.0))
        db.add(ref)
        db.add(VoiceConsent(
            profile_id=ho_so.id, owner_id=uid,
            phien_ban_dieu_khoan=PHIEN_BAN_DIEU_KHOAN, ref_sha256=sha,
            loai="tu_thu",
            ip=(request.client.host if request.client else "")[:64],
            user_agent=(request.headers.get("user-agent") or "")[:256]))
        db.flush()

        params = {"owner_id": uid, "voice_id": ho_so.public_id,
                  "source_key": khoa, "ref_id": ref.id,
                  "nguon": "giong",
                  "_job_type": "ltt_voice.enroll"}
        job = submit_with_credit(
            db, user_id=str(uid), app_slug=MANIFEST.slug,
            job_type="ltt_voice.enroll",
            params=params,
            # Chặn double-submit (F5 / hai tab) cùng khuôn với Studio (`test_519`):
            # cùng khách + cùng TÊN giọng trong lúc job trước còn chạy ⇒ MỘT job.
            dedupe_key=dedupe_key_for(
                "ltt_voice.enroll", {"owner": uid, "ten": ten.strip()}),
            max_attempts=SO_LAN_THU_JOB)
        db.commit()
        return JSONResponse({"ok": True, "voice_id": ho_so.public_id,
                             "job_id": str(job.id),
                             "canh_bao": list(mo_ta.get("canh_bao") or ())})
    except Exception as e:  # noqa: BLE001
        db.rollback()
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/giong/{public_id}/tat")
def tat_giong(request: Request, public_id: str, csrf_token: str = Form(""),
              user=Depends(user_hien_tai), _=Depends(require_login)):
    """Vô hiệu hoá. ⛔ KHÔNG xoá — xoá là làm mồ côi lịch sử đã tính tiền."""
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    gen = _db()
    db = next(gen)
    try:
        # ⛔ KHÔNG `cho_dung_chung` ở đây, và đó là cả ý nghĩa của cửa này.
        #    Giọng kho chung ai cũng DÙNG được nhưng không ai SỬA được; tìm
        #    theo chủ sở hữu là thứ giữ điều đó đúng. Nếu một ngày ai thêm
        #    `cho_dung_chung=True` cho tiện, khách đầu tiên bấm "Tắt giọng này"
        #    sẽ tắt nó cho toàn bộ nền tảng.
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id=_uid(user))
        if ho_so is None or not tham_chieu.chi_chu_so_huu(ho_so, _uid(user)):
            return JSONResponse({"ok": False, "loi": _t("Không tìm thấy giọng.")},
                                status_code=404)
        # 🔴 T-07: qua `co_the_chuyen`, KHÔNG gán thẳng nữa. `_CHUYEN` chỉ cho
        #    `active -> disabled` — một giọng `revoked` (đã xoá dữ liệu sinh
        #    trắc) hay `loi`/`dang_ghi_danh` (chưa từng có gì để "tắt") không
        #    còn đường này. Trước bản vá này gán thẳng sẽ ÂM THẦM đưa một
        #    giọng `revoked` "trở lại" `disabled` — trông như còn cứu được,
        #    trong khi dữ liệu đã xoá thật.
        if not giong_vong_doi.co_the_chuyen(ho_so.trang_thai,
                                            giong_vong_doi.TT_DISABLED):
            return JSONResponse({"ok": False, "loi": _t(
                "Giọng đang ở trạng thái không tắt được.")}, status_code=400)
        ho_so.trang_thai = giong_vong_doi.TT_DISABLED
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def _xoa_khoa(khoa: list) -> None:
    """Xoá best-effort các khoá kho. **Không bao giờ ném.**

    ⛔ Một khoá xoá không được (kho chập, tệp đã mất) không được làm hỏng một
       lượt thu hồi đã ghi vào CSDL. Nó được ghi lại để một vòng dọn về sau nhặt
       nốt — mất một tệp là một vết rác, không phải một lỗi cho khách.
    """
    import logging

    from platform_core.storage import get_storage
    st = get_storage()
    for k in dict.fromkeys(x for x in khoa if x):  # khử trùng, giữ thứ tự
        try:
            st.delete(k)
        except Exception:  # noqa: BLE001 - xem docstring
            logging.getLogger(__name__).warning(
                "khong xoa duoc khoa kho khi thu hoi: %s", k, exc_info=True)


def _thu_hoi_mot(db, ho_so) -> tuple:
    """Thu hồi MỘT hồ sơ đã xác nhận là của khách. Trả `(True, "")` nếu vừa
    thu hồi, `(False, "voice_state_invalid")` nếu trạng thái hiện tại không
    cho phép (INV-THU-HOI-1: chỉ qua `co_the_chuyen`, không có đường tắt).

    🔴 KHÔNG idempotent trên `revoked` — gọi lại một hồ sơ ĐÃ thu hồi trả về
       `(False, "voice_state_invalid")`, không phải `(True, "")` im lặng.
       `revoked` là điểm cuối (`_CHUYEN[TT_REVOKED] = set()`), và một cửa
       "thu hồi lần nữa" thành công không có ý nghĩa nghiệp vụ nào — nó chỉ
       có ý nghĩa khi trạng thái TRƯỚC ĐÓ thật sự cho phép đi tới `revoked`.

    ⭐ Đánh dấu `revoked` và COMMIT TRƯỚC, xoá tệp SAU. Trạng thái là thứ quyết
       định "còn dùng được không" (`features.giai_giong` chặn mọi thứ khác
       `active`), nên nó phải là thật ngay cả khi một lượt xoá tệp lỗi giữa
       chừng. Một tệp còn sót là rác dọn được; một giọng nói "đã thu hồi" mà
       vẫn dùng được thì không.
    """
    if not giong_vong_doi.co_the_chuyen(ho_so.trang_thai, giong_vong_doi.TT_REVOKED):
        return False, "voice_state_invalid"
    khoa = giong_vong_doi.khoa_da_biet(db, ho_so)
    # Chỉ để LOG — xem docstring `giong_vong_doi.khoa_can_xoa` cho vì sao
    # không xoá được thẳng bằng tiền tố này (thiếu API liệt kê ở storage.py).
    tien_to = giong_vong_doi.khoa_can_xoa(str(ho_so.owner_id), str(ho_so.public_id))
    ho_so.trang_thai = giong_vong_doi.TT_REVOKED
    db.commit()
    _xoa_khoa(khoa)
    import logging
    logging.getLogger(__name__).info(
        "thu hoi giong %s: xoa %d khoa da biet duoi tien to %s (co the con sot "
        "mot ban nghe thu PHIEN_BAN cu hon — khong liet ke duoc, xem "
        "giong_vong_doi.khoa_can_xoa)", ho_so.public_id, len(khoa), tien_to)
    return True, ""


def _tra_loi_xoa(muon_json: bool, loi: str, ma: str, *,
                 that_bai: int = 400) -> Response:
    """Cùng khuôn content-negotiation với `_tra_loi_ngon_ngu` ngay dưới đây:
    303 kèm câu lỗi cho một `<form>` HTML thật, JSON cho fetch có
    `Accept: application/json`. TÁCH RIÊNG (không tái dùng `_tra_loi_ngon_ngu`)
    vì tên hàm đó neo vào ngữ cảnh ngôn ngữ, còn cửa xoá không liên quan gì
    tới làn — dùng chung tên sẽ đọc sai ở một trong hai chỗ gọi."""
    if muon_json:
        return JSONResponse({"ok": False, "loi": loi, "ma_loi": ma},
                            status_code=that_bai)
    from urllib.parse import quote

    from fastapi.responses import RedirectResponse
    return RedirectResponse(f"{MANIFEST.route_prefix}/giong?loi={quote(loi)}",
                            status_code=303)


@router.post("/giong/{public_id}/xoa")
def xoa_giong(request: Request, public_id: str, csrf_token: str = Form(""),
              user=Depends(user_hien_tai), _=Depends(require_login)):
    """THU HỒI một giọng: xoá dữ liệu sinh trắc, GIỮ lịch sử đã tính tiền
    (T-07, T-14, INV-THU-HOI-1).

    🔴 KHÁC `tat` (`disabled`) Ở HAI ĐIỂM:
         · `disabled` đảo ngược được, mọi tệp còn nguyên (điều khoản hứa giữ clip
           gốc để dựng lại giọng khi nâng engine);
         · `xoa` (`revoked`) là **quyền được xoá** của khách — nó xoá mọi khoá
           kho TA BIẾT (clip nguồn, biểu diễn, bản nghe thử hiện hành — xem
           `giong_vong_doi.khoa_da_biet`), và KHÔNG đảo ngược được. Đó là chủ
           ý: dữ liệu sinh trắc thuộc về người, không thuộc về ta.

    ⛔ CÙNG PHÉP KIỂM SỞ HỮU với `tat`: tìm theo `owner_id`, KHÔNG mở kho chung.
       Một khách không được thu hồi giọng của người khác, và không được xoá một
       giọng kho chung của nền tảng.

    ⛔ Lịch sử lượt tạo và bút toán credit GIỮ NGUYÊN. Xoá cả hàng là làm mồ côi
       tiền đã thu — đúng lý do `tables.py` không có trạng thái `deleted`.

    ⭐ CONTENT-NEGOTIATION cùng khuôn `khai_ngon_ngu_giong` (`/ngon-ngu`): một
       `<form>` HTML thật (không JS) nhận 303 kèm `?loi=`; một lời gọi khai
       `Accept: application/json` nhận JSON. Mẫu template ở
       `ltt_voice_giong.html` gọi qua `fetch` với `Accept: application/json`
       tường minh — xem chú thích ở đó.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)
    muon_json = "application/json" in (request.headers.get("accept") or "")
    gen = _db()
    db = next(gen)
    try:
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id=uid)
        if ho_so is None or not tham_chieu.chi_chu_so_huu(ho_so, uid):
            # Một câu cho cả "không tồn tại" lẫn "không phải của bạn" — không để
            # cửa này thành máy dò `public_id` nào có thật.
            return JSONResponse({"ok": False, "loi": _t("Không tìm thấy giọng.")},
                                status_code=404)
        ok, ma_loi = _thu_hoi_mot(db, ho_so)
        if not ok:
            return _tra_loi_xoa(muon_json, _t(
                "Giọng đang ở trạng thái không thu hồi được."), ma_loi)
        if muon_json:
            return JSONResponse({"ok": True})
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{MANIFEST.route_prefix}/giong", status_code=303)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/giong/xoa-nhieu")
def xoa_nhieu_giong(request: Request, public_ids: str = Form(""),
                    csrf_token: str = Form(""),
                    user=Depends(user_hien_tai), _=Depends(require_login)):
    """Thu hồi HÀNG LOẠT. `public_ids` là danh sách ngăn bằng dấu phẩy.

    ⛔ MỖI GIỌNG QUA ĐÚNG PHÉP KIỂM SỞ HỮU + MÁY TRẠNG THÁI của cửa đơn
       (`_thu_hoi_mot`) — không có đường tắt nào cho lô. Một id không phải
       của khách, hay một id ở trạng thái không thu hồi được (`dang_ghi_danh`,
       hoặc đã `revoked` từ trước), chỉ bị **bỏ qua**: không báo lỗi cho cả lô,
       và không tiết lộ "không phải của bạn" khác gì "trạng thái không hợp lệ".

    Trả tóm tắt JSON: `da_thu_hoi` (id đã thu hồi xong) và `bo_qua` (mọi id
    còn lại — không phân biệt lý do, cùng lý do ẩn danh ở trên).
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)
    ids = [x.strip() for x in (public_ids or "").split(",") if x.strip()]
    gen = _db()
    db = next(gen)
    da_thu_hoi: list = []
    bo_qua: list = []
    try:
        for pid in ids:
            ho_so = tham_chieu.tim_profile(db, pid, owner_id=uid)
            if ho_so is None or not tham_chieu.chi_chu_so_huu(ho_so, uid):
                bo_qua.append(pid)
                continue
            ok, _ma = _thu_hoi_mot(db, ho_so)
            (da_thu_hoi if ok else bo_qua).append(pid)
        return JSONResponse({"ok": True, "da_thu_hoi": da_thu_hoi,
                             "bo_qua": bo_qua})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/giong/{public_id}/ngon-ngu")
def khai_ngon_ngu_giong(request: Request, public_id: str,
                        ngon_ngu: str = Form(""), csrf_token: str = Form(""),
                        user=Depends(user_hien_tai), _=Depends(require_login)):
    """MỘT cửa cho cả XÁC NHẬN và ĐỔI làn của một giọng đã có (D004).

    🔴 VÌ SAO MỘT CỬA, KHÔNG PHẢI HAI.

       Một giọng `mac_dinh_cu` (dòng có trước D003, xem `giong_vong_doi.py`) và
       một giọng `khai_bao` muốn đổi làn đứng trước ĐÚNG một câu hỏi: *"làn này
       có được không"* — câu đó là việc của `khai_lan_hop_le`, và nó không cần
       biết khách đang XÁC NHẬN (cùng làn) hay ĐỔI (khác làn). Tách hai cửa là
       tách một quyết định làm hai, và hai bản dễ lệch luật hơn một.

    Luật (đọc từ `giong_vong_doi.khai_lan_hop_le`, chốt D004):
      · rỗng/lạ                              ⇒ CHẶN `voice_language_required`.
      · làn hiện tại đến từ PHÉP ĐO (`do_asr`) và khách xin làn KHÁC làn đã đo
                                              ⇒ CHẶN `voice_language_measured`.
      · giọng đã `revoked`                   ⇒ CHẶN `voice_revoked` (dữ liệu
        sinh trắc đã xoá — không còn gì để gán làn nữa).
      · làn ĐỔI                              ⇒ ghi `ngon_ngu` mới, nguồn thành
        `khai_bao`, và HUỶ tệp nghe thử cũ (`nghe_thu.dung_lai_cho_giong`) —
        tệp cũ đọc câu của làn CŨ, phục vụ tiếp là phục vụ sai làn.
      · làn GIỮ NGUYÊN nhưng nguồn là `mac_dinh_cu` ⇒ chỉ đổi nguồn thành
        `khai_bao` (một lời XÁC NHẬN — không có gì để dựng lại).
      · làn GIỮ NGUYÊN và nguồn đã là `khai_bao`/`do_asr` ⇒ no-op hợp lệ.

    ⛔ CÙNG PHÉP KIỂM SỞ HỮU với `tat_giong` ngay trên: tìm theo `owner_id`,
       KHÔNG mở kho chung. Làn của kho chung đổi bằng công cụ vận hành, không
       bằng một nút trên web của một khách.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    uid = _uid(user)
    muon_json = "application/json" in (request.headers.get("accept") or "")
    gen = _db()
    db = next(gen)
    try:
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id=uid)
        if ho_so is None or not tham_chieu.chi_chu_so_huu(ho_so, uid):
            # Một câu cho cả "không tồn tại" lẫn "không phải của bạn" — không để
            # cửa này thành máy dò `public_id` nào có thật (cùng khuôn `xoa_giong`
            # của `29ac2300`).
            return _tra_loi_ngon_ngu(muon_json, _t("Không tìm thấy giọng."), "",
                                     that_bai=404)
        if ho_so.trang_thai == giong_vong_doi.TT_REVOKED:
            return _tra_loi_ngon_ngu(muon_json, _t(
                "Giọng này đã bị thu hồi, không sửa được nữa."
            ), "voice_revoked")

        ma_loi_lan = giong_vong_doi.khai_lan_hop_le(
            ngon_ngu, lan_hien=ho_so.ngon_ngu, nguon_hien=ho_so.ngon_ngu_nguon)
        if ma_loi_lan:
            if ma_loi_lan == "voice_language_measured":
                nhan = _t(lan_ngon_ngu.NHAN_LAN.get(ho_so.ngon_ngu, ho_so.ngon_ngu))
                loi = _t(
                    "Clip nguồn của giọng này đo được là {lan}. Không đổi được "
                    "sang ngôn ngữ khác."
                ).format(lan=nhan)
            else:
                loi = _t(
                    "Hãy chọn ngôn ngữ của clip giọng: Tiếng Việt hoặc Tiếng Anh.")
            return _tra_loi_ngon_ngu(muon_json, loi, ma_loi_lan)

        lan_moi = lan_ngon_ngu.chuan_lan(ngon_ngu)
        can_dung_lai = False
        if lan_moi != ho_so.ngon_ngu:
            # ĐỔI làn thật: tệp nghe thử cũ đọc câu của làn CŨ, nên nó không còn
            # đúng cho giọng này — huỷ để bước `_dung_giong_rieng_con_thieu`
            # của `bao_tri()` dựng lại đúng làn mới ở lượt kế.
            ho_so.ngon_ngu = lan_moi
            ho_so.ngon_ngu_nguon = giong_vong_doi.NGUON_KHAI_BAO
            can_dung_lai = True
        elif ho_so.ngon_ngu_nguon == giong_vong_doi.NGUON_MAC_DINH_CU:
            # Cùng làn, chỉ XÁC NHẬN nguồn — không có gì để dựng lại.
            ho_so.ngon_ngu_nguon = giong_vong_doi.NGUON_KHAI_BAO
        # else: cùng làn, nguồn đã là `khai_bao`/`do_asr` — no-op hợp lệ.
        db.commit()

        # 🔴 HUỶ TỆP NGHE THỬ **SAU** COMMIT, KHÔNG TRƯỚC.
        #
        #    Đổi làn CSDL và huỷ tệp kho là hai hệ thống khác nhau — không có
        #    transaction chung. Xoá tệp TRƯỚC rồi `commit()` hỏng giữa chừng
        #    (deadlock, mất kết nối) để lại một giọng vẫn khai làn CŨ mà đã
        #    KHÔNG CÒN tệp nghe thử nào — tệ hơn hẳn trạng thái ban đầu (tệp cũ
        #    đọc sai làn, nhưng ít nhất còn phát được gì đó). Xoá SAU khi commit
        #    thành công thì trường hợp xấu nhất chỉ là: đổi làn đã ghi xong,
        #    tệp cũ (sai làn) còn sống thêm tới lượt bảo trì kế — vẫn đúng
        #    hướng an toàn hơn.
        if can_dung_lai:
            nghe_thu.dung_lai_cho_giong(db, ho_so)

        if muon_json:
            return JSONResponse({"ok": True, "ngon_ngu": ho_so.ngon_ngu})
        # ⛔ CHUYỂN HƯỚNG, không trả JSON. Cửa này được gọi bởi một `<form>` HTML
        #    thật (thẻ giọng, không JS) — trả JSON thì khách nhìn thấy một trang
        #    trắng ghi `{"ok": true}` và không có đường quay lại. 303 sau POST
        #    cũng là thứ chặn F5 gửi lại biểu mẫu (`65e099af`).
        from fastapi.responses import RedirectResponse
        return RedirectResponse(f"{MANIFEST.route_prefix}/giong", status_code=303)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


