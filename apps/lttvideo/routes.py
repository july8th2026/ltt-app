"""Giao diện `lttvideo` — **Unified Composer**, không tab mode.

⛔ Người dùng **không** chọn T2V / I2V / V2V / VACE / Animate. Đó là ngữ nghĩa
   thực thi của engine, và kiến trúc V2.1 §2.D đã dựng ranh giới: trình duyệt
   gửi **mô tả + tuỳ chọn đơn giản**, A-CONTROL chọn `profile_id`.

⛔ Route CHỈ lo HTTP (`AGENTS.md` §8.1). Quy tắc giá ở `cost`, quy tắc tham số ở
   `ho_so`, quy tắc quyền ở `kha_nang`. Không có con số nghiệp vụ nào trong tệp
   này — có phép kiểm canh (`test_724`).

Router **không** tự viết prefix `/lttvideo` — nền tảng gắn từ
`MANIFEST.route_prefix`. Tự viết là gắn hai lần.

App tự phục vụ video qua `/video/{key}`, kiểm sở hữu bằng **danh sách trắng khuôn
khoá** (`khoa_hop_le`) chứ không bằng tiền tố — xem chú thích ở `_KHUON_KHOA`.
Không dùng `download_token` của storage: token giữ trong RAM của **từng tiến
trình**, mà worker (tạo tệp) và web (phục vụ) là hai tiến trình khác nhau.
"""
from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db, user_hien_tai
from server.templating import templates

from . import cost, features, kha_nang
from .manifest import MANIFEST

router = APIRouter(tags=["lttvideo"])


def _nguoi_dung(request: Request):
    """User **CSDL** của phiên hiện tại.

    🔴 `require_login` trả về một **chuỗi** (email, hoặc username của đường
       admin-env) — xem docstring của nó. Nó là *cổng* 303, không phải nguồn
       user. Bản đầu của tệp này đối xử với giá trị ấy như một đối tượng, và hai
       kiểu hỏng đi kèm nhau:

       1. `user.id` ném `AttributeError` ⇒ trang **500**. Ồn ào, thấy ngay khi
          mở trang bằng trình duyệt.
       2. `getattr(user, "vai", "nhan_vien")` **không** ném gì cả — nó trả về giá
          trị mặc định. Nghĩa là phép kiểm quyền của app chưa từng đọc vai thật
          của ai; nó luôn chấm trên một hằng số. Im lặng, và là cái tệ hơn.

    ⭐ Trả `None` khi đăng nhập bằng admin-env (không có hàng trong `users`).
       Đường ấy là lối vận hành, không chạy job — nên nơi gọi phải xử lý `None`
       chứ không được giả định có user.
    """
    return user_hien_tai(request)

#: 🔴 Khuôn khoá video — DANH SÁCH TRẮNG, không phải bộ lọc `..`.
#:
#: `key.startswith(f"lttvideo/{user.id}/")` một mình **KHÔNG đủ**:
#: `lttvideo/42/../../khac/bi_mat.mp4` qua được phép kiểm tiền tố nhưng đường
#: dẫn giải ra thì thoát khỏi thư mục của chủ.
#:
#: ⭐ Khoá do `jobs._khoa_kho()` sinh luôn có dạng cố định, nên khớp **đúng
#:    khuôn đó** vừa chặt hơn vừa ngắn hơn việc đi liệt kê thứ cần chặn — và
#:    `test_724` đối chứng hai bên bằng chính hàm sinh khoá.
_KHUON_KHOA = re.compile(r"^lttvideo/(\d+)/[0-9a-f]{32}\.(mp4|webm)$")


def khoa_hop_le(key: str, user_id) -> bool:
    """Khoá này có đúng khuôn LTT sinh ra, và có thuộc về `user_id` không?"""
    m = _KHUON_KHOA.match(key or "")
    if m is None:
        return False
    return m.group(1) == str(user_id)


#: Tỉ lệ khung hình cho người dùng chọn — nhãn sản phẩm, không phải độ phân giải.
#: Ánh xạ sang `resolution` nằm ở `_DO_PHAN_GIAI` bên dưới, một chỗ duy nhất.
TI_LE = ("16:9", "9:16", "1:1")

#: ⛔ Ba giá trị này lấy **nguyên văn** từ nhóm `# 480p` của
#:   `Wan2GP/shared/resolutions.py:DEFAULT_RESOLUTION_CHOICES`. Không tự tính
#:   ra từ tỉ lệ: WanGP chọn kích thước chia hết cho `vae_block_size`, nên một
#:   con số "đúng tỉ lệ" mà không có trong danh sách của nó là một con số WanGP
#:   sẽ phải làm tròn lại.
#:
#: 🔴 Bản trước dùng nhóm **720p** (`1280x720` · `720x1280` · `960x960`). Nó đi
#:   CỬA TRƯỚC — route gửi `resolution` như khoá người dùng đổi được, nên nó ghi
#:   đè hồ sơ. Tức chữa hồ sơ về 480p mà quên chỗ này thì 720p vẫn quay lại,
#:   lặng lẽ, và hồ sơ trông vẫn đúng.
_DO_PHAN_GIAI = {
    "16:9": "832x480",
    "9:16": "480x832",
    "1:1": "720x720",
}

