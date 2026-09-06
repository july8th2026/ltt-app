"""Giao dien khach cua Auto Scan Video.

Router KHONG tu viet prefix — nen tang gan tu `MANIFEST.route_prefix`.

## Tep nay CHI lo HTTP

Doc request, kiem quyen + CSRF, goi dich vu, dung phan hoi. Moi quyet dinh
nghiep vu o `features.py` / `gia.py` / `quan_sat.py`. Tran cung cua hop dong app
la 900 dong / 30 handler; tep nay co bay handler va o day khong phai vi no be ma
vi **chuoi la co dinh** — khong co do thi de dung, khong co node de keo tha
(Prompt 20 cam ro).

## Ba dieu quyet dinh hinh dang cua man hinh nay

1. **Khach khong can biet chin giai doan ten la gi trong ma nguon.** Ho thay
   chin buoc co nhan tieng Viet. `pipeline.CHUOI` van la nguon chan ly ve thu
   tu — ta chi dat nhan len tren.

2. **Chi tiet ky thuat mac dinh AN** (muc 6). `quan_sat.dong_thoi_gian` mac dinh
   tra ban cho khach; ban van hanh nam sau mot `<details>` va chi hien cho
   operator. Khong co duong dan tep, khong ten worker, khong job id.

3. **Moi truy van deu loc theo chu so huu o TANG DICH VU**, khong o day.
   `features.lay_run(db, id, owner)` nem neu khong phai cua ho — nen mot handler
   quen viet menh de loc van khong ro ri. Do la I6, va no duoc chot lai o
   `test_423` bang hai nguoi dung that.
"""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import (HTMLResponse, JSONResponse,
                               RedirectResponse, StreamingResponse)
from sqlalchemy.orm import Session

from platform_core.i18n import N_, _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

from . import hop_dong_v4, features, gia, pipeline, quan_sat
from .manifest import MANIFEST

log = logging.getLogger(__name__)
router = APIRouter(tags=["auto_scan_video"])

#: Co mo app. ⛔ MAC DINH TAT.
#:
#: 🔴 `MANIFEST.enabled=False` **KHONG** dong route. `registry.mount_all` gan
#:    router cho moi app khong loi, bat ke `enabled` — no chi anh huong the
#:    catalog. Nen mot app "chua mo" van co URL song ngay khi co `routes.py`.
#:
#: ⇒ Prompt 20 muc 8 doi giu app khong cong khai toi luc nghiem thu, va thu lam
#:   duoc dieu do la CO NAY, khong phai `enabled`.
CO_MO = "LTT_AUTO_SCAN_VIDEO"


def _cong_co() -> None:
    """Co tat -> 404.

    ⚠️ Phai dat TRUOC `require_login` trong MOI chu ky handler. `Depends` chay
       theo thu tu khai bao, nen dat sau thi mot route "da dong" van 303 ve
       `/login` — tuc no van thua nhan minh ton tai.

    ⭐ Va 404 chu khong 403: 403 xac nhan co mot thu o day.
    """
    import os
    if str(os.environ.get(CO_MO, "")).strip() != "1":
        raise HTTPException(status_code=404)

#: Kieu tep nhan o cua vao. `MVP_CONTRACT.md` §2 chot chinh sach; day chi la
#: lop chan som de khach biet ngay thay vi cho mot job hong.
KIEU_VIDEO = ("video/mp4", "video/quicktime", "video/x-matroska", "video/webm")

#: Tran tep tai truc tiep. Cloudflare cat o 100 MB truoc khi request toi may
#: chu, nen dat duoi nguong do la de khach nhan mot cau tieng Viet thay vi mot
#: trang loi 413 cua Cloudflare.
TRAN_TAI_LEN = 90 * 1024 * 1024

#: Khoi doc moi vong khi chay tep tai len xuong dia. 1 MiB — du lon de khong
#: thanh mot vong lap syscall, du nho de dinh bo nho khong phu thuoc kich thuoc
#: video. Day la con so bien G6 tu mot loi hua thanh mot rang buoc.
KHOI_TAI_LEN = 1024 * 1024

