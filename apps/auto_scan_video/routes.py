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

import json
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

from . import cat_dau_cuoi, hop_dong_v4, features, gia, pipeline, quan_sat, vung_che, rang_giong
from . import lop_phu as lop_phu_mod
from . import logo as logo_mod
from . import phu_de as phu_de_mod
from . import tu_dien as tu_dien_mod
from . import cai_dat as cai_dat_mod
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


#: Nhan tieng Viet cho trang thai mot lan chay.
#:
#: 🔴 Ban truoc cua giao dien in **`r.status` tho** vao bang lich su, nen khach
#:    doc `queued` / `running` / `error` bang tieng Anh — trong mot san pham
#:    khong co mot chu tieng Anh nao khac.
#:
#: ⚠️ `N_` chu khong `_t`, cung ly do voi `NHAN_GIAI_DOAN`: day la hang so cap
#:    MODULE. Dung `_t` se dong bang ngon ngu cua request DAU TIEN vao bien toan
#:    cuc, va moi khach sau do doc nhan bang ngon ngu cua nguoi den truoc.
NHAN_TRANG_THAI = {
    "queued": N_('Đang chờ'),
    "running": N_('Đang xử lý'),
    "done": N_('Đã xong'),
    "error": N_('Không hoàn tất'),
    "cancelled": N_('Đã huỷ'),
}