#: Độ dài cho chọn, theo giây.
#:
#: ⭐ 15 giây làm được vì `t2v_2_2` có `sliding_window` (`wan_handler.py:368`).
#:    WanGP ghép nhiều cửa sổ và mã hoá MỘT lần — `PROCESSING.md` gọi đó là
#:    "best technical quality".
#:
#: ⛔ KHÔNG tự quy ra số khung ở đây. `apply_video_length_duration()` của WanGP
#:    nhận thẳng chuỗi `"15s"` và chọn số khung hợp lệ cho model
#:    (`frames_minimum=5`, `frames_steps=4`). Tự tính là dựng bản sao thứ hai
#:    của một quy tắc thượng nguồn.
DO_DAI_S = (5, 10, 15)


#: Trần cỡ tệp video đính kèm. Ảnh đã có trần riêng 8 MB trong
#: `platform_core.image_input`; video thì chưa ai đặt, và Cloudflare cắt ở
#: **100 MB** mỗi request (`CLAUDE.md`) nên đặt dưới mức đó là bắt buộc —
#: vượt trần Cloudflare thì người dùng nhận HTTP 413 **trước khi** chạm máy chủ,
#: tức ta không có cơ hội báo lỗi tử tế.
TRAN_VIDEO_BYTE = 80 * 1024 * 1024

#: Đuôi tệp theo MIME. Dùng bảng thay vì cắt tên tệp người dùng gửi lên: tên ấy
#: do trình duyệt cung cấp và không có gì bảo đảm nó khớp nội dung.
_DUOI_THEO_MIME = {
    "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp",
    "video/mp4": "mp4",
}


class LoiMedia(ValueError):
    """Media đính kèm không dùng được. Thông điệp đưa thẳng ra giao diện."""


def _luu_media(media, nguoi_dung_id) -> str:
    """Kiểm rồi cất media người dùng đính kèm; trả khoá kho, hoặc chuỗi rỗng.

    ⛔ Ảnh đi qua `platform_core.image_input.validate_reference` — nó **giải mã
       thật** chứ không tin MIME của trình duyệt. Chép lại phép kiểm ấy ở đây là
       dựng bản sao thứ hai của một quy tắc bảo mật.
    """
    if media is None or not getattr(media, "filename", ""):
        return ""
    du_lieu = media.file.read()
    mime = (getattr(media, "content_type", "") or "").lower()

    if mime.startswith("image/"):
        from platform_core.image_input import validate_reference  # noqa: PLC0415
        try:
            mime, _kich_thuoc = validate_reference(du_lieu, mime)
        except ValueError as e:
            raise LoiMedia(str(e)) from e
    elif mime == "video/mp4":
        if not du_lieu:
            raise LoiMedia(_t("Tệp đính kèm rỗng."))
        if len(du_lieu) > TRAN_VIDEO_BYTE:
            raise LoiMedia(_t("Video đính kèm vượt giới hạn 80 MB."))
    else:
        raise LoiMedia(_t("Chỉ nhận ảnh PNG/JPEG/WebP hoặc video MP4."))

    from platform_core.storage import get_storage  # noqa: PLC0415

    duoi = _DUOI_THEO_MIME.get(mime, "bin")
    khoa = f"lttvideo/{nguoi_dung_id}/vao/{uuid.uuid4().hex}.{duoi}"
    get_storage().put(khoa, du_lieu, mime)
    return khoa


def _uoc_gia() -> dict[int, int]:
    """Bảng ước phí cho từng độ dài, để hiện ngay trên giao diện."""
    return {g: cost.uoc_credit(giay_video=g) for g in DO_DAI_S}


