"""Màn Chạy lô: nhận danh sách, kiểm hết, chạy hết, tải cả lô.

🔴 KIỂM TRƯỚC KHI THU TIỀN. `POST /lo/kiem` là một cửa **không để lại dấu vết
   nào** — không ghi CSDL, không giữ credit, không nộp job. Nó tồn tại để bảng
   xem trước nói được "dòng nào sai và sai gì" trước khi khách bấm chạy.

⛔ CHỈ LO HTTP. Nghiệp vụ ở `lo.py` (riêng của lô) và `du_an.py` (dùng chung).
"""
from __future__ import annotations

import io
import zipfile

from fastapi import File, UploadFile
from fastapi.responses import StreamingResponse

from ._chung import (MANIFEST, TRAN_KY_TU_CONG_KHAI, Depends, Form,
                     HTMLResponse, JSONResponse, Request, _db, _het_phien,
                     _t, _uid, du_an, features, giong_mau, require_login,
                     router, templates, tham_chieu, user_hien_tai,
                     verify_csrf_token, vo)
from .. import lo as lo_mod


def _ngu_canh_giong(**them) -> dict:
    d = {"giong_mau": giong_mau.DANH_SACH,
         "nhan_gioi": giong_mau.NHAN_GIOI,
         "nhan_vung": giong_mau.NHAN_VUNG,
         "nhan_phong_cach": giong_mau.NHAN_PHONG_CACH,
         "mac_dinh": giong_mau.MAC_DINH}
    d.update(them)
    return d


# ── Danh sách lô + tạo ───────────────────────────────────────────────────────

@router.get("/lo", response_class=HTMLResponse)
def trang_lo(request: Request, user=Depends(user_hien_tai),
             _=Depends(require_login)):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        ds = lo_mod.danh_sach(db, uid)
        dem = {x.public_id: lo_mod.tom_tat(du_an.cac_khoi(db, x.id)) for x in ds}
        hang_doi = vo.dem_dang_chay(db, uid)
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_lo.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_LO, hang_doi=hang_doi,
                    **_ngu_canh_giong(lo_ds=ds, dem=dem, giong=cua_toi,
                                      giong_chon="",
                                      tran_dong=lo_mod.TRAN_DONG)))


def _doc_va_kiem(db, uid: str, noi_dung: str, la_csv, giong: str) -> dict:
    """`la_csv=None` thì để `doc_danh_sach` tự nhận dạng — xem `lo.co_ve_csv`."""
    dong = lo_mod.doc_danh_sach(noi_dung, la_csv=la_csv)
    return lo_mod.kiem(db, dong, owner_id=uid, giong_mac_dinh=giong,
                       tran_ky_tu=TRAN_KY_TU_CONG_KHAI)


@router.post("/lo/kiem")
async def kiem_danh_sach(request: Request, noi_dung: str = Form(""),
                         giong: str = Form(""), tep: UploadFile = File(None),
                         csrf_token: str = Form(""),
                         user=Depends(user_hien_tai), _=Depends(require_login)):
    """Đọc + kiểm, KHÔNG tạo gì. Trả bảng xem trước.

    ⭐ Đây là cửa duy nhất của app **cố ý không có tác dụng phụ nào**. Nó tồn
       tại để câu trả lời "danh sách này chạy được không" có giá bằng không —
       và một câu trả lời miễn phí là câu trả lời khách sẽ hỏi trước khi bấm.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    # `None` = de tu nhan dang. Chi khang dinh khi CO tep va biet duoi cua no.
    la_csv = None
    if tep is not None and getattr(tep, "filename", ""):
        raw = await tep.read()
        try:
            noi_dung = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            # ⚠️ Excel bản Việt lưu CSV bằng bảng mã hệ thống, không phải UTF-8.
            #    Từ chối thẳng thì khách không biết phải làm gì; thử `cp1258`
            #    rồi `latin-1` cho ra chữ đọc được trong đa số ca.
            for bang_ma in ("cp1258", "cp1252", "latin-1"):
                try:
                    noi_dung = raw.decode(bang_ma)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return JSONResponse({"ok": False, "loi": _t(
                    "Không đọc được tệp. Hãy lưu lại dưới dạng CSV UTF-8.")},
                    status_code=400)
        la_csv = True if (tep.filename or "").lower().endswith(".csv") else None

    gen = _db()
    db = next(gen)
    try:
        kq = _doc_va_kiem(db, _uid(user), noi_dung, la_csv, giong)
        return JSONResponse({"ok": True, **kq})
    except lo_mod.LoiLo as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/lo/tao")
async def tao_lo(request: Request, ten: str = Form(""), noi_dung: str = Form(""),
                 giong: str = Form(""), csrf_token: str = Form(""),
                 user=Depends(user_hien_tai), _=Depends(require_login)):
    """Tạo lô. **Từ chối nếu còn một dòng hỏng** — không tạo một nửa.

    🔴 Đây là chỗ luật lớn nhất của màn được thi hành. Tạo lô rồi để khách tự
       phát hiện dòng 47 hỏng nghĩa là 46 job đã giữ tiền trước khi ai biết.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        # ⛔ KIEM LAI o may chu, khong tin nut bi khoa o trinh duyet. Nut
        #    `disabled` la mot tien nghi; cua nay moi la cua.
        kq = _doc_va_kiem(db, uid, noi_dung, None, giong)
        if kq["so_hong"]:
            return JSONResponse({"ok": False, "loi": _t(
                "Còn {n} dòng chưa hợp lệ. Sửa xong rồi tạo lô — chưa đồng "
                "credit nào bị giữ."
            ).format(n=kq["so_hong"]), **kq}, status_code=400)

        x = lo_mod.tao_lo(db, owner_id=uid, ten=ten, giong=giong,
                          dong=kq["dong"])
        db.commit()
        return JSONResponse({"ok": True, "id": x.public_id,
                             "so_dong": len(kq["dong"])})
    except lo_mod.LoiLo as e:
        db.rollback()
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


