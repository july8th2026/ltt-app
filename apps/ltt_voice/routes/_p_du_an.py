"""Màn Dự án: danh sách · khối · sinh tiếng theo khối · xuất.

⛔ CHỈ LO HTTP. Nghiệp vụ ở `du_an.py`. Mọi handler ở đây làm đúng bốn việc:
   kiểm CSRF, tra dự án **kèm chủ sở hữu**, gọi `du_an.*`, dựng phản hồi.

🔴 KHÔNG CÓ LOẠI JOB MỚI. Sinh một khối là một `ltt_voice.synthesize` bình
   thường + `nguon="du_an"`. Xem lý do đầy đủ ở đầu `du_an.py`.
"""
from __future__ import annotations

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, Form,
                     HTMLResponse, JSONResponse, Request, _db, _het_phien,
                     _t, _uid, du_an, features, giong_mau, require_login,
                     router, templates, tham_chieu, user_hien_tai,
                     verify_csrf_token, vo)


def _mo_du_an(db, request, user, public_id: str):
    """Tra dự án theo `public_id` **và** chủ. Trả `None` nếu không phải của họ.

    ⛔ Một hàm, dùng ở mọi handler. Viết lại phép tra ở từng chỗ là mời một chỗ
       quên mất vế `owner_id` — và vế đó là toàn bộ phép kiểm quyền của màn này.
    """
    return du_an.tim(db, public_id, owner_id=_uid(user))


def _ngu_canh_giong(**them) -> dict:
    """Bộ khoá mà `_voice_chon.html` cần. Ba màn dùng chung nên gom một chỗ."""
    d = {"giong_mau": giong_mau.DANH_SACH,
         "nhan_gioi": giong_mau.NHAN_GIOI,
         "nhan_vung": giong_mau.NHAN_VUNG,
         "nhan_phong_cach": giong_mau.NHAN_PHONG_CACH,
         "mac_dinh": giong_mau.MAC_DINH}
    d.update(them)
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
        dem = {d.public_id: du_an.tom_tat(du_an.cac_khoi(db, d.id)) for d in ds}
        hang_doi = vo.dem_dang_chay(db, uid)
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_du_an.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_DU_AN, hang_doi=hang_doi,
                    **_ngu_canh_giong(du_an_ds=ds, dem=dem, giong=cua_toi,
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
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
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
        tt = du_an.tom_tat(khoi)
        hang_doi = vo.dem_dang_chay(db, uid)
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid)
        # Bản sao phẳng cho template — tránh chạm ORM trong Jinja.
        ds_khoi = [{
            "id": k.id, "thu_tu": k.thu_tu, "text": k.text, "giong": k.giong,
            "trang_thai": k.trang_thai, "job_id": k.job_id,
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
                                      giong=cua_toi,
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
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
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
        if text is not None and len(text) > TRAN_KY_TU_CONG_KHAI:
            return JSONResponse({"ok": False, "loi": _t(
                "Khối dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
            ).format(n=len(text), t=TRAN_KY_TU_CONG_KHAI)}, status_code=400)
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
        so = du_an.nhap_van_ban(db, d, text,
                                tran_moi_khoi=TRAN_KY_TU_CONG_KHAI)
        db.commit()
        return JSONResponse({"ok": True, "so_khoi": so})
    except du_an.LoiDuAn as e:
        db.rollback()
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
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
    """
    from platform_core.job_submit import submit_with_credit

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
        admission_resource=tool.admission_resource,
        admission_slots=tool.admission_slots)
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
                "Khối này chưa có văn bản.")}, status_code=400)
        jid = _nop_mot_khoi(db, user, d, k)
        db.commit()
        return JSONResponse({"ok": True, "job_id": jid})
    except Exception as e:  # noqa: BLE001 - thieu credit cung di duong nay
        db.rollback()
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
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

        tt = du_an.tom_tat(khoi)
        duong = du_an.duong_tieng(db, khoi, MANIFEST.route_prefix)
        return JSONResponse({
            "ok": True,
            "tom_tat": tt,
            "khoi": [{
                "id": k.id, "trang_thai": k.trang_thai,
                "giay": k.giay, "credit": k.credit,
                "audio_url": duong.get(k.id, ""),
            } for k in khoi],
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