def _ngu_canh_studio(db, u, loi: str = "", nap_lai: dict | None = None) -> dict:
    """Ngu canh cua man Studio.

    🔑 MOT ham, dung boi ca duong xanh lan duong loi. Truoc day hai cho dung
       ngu canh **rieng** va chung da lech: them mot truong cho trang chinh ma
       quen `_lai_voi_loi` thi trang bao loi hien mot man hinh thieu o.

    `nap_lai` — cai dat cua mot lan chay CU, de khach chay lai khong phai go lai.

    ⛔ **KHONG nap lai `vung`.** Vung che la toa do tren khung hinh cua MOT video
       cu the; dat chung len mot video khac la che nham mot vung khach khong
       chon — va khach se khong biet, vi o chon tep da doi con cac o khac thi
       khong. Cai dat noi "xu ly the nao" thi nap lai duoc; cai dat noi "o cho
       nao tren khung hinh nay" thi khong.
    """
    nl = nap_lai or {}
    return {
        "che_do": gia.CHE_DO_THOI_GIAN,
        #: ⭐ `*_chon` chu khong `*_mac_dinh`: mot ten noi "dang chon cai nao"
        #:    dung duoc cho ca lan dau (= mac dinh) lan lan chay lai (= cai cu).
        #:    Giu ten `mac_dinh` roi ghi de o template la de mot nguoi doc sau
        #:    tin rang trang nay luon hien mac dinh.
        "che_do_chon": nl.get("timing_mode") or gia.CHE_DO_MAC_DINH,
        "preset_chon": nl.get("preset") or gia.preset_mac_dinh(),
        "giong_chon": nl.get("giong_id") or "",
        "che_do_giong_chon": (nl.get("che_do_giong")
                              or hop_dong_v4.CHE_DO_GIONG_MAC_DINH),
        "nap_lai_tu": nl.get("_tu_run") or "",
        "preset": gia.PRESET_BANG,
        "preset_mac_dinh": gia.preset_mac_dinh(),
        "che_do_giong": gia.CHE_DO_GIONG_BANG,
        "che_do_giong_mac_dinh": hop_dong_v4.CHE_DO_GIONG_MAC_DINH,
        #: 🔑 Che do DUY NHAT bat buoc phai kem `giong_id` — chinh la luat o
        #: `tao()` duoi day. Phat ra day de giao dien **doc** no thay vi
        #: chep lai chuoi "USER_SELECTED" vao JS; mot ban sao la mot thu se
        #: troi khi hop dong doi, va troi im lang.
        "che_do_giong_can_giong": hop_dong_v4.CHE_DO_GIONG_TU_CHON,
        "giong": gia.giong_cho_giao_dien(db, u.id) if u else [],
        "nhan_loc": gia.NHAN_LOC,
        #: Preset DUY NHAT ma vung che dung duoc. Giao dien doc no de bat/tat
        #: cong cu ve vung.
        #:
        #: ⛔ Lay TU hop dong, khong go chuoi `"smart_localize"` vao template:
        #:    mot chuoi go tay o giao dien la mot cho se lech khi hop dong doi.
        "preset_can_cho_vung": hop_dong_v4.PRESET_CAT_THONG_MINH,
        #: ── Ba han muc cua lop phu chu, LAY TU MODULE ─────────────────────
        #:
        #: ⛔ Khong go `3` va `80` vao template. Do la cach mot han muc troi im
        #:    lang: giao dien cho go 100 ky tu, may chu tu choi o 80, va khach
        #:    chi biet sau khi bam Gui. Cung ly do `preset_can_cho_vung` o tren
        #:    lay tu hop dong chu khong go chuoi.
        "lop_phu_toi_da": lop_phu_mod.SO_LOP_PHU_TOI_DA,
        "lop_phu_chu_toi_da": lop_phu_mod.CHU_TOI_DA,
        "lop_phu_mau": list(lop_phu_mod.MAU),
        #: Han muc cua logo — cung ly do voi lop phu: khong go `2` va `8` vao
        #: template. Giao dien cho them 3 logo trong khi may chu tu choi o 2 la
        #: cach mot han muc troi im lang.
        #: Danh sach kieu + che do phu de. Cung ly do voi hai khoi tren.
        "phu_de": phu_de_mod.cho_giao_dien(),
        "logo_toi_da": logo_mod.SO_LOGO_TOI_DA,
        "logo_tran_mb": features.tran_logo_byte() // (1024 * 1024),
        "nhan_trang_thai": NHAN_TRANG_THAI,
        #: Tran hien cho khach doc, tinh tu hang so — khong go tay mot so thu hai.
        "tran_mb": TRAN_TAI_LEN // (1024 * 1024),
        #: ── Hai so cua duong BEN VUNG ──────────────────────────────────────
        #:
        #: 🔑 Ca hai lay TU `features`, khong go tay. `TRAN_BEN_VUNG` la 2 GiB
        #:    (tran cua `upload_sessions`) chu khong phai 90 MB — vi tep khong
        #:    di qua Cloudflare nua.
        #:
        #: ⚠️ Va `KIEU_VIDEO_HOP_LE` HEP HON `KIEU_VIDEO` cua duong multipart:
        #:    no khong nhan `x-matroska` va `webm`. O chon tep van nhan hai kieu
        #:    do, nen client phai tu lui ve multipart cho chung — neu khong,
        #:    khach chon mot tep `.mkv` se nhan mot loi cap ve kho hieu.
        "tran_ben_vung_mb": features.TRAN_BEN_VUNG // (1024 * 1024),
        "kieu_ben_vung": list(features.KIEU_VIDEO_HOP_LE),
        "lich_su": features.lich_su(db, u.id) if u else [],
        "loi": loi,
    }