#: Nhan tieng Viet cho chin giai doan. ⭐ Khoa lay TU `pipeline`, khong go tay:
#: doi ten mot giai doan ma quen sua cho nay se lam `test_423` do, thay vi de
#: giao dien hien mot o trong.
#: ⚠️ `N_` chu khong `_t`: day la mot hang so o cap MODULE, danh dau luc nap.
#:    Dung `_t` o day se **dong bang ngon ngu cua request dau tien** vao bien
#:    toan cuc, va moi khach sau do doc nhan bang ngon ngu cua nguoi den truoc.
#:    Ban dich thuc su xay ra o template, noi `_()` chay trong ngu canh request.
NHAN_GIAI_DOAN = {
    pipeline.MEDIA_PREPARE: N_('Chuẩn bị video'),
    pipeline.AUDIO_PREPARE: N_('Tách nhạc nền khỏi giọng'),
    pipeline.TRANSCRIBE: N_('Chép lời thoại gốc'),
    # ⭐ Nhãn nói cho khách biết **việc gì đang xảy ra**, không nói tên kỹ thuật.
    #    Ở chế độ giữ nguyên hình bước này gần như tức thì; ở chế độ cắt thông
    #    minh nó là lúc hệ thống quyết định giữ lại những gì.
    pipeline.EDIT_PLAN: N_('Chọn phần giữ lại'),
    pipeline.CONTENT_PROCESS: N_('Dịch sang tiếng Việt'),
    pipeline.VOICE_SYNTHESIS: N_('Tạo giọng đọc'),
    pipeline.TIMING_ALIGN: N_('Khớp thời điểm'),
    pipeline.COMPOSE: N_('Dựng bản ghép'),
    pipeline.RENDER: N_('Kết xuất video'),
    pipeline.QC: N_('Kiểm chất lượng'),
    # ⭐ Nhãn nói **việc gì đang xảy ra**, không nói tên kỹ thuật `qc_ai`.
    #    Bước này mặc định TẮT (`LTT_ASV_QC_AI`), và khi tắt nó chạy qua
    #    tức thì — khách vẫn thấy đủ chuỗi bước thay vì thấy một chuỗi
    #    ngắn đi rồi dài ra tuỳ cấu hình của người vận hành.
    pipeline.QC_AI: N_('Soát lại nghĩa bản dịch'),
}


def _la_operator(request: Request) -> bool:
    u = user_hien_tai(request)
    return bool(u is not None and getattr(u, "is_admin", False))


def _dung_trang(request: Request, ten: str, ngu_canh: dict,
                status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(request, ten, {
        "nav": MANIFEST.slug, "app": MANIFEST,
        "csrf_token": issue_csrf_token(request),
        "nhan_giai_doan": NHAN_GIAI_DOAN,
        **ngu_canh,
    }, status_code=status_code)


@router.get("", response_class=HTMLResponse)
def trang_chinh(request: Request, _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
                db: Session = Depends(get_db), loi: str = ""):
    """Man tao lan chay moi + lich su cua CHINH nguoi dung."""
    u = user_hien_tai(request)
    return _dung_trang(request, "asv_trang_chinh.html", {
        "che_do": gia.CHE_DO_THOI_GIAN,
        "che_do_mac_dinh": gia.CHE_DO_MAC_DINH,
        "preset": gia.PRESET_BANG,
        "preset_mac_dinh": gia.preset_mac_dinh(),
        "che_do_giong": gia.CHE_DO_GIONG_BANG,
        "che_do_giong_mac_dinh": hop_dong_v4.CHE_DO_GIONG_MAC_DINH,
        "giong": gia.giong_chon_duoc(db, u.id) if u else [],
        "lich_su": features.lich_su(db, u.id) if u else [],
        "loi": loi,
    })


@router.post("/ve")
async def cap_ve(request: Request,
                 ten_tep: str = Form(...),
                 kieu: str = Form(...),
                 co: int = Form(...),
                 csrf_token: str = Form(""),
                 _g: None = Depends(_cong_co),
                 user: str = Depends(require_login),
                 db: Session = Depends(get_db)):
    """Cap mot ve tai len TRUC TIEP browser -> kho (G6).

    🔑 Tep khong di qua tien trinh nay, va khong di qua Cloudflare. Do la ca ly
       do tran 90 MB bien mat: `routes.py:79 TRAN_TAI_LEN` ton tai vi Cloudflare
       cat o 100 MB **tren duong vao may chu** — mot duong ma tep khong con di.
    """
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401)
    from platform_core import upload_sessions
    from platform_core.storage import get_storage
    try:
        ra = features.tao_ve_tai_len(
            db, get_storage(), owner_id=u.id, ten_tep=ten_tep, kieu=kieu,
            co_du_kien=co)
        db.commit()
    except upload_sessions.UploadSessionError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(ra)