#: Nhan tab, ghep voi `features.TRANG_THAI_TAB`. Nhan o day (viec cua HTTP),
#: khoa o kia (viec cua nghiep vu) — khong tron hai thu.
_NHAN_TAB = {
    "all": N_("Tất cả"), "running": N_("Đang xử lý"), "done": N_("Hoàn tất"),
    "error": N_("Lỗi"), "cancelled": N_("Đã huỷ"),
}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def trang_chinh(request: Request, _dinh_danh: str = Depends(require_login),
                      db=Depends(get_db)):
    nd = _nguoi_dung(request)
    vai = getattr(nd, "role", "") or ""
    duoc, ly_do = kha_nang.kiem("tao_video", vai=vai)

    tt = str(request.query_params.get("trang_thai") or "all")
    if tt not in features.TRANG_THAI_TAB:
        tt = "all"
    sx = "cu" if request.query_params.get("sap_xep") == "cu" else "moi"

    kho_du_lieu = (features.thu_vien(db, nd.id, trang_thai=tt, sap_xep=sx)
                   if duoc and nd is not None
                   else {"so_dem": {}, "video": [], "prompt_gan_day": [],
                         "tai_san": []})

    return templates.TemplateResponse(
        request,
        "lttvideo.html",
        {
            "user": nd,
            # `app` cho `{{ app.route_prefix }}` trong template, `nav` de thanh
            # ben to sang muc dang mo — cung khuon `thumbnail`/`taovideo`.
            "app": MANIFEST,
            "nav": MANIFEST.slug,
            "csrf_token": issue_csrf_token(request),
            "ti_le": TI_LE,
            "do_dai": DO_DAI_S,
            "uoc_gia": _uoc_gia(),
            "duoc_dung": duoc,
            "ly_do_tu_choi": ly_do,
            # `A5`: chua mo thi KHONG ve o tick. Xem `kha_nang.NANG_LUC_MO`.
            "duoc_mo_rong": kha_nang.duoc_phep("mo_rong_prompt", vai=vai),
            "trang_thai_tab": [(k, _t(_NHAN_TAB[k]))
                               for k in features.TRANG_THAI_TAB],
            "loc_trang_thai": tt,
            "loc_sap_xep": sx,
            **kho_du_lieu,
        },
    )


@router.get("/trang-thai-may", response_class=HTMLResponse)
async def trang_thai_may(request: Request,
                         _dinh_danh: str = Depends(require_login)):
    """Một dòng nói máy dựng đang bật hay tắt.

    🔴 Vì sao cần: `B1` bật máy **theo nhu cầu**, và lượt đầu sau khi máy nghỉ
       phải chờ khởi động (trần `dieu_phoi.CHO_TOI_DA_S` = 900 giây). Seedance
       không có vấn đề này vì nó gọi một API luôn sẵn sàng. Im lặng ở đây thì
       người dùng đọc mười lăm phút chờ thành "hỏng rồi".

    ⛔ KHÔNG hỏi RunPod ở đây. Trang chủ mà đi gọi một API ngoài là buộc thời
       gian dựng trang vào độ trễ của người khác. Chỉ đọc cấu hình.
    """
    import os  # noqa: PLC0415

    if not (os.environ.get("LTTV_POD_ID") or "").strip():
        # Khong cau hinh pod = moi truong co may chay san. Khong doa nguoi dung
        # bang mot canh bao khong dung voi ho.
        return HTMLResponse("")
    return HTMLResponse(
        f"<span>{_t('Máy dựng bật theo nhu cầu — lượt đầu có thể mất thêm vài phút để khởi động.')}</span>")


