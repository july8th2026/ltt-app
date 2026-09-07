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

from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import get_db
from server.templating import templates

from . import cost, kha_nang

router = APIRouter(tags=["lttvideo"])

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


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def trang_chinh(request: Request, user=Depends(require_login),
                      db=Depends(get_db)):
    duoc, ly_do = kha_nang.kiem("tao_video", vai=getattr(user, "vai", "nhan_vien"))
    return templates.TemplateResponse(
        request,
        "lttvideo.html",
        {
            "user": user,
            "csrf_token": issue_csrf_token(request),
            "ti_le": TI_LE,
            "do_dai": DO_DAI_S,
            "uoc_gia": _uoc_gia(),
            "duoc_dung": duoc,
            "ly_do_tu_choi": ly_do,
            "video_gan_day": _video_gan_day(db, user.id) if duoc else [],
        },
    )


@router.post("/tao")
async def tao_video(
    request: Request,
    prompt: str = Form(""),
    ti_le: str = Form("16:9"),
    do_dai_s: int = Form(5),
    csrf_token: str = Form(""),
    media: UploadFile | None = File(None),
    user=Depends(require_login),
    db=Depends(get_db),
):
    verify_csrf_token(request, csrf_token)

    duoc, ly_do = kha_nang.kiem("tao_video", vai=getattr(user, "vai", "nhan_vien"))
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

    from .manifest import MANIFEST

    tham_so = {
        "prompt": mo_ta,          # `C3`: nen tang luu `params` => lich su co prompt
        "duration_s": do_dai_s,
        "resolution": _DO_PHAN_GIAI[ti_le],
        "nguoi_dung_id": user.id,
    }
    if media_key:
        tham_so["media_key"] = media_key

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


def _job_video_cua_toi(db, user_id, job_id: str):
    """Job `lttvideo` ĐÃ XONG và thuộc về `user_id`, hoặc `None`.

    ⛔ Kiểm **cả ba**: đúng chủ, đúng app, đã xong. Thiếu vế "đúng app" thì một
       `job_id` của app khác cũng qua được, và ta sẽ đem khoá của nó đi nâng cấp.
    """
    from platform_core.models import Job  # noqa: PLC0415

    j = db.get(Job, (job_id or "")[:36])
    if j is None or str(j.user_id) != str(user_id):
        return None
    if j.app_slug != "lttvideo" or j.status != "done":
        return None
    return j


def _khoa_video(job) -> str:
    """Khoá video đầu tiên trong kết quả, hoặc rỗng.

    ⭐ Dùng để dựng nút **Nâng nét** — một `<form>` post thẳng sang bề mặt HTTP
       công khai của `upscalevideo`. Xem chú thích ở template.
    """
    ds = (job.result or {}).get("video_keys") or []
    return str(ds[0]) if ds else ""


def _video_gan_day(db, user_id, gioi_han: int = 12) -> list[dict]:
    """Vài video mới nhất của chính chủ, để trang app có chỗ bấm Nâng nét.

    📌 Đây **không** phải một trang lịch sử thứ hai — lịch sử là
       `/jobs?app=lttvideo` của nền tảng. Đây là chỗ đặt **hành động riêng của
       app**, thứ trang job dùng chung không có móc để cắm vào.
    """
    from platform_core.models import Job  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    rows = db.execute(
        select(Job).where(Job.user_id == user_id, Job.app_slug == "lttvideo",
                          Job.status == "done")
        .order_by(Job.created_at.desc()).limit(gioi_han)
    ).scalars().all()
    ra = []
    for j in rows:
        khoa = _khoa_video(j)
        if khoa:
            ra.append({"job_id": j.id, "khoa": khoa,
                       "prompt": (j.params or {}).get("prompt", ""),
                       "luc": j.created_at})
    return ra


@router.get("/video/{key:path}")
async def phuc_vu_video(key: str, user=Depends(require_login)):
    """Phục vụ video của **chính chủ**, kiểm bằng danh sách trắng khuôn khoá."""
    from fastapi import HTTPException

    from platform_core.storage import get_storage

    if not khoa_hop_le(key, user.id):
        raise HTTPException(status_code=404)

    kho = get_storage()
    if not kho.exists(key):
        raise HTTPException(status_code=404)

    return StreamingResponse(kho.open(key), media_type="video/mp4")