@router.post("/tao", response_class=HTMLResponse)
async def tao(request: Request,
              upload_id: str = Form(""),
              video: UploadFile | None = File(None),
              che_do: str = Form(gia.CHE_DO_MAC_DINH),
              preset: str = Form(""),
              che_do_giong: str = Form(""),
              giong_id: str = Form(""),
              csrf_token: str = Form(""),
              _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
              db: Session = Depends(get_db)):
    """Nhan video, tao lan chay. Moi loi deu tra ve mot cau tieng Viet."""
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401)

    if not gia.che_do_hop_le(che_do):
        return _lai_voi_loi(request, db, u,
                            _t('Chế độ thời gian không hợp lệ.'))

    # ── Hai lua chon ma pha 21 mo ra ────────────────────────────────────────
    #
    # 🔴 Truoc pha 21 khong route nao nhan `preset`, nen moi lan chay deu roi ve
    #    mac dinh va ca duong `smart_localize` khong ai voi toi duoc.
    #
    # ⛔ Rong = mac dinh, **khong** = "nhan bua". Mot gia tri khong hop le phai bi
    #    tu choi ngay o cua chu khong di xuong worker roi hong o giua chuoi.
    preset = preset or gia.preset_mac_dinh()
    if not gia.preset_hop_le(preset):
        return _lai_voi_loi(request, db, u, _t('Kiểu xử lý không hợp lệ.'))

    che_do_giong = che_do_giong or hop_dong_v4.CHE_DO_GIONG_MAC_DINH
    if not gia.che_do_giong_hop_le(che_do_giong):
        return _lai_voi_loi(request, db, u, _t('Cách chọn giọng không hợp lệ.'))

    # ⭐ Bat SOM: `USER_SELECTED` ma khong co giong thi pha 14 se nem o giua chuoi
    #    — sau khi khach da doi qua bon giai doan va da bi giu credit. Mot cau
    #    tra loi "ban chua chon giong" o day tot hon mot lan chay hong o phut thu
    #    muoi.
    if (che_do_giong == hop_dong_v4.CHE_DO_GIONG_TU_CHON and not giong_id):
        return _lai_voi_loi(request, db, u, _t('Hãy chọn một giọng đọc.'))

    cai_dat = {"timing_mode": che_do, "preset": preset,
               "che_do_giong": che_do_giong, "giong_id": giong_id,
               # ⚠️ Giu `voice_id` cho tuong thich nguoc: `giai_doan_giong` doc
               #    no lam duong lui cho nhung run tao truoc pha 15.
               "voice_id": giong_id}
    # ── Duong BEN VUNG: tep da nam trong kho, ta chi nhan mot ma ve ───────────
    #
    # ⭐ Dat truoc duong multipart co chu y. Khi ca hai cung co mat, duong ben
    #    vung phai thang — nguoc lai mot client cu gui kem ca hai se lang le keo
    #    ca lan chay ve duong co tran 90 MB.
    if upload_id:
        from platform_core.storage import get_storage
        try:
            run = features.tao_run_tu_ve(
                db, get_storage(), owner_id=u.id, upload_id=upload_id,
                settings=dict(cai_dat))
            db.commit()
        except features.AsvError as exc:
            db.rollback()
            return _lai_voi_loi(request, db, u, str(exc))
        return RedirectResponse(f"{MANIFEST.route_prefix}/run/{run.id}",
                                status_code=303)

    # ── Duong multipart NHO: chi con cho tep duoi tran, va tran do la co y ────
    #
    # ⚠️ Pha 05 giu duong nay co chu dinh (Prompt 05 muc 4 cho phep "a tiny dev
    #    upload path only if explicitly bounded"). No la duong duy nhat chay
    #    duoc khi kho la `LocalStorage` — tuc tren may phat trien va trong ca bo
    #    test — vi backend cuc bo khong cap presigned PUT.
    if video is None:
        return _lai_voi_loi(request, db, u, _t('Chưa chọn video.'))
    kieu = (video.content_type or "").split(";")[0].strip().lower()
    if kieu and kieu not in KIEU_VIDEO:
        return _lai_voi_loi(request, db, u,
                            _t('Định dạng video không được hỗ trợ.'))

    # 🔴 **Dong cu o day la `du_lieu = await video.read()`, va no vi pham G6
    #    theo dung tung chu: *"production path does not `await read()` entire
    #    large video into RAM"*.**
    #
    #    Te hon ca viec cap phat: tran 90 MB duoc kiem o dong NGAY SAU no, tuc
    #    mot tep 100 MB van duoc cap phat du 100 MB truoc khi bi tu choi. Mot
    #    quyet dinh "co nhan khong" dat sau hanh dong ma no le ra phai chan.
    #
    # ⇒ Chay theo khoi va ap tran NGAY TRONG luc chay: byte thu (tran + 1) lam
    #   vong lap dung lai, va khong byte nao nua duoc doc.
    #
    # ⭐ `SpooledTemporaryFile` cua Starlette da giu tep tren DIA khi no vuot
    #    nguong, nen o day ta khong tao them mot ban sao thu ba — ta chi thoi
    #    keo no nguyen khoi vao `bytes`.
    with tempfile.TemporaryDirectory(prefix="asv-tai-len-") as tam:
        tep = Path(tam) / "nguon"
        da = 0
        with tep.open("wb") as ra:
            while True:
                khoi = await video.read(KHOI_TAI_LEN)
                if not khoi:
                    break
                da += len(khoi)
                if da > TRAN_TAI_LEN:
                    return _lai_voi_loi(request, db, u, _t(
                        'Video vượt quá 90 MB. Hãy cắt ngắn hoặc giảm chất lượng trước.'))
                ra.write(khoi)
        if da <= 0:
            return _lai_voi_loi(request, db, u, _t('Tệp rỗng.'))

        try:
            run = features.tao_run_tu_tai_len(
                db, owner_id=u.id, duong_tep=str(tep),
                ten_tep=video.filename or "video.mp4",
                settings=dict(cai_dat))
            db.commit()
        except features.AsvError as exc:
            db.rollback()
            return _lai_voi_loi(request, db, u, str(exc))

    return RedirectResponse(f"{MANIFEST.route_prefix}/run/{run.id}",
                            status_code=303)


