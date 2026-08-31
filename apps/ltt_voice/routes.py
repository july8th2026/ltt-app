"""
Giao diện của LTT VOICE. Router **không** tự viết prefix — nền tảng gắn từ
`MANIFEST.route_prefix`.

⛔ FILE NÀY CHỈ LO HTTP. Đọc request, kiểm quyền/CSRF, gọi `features`, dựng phản
   hồi. Không một quy tắc nghiệp vụ nào ở đây (`AGENTS.md` mục 8): route là **một
   cánh cửa**, và quy tắc nằm trong một cánh cửa thì cửa thứ hai phải chép lại.

⭐ App tự phục vụ tệp tiếng qua `/audio/{key}` thay vì dựa vào `download_token`
   của storage: token giữ trong RAM của TỪNG tiến trình, mà worker (tạo tệp) và
   web (phục vụ) là hai tiến trình khác nhau. Cùng lý do `apps/thumbnail` đã làm
   vậy — không phải sáng kiến riêng.
"""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse, RedirectResponse,
                               Response, StreamingResponse)

from platform_core.i18n import _ as _t
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

from . import features, gia, sidecar_client, tham_chieu
from .manifest import MANIFEST
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

router = APIRouter(tags=["ltt_voice"])


def _uid(user) -> str:
    """Id người dùng, dạng CHUỖI.

    ⛔ Đừng ép `int()`. `User.id` là UUID chuỗi, nên `int()` ném, và bản
       đầu của hàm này bắt lỗi rồi trả `0` — một giá trị **hợp lệ về kiểu
       nhưng sai về nghĩa**. Hậu quả đo được trên máy chủ thật 31/08/2026:
       trang hiện đúng "56 credit" ở header (chỗ đó đọc phiên trực tiếp)
       trong khi nút Tạo trả *"Khong du credit: can 2, con 0"*, vì handler
       tra sổ của người dùng "0". Và nguy hơn tiền: mọi `owner_id` đều
       thành 0, tức giọng của mọi khách chung một chủ.
    """
    return str(getattr(user, "id", "") or "")


def _db():
    from platform_core.db import get_session
    return get_session()


def _ngu_canh(request: Request, user, **them) -> dict:
    d = {"request": request, "user": user, "manifest": MANIFEST,
         "tran_ky_tu": TRAN_KY_TU_CONG_KHAI,
         "bang_gia": gia.bang_gia(),
         "cong_san_sang": sidecar_client.san_sang()}
    d.update(them)
    return d


# ── Tạo tiếng nói ────────────────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def trang_tao(request: Request, user=Depends(user_hien_tai),
              _=Depends(require_login)):
    gen = _db()
    db = next(gen)
    try:
        giong = tham_chieu.danh_sach(db, owner_id=_uid(user))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_studio.html", _ngu_canh(request, user, giong=giong))


@router.post("/tao")
def tao(request: Request, text: str = Form(""), voice_id: str = Form(""),
        preset: str = Form(""), csrf_token: str = Form(""),
        user=Depends(user_hien_tai), _=Depends(require_login)):
    verify_csrf_token(request, csrf_token)

    from platform_core.job_submit import submit_with_credit

    # Nghiệp vụ ở `features`, kể cả phép kiểm "không được vừa voice_id vừa preset".
    try:
        yc = features.chuan_hoa({"text": text, "voice_id": voice_id,
                                 "preset": preset, "owner_id": _uid(user)})
    except features.LoiGiongNoi as e:
        return JSONResponse({"ok": False, "loi": str(e)}, status_code=400)

    if len(yc.text) > TRAN_KY_TU_CONG_KHAI:
        return JSONResponse({"ok": False, "loi": _t(
            "Văn bản dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
        ).format(n=len(yc.text), t=TRAN_KY_TU_CONG_KHAI)}, status_code=400)

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
            params={"text": yc.text, "voice_id": yc.voice_id,
                    "preset": yc.preset, "owner_id": _uid(user)},
            # Một GPU = một việc, và cả ba cửa giành cùng một slot (Q114).
            admission_resource=tool.admission_resource,
            admission_slots=tool.admission_slots)
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


# ── Giọng của tôi ────────────────────────────────────────────────────────────

@router.get("/giong", response_class=HTMLResponse)
def trang_giong(request: Request, user=Depends(user_hien_tai),
                _=Depends(require_login)):
    gen = _db()
    db = next(gen)
    try:
        giong = tham_chieu.danh_sach(db, owner_id=_uid(user))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    from .dieu_khoan import CAM_KET, cac_dieu
    return templates.TemplateResponse(
        request, "ltt_voice_giong.html",
        _ngu_canh(request, user, giong=giong, dieu_khoan=cac_dieu(),
                  cam_ket=CAM_KET))


@router.post("/giong/tao")
async def tao_giong(request: Request, ten: str = Form(""),
                    dong_y: str = Form(""), csrf_token: str = Form(""),
                    tep: UploadFile = File(...),
                    user=Depends(user_hien_tai), _=Depends(require_login)):
    """Ghi danh một giọng mới. Consent lưu thành **dữ liệu**, không phải ghi chú."""
    verify_csrf_token(request, csrf_token)
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

    from .dieu_khoan import PHIEN_BAN_DIEU_KHOAN
    from .tables import VoiceConsent, VoiceProfile, VoiceRef

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
    verify_csrf_token(request, csrf_token)
    gen = _db()
    db = next(gen)
    try:
        ho_so = tham_chieu.tim_profile(db, public_id, owner_id=_uid(user))
        if ho_so is None:
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


# ── Lịch sử ──────────────────────────────────────────────────────────────────

@router.get("/lich-su", response_class=HTMLResponse)
def trang_lich_su(request: Request, user=Depends(user_hien_tai),
                  _=Depends(require_login)):
    from platform_core import job_history
    gen = _db()
    db = next(gen)
    try:
        lich_su, _cursor = job_history.list_owned(
            db, _uid(user), app_slug=MANIFEST.slug, limit=50)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_lich_su.html", _ngu_canh(request, user, lich_su=lich_su))


# ── Phục vụ tệp tiếng ────────────────────────────────────────────────────────

@router.get("/audio/{key:path}")
def audio(key: str, user=Depends(user_hien_tai), _=Depends(require_login)):
    """Phục vụ tệp tiếng. **Kiểm sở hữu bằng chính hình dạng khoá.**

    Khoá có dạng `voice/out/{owner_id}/{job_id}.wav`, nên chỉ chủ mới đọc được
    tệp của mình. Đoán một `job_id` khác cũng không ra vì phần `owner_id` không
    khớp.
    """
    uid = _uid(user)
    if not key.startswith(f"voice/out/{uid}/"):
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
    return StreamingResponse(io.BytesIO(data), media_type="audio/wav")