@router.get("", response_class=HTMLResponse)
def trang_chinh(request: Request, _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
                db: Session = Depends(get_db), loi: str = "",
                run_id: str = ""):
    """Man tao lan chay moi + lich su cua CHINH nguoi dung.

    `run_id` — nap lai cai dat cua mot lan chay cu ("Chay lai voi cai dat nay").

    ⭐ Tham so ten DUNG LA `run_id`, va do la co y: `test_455` chot bang AST rang
       **moi** handler nhan `run_id` phai di qua `_run_cua_toi`. Dat mot ten khac
       (`tu_run`, `nguon`) van chay, nhung se roi ra ngoai tam cua chot do — va
       mot duong doc lan chay khong duoc chot quyen so huu la dung hinh dang mot
       lo IDOR.
    """
    u = user_hien_tai(request)
    nap_lai = None
    if run_id:
        run = _run_cua_toi(db, run_id, u)      # nem 404 neu khong phai cua ho
        nap_lai = dict(run.settings or {})
        nap_lai["_tu_run"] = run.id
    return _dung_trang(request, "asv_trang_chinh.html",
                       _ngu_canh_studio(db, u, loi, nap_lai))


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
              tu_dien: str = Form(""),
              #: Vung che, JSON do trinh sua vung dung. Rong = khong co vung nao,
              #: va do la truong hop BINH THUONG cua phan lon lan chay.
              vung: str = Form(""),
              #: Cua so cat dau/cuoi, JSON `[bat_dau, ket_thuc]` phan so 0..1.
              #: Rong = giu ca video, va do la truong hop BINH THUONG.
              cat: str = Form(""),
              #: Lop phu chu, JSON mot mang toi da `SO_LOP_PHU_TOI_DA` muc.
              #: Rong = khong ve gi, va do la truong hop BINH THUONG.
              lop_phu: str = Form(""),
              #: Hinh hoc cua tung logo, JSON mot mang. **Cung do dai** voi
              #: `logo_anh` — xem `_doc_logo` de biet vi sao khong zip mu.
              logo: str = Form(""),
              logo_anh: list[UploadFile] | None = File(None),
              #: Phu de, JSON `{che_do, kieu, phan_doan, xuat_srt}` (V6 pha 14).
              #: Rong = khong phu de, va do la truong hop BINH THUONG.
              phu_de: str = Form(""),
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

    # ⭐ Bat SOM, TRUOC khi giu credit: giong trong, giong cua nguoi khac, giong da
    #    tat deu bi tu choi o day (V6 pha 19). Xem `rang_giong.kiem_o_cua`.
    try:
        rang_giong.kiem_o_cua(db, owner_id=u.id, che_do=che_do_giong, giong_id=giong_id)
    except rang_giong.RangGiongError as exc:
        return _lai_voi_loi(request, db, u, str(exc))

    # ── Vung che ────────────────────────────────────────────────────────────
    #
    # ⭐ Kiem o CUA, va kiem bang `vung_che.chuan_hoa` chu khong bang mot doan
    #    kiem viet tai cho. Bon luat hinh hoc song o mot module vi chung phai
    #    dung o ca ba noi — luc ve, luc luu, luc thi hanh — va ba ban cua mot
    #    quy tac la ba ban se lech.
    #
    # ⛔ Sai thi TU CHOI, khong doan va khong lam ngo. Mot hop bi bo im lang la
    #    mot khach tra tien cho mot lan chay **khong che gi ca**, va ho chi biet
    #    khi xem video da giao.
    try:
        ds_vung = vung_che.chuan_hoa(json.loads(vung) if vung.strip() else [])
    except vung_che.VungLoi as exc:
        return _lai_voi_loi(request, db, u, str(exc))
    except (ValueError, TypeError):
        return _lai_voi_loi(request, db, u, _t('Vùng che không đọc được.'))

    # ── Cua so cat dau/cuoi ─────────────────────────────────────────────────
    #
    # ⭐ Tang thu nhat trong ba tang. Hai tang kia: giao dien an hai tay cam khi
    #    preset la giu hinh, va `giai_doan_ban_dung` chi giao voi cua so o duong
    #    cat — no khong tin giao dien.
    #
    # 🔑 Va tang nay tu choi **truoc khi giu credit**. Doan ngay tren da noi ra
    #    nguyen tac do bang chinh chu cua no: *"mot cau tra loi o day tot hon mot
    #    lan chay hong o phut thu muoi"*. Voi trim thi con dat hon — mot lan chay
    #    bi `ban_dung.kiem` chan la mot lan chay da di qua chin giai doan.
    try:
        cua_so_cat = cat_dau_cuoi.chuan_hoa(json.loads(cat) if cat.strip() else None)
    except cat_dau_cuoi.CatLoi as exc:
        return _lai_voi_loi(request, db, u, str(exc))
    except (ValueError, TypeError):
        return _lai_voi_loi(request, db, u, _t('Đoạn cắt không đọc được.'))
    # ⭐ CUNG mot cau voi cau giao dien hien khi khoa hai o (`asv-cat-chan`).
    #    Mot y, mot chuoi: hai cach dien dat cho cung mot luat la hai ban dich
    #    phai giu dong bo, va la hai co hoi de chung lech nhau.
    if cua_so_cat and preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        return _lai_voi_loi(request, db, u, _t(
            'Kiểu “Giữ nguyên hình ảnh” hứa video ra dài đúng bằng video vào, '
            'nên không cắt bớt được. Chọn “Rút gọn có biên tập” nếu bạn muốn cắt.'))

    # ── Lop phu chu (V6 pha 11) ─────────────────────────────────────────────
    #
    # ⭐ Tang thu nhat trong ba tang, y het `vung`. Va no dung o day — TRUOC khi
    #    giu credit — chu khong o `ban_dung.kiem`: mot lan chay bi chan o do la
    #    mot lan chay da di qua chin giai doan.
    try:
        ds_lop_phu = lop_phu_mod.chuan_hoa(
            json.loads(lop_phu) if lop_phu.strip() else [])
    except lop_phu_mod.LopPhuLoi as exc:
        return _lai_voi_loi(request, db, u, str(exc))
    except (ValueError, TypeError):
        return _lai_voi_loi(request, db, u, _t('Lớp phủ chữ không đọc được.'))
    # 🔴 Cung mot cau voi cau giao dien hien khi khoa cong cu, va cung mot ly do
    #    VAT LY voi vung che: `drawtext` la mot bo loc, bo loc doi hoi giai ma,
    #    `-c:v copy` khong giai ma khung nao.
    if ds_lop_phu and preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        return _lai_voi_loi(request, db, u, _t(
            'Kiểu “Giữ nguyên hình ảnh” sao chép nguyên vẹn từng điểm ảnh, nên '
            'không thể vẽ chữ lên hình. Chọn “Rút gọn có biên tập” nếu bạn muốn '
            'thêm lớp phủ chữ.'))

    # ⚠️ Cung luat voi vung che: sai thi TU CHOI, khong doan. Mot dong
    #    `Ten - cach doc` khong duoc tu hieu thanh dau `=` — doan dung mot
    #    lan thi lan sau khach tin rang ta luon doan dung.
    try:
        bang_tu_dien = tu_dien_mod.phan_tich(tu_dien)
    except tu_dien_mod.TuDienLoi as exc:
        return _lai_voi_loi(request, db, u, str(exc))

    # ⛔ Ban THO. Ho so that duoc `cai_dat_mod.chuan_hoa` sinh ra o duoi:
    #    no khai `schema`, gom `giong_id`/`voice_id` lam mot, va dat moi
    #    mac dinh o DUNG MOT cho. Truoc pha 07, muoi cho doc tu dat mac
    #    dinh cua rieng minh va hai trong so do da lech ve `timing_mode`.
    cai_dat = {"timing_mode": che_do, "preset": preset,
               "che_do_giong": che_do_giong, "giong_id": giong_id,
               "vung": ds_vung,
               "tu_dien": bang_tu_dien,
               # ⚠️ Giu `voice_id` cho tuong thich nguoc: `giai_doan_giong` doc
               #    no lam duong lui cho nhung run tao truoc pha 15.
               "voice_id": giong_id}
    # ⛔ L4 cua `cat_dau_cuoi`: khong thu hep gi thi KHONG ghi khoa nao.
    #
    #    `chuan_hoa` da tra `None` cho ca "vang mat" lan "(0.0, 1.0)", nen hai
    #    truong hop do khong the phan biet duoc o duoi — va do la chu y: chung
    #    la CUNG mot y dinh. Ghi mot khoa cho chung se lam moi lan chay khong
    #    cat cung mang mot truong ma khong lan nao dung toi.
    if cua_so_cat:
        cai_dat["cat"] = [cua_so_cat[0], cua_so_cat[1]]
    # ⛔ Cung luat: khong co lop nao thi KHONG ghi khoa. Mot mang rong ghi vao
    #    moi lan chay la mot truong khong ai doc, va no lam ho so cua nhung lan
    #    chay khong dung tinh nang nay khac di ma khong vi ly do gi.
    if ds_lop_phu:
        cai_dat["lop_phu"] = ds_lop_phu

    # ⭐ Ca tang doc + duyet + doi chieu preset nam o `phu_de.tu_form`, khong o
    #    day. Tep nay o 880/900 dong (`tools/lint_app_contract.py`), va hop dong
    #    app noi thang route khong phai cho chua nghiep vu.
    #
    # ⛔ `tu_form` chan truc DOT o preset giu hinh, nhung **khong** chan truc
    #    `.srt` — khac ba tinh nang tren. Xem docstring cua no.
    try:
        ho_so_phu_de = phu_de_mod.tu_form(phu_de, preset=preset)
    except phu_de_mod.PhuDeLoi as exc:
        return _lai_voi_loi(request, db, u, str(exc))
    if ho_so_phu_de:
        cai_dat["phu_de"] = ho_so_phu_de

    # ── Logo (V6 pha 11b) ───────────────────────────────────────────────────
    #
    # 🔑 Doc va kiem o day, nhung **LUU sau khi co `run`**: khoa artifact mang
    #    `run.id`, va `ban_dung.kiem` doi moi khoa la mot `AsvAsset` cua chinh
    #    lan chay do.
    try:
        ds_logo_hh, anh_logo = await _doc_logo(logo, logo_anh)
    except (logo_mod.LogoLoi, ValueError, TypeError) as exc:
        return _lai_voi_loi(request, db, u, str(exc) if isinstance(
            exc, logo_mod.LogoLoi) else _t('Logo không đọc được.'))
    if ds_logo_hh and preset != hop_dong_v4.PRESET_CAT_THONG_MINH:
        return _lai_voi_loi(request, db, u, _t(
            'Kiểu “Giữ nguyên hình ảnh” sao chép nguyên vẹn từng điểm ảnh, nên '
            'không thể dán logo lên hình. Chọn “Rút gọn có biên tập” nếu bạn '
            'muốn thêm logo.'))
    # ── Duong BEN VUNG: tep da nam trong kho, ta chi nhan mot ma ve ───────────
    #
    # ⭐ Dat truoc duong multipart co chu y. Khi ca hai cung co mat, duong ben
    #    vung phai thang — nguoc lai mot client cu gui kem ca hai se lang le keo
    #    ca lan chay ve duong co tran 90 MB.
    if upload_id:
        from platform_core.storage import get_storage
        try:
            _kho = get_storage()
            run = features.tao_run_tu_ve(
                db, _kho, owner_id=u.id, upload_id=upload_id,
                settings=cai_dat_mod.chuan_hoa(cai_dat))
            _gan_logo_vao_run(db, _kho, run=run, ds_hinh_hoc=ds_logo_hh,
                              anh=anh_logo)
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
                settings=cai_dat_mod.chuan_hoa(cai_dat))
            from platform_core.storage import get_storage as _lay_kho
            _gan_logo_vao_run(db, _lay_kho(), run=run, ds_hinh_hoc=ds_logo_hh,
                              anh=anh_logo)
            db.commit()
        except features.AsvError as exc:
            db.rollback()
            return _lai_voi_loi(request, db, u, str(exc))

    return RedirectResponse(f"{MANIFEST.route_prefix}/run/{run.id}",
                            status_code=303)


