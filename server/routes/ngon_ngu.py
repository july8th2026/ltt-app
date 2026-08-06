"""
ngon_ngu.py — đổi ngôn ngữ thủ công (H24).

Lựa chọn tường minh của người dùng phải **thắng mọi suy đoán của máy** và phải
**bền qua các phiên**. Đây là lỗi kinh điển của web đa ngôn ngữ: bấm đổi sang
tiếng Anh, tải lại trang, IP Việt Nam đẩy về tiếng Việt, đổi mãi không được.

Nên lưu ở hai chỗ:
- **cookie** — có tác dụng ngay, kể cả khi chưa đăng nhập;
- **hồ sơ phiên** — theo người chứ không theo máy.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from platform_core import i18n
from server.auth.csrf import verify_csrf_token
from server.auth.session import safe_next

router = APIRouter(tags=["i18n"])


@router.post("/doi-ngon-ngu")
def doi_ngon_ngu(request: Request, lang: str = Form(...),
                 csrf_token: str = Form(""), next: str = Form("/")):
    """Đổi ngôn ngữ rồi quay lại đúng trang đang đứng.

    Có CSRF vì đây là thao tác đổi trạng thái. Không có nó thì trang khác ép được
    người dùng đổi ngôn ngữ — phiền hơn là nguy hiểm, nhưng vẫn không nên để.
    """
    moi = i18n.chuan_hoa(lang)
    if moi is None or not verify_csrf_token(request, csrf_token):
        # Ngôn ngữ lạ hoặc token sai → không đổi gì, quay lại chỗ cũ. Kết quả an
        # toàn: giữ nguyên trạng thái đang có.
        return RedirectResponse(safe_next(next), status_code=303)

    # `safe_next` chặn open-redirect. Bóc tiền tố cũ rồi gắn tiền tố mới, nếu
    # không thì đang ở `/en/nap` đổi sang tiếng Việt sẽ ra `/en/nap` — đổi mà
    # không đổi.
    dich, _cu = i18n.tach_tien_to(safe_next(next))
    dich = i18n.them_tien_to(dich, moi)

    try:
        request.session["lang"] = moi          # theo người
    except Exception:                          # noqa: BLE001 - chưa có phiên
        pass

    resp = RedirectResponse(dich, status_code=303)
    resp.set_cookie(
        i18n.COOKIE, moi,
        max_age=i18n.COOKIE_TUOI,
        httponly=False,      # JS đọc được để hiện đúng trạng thái nút
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    return resp