def _lai_voi_loi(request: Request, db, u, thong_bao: str) -> HTMLResponse:
    return _dung_trang(request, "asv_trang_chinh.html", {
        "che_do": gia.CHE_DO_THOI_GIAN,
        "che_do_mac_dinh": gia.CHE_DO_MAC_DINH,
        "preset": gia.PRESET_BANG,
        "preset_mac_dinh": gia.preset_mac_dinh(),
        "che_do_giong": gia.CHE_DO_GIONG_BANG,
        "che_do_giong_mac_dinh": hop_dong_v4.CHE_DO_GIONG_MAC_DINH,
        "giong": gia.giong_chon_duoc(db, u.id),
        "lich_su": features.lich_su(db, u.id),
        "loi": thong_bao,
    }, status_code=400)


@router.get("/run/{run_id}", response_class=HTMLResponse)
def chi_tiet(request: Request, run_id: str,
             _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
             db: Session = Depends(get_db)):
    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    return _dung_trang(request, "asv_chi_tiet.html", {
        "run": run,
        "dong": quan_sat.dong_thoi_gian(db, run),
        "van_hanh": (quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
                     if _la_operator(request) else None),
        "loi_khach": quan_sat.tom_tat_loi_cho_khach(db, run),
        "co_ket_qua": bool(features.khoa_ket_qua(db, run)),
    })


