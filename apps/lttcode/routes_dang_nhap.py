"""HTTP của "Đăng nhập LTT Studios" cho LTTCODE. Nghiệp vụ ở `dang_nhap.py`.

Gắn vào router chính ở `routes.py` (nền tảng chỉ nạp `routes.router`).

Ba bề mặt, ba cách xác thực — cố ý:

* `/authorize` (GET trang xác nhận, POST form): **phiên web** của người dùng + CSRF.
  Không dùng `Depends(require_login)` vì nó làm rơi query string khi chuyển về
  `/login?next=` — mà query ở đây chính là PKCE challenge, state và port.
  Form POST trả một TRANG dẫn về `http://127.0.0.1:<port>/callback`, không 302:
  CSP nền tảng `form-action 'self'` khiến trình duyệt chặn redirect của form ra
  origin khác.
* `/token` (POST JSON): gọi từ ứng dụng desktop, không có cookie ⇒ không CSRF (CSRF
  bảo vệ phiên trình duyệt; request này không mang phiên nào). Bảo vệ bằng mã
  một lần + PKCE + giới hạn lượt theo IP.
* `/revoke` (POST): Bearer chính khoá cần thu hồi; luôn 204.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from apps.lttcode import dang_nhap
from platform_core.models import User
from platform_core.public_api import keys as devkeys
from platform_core.public_api import projects
from platform_core.public_api.scopes import ScopeError
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth.session import client_ip, current_identity_optional
from server.deps import get_db, user_hien_tai
from server.templating import templates

log = logging.getLogger(__name__)
router = APIRouter()

_KHONG_LUU = {"Cache-Control": "no-store"}


class GioiHanLuot:
    """Cửa sổ trượt trong tiến trình, theo khoá (IP). Đủ cho một máy chủ một tiến trình."""

    def __init__(self, toi_da: int, cua_so_s: float) -> None:
        self.toi_da, self.cua_so_s = toi_da, cua_so_s
        self._lan: dict[str, deque[float]] = {}
        self._khoa = threading.Lock()

    def cho_phep(self, khoa: str) -> bool:
        now = time.monotonic()
        with self._khoa:
            q = self._lan.setdefault(khoa, deque())
            while q and now - q[0] > self.cua_so_s:
                q.popleft()
            if len(q) >= self.toi_da:
                return False
            q.append(now)
            return True

    def xoa(self) -> None:
        with self._khoa:
            self._lan.clear()


GIOI_HAN_TOKEN = GioiHanLuot(dang_nhap.LUOT_TOKEN_MOI_PHUT, 60.0)


def _loi(request: Request, status: int) -> HTMLResponse:
    return templates.TemplateResponse(request, "lttcode_loi.html", {}, status_code=status, headers=_KHONG_LUU)


@router.get("/authorize")
async def trang_xac_nhan(request: Request, port: str = "", state: str = "", code_challenge: str = "",
                         code_challenge_method: str = "", device: str = ""):
    ts = dang_nhap.kiem_tham_so(port, state, code_challenge, code_challenge_method, device)
    if ts is None:
        return _loi(request, 400)
    if current_identity_optional(request) is None:
        dich = request.url.path + "?" + request.url.query
        return RedirectResponse(f"/login?next={quote(dich, safe='')}", status_code=303)
    user = user_hien_tai(request)
    if user is None:
        return _loi(request, 403)
    cong, st, challenge, may = ts
    return templates.TemplateResponse(request, "lttcode_authorize.html", {
        "email": getattr(user, "email", ""), "port": cong, "state": st, "code_challenge": challenge,
        "device": may, "csrf_token": issue_csrf_token(request)}, headers=_KHONG_LUU)


@router.post("/authorize")
def cho_phep(request: Request, port: str = Form(""), state: str = Form(""),
             code_challenge: str = Form(""), code_challenge_method: str = Form(""),
             device: str = Form(""), action: str = Form(""), csrf_token: str = Form(""),
             db: Session = Depends(get_db)):
    if not verify_csrf_token(request, csrf_token):
        return _loi(request, 400)
    ts = dang_nhap.kiem_tham_so(port, state, code_challenge, code_challenge_method, device)
    user = user_hien_tai(request)
    if ts is None or user is None:
        return _loi(request, 400)
    cong, st, challenge, may = ts
    if action != "allow":
        url = dang_nhap.url_loopback(cong, error="access_denied", state=st)
        dong_y = False
    else:
        code = dang_nhap.tao_ma(db, user_id=str(getattr(user, "id", "")), challenge=challenge,
                                port=cong, device=may)
        url = dang_nhap.url_loopback(cong, code=code, state=st)
        dong_y = True
    return templates.TemplateResponse(request, "lttcode_loopback.html",
                                      {"url": url, "dong_y": dong_y}, headers=_KHONG_LUU)


@router.post("/token")
async def doi_ma(request: Request, db: Session = Depends(get_db)):
    if not GIOI_HAN_TOKEN.cho_phep(client_ip(request)):
        return JSONResponse({"error": "slow_down"}, status_code=429, headers=_KHONG_LUU)
    try:
        body = await request.json()
    except ValueError:
        body = None
    body = body if isinstance(body, dict) else {}
    port = body.get("port")
    ket_qua = dang_nhap.doi_ma(db, code=body.get("code"), verifier=body.get("code_verifier"),
                               port=port if isinstance(port, int) else -1)
    if ket_qua is None:
        return JSONResponse({"error": "invalid_grant"}, status_code=400, headers=_KHONG_LUU)
    user_id, may = ket_qua
    try:
        row, token = dang_nhap.cap_khoa(db, user_id=user_id, device=may)
    except (devkeys.DeveloperKeyError, ScopeError, projects.ProjectError) as exc:
        log.warning("lttcode: cannot issue device key: %s", exc)
        return JSONResponse({"error": "cannot_issue_key", "message": str(exc)}, status_code=400,
                            headers=_KHONG_LUU)
    log.info("lttcode: issued device key %s", row.key_id)
    # `account` + `device`: để ứng dụng hiện "Đã đăng nhập: <email> · máy <tên>" thay
    # cho một chuỗi khoá che mặt nạ — người dùng vừa đăng nhập TÀI KHOẢN, không nhập khoá.
    user = db.get(User, user_id)
    return JSONResponse({"api_key": token, "key_id": row.key_id, "name": row.name,
                         "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                         "account": user.email if user is not None else "",
                         "device": may},
                        headers=_KHONG_LUU)


@router.post("/revoke")
def thu_hoi(request: Request, db: Session = Depends(get_db)):
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        key = devkeys.verify(db, header[7:].strip())
        if key is not None:
            devkeys.revoke(db, key)
            log.info("lttcode: device key %s revoked by its holder", key.key_id)
    return Response(status_code=204, headers=_KHONG_LUU)