# ── Một lô ───────────────────────────────────────────────────────────────────

@router.get("/lo/{public_id}", response_class=HTMLResponse)
def trang_mot_lo(request: Request, public_id: str,
                 user=Depends(user_hien_tai), _=Depends(require_login)):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        x = lo_mod.tim(db, public_id, owner_id=uid)
        if x is None:
            return templates.TemplateResponse(
                request, "ltt_voice_chua_xay.html",
                vo.ngu_canh(request, user, nav_key=vo.NAV_LO,
                            man={"tieu_de": _t("Không tìm thấy lô"),
                                 "mo_ta": _t("Lô này không tồn tại, hoặc không "
                                             "thuộc tài khoản của bạn."),
                                 "sap_co": ()}),
                status_code=404)
        cac = du_an.cac_khoi(db, x.id)
        tt = lo_mod.tom_tat(cac)
        hang_doi = vo.dem_dang_chay(db, uid)
        dong = [{
            "id": k.id, "stt": i, "nhan": k.nhan, "text": k.text,
            "giong": k.giong or x.giong_mac_dinh,
            "trang_thai": k.trang_thai, "giay": k.giay, "credit": k.credit,
            "loi": k.loi,
            "audio_url": (f"{MANIFEST.route_prefix}/audio/{k.audio_key}"
                          if k.audio_key else ""),
        } for i, k in enumerate(cac, 1)]
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_mot_lo.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_LO, hang_doi=hang_doi,
                    lo=x, dong=dong, tom_tat=tt))


@router.post("/lo/{public_id}/chay")
def chay_lo(request: Request, public_id: str, csrf_token: str = Form(""),
            user=Depends(user_hien_tai), _=Depends(require_login)):
    """Nộp job cho mọi dòng còn thiếu.

    ⭐ Dùng lại `_p_du_an._nop_mot_khoi` — cùng một cửa nộp, cùng phép kiểm
       quyền giọng, cùng cách giữ credit. Một cửa nộp thứ hai là một chỗ để hai
       cách tính tiền lệch nhau.

    🔴 DỪNG Ở DÒNG ĐẦU TIÊN HỎNG. Hết credit ở dòng thứ ba trong năm trăm thì
       nộp tiếp 497 dòng chỉ để mỗi dòng tự hỏng là 497 vòng xếp hàng vô ích, và
       497 dòng lỗi giống nhau che mất dòng đầu — dòng duy nhất nói ra nguyên
       nhân.
    """
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    from ._p_du_an import _nop_mot_khoi

    gen = _db()
    db = next(gen)
    try:
        x = lo_mod.tim(db, public_id, owner_id=_uid(user))
        if x is None:
            return JSONResponse({"ok": False}, status_code=404)

        can = du_an.khoi_can_tao(du_an.cac_khoi(db, x.id))
        if not can:
            return JSONResponse({"ok": True, "so_nop": 0, "het": True})

        da_nop, loi = 0, ""
        for k in can:
            try:
                _nop_mot_khoi(db, user, x, k)
                da_nop += 1
            except Exception as e:  # noqa: BLE001 - thieu credit cung di duong nay
                loi = str(e)
                break
        x.trang_thai = "dang_lam"
        db.commit()
        return JSONResponse({"ok": True, "so_nop": da_nop,
                             "con_lai": len(can) - da_nop, "loi": loi})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/lo/{public_id}/trang-thai")