@router.post("/tao")
async def tao_video(
    request: Request,
    prompt: str = Form(""),
    ti_le: str = Form("16:9"),
    do_dai_s: int = Form(5),
    mo_rong_prompt: str = Form(""),
    tai_san_khoa: str = Form(""),
    seed: str = Form(""),
    negative_prompt: str = Form(""),
    csrf_token: str = Form(""),
    media: UploadFile | None = File(None),
    _dinh_danh: str = Depends(require_login),
    db=Depends(get_db),
):
    verify_csrf_token(request, csrf_token)

    user = _nguoi_dung(request)
    if user is None:
        # Dang nhap bang admin-env: khong co hang trong `users`, nen khong co so
        # credit de tru va khong co chu de gan job. Tu choi ro rang.
        return RedirectResponse(
            f"?loi={_t('Hãy đăng nhập bằng tài khoản người dùng để tạo video.')}",
            status_code=303)

    vai = getattr(user, "role", "") or ""
    duoc, ly_do = kha_nang.kiem("tao_video", vai=vai)
    if not duoc:
        return RedirectResponse(f"?loi={ly_do}", status_code=303)

    mo_ta = (prompt or "").strip()
    if not mo_ta:
        return RedirectResponse(f"?loi={_t('Hãy mô tả video bạn muốn.')}",
                                status_code=303)

    if ti_le not in _DO_PHAN_GIAI:
        ti_le = "16:9"
    if do_dai_s not in DO_DAI_S:
        do_dai_s = DO_DAI_S[0]

    try:
        media_key = _luu_media(media, user.id)
    except LoiMedia as e:
        return RedirectResponse(f"?loi={e}", status_code=303)

    from platform_core.job_submit import (  # noqa: PLC0415
        dedupe_key_for, submit_with_credit)

    tham_so = {
        "prompt": mo_ta,          # `C3`: nen tang luu `params` => lich su co prompt
        "duration_s": do_dai_s,
        "resolution": _DO_PHAN_GIAI[ti_le],
        "nguoi_dung_id": user.id,
    }

    # ── Hai tuy chon nang cao ────────────────────────────────────────────
    #
    # ⭐ Ca hai DA nam trong `ho_so.KHOA_NGUOI_DUNG_DOI_DUOC` tu dau; thu thieu
    #    la mot o nhap tren giao dien. Nguoi dung khong dieu khien duoc thu ma
    #    kien truc da cho phep ho dieu khien.
    #
    # ⛔ Bo QUA gia tri sai thay vi bao loi: mot seed go nham khong dang lam
    #    hong ca luot tao. WanGP tu chon seed khi khong co.
    if seed.strip():
        try:
            gia_tri = int(seed.strip())
        except ValueError:
            gia_tri = -1
        if 0 <= gia_tri <= 2147483647:
            tham_so["seed"] = gia_tri
    if negative_prompt.strip():
        tham_so["negative_prompt"] = negative_prompt.strip()[:2000]
    if media_key:
        tham_so["media_key"] = media_key
    elif tai_san_khoa:
        # 🔴 KHONG tin khoa do trinh duyet gui. `features.khoa_tai_san_hop_le`
        #    doi chieu voi chinh lich su job CUA CHU va kiem tep con ton tai —
        #    cung ho bao ve voi `_KHUON_KHOA`: mot danh sach trang dung tu du
        #    lieu cua chu, khong phai mot bo loc chuoi.
        from sqlalchemy import select  # noqa: PLC0415

        from platform_core.models import Job  # noqa: PLC0415

        cua_toi = db.execute(
            select(Job).where(Job.user_id == user.id,
                              Job.app_slug == MANIFEST.slug)
            .order_by(Job.created_at.desc())
            .limit(features.GIOI_HAN_THU_VIEN)).scalars().all()
        if not features.khoa_tai_san_hop_le(cua_toi, tai_san_khoa):
            return RedirectResponse(
                f"?loi={_t('Tài sản đã chọn không còn dùng được.')}",
                status_code=303)
        tham_so["media_key"] = tai_san_khoa

    # ⛔ KHÔNG tin ô tick trong biểu mẫu. Trình duyệt gửi được bất cứ trường nào;
    #    năng lực chưa mở mà vẫn nhận là mở cửa sau cho đúng thứ `kha_nang` đang
    #    đóng. Nhánh này hỏi lại chính sách, không đọc lại thứ vừa nhận.
    if mo_rong_prompt and kha_nang.duoc_phep("mo_rong_prompt", vai=vai):
        tham_so["mo_rong_prompt"] = True

    # ⛔ `dedupe_key_for` chan F5 / bam hai lan: cung `job_type` + cung `params`
    #    trong khi job CU CHUA XONG => tra ve job cu, KHONG tru tien lan hai.
    #    Docstring cua no noi "moi route submit NEN truyen khoa nay"; day la mot
    #    lop bao ve da co san ma app khong dung thi tu minh chiu.
    #
    # ⚠️ Voi luot CO DINH MEDIA thi lop nay yeu hon: moi lan tai len sinh mot
    #    `media_key` khac (uuid), nen hai lan bam ra hai khoa khac nhau. Chan
    #    duoc truong hop pho bien nhat (khong media), va noi ro gioi han thay vi
    #    de nguoi sau tuong no chan tat ca.
    job = submit_with_credit(
        db,
        user_id=user.id,
        app_slug=MANIFEST.slug,
        job_type="lttvideo.tao",
        params=tham_so,
        dedupe_key=dedupe_key_for("lttvideo.tao", tham_so),
    )
    db.commit()
    # ⭐ Di thang toi trang job CUA NEN TANG: o do da co tien do tu dieu nhip,
    #    nut huy, dong thoi gian va o tai ket qua. Dung tu dung mot man cho.
    return RedirectResponse(f"/jobs/{getattr(job, 'id', '')}", status_code=303)


@router.get("/video/{key:path}")
async def phuc_vu_video(key: str, request: Request,
                        _dinh_danh: str = Depends(require_login)):
    """Phục vụ video của **chính chủ**, kiểm bằng danh sách trắng khuôn khoá."""
    from fastapi import HTTPException

    from platform_core.storage import get_storage

    nd = _nguoi_dung(request)
    if nd is None or not khoa_hop_le(key, nd.id):
        raise HTTPException(status_code=404)

    kho = get_storage()
    if not kho.exists(key):
        raise HTTPException(status_code=404)

    return StreamingResponse(kho.open(key), media_type="video/mp4")
