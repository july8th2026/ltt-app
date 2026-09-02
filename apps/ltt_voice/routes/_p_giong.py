"""Màn Giọng: lưới giọng, ghi danh giọng mới, tắt giọng."""
from __future__ import annotations

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, File, Form,
                     HTMLResponse, JSONResponse, Request, Response,
                     StreamingResponse, UploadFile, _db, _het_phien,
                     _t, _uid, doc_man_giong, doc_man_lich_su, features,
                     gia, giong_mau, io, require_login, router, templates,
                     tham_chieu, user_hien_tai, verify_csrf_token, vo,
                     NHAN_NGUON, lan_ngon_ngu, nghe_thu)


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
                    giong=giong, giong_mau=giong_mau.DANH_SACH,
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
                    tep: UploadFile = File(...),
                    user=Depends(user_hien_tai), _=Depends(require_login)):
    """Ghi danh một giọng mới. Consent lưu thành **dữ liệu**, không phải ghi chú."""
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

    data = await tep.read()
    try:
        mo_ta = features.kiem_ghi_danh(data, tep.content_type or "")
    except features.LoiGiongNoi as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

    sha = features.hash_noi_dung(data)

    from platform_core.job_submit import submit_with_credit

    from ..dieu_khoan import PHIEN_BAN_DIEU_KHOAN
    from ..tables import VoiceConsent, VoiceProfile, VoiceRef

    gen = _db()
    db = next(gen)
    try:
        ho_so = VoiceProfile(owner_id=uid, ten_hien_thi=ten.strip(),
                             trang_thai="dang_ghi_danh")
        db.add(ho_so)
        db.flush()

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

        job = submit_with_credit(
            db, user_id=str(uid), app_slug=MANIFEST.slug,
            job_type="ltt_voice.enroll",
            params={"owner_id": uid, "voice_id": ho_so.public_id,
                    "source_key": khoa, "ref_id": ref.id,
                    "nguon": "giong",
                    "_job_type": "ltt_voice.enroll"})
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
        ho_so.trang_thai = "disabled"
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