@router.get("/run/{run_id}/tien-do", response_class=HTMLResponse)
def tien_do(request: Request, run_id: str,
            _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
            db: Session = Depends(get_db)):
    """Manh HTML cho htmx hoi lai. Cung du lieu, khong co khung trang."""
    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    return _dung_trang(request, "asv_tien_do.html", {
        "run": run,
        "dong": quan_sat.dong_thoi_gian(db, run),
        "loi_khach": quan_sat.tom_tat_loi_cho_khach(db, run),
        "co_ket_qua": bool(features.khoa_ket_qua(db, run)),
    })


@router.post("/run/{run_id}/huy")
def huy(request: Request, run_id: str, csrf_token: str = Form(""),
        _g: None = Depends(_cong_co),
                user: str = Depends(require_login), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    _run_cua_toi(db, run_id, u)         # nem 404 neu khong phai cua ho
    features.huy_run(db, run_id, u.id)
    db.commit()
    return RedirectResponse(f"{MANIFEST.route_prefix}/run/{run_id}",
                            status_code=303)


@router.post("/run/{run_id}/thu-lai")
def thu_lai(request: Request, run_id: str, giai_doan: str = Form(""),
            csrf_token: str = Form(""),
            _g: None = Depends(_cong_co),
                user: str = Depends(require_login), db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        raise HTTPException(status_code=400, detail=_t('Phiên đã hết hạn.'))
    u = user_hien_tai(request)
    _run_cua_toi(db, run_id, u)
    try:
        features.thu_lai_giai_doan(db, run_id, u.id, giai_doan)
        db.commit()
    except features.AsvError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return RedirectResponse(f"{MANIFEST.route_prefix}/run/{run_id}",
                            status_code=303)


@router.get("/run/{run_id}/tai", response_class=StreamingResponse)
def tai_ket_qua(request: Request, run_id: str,
                _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
                db: Session = Depends(get_db)):
    """Phuc vu ban long tieng. Quyen kiem o TANG DICH VU, khong o day.

    ⛔ Khong nhan `key` tu client. Mot route `/tai?key=...` la mot route trong do
       quyen so huu duoc suy tu mot chuoi khach gui len — va do la dung hinh
       dang cua mot lo IDOR, ke ca khi hom nay ta co kiem tien to.
    """
    from platform_core.storage import get_storage

    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    khoa = features.khoa_ket_qua(db, run)
    if not khoa:
        raise HTTPException(status_code=404,
                            detail=_t('Lần chạy này chưa có kết quả.'))
    f = get_storage().open(khoa)
    return StreamingResponse(
        f, media_type="video/mp4",
        headers={"Content-Disposition":
                 f'attachment; filename="long-tieng-{run_id[:8]}.mp4"'})


def _run_cua_toi(db, run_id: str, u):
    """Doc run co PHAM VI CHU SO HUU. 404 khi khong phai cua ho.

    ⚠️ 404 chu khong phai 403: mot 403 xac nhan rang `run_id` do co that, va do
       la mot ro ri nho nhung that — no cho phep do xem ai co lan chay nao.
    """
    if u is None:
        raise HTTPException(status_code=401)
    try:
        return features.lay_run(db, run_id, u.id)
    except features.AsvError:
        raise HTTPException(status_code=404,
                            detail=_t('Không tìm thấy lần chạy.')) from None