async def _doc_logo(hinh_hoc_json: str, tep: list | None
                    ) -> tuple[list[dict], list[tuple[bytes, str]]]:
    """`(hinh hoc da kiem, [(bytes, kieu)])` — CUNG do dai, hoac nem.

    ⛔ **Khong zip mu hai danh sach.** Lech so luong hay lech thu tu deu KHONG
       lam gi hong — chung chi lam logo thu nhat mang anh cua logo thu hai, dat
       o toa do cua logo thu nhat. Cung hinh dang loi ma `dung_lenh` da phai
       tu kiem cho `duong_lop` va `duong_chu`.

    ⚠️ Va tran kich thuoc ap **trong luc doc**, khong sau: mot tep 100 MB khong
       duoc cap phat 100 MB roi moi bi tu choi.
    """
    ds = logo_mod.chuan_hoa(json.loads(hinh_hoc_json) if hinh_hoc_json.strip()
                            else [])
    ds_tep = [t for t in (tep or []) if getattr(t, "filename", "")]
    if len(ds_tep) != len(ds):
        raise logo_mod.LogoLoi(_t(
            'Số ảnh logo ({co}) không khớp số logo đã đặt ({can}).').format(
                co=len(ds_tep), can=len(ds)))

    tran = features.tran_logo_byte()
    anh: list[tuple[bytes, str]] = []
    for t in ds_tep:
        du_lieu = await t.read()
        if len(du_lieu) > tran:
            raise logo_mod.LogoLoi(_t('Ảnh logo vượt quá {mb} MB.').format(
                mb=tran // (1024 * 1024)))
        if not du_lieu:
            raise logo_mod.LogoLoi(_t('Ảnh logo rỗng.'))
        anh.append((du_lieu, (t.content_type or "").split(";")[0].strip().lower()))
    return ds, anh


def _gan_logo_vao_run(db, kho, *, run, ds_hinh_hoc: list[dict],
                      anh: list[tuple[bytes, str]]) -> None:
    """Luu anh, gan khoa vao `run.settings["logo"]`, roi ghi lai settings.

    ⭐ Chay SAU `tao_run` va TRUOC `commit`, nen hoac ca run lan logo cung thanh,
       hoac ca hai cung khong — cung bat bien I2 ma `tao_run` giu cho tien.
    """
    if not ds_hinh_hoc:
        return
    khoa = features.gan_logo(db, kho, run=run, anh=anh)
    cai = dict(run.settings or {})
    # ⛔ `strict=True`: lech do dai o day lam logo thu nhat mang khoa cua
    #    logo thu hai — khong hong gi ca, chi SAI. `_doc_logo` da doi chieu
    #    mot lan, va chot nay la lan thu hai o dung cho hai mang gap nhau.
    #
    # ⭐ Chinh `ruff B905` bat duoc dong nay, sau khi toi vua viet mot bai
    #    kiem cam dung viec ay o `_doc_logo`. Mot bo lint doc CU PHAP thay
    #    duoc thu mot bai kiem doc HANH VI bo sot.
    cai["logo"] = [dict(h, khoa=k)
                   for h, k in zip(ds_hinh_hoc, khoa, strict=True)]
    # ⭐ Chuan hoa LAI sau khi them logo. Mot ho so duoc ghi hai lan ma
    #    chi chuan hoa mot lan la mot ho so co the ra khoi dang chuan o
    #    lan thu hai — va `cai_dat.chuan_hoa` luy dang nen goi lai khong
    #    ton gi.
    run.settings = cai_dat_mod.chuan_hoa(cai)
    db.flush()


def _lai_voi_loi(request: Request, db, u, thong_bao: str) -> HTMLResponse:
    return _dung_trang(request, "asv_trang_chinh.html",
                       _ngu_canh_studio(db, u, thong_bao), status_code=400)


@router.get("/run/{run_id}", response_class=HTMLResponse)
def chi_tiet(request: Request, run_id: str,
             _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
             db: Session = Depends(get_db)):
    # ⚠️ Nhap TRONG ham, cung khuon voi cac handler khac cua tep nay: kho luu
    #    tru duoc dung o dung mot vai cho, va keo no vao dau tep la bat moi
    #    tien trinh nap `routes` phai tra gia cho mot thu no khong goi.
    from platform_core.storage import get_storage

    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    return _dung_trang(request, "asv_chi_tiet.html", {
        "run": run,
        "dong": quan_sat.dong_thoi_gian(db, run),
        "van_hanh": (quan_sat.dong_thoi_gian(db, run, cho_van_hanh=True)
                     if _la_operator(request) else None),
        "loi_khach": quan_sat.tom_tat_loi_cho_khach(db, run),
        "co_ket_qua": bool(features.khoa_ket_qua(db, run)),
        # ⭐ Bang ke canh (V6 pha 09). `None` khi `edit_plan` chua xong — khoi
        #    giao dien khi do khong hien, chu khong hien mot khoi rong.
        #
        # 🔴 Truoc pha 09, chuoi nay tach canh bang ffmpeg, goi model doc tung
        #    canh — mot buoc CO TINH TIEN — roi quyet dinh bo canh nao, va khach
        #    khong thay duoc mot dong nao trong so do. Ho tra tien cho mot quyet
        #    dinh ho khong duoc xem.
        "canh": quan_sat.dong_canh(db, get_storage(), run),
        # ⭐ Hai bang nhan de man "Cai dat da dung" doc duoc `run.settings` bang
        #    TIENG VIET. Khong go lai nhan o template: chung song o `gia.py`, va
        #    hai ban cua mot nhan la hai ban se lech.
        "preset": gia.PRESET_BANG,
        "che_do": gia.CHE_DO_THOI_GIAN,
        # ⭐ Hai con so cua ho so (V6 pha 07). Truoc do khong ai tra loi duoc
        #    *"ho so nay theo schema nao"* va *"ca cau hinh bam ra gi"* — va cau
        #    thu hai la cau hoi DAU TIEN khi mot khach hoi vi sao hai lan chay
        #    trong nhu nhau lai cho hai ket qua khac nhau.
        #
        # ⚠️ `van_tay` tinh TAI CHO, khong doc mot gia tri da luu. Mot van tay
        #    duoc luu la mot van tay se cu di trong khi thu no dai dien thi doi,
        #    va no cu **im lang** — mot chuoi bam trong khong khac gi mot chuoi
        #    bam dung.
        # ⛔ Ban doc TOAN PHAN cho template. Truoc pha 07 template tu goi
        #    `run.settings.get(...)` **khong kem mac dinh**, nen mot ho so
        #    thieu khoa lam mot dong bien mat khoi man hinh — khach doc mot o
        #    trong o cho le ra phai noi cach khop thoi gian.
        "cai": cai_dat_mod.doc(run),
        "ho_so_phien_ban": cai_dat_mod.phien_ban_ho_so(run.settings),
        "ho_so_van_tay": cai_dat_mod.van_tay(run.settings),
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


# ══════════════════════════════════════════════════════════════════════════════
#  V5 — bon duong ma man Studio can
# ══════════════════════════════════════════════════════════════════════════════
#
# ⚠️ Ca bon deu giu nguyen bon tai san cua `CURRENT_UI_AUDIT.md` §3: co tinh nang
#    dat TRUOC `require_login`, loc chu so huu o TANG DICH VU qua `_run_cua_toi`,
#    404 chu khong 403, va CSRF tren moi duong ghi.
#
# ⭐ `test_455` cuong che ca bon bang AST tren TOAN BO tep, nen chung khong the
#    bi bo quen o day — do la ly do tep chot ay duoc viet TRUOC bon handler nay.


@router.get("/uoc-tinh")
def uoc_tinh(request: Request, giay: float = 0.0,
             _g: None = Depends(_cong_co),
             user: str = Depends(require_login)):
    """Uoc chi phi + thoi gian cho MOT do dai video, de hien truoc khi bam.

    🔴 **Vi sao la mot duong may chu chu khong phai vai dong JavaScript.**

       Cong thuc gia la mot thu san pham, khong phai mot hang so hien thi. Tinh
       no o trinh duyet la xuat ban no — va la tao mot ban thu hai se troi khoi
       ban that o `gia.py` ngay lan dau ai do sua mot con so.

    ⛔ Va o day khong co phep tinh nao: handler goi `gia.uoc_khoang` roi tra ve.
       Moi so deu do tang dich vu quyet dinh, dung nhu `test_423` chot.

    ⭐ Tra ve mot KHOANG, va giao dien hien can tren. `gia.BIEN_DO_UOC` ghi ly
       do: chi phi that ti le voi **luong noi**, con o day ta moi biet **do
       dai** — mot con so don se noi doi o it nhat mot trong hai truong hop.
    """
    thap, cao = gia.uoc_khoang(giay)
    return JSONResponse({
        "credit_thap": thap, "credit_cao": cao,
        "thoi_gian_giay": gia.uoc_thoi_gian_giay(giay),
        # ⛔ KHONG tra ve cong thuc, he so hay ten bien nao. Khach nhan CON SO.
    })


@router.get("/giong")
def danh_muc_giong(request: Request,
                   gioi: str = "", vung: str = "", phong_cach: str = "",
                   _g: None = Depends(_cong_co),
                   user: str = Depends(require_login),
                   db: Session = Depends(get_db)):
    """Danh muc giong da loc, kem duong nghe thu.

    ⛔ Loc o MAY CHU chu khong o trinh duyet, va khong phai vi hieu nang: danh
       sach nay da duoc `ltt_voice` loc theo chu so huu roi. Gui ca danh sach
       xuong roi de JavaScript an bot la gui **ten giong nhan ban cua nguoi
       khac** xuong may khach — chung chi bi an, khong bi vang mat.
    """
    u = user_hien_tai(request)
    if u is None:
        raise HTTPException(status_code=401)
    ds = gia.giong_cho_giao_dien(db, u.id)
    if gioi:
        ds = [g for g in ds if g.get("gioi") == gioi]
    if vung:
        ds = [g for g in ds if g.get("vung") == vung]
    if phong_cach:
        ds = [g for g in ds if g.get("phong_cach") == phong_cach]
    return JSONResponse({"giong": ds})


def _phuc_vu_inline(khoa: str, ten_goi: str):
    """Phuc vu mot tep de PHAT trong trang, khong de tai ve.

    🔑 Hai duong, va duong thu nhat la duong that o production:

      - Kho doi tuong (R2) tra presigned URL -> **307 sang thang CDN**. Tep
        khong di qua tien trinh nay va khong di qua Cloudflare, nen mot ban xem
        truoc 800 MB khong cham tran 100 MB lan tran 100 giay.
      - Kho cuc bo tra `None` (no khong cap presigned duoc) -> ta tu phuc vu.
        Do la duong cua may phat trien va cua bo test.

    ⚠️ `inline` chu khong `attachment`: mot `attachment` lam the `<video>` tai
       tep ve thay vi phat no.
    """
    from platform_core.storage import get_storage

    kho = get_storage()
    u = kho.url_for(khoa)
    if u:
        return RedirectResponse(u, status_code=307)
    return StreamingResponse(
        kho.open(khoa), media_type="video/mp4",
        headers={"Content-Disposition": f'inline; filename="{ten_goi}"'})


@router.get("/run/{run_id}/nguon")
def xem_nguon(request: Request, run_id: str,
              _g: None = Depends(_cong_co),
              user: str = Depends(require_login),
              db: Session = Depends(get_db)):
    """Video NGUON, de xem truoc va de ve vung che len tren.

    ⛔ Khong nhan `key` tu client — cung ly do voi `tai_ket_qua`: mot route trong
       do quyen so huu duoc suy tu mot chuoi khach gui len la dung hinh dang cua
       mot lo IDOR.

    🔴 Va o day hau qua nang hon mot bac: duong nay tra ve **video cua khach**.
       Mot lo o day khong ro ri mot dong sieu du lieu, no ro ri ca tep.
    """
    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    khoa = getattr(run, "source_key", "")
    if not khoa:
        raise HTTPException(status_code=404,
                            detail=_t('Lần chạy này không còn video nguồn.'))
    return _phuc_vu_inline(khoa, f"nguon-{run_id[:8]}.mp4")


@router.get("/run/{run_id}/xem")
def xem_ket_qua(request: Request, run_id: str,
                _g: None = Depends(_cong_co),
                user: str = Depends(require_login),
                db: Session = Depends(get_db)):
    """Ban long tieng, de PHAT trong trang ket qua.

    ⚠️ Khac `/tai` o dung mot cho: `Content-Disposition`. Giu hai duong rieng
       thay vi them mot tham so `?tai=1` la co y — mot tham so nhu the la mot
       duong dan de quen, va quen no lam nut "Tai video" phat nhac trong trang.
    """
    u = user_hien_tai(request)
    run = _run_cua_toi(db, run_id, u)
    khoa = features.khoa_ket_qua(db, run)
    if not khoa:
        raise HTTPException(status_code=404,
                            detail=_t('Lần chạy này chưa có kết quả.'))
    return _phuc_vu_inline(khoa, f"long-tieng-{run_id[:8]}.mp4")


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
