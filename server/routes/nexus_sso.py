"""Đổi vé một-lần của ứng dụng LTT Nexus lấy phiên trình duyệt (B3).

Đây là nửa **trình duyệt** của cặp: nửa kia là `POST /nexus-agent/web-login`
(ứng dụng ký bằng khoá thiết bị để xin vé). Lý do và các ràng buộc bảo mật viết
ở `platform_core/nexus/sso.py` — đọc file đó trước khi sửa gì ở đây.

Ba điều dễ làm sai, đã chốt:

* **`GET` nhưng có tác dụng phụ.** Bình thường là mùi tệ; ở đây bắt buộc, vì thứ
  duy nhất ứng dụng làm được với trình duyệt là *mở một URL*. Bù lại bằng: vé
  dùng một lần, sống 90 giây, và trả `Cache-Control: no-store` để không nằm lại
  trong cache.
* **Chuyển hướng phải qua `safe_next`.** `next` đi từ ứng dụng qua thanh địa chỉ
  nên phải coi là dữ liệu người ngoài; không lọc thì đây là một open-redirect
  gắn sẵn phiên đăng nhập.
* **Vé hỏng không được nói vì sao.** Hết hạn, đã dùng, hay bịa ra — cùng một câu
  trả lời: về `/login`.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core import nexus
from server.auth.session import client_ip, log_in_db, safe_next

router = APIRouter(tags=["nexus-sso"])

#: Nexus tắt → 404 y như mọi bề mặt Nexus khác (Q93 fail-closed).
_TAT = HTMLResponse(status_code=404, content="Not found")

_NO_STORE = {"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"}


@router.get("/nexus-sso")
def doi_ve_lay_phien(request: Request):
    """Ứng dụng mở đường này kèm `?ma=<vé>` → đăng nhập rồi đi tiếp `next`."""
    if not nexus.enabled():
        return _TAT

    from platform_core.db import get_session
    from platform_core.nexus import sso

    dich = safe_next(request.query_params.get("next") or "/may-cua-toi")
    ma = request.query_params.get("ma") or ""

    sid = None
    gen = get_session(); db = next(gen)
    try:
        sid = sso.doi_ve(
            db, ma, ip=client_ip(request),
            user_agent=request.headers.get("user-agent", ""))
        if sid is not None:
            db.commit()
    finally:
        try: next(gen)
        except StopIteration: pass

    if sid is None:
        return RedirectResponse(f"/login?next={dich}", status_code=303,
                                headers=_NO_STORE)
    log_in_db(request, sid)
    return RedirectResponse(dich, status_code=303, headers=_NO_STORE)
