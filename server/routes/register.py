"""
register.py — đăng ký, xác thực email, quên/đặt lại mật khẩu (H1.3).

Đây là hệ quả trực tiếp của Q7 (tự đăng ký + credit dùng thử): nếu ai cũng tạo
được tài khoản đã-xác-thực ngay thì credit dùng thử bị hút cạn bằng tài khoản
ảo. Vì vậy đăng ký đi qua nhiều lớp chặn, và **credit dùng thử chỉ được cấp
sau khi xác thực email** (Q9).

Các route ở đây công khai (không cần đăng nhập) — nên chúng là bề mặt bị dò
nhiều nhất, và mọi phản hồi đều cố ý **không tiết lộ email nào đã đăng ký**.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from platform_core.antifraud import la_email_dung_mot_lan, vuot_gioi_han_ip
from platform_core.mailer import Email, get_mailer
from platform_core.tokens import (doc_token_dat_lai_mk, doc_token_xac_thuc_email,
                                  tao_token_dat_lai_mk, tao_token_xac_thuc_email)
from platform_core.users import (UserError, chuan_hoa_email, doi_mat_khau,
                                 tao_nguoi_dung, tim_theo_email)
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from server.auth import turnstile
from server.deps import mo_db_optional
from server.templating import templates

router = APIRouter(tags=["register"])

# Credit dùng thử cấp MỘT LẦN sau khi xác thực email (Q7). Chỉnh qua biến môi
# trường LTT_TRIAL_CREDIT; mặc định 20 (đủ chạy thử demo/tool nhẹ). Đặt 0 để tắt.
try:
    TRIAL_CREDIT_AMOUNT = max(0, int((os.environ.get("LTT_TRIAL_CREDIT") or "20").strip()))
except ValueError:
    TRIAL_CREDIT_AMOUNT = 20


def _client_ip(request: Request) -> str:
    # IP THẬT sau Cloudflare Tunnel — nếu dùng request.client.host thì mọi khách
    # đều là 127.0.0.1, cap đăng ký theo IP sẽ chặn cả nền tảng. Xem client_ip.
    from server.auth.session import client_ip
    return client_ip(request)


def _base_url(request: Request) -> str:
    # Dùng để dựng link tuyệt đối trong email. Tôn trọng proxy phía trước.
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("host", request.url.netloc)
    return f"{proto}://{host}"


def _render_register(request: Request, error: str = "", email: str = "",
                     status_code: int = 200) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "register.html",
        {
            "csrf_token": issue_csrf_token(request),
            "error": error, "email": email,
            "turnstile_site_key": turnstile.site_key(),
        },
        status_code=status_code,
    )


# ── Đăng ký ───────────────────────────────────────────────────────────────────

@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return _render_register(request)


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
    cf_turnstile_response: str = Form("", alias="cf-turnstile-response"),
):
    if not verify_csrf_token(request, csrf_token):
        return _render_register(request, "Phiên đã hết hạn — tải lại trang rồi thử lại.",
                                email, status_code=400)

    email = chuan_hoa_email(email)
    ip = _client_ip(request)

    # Kiểm tra rẻ trước, tốn kém sau.
    if not email or "@" not in email or not password:
        return _render_register(request, "Nhập email hợp lệ và mật khẩu.", email, 400)
    if len(password) < 8:
        return _render_register(request, "Mật khẩu tối thiểu 8 ký tự.", email, 400)
    if la_email_dung_mot_lan(email):
        return _render_register(request, "Email dùng-một-lần không được chấp nhận. "
                                "Dùng email thật.", email, 400)
    if not turnstile.xac_minh(cf_turnstile_response, remote_ip=ip):
        return _render_register(request, "Xác minh chống bot thất bại — thử lại.",
                                email, 400)

    with mo_db_optional() as db:
        if db is None:
            return _render_register(request, "Hệ thống chưa sẵn sàng nhận đăng ký "
                                    "(chưa cấu hình CSDL).", email, 503)

        if vuot_gioi_han_ip(db, ip):
            # Không nói rõ "IP của bạn đã tạo quá nhiều" — chỉ báo chung.
            return _render_register(request, "Đã đạt giới hạn tạo tài khoản hôm nay. "
                                    "Thử lại sau.", email, 429)

        try:
            user = tao_nguoi_dung(db, email=email, password=password,
                                  is_verified=False, registration_ip=ip)
        except UserError:
            # Email đã tồn tại: KHÔNG báo thẳng (lộ email đã đăng ký). Giả vờ đã
            # gửi thư như trường hợp thành công; người sở hữu email thật sẽ nhận
            # được thông báo tài khoản đã tồn tại, kẻ dò thì không phân biệt được.
            return templates.TemplateResponse(request, "register_sent.html",
                                              {"email": email})

        token = tao_token_xac_thuc_email(user.id)

    link = f"{_base_url(request)}/verify-email?token={token}"
    _gui_mail_xac_thuc(email, link)
    return templates.TemplateResponse(request, "register_sent.html", {"email": email})


def _gui_mail_xac_thuc(email: str, link: str) -> None:
    get_mailer().send(Email(
        to=email,
        subject="Xác thực tài khoản LTT AI Studio",
        html=(f"<p>Chào bạn,</p><p>Bấm vào liên kết dưới đây để xác thực tài "
              f"khoản (hết hạn sau 24 giờ):</p>"
              f'<p><a href="{link}">{link}</a></p>'
              f"<p>Nếu bạn không đăng ký, bỏ qua email này.</p>"),
        text=f"Xác thực tài khoản: {link}",
    ))


# ── Xác thực email ────────────────────────────────────────────────────────────

@router.get("/verify-email", response_class=HTMLResponse)
def verify_email(request: Request, token: str = ""):
    user_id = doc_token_xac_thuc_email(token)
    ok = False
    if user_id:
        with mo_db_optional() as db:
            if db is not None:
                from platform_core.models import User
                user = db.get(User, user_id)
                if user is not None:
                    was_verified = user.is_verified
                    user.is_verified = True
                    ok = True
                    # Cấp credit dùng thử MỘT LẦN, đúng lần xác thực đầu tiên
                    # (Q7 + Q9 — chỉ sau khi email đã xác thực). Idempotent theo
                    # chuyển trạng thái: bấm lại link (đã verified) không cấp lại.
                    if not was_verified and TRIAL_CREDIT_AMOUNT > 0:
                        from platform_core.credit import cap_tay
                        cap_tay(db, user.id, TRIAL_CREDIT_AMOUNT, by="system",
                                note="Credit dùng thử sau xác thực email")
    return templates.TemplateResponse(
        request, "verify_result.html", {"ok": ok},
        status_code=200 if ok else 400,
    )


# ── Quên / đặt lại mật khẩu ───────────────────────────────────────────────────

@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_form(request: Request):
    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"csrf_token": issue_csrf_token(request), "sent": False, "error": ""},
    )


@router.post("/forgot-password", response_class=HTMLResponse)
def forgot_submit(request: Request, email: str = Form(""), csrf_token: str = Form("")):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "forgot_password.html",
            {"csrf_token": issue_csrf_token(request), "sent": False,
             "error": "Phiên đã hết hạn — thử lại."}, status_code=400)

    email = chuan_hoa_email(email)
    # Rate-limit (W1.4): không có giới hạn thì đây là vòi gửi mail — kẻ xấu bơm
    # reset về một email (quấy rối) và đốt hạn ngạch Resend. Khoá theo IP THẬT +
    # theo email, dùng chung limiter với login.
    lim = request.app.state.login_rate_limiter
    if not lim.allow("forgot-ip:" + _client_ip(request)) or not lim.allow("forgot-email:" + email):
        return templates.TemplateResponse(
            request, "forgot_password.html",
            {"csrf_token": issue_csrf_token(request), "sent": False,
             "error": "Bạn yêu cầu quá nhiều lần — vui lòng đợi 1 phút rồi thử lại."},
            status_code=429)

    with mo_db_optional() as db:
        if db is not None:
            user = tim_theo_email(db, email)
            if user is not None:
                token = tao_token_dat_lai_mk(user.id)
                link = f"{_base_url(request)}/reset-password?token={token}"
                get_mailer().send(Email(
                    to=email, subject="Đặt lại mật khẩu LTT AI Studio",
                    html=(f"<p>Bấm để đặt lại mật khẩu (hết hạn sau 1 giờ):</p>"
                          f'<p><a href="{link}">{link}</a></p>'
                          f"<p>Nếu bạn không yêu cầu, bỏ qua email này.</p>"),
                    text=f"Đặt lại mật khẩu: {link}",
                ))
    # LUÔN báo như nhau, dù email có tồn tại hay không — không lộ danh sách khách.
    return templates.TemplateResponse(
        request, "forgot_password.html",
        {"csrf_token": issue_csrf_token(request), "sent": True, "error": ""})


@router.get("/reset-password", response_class=HTMLResponse)
def reset_form(request: Request, token: str = ""):
    hop_le = doc_token_dat_lai_mk(token) is not None
    return templates.TemplateResponse(
        request, "reset_password.html",
        {"csrf_token": issue_csrf_token(request), "token": token,
         "hop_le": hop_le, "error": ""},
        status_code=200 if hop_le else 400,
    )


@router.post("/reset-password", response_class=HTMLResponse)
def reset_submit(request: Request, token: str = Form(""), password: str = Form(""),
                 csrf_token: str = Form("")):
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"csrf_token": issue_csrf_token(request), "token": token,
             "hop_le": True, "error": "Phiên đã hết hạn — thử lại."}, status_code=400)

    user_id = doc_token_dat_lai_mk(token)
    if not user_id:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"csrf_token": issue_csrf_token(request), "token": token,
             "hop_le": False, "error": "Liên kết hết hạn hoặc không hợp lệ."},
            status_code=400)
    if len(password) < 8:
        return templates.TemplateResponse(
            request, "reset_password.html",
            {"csrf_token": issue_csrf_token(request), "token": token,
             "hop_le": True, "error": "Mật khẩu tối thiểu 8 ký tự."}, status_code=400)

    with mo_db_optional() as db:
        if db is not None:
            from platform_core.models import User
            user = db.get(User, user_id)
            if user is not None:
                # doi_mat_khau thu hồi MỌI phiên — kẻ đã chiếm phiên mất quyền.
                doi_mat_khau(db, user, password)
    return RedirectResponse("/login", status_code=303)
