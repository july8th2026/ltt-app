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

from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.csrf import verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

from . import (doc_man_giong, doc_man_lich_su, features, gia, giong_mau,
               tham_chieu, vo)
from .manifest import MANIFEST
from .tham_so_cong_khai import TRAN_KY_TU_CONG_KHAI

#: Nhãn người đọc cho `params["nguon"]`. Khai ở đây vì nó là chuyện của **màn
#: hình**, không phải của nghiệp vụ — worker không quan tâm lượt này đến từ đâu.
NHAN_NGUON = {
    "studio": N_('Tạo tiếng nói'),
    "giong": N_('Ghi danh giọng'),
    "du_an": N_('Dự án'),
    "lo": N_('Chạy lô'),
    "api": N_('API'),
}

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


def _het_phien():
    """Phản hồi khi CSRF không khớp.

    🔴 LỖI ĐANG SỐNG, PHÁT HIỆN 31/08/2026 — VÀ HÌNH DẠNG CỦA NÓ ĐÁNG GHI LẠI.

       `verify_csrf_token` **trả về `bool`**, nó không ném. Bốn cửa POST của app
       này gọi nó rồi **vứt kết quả đi**:

           verify_csrf_token(request, csrf_token)      # <- không dùng gì cả

       Nên CSRF chưa bao giờ được thi hành ở đây, kể từ ngày phát hành. Ba cửa
       bị ảnh hưởng đều là cửa có hậu quả: `/tao` tiêu credit, `/giong/tao` tạo
       hồ sơ giọng **và ghi một cam kết pháp lý**, `/giong/{id}/tat` vô hiệu hoá
       giọng của khách.

    ⭐ Vì sao không ai thấy: dòng gọi **trông đúng**, và chú thích đầu tệp còn
       ghi rõ *"kiểm quyền/CSRF"* — nên đọc lướt thì mọi thứ ở đúng chỗ. Nó chỉ
       lộ ra khi có người gửi một token sai và **đòi** một mã lỗi.
       Đối chiếu: mọi app khác trong kho đều viết `if not verify_csrf_token(...)`.
       `ltt_voice` là app duy nhất không.

    ⚠️ Mức nguy hiểm thật, nói cho đúng chứ không nói to: cookie phiên đặt
       `same_site="lax"` (`server/app.py`), nên một biểu mẫu POST từ site khác
       **không** kèm được cookie — trình duyệt hiện đại đã chặn phần lớn đường
       khai thác. Đây là phòng thủ nhiều lớp bị hụt một lớp, không phải một cánh
       cửa mở toang. Nhưng lớp đó tồn tại vì `lax` không bảo vệ mọi thứ, và vì
       một app không được dựa vào cấu hình của app khác.
    """
    return JSONResponse(
        {"ok": False, "loi": _t("Phiên đã hết hạn. Hãy tải lại trang.")},
        status_code=400)


