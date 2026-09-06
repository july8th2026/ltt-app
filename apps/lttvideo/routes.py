"""Giao diện `lttvideo` — **Unified Composer**, không tab mode.

⛔ Người dùng **không** chọn T2V / I2V / V2V / VACE / Animate. Đó là ngữ nghĩa
   thực thi của engine, và kiến trúc V2.1 §2.D đã dựng ranh giới: trình duyệt
   gửi **mô tả + tuỳ chọn đơn giản**, A-CONTROL chọn `profile_id`.

⛔ Route CHỈ lo HTTP (`AGENTS.md` §8.1). Quy tắc giá ở `cost`, quy tắc tham số ở
   `ho_so`, quy tắc quyền ở `kha_nang`. Không có con số nghiệp vụ nào trong tệp
   này — có phép kiểm canh (`test_724`).

Router **không** tự viết prefix `/lttvideo` — nền tảng gắn từ
`MANIFEST.route_prefix`. Tự viết là gắn hai lần.

App tự phục vụ video qua `/video/{key}`: khoá có dạng `lttvideo/{owner}/...` nên
kiểm sở hữu bằng chính khoá. Không dùng `download_token` của storage — token giữ
trong RAM của **từng tiến trình**, mà worker (tạo tệp) và web (phục vụ) là hai
tiến trình khác nhau.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from platform_core.i18n import _ as _t
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import require_login
from server.deps import user_hien_tai
from server.templating import templates

from . import cost, kha_nang

router = APIRouter(tags=["lttvideo"])

#: Tỉ lệ khung hình cho người dùng chọn — nhãn sản phẩm, không phải độ phân giải.
#: Ánh xạ sang `resolution` nằm ở `_DO_PHAN_GIAI` bên dưới, một chỗ duy nhất.
TI_LE = ("16:9", "9:16", "1:1")

_DO_PHAN_GIAI = {
    "16:9": "1280x720",
    "9:16": "720x1280",
    "1:1": "960x960",
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

    from platform_core.jobs import tao_job  # noqa: PLC0415 — tranh vong import

    job = tao_job(
        job_type="lttvideo.tao",
        user_id=user.id,
        params={
            "prompt": mo_ta,
            "duration_s": do_dai_s,
            "resolution": _DO_PHAN_GIAI[ti_le],
            "nguoi_dung_id": user.id,
        },
    )
    return RedirectResponse(f"?job={getattr(job, 'id', '')}", status_code=303)


@router.get("/video/{key:path}")
async def phuc_vu_video(key: str, user=Depends(require_login)):
    """Phục vụ video của **chính chủ**, kiểm sở hữu bằng tiền tố khoá."""
    from fastapi import HTTPException

    from platform_core.storage import get_storage

    if not key.startswith(f"lttvideo/{user.id}/"):
        raise HTTPException(status_code=404)

    kho = get_storage()
    if not kho.exists(key):
        raise HTTPException(status_code=404)

    return StreamingResponse(kho.open(key), media_type="video/mp4")
