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

from fastapi import APIRouter, Depends, Form, Request
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

#: Độ dài cho chọn, theo giây. Trần 10 giây cho baseline.
DO_DAI_S = (5, 10)


def _uoc_gia() -> dict[int, int]:
    """Bảng ước phí cho từng độ dài, để hiện ngay trên giao diện."""
    return {g: cost.uoc_credit(giay_video=g) for g in DO_DAI_S}


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def trang_chinh(request: Request, user=Depends(require_login)):
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
        },
    )


@router.post("/tao")
async def tao_video(
    request: Request,
    prompt: str = Form(""),
    ti_le: str = Form("16:9"),
    do_dai_s: int = Form(5),
    csrf_token: str = Form(""),
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

    from platform_core.job_submit import submit_with_credit  # noqa: PLC0415

    from .manifest import MANIFEST

    job = submit_with_credit(
        db,
        user_id=user.id,
        app_slug=MANIFEST.slug,
        job_type="lttvideo.tao",
        params={
            "prompt": mo_ta,
            "duration_s": do_dai_s,
            "resolution": _DO_PHAN_GIAI[ti_le],
            "nguoi_dung_id": user.id,
        },
    )
    db.commit()
    return RedirectResponse(f"?job={getattr(job, 'id', '')}", status_code=303)


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