# ⭐ Vỏ dùng chung đã chuyển sang `vo.py`. Route chỉ còn gọi nó.
#
#    Trước P1 hàm này nằm ngay đây và **không đặt `nav`** — nên phép so
#    `nav == entry.nav_key` trong `base.html` luôn False và cả ba tab của Voice
#    đều xám kể từ ngày phát hành. Không phép kiểm nào bắt được: trang vẫn 200,
#    chỉ là không tab nào sáng. `vo.ngu_canh` bắt buộc truyền `nav_key`, nên lỗi
#    đó không tái diễn được nữa.


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
        cua_toi = tham_chieu.danh_sach(db, owner_id=uid)
        hang_doi = vo.dem_dang_chay(db, uid)
        # "Gần đây" chỉ ba dòng: nó là một lối quay lại, không phải màn Lịch sử
        # thu nhỏ. Nhiều hơn thì cột giữa dài ra và đẩy ô kịch bản lên trên.
        gan_day, _cur = job_history.list_owned(
            db, uid, app_slug=MANIFEST.slug, limit=3)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    xin = (giong or "").strip()
    hop_le = (giong_mau.hop_le(xin)
              or any(g.public_id == xin and g.trang_thai == "active"
                     for g in cua_toi))
    return templates.TemplateResponse(
        request, "ltt_voice_studio.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_STUDIO, hang_doi=hang_doi,
                    giong=cua_toi, giong_mau=giong_mau.DANH_SACH,
                    nhan_gioi=giong_mau.NHAN_GIOI,
                    nhan_vung=giong_mau.NHAN_VUNG,
                    nhan_phong_cach=giong_mau.NHAN_PHONG_CACH,
                    giong_chon=(xin if hop_le else ""),
                    mac_dinh=giong_mau.MAC_DINH,
                    gan_day=gan_day))


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

    from . import text_pipeline
    from .tham_so_cong_khai import TRAN_MOI_LUOT_SINH

    tho = (text or "").strip()
    if not tho:
        return JSONResponse({"ok": False, "loi": _t("Chưa có văn bản để đọc.")},
                            status_code=400)
    if len(tho) > TRAN_KY_TU_CONG_KHAI:
        return JSONResponse({"ok": False, "loi": _t(
            "Văn bản dài {n} ký tự, vượt giới hạn {t} cho một lượt đọc."
        ).format(n=len(tho), t=TRAN_KY_TU_CONG_KHAI)}, status_code=400)

    chuan = text_pipeline.chuan_bi(tho, tran_moi_doan=TRAN_MOI_LUOT_SINH)
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
        preset: str = Form(""), csrf_token: str = Form(""),
        user=Depends(user_hien_tai), _=Depends(require_login)):
    if not verify_csrf_token(request, csrf_token):
        return _het_phien()

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
                    "nguon": "studio"},
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
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        giong = tham_chieu.danh_sach(db, owner_id=uid)
        hang_doi = vo.dem_dang_chay(db, uid)
        thong_ke = doc_man_giong.thong_ke_theo_giong(db, uid, MANIFEST.slug)
        chi_tiet = doc_man_giong.chi_tiet_cho_trang(
            db, giong, thong_ke, f"{MANIFEST.route_prefix}/audio")
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    from .dieu_khoan import CAM_KET, cac_dieu
    return templates.TemplateResponse(
        request, "ltt_voice_giong.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_GIONG, hang_doi=hang_doi,
                    giong=giong, giong_mau=giong_mau.DANH_SACH,
                    nhan_gioi=giong_mau.NHAN_GIOI,
                    nhan_vung=giong_mau.NHAN_VUNG,
                    nhan_phong_cach=giong_mau.NHAN_PHONG_CACH,
                    thong_ke=thong_ke, chi_tiet=chi_tiet,
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
def trang_lich_su(request: Request, tt: str = "", nguon: str = "",
                  giong: str = "", user=Depends(user_hien_tai),
                  _=Depends(require_login)):
    """Lịch sử tạo tiếng, lọc theo trạng thái · nguồn · giọng.

    ⛔ Ba tham số lọc là **chuỗi khách gửi**, nhưng chúng không chạm SQL: chúng
       chỉ đi vào một phép so bằng trong Python (`doc_man_lich_su.loc`). Giá trị
       lạ thì không khớp gì và trả danh sách rỗng — an toàn, và đúng nghĩa.
    """
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        goi = doc_man_lich_su.doc(db, uid, MANIFEST.slug,
                                  trang_thai=tt, nguon=nguon, giong=giong)
        hang_doi = vo.dem_dang_chay(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    duong_audio = f"{MANIFEST.route_prefix}/audio"
    return templates.TemplateResponse(
        request, "ltt_voice_lich_su.html",
        vo.ngu_canh(request, user, nav_key=vo.NAV_LICH_SU, hang_doi=hang_doi,
                    dong=[doc_man_lich_su.dong_cho_trang(j, duong_audio)
                          for j in goi["dong"]],
                    tom_tat=goi["tom_tat"], bi_cat=goi["bi_cat"],
                    tran=goi["tran"],
                    giong_da_dung=goi["giong_da_dung"],
                    nguon_da_dung=goi["nguon_da_dung"],
                    nhan_nguon=NHAN_NGUON,
                    f_tt=tt, f_nguon=nguon, f_giong=giong))


# ── Màn chưa xây ─────────────────────────────────────────────────────────────
#
# ⭐ MỘT HANDLER CHO CẢ BA, không ba bản chép. Nội dung khác nhau là **dữ liệu**
#    (`vo.CHUA_XAY`), không phải mã — nên ngày một màn được xây thật, việc phải
#    làm là xoá một khoá trong từ điển và lật `built=True`, không phải đi tìm
#    xem còn bản chép nào sót lại.
#
# ⛔ Trang này KHÔNG vẽ giao diện giả. Nó nói sẽ có gì, không mô phỏng cái sẽ có.

def _trang_chua_xay(request: Request, user, nav_key: str):
    uid = _uid(user)
    gen = _db()
    db = next(gen)
    try:
        hang_doi = vo.dem_dang_chay(db, uid)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return templates.TemplateResponse(
        request, "ltt_voice_chua_xay.html",
        vo.ngu_canh(request, user, nav_key=nav_key, hang_doi=hang_doi,
                    man=vo.CHUA_XAY[nav_key]))


@router.get("/du-an", response_class=HTMLResponse)
def trang_du_an(request: Request, user=Depends(user_hien_tai),
                _=Depends(require_login)):
    return _trang_chua_xay(request, user, vo.NAV_DU_AN)


@router.get("/lo", response_class=HTMLResponse)
def trang_lo(request: Request, user=Depends(user_hien_tai),
             _=Depends(require_login)):
    return _trang_chua_xay(request, user, vo.NAV_LO)


@router.get("/api", response_class=HTMLResponse)
def trang_api(request: Request, user=Depends(user_hien_tai),
              _=Depends(require_login)):
    return _trang_chua_xay(request, user, vo.NAV_API)


# ── Phục vụ tệp tiếng ────────────────────────────────────────────────────────

@router.get("/audio/{key:path}")
def audio(key: str, user=Depends(user_hien_tai), _=Depends(require_login)):
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
    if not (la_ket_qua or la_clip_goc):
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
    return StreamingResponse(io.BytesIO(data), media_type=kieu)