def trang_thai_lo(public_id: str, user=Depends(user_hien_tai),
                  _=Depends(require_login)):
    """Trạng thái mọi dòng, MỘT lời gọi cho cả lô."""
    from platform_core import job_events, job_history

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        x = lo_mod.tim(db, public_id, owner_id=uid)
        if x is None:
            return JSONResponse({"ok": False}, status_code=404)

        cac = du_an.cac_khoi(db, x.id)
        for k in cac:
            if k.trang_thai == "dang_tao" and k.job_id:
                job = job_history.get_owned(db, uid, k.job_id)
                du_an.gan_ket_qua(db, k, job)
                if job is not None and job.status == "error":
                    # ⛔ Câu ĐÃ DUYỆT, không phải `job.error` thô.
                    cau = [e.public_message
                           for e in job_events.timeline(db, job.id)
                           if e.level == "error" and e.public_message]
                    k.loi = (cau[-1] if cau else _t(
                        "Không tạo được tiếng nói."))[:500]
        if cac and all(k.trang_thai == "xong" for k in cac):
            x.trang_thai = "xong"
        db.commit()

        return JSONResponse({
            "ok": True,
            "tom_tat": lo_mod.tom_tat(cac),
            "dong": [{
                "id": k.id, "trang_thai": k.trang_thai, "giay": k.giay,
                "credit": k.credit, "loi": k.loi,
                "audio_url": (f"{MANIFEST.route_prefix}/audio/{k.audio_key}"
                              if k.audio_key else ""),
            } for k in cac],
        })
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.post("/lo/{public_id}/xoa")
def xoa_lo(request: Request, public_id: str, csrf_token: str = Form(""),
           user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()
    from sqlalchemy import delete

    from ..tables_du_an import VoiceBlock, VoiceProject
    gen = _db()
    db = next(gen)
    try:
        x = lo_mod.tim(db, public_id, owner_id=_uid(user))
        if x is None:
            return JSONResponse({"ok": False}, status_code=404)
        db.execute(delete(VoiceBlock).where(VoiceBlock.project_id == x.id))
        db.execute(delete(VoiceProject).where(VoiceProject.id == x.id))
        db.commit()
        return JSONResponse({"ok": True})
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


@router.get("/lo/{public_id}/tai")
def tai_ca_lo(public_id: str, user=Depends(user_hien_tai),
              _=Depends(require_login)):
    """Tải mọi tệp đã xong của lô trong một zip.

    ⭐ Nén ĐỒNG BỘ, và đó là một lựa chọn chứ không phải lười: zip ở đây chỉ là
       đóng gói, không mã hoá lại gì. Năm trăm tệp WAV mười giây là ~400 MB đọc
       tuần tự — dưới trần 100 giây của Cloudflare.

    ⚠️ Và đó cũng là chỗ nó sẽ hỏng trước: một lô rất lớn với tệp rất dài sẽ
       chạm trần. Khi điều đó xảy ra, đường đúng là đẩy việc nén sang hàng đợi
       job — **không** phải nới trần.

    ⛔ Tên tệp trong zip lấy từ `nhan`, đã đi qua `_sach_ten_tep` lúc nhập. Không
       bao giờ ghép thẳng chuỗi của khách vào đường dẫn trong zip.
    """
    from platform_core.storage import get_storage

    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        x = lo_mod.tim(db, public_id, owner_id=uid)
        if x is None:
            return JSONResponse({"ok": False}, status_code=404)
        cac = [k for k in du_an.cac_khoi(db, x.id)
               if k.trang_thai == "xong" and k.audio_key]
        if not cac:
            return JSONResponse({"ok": False, "loi": _t(
                "Lô chưa có tệp nào xong.")}, status_code=400)
        ten_lo = lo_mod._sach_ten_tep(x.ten) or "lo"
        muc = [(k.nhan or f"{int(k.thu_tu):03d}", k.audio_key) for k in cac]
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    st = get_storage()
    bo_nho = io.BytesIO()
    # ZIP_STORED, khong DEFLATE: WAV da la du lieu am thanh tho, nen nen lai chi
    # duoc vai phan tram doi lay CPU cua ca may chu. Dong goi la du.
    with zipfile.ZipFile(bo_nho, "w", zipfile.ZIP_STORED) as z:
        da_dung: set = set()
        for nhan, khoa in muc:
            # Hai dong CSV cung ten thi trong zip chung se de nhau. Them hau to.
            ten = f"{nhan}.wav"
            n = 2
            while ten in da_dung:
                ten = f"{nhan}_{n}.wav"
                n += 1
            da_dung.add(ten)
            try:
                with st.open(khoa) as f:
                    z.writestr(ten, f.read())
            except Exception as e:  # noqa: BLE001 - mot tep thieu khong huy ca zip
                import logging
                logging.getLogger(__name__).warning(
                    "khong doc duoc %s cho zip: %s", khoa, e)
    bo_nho.seek(0)
    return StreamingResponse(
        bo_nho, media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{ten_lo}.zip"'})
