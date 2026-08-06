"""Login / logout routes (P3)."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from server.auth import turnstile
from server.auth.csrf import issue_csrf_token, verify_csrf_token
from platform_core.password_hashing import verify_password
from server.auth.rate_limit import RateLimiter
from server.auth.session import (client_ip, current_identity_optional, log_in,
                                 log_in_db, log_out, safe_next)
from server.deps import mo_db_optional
from server.templating import templates

router = APIRouter(tags=["auth"])

# ── Ngưỡng leo thang khi đăng nhập sai ────────────────────────────────────────
# Khoá tài khoản sau N lần sai là một **lỗ từ chối dịch vụ**: ai biết email của
# khách đều khoá được họ, chỉ cần gửi vài lần thử rác mỗi phút. OWASP nói thẳng
# điều này — lockout "có thể vô tình thành tấn công từ chối dịch vụ nhắm vào
# người dùng hợp lệ" — và khuyên **leo thang sang thách đố** thay vì khoá.
#
# Nên ở đây:
#   - quá NGUONG_THACH_DO lần sai (theo IP HOẶC theo tài khoản) → bắt giải
#     Turnstile. Người thật gõ nhầm mật khẩu chỉ mất một cú click (thường là vô
#     hình); bot không giải được. Tài khoản KHÔNG bị khoá.
#   - quá NGUONG_CHAN_CUNG lần sai từ MỘT IP → chặn cứng 429. Chỉ theo IP, vì
#     chặn cứng theo tài khoản chính là cái lỗ nói trên.
#
# Ngưỡng chặn cứng để cao (20) có chủ ý: nhà mạng di động Việt Nam dùng CGNAT,
# rất nhiều người thật dùng chung một IP công cộng. Ngưỡng thấp sẽ khoá nhầm cả
# đám người vô can.
NGUONG_THACH_DO = 3
NGUONG_CHAN_CUNG = 20

# Khi Turnstile CHƯA cấu hình thì không có gì để leo thang tới. Nếu vẫn giữ trần
# 20 thì việc thiếu một biến môi trường sẽ **âm thầm nới phòng thủ từ 5 lên 20**
# — không lỗi, không cảnh báo. Nên lúc đó lùi về trần chặt như bản cũ.
#
# Không có thách đố thì cũng không còn cách nào chặn dò-một-tài-khoản-từ-nhiều-IP
# ngoài khoá tài khoản. Nên lúc đó **lùi hẳn về hành vi cũ**, chấp nhận luôn lỗ
# từ chối dịch vụ đi kèm — thà giữ phòng thủ thô còn hơn không có gì.
#
# Nói cách khác: Turnstile giờ là **cấu kiện chịu lực**, không còn là thứ trang
# trí cho trang đăng ký. Có nó thì phòng thủ vừa mạnh vừa không khoá nhầm người
# thật; mất nó thì tụt về mức cũ (và production PHẢI có nó).
NGUONG_CHAN_CUNG_KHONG_THACH_DO = 5


def _limiter(request: Request) -> RateLimiter:
    """Per-application limiter, created by create_app() and held on
    app.state.

    Deliberately not module-level: module state is shared by every app
    instance in a process, so two apps would share login-attempt counters
    (and a test that exhausts the limit would silently lock out unrelated
    tests). Within one running server there is still exactly one limiter,
    which is what ADR-005's single-process model wants.
    """
    return request.app.state.login_rate_limiter


def _client_key(request: Request) -> str:
    # IP THẬT sau Cloudflare Tunnel (CF-Connecting-IP), không phải 127.0.0.1 của
    # loopback — nếu không rate-limit sẽ khoá nhầm toàn hệ thống. Xem client_ip.
    return client_ip(request)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = ""):
    # Đã đăng nhập bằng đường nào (admin-env hoặc phiên CSDL) đều khỏi hiện form.
    # PHẢI xác thực đồng nhất với require_login (current_identity_optional có
    # RESOLVE sid với CSDL), không chỉ kiểm sự hiện diện của sid. Nếu chỉ kiểm
    # hiện diện: phiên có sid nhưng đã bị thu hồi/hết hạn sẽ khiến /login đá sang
    # trang trong khi require_login đá ngược về /login → vòng lặp vô tận
    # (ERR_TOO_MANY_REDIRECTS). `next` (H6): quay lại đúng trang, lọc open-redirect.
    if current_identity_optional(request):
        return RedirectResponse(safe_next(next), status_code=303)
    token = issue_csrf_token(request)
    # Hiện sẵn thách đố nếu IP này vừa sai nhiều lần. Không có bước này thì
    # người dùng gõ xong mới bị đá về — thêm một vòng bực mình vô ích.
    # `so_lan` CHỈ ĐỌC: mở trang không được tính là một lần thử.
    can_thach_do = (turnstile.bat_buoc()
                    and _limiter(request).so_lan(_client_key(request)) >= NGUONG_THACH_DO)
    return templates.TemplateResponse(
        request, "login.html",
        {"csrf_token": token, "error": None, "next": next,
         "turnstile_site_key": turnstile.site_key() if can_thach_do else ""},
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: str = Form(""),
    cf_turnstile_response: str = Form("", alias="cf-turnstile-response"),
):
    settings = request.app.state.server_settings

    # Đo HAI CHIỀU (W1.4): theo IP (một máy dò nhiều tài khoản) VÀ theo TÀI KHOẢN
    # (dò một tài khoản từ nhiều IP — chỉ đo theo IP thì không thấy). Nhưng hai
    # chiều này dẫn tới hai HÀNH ĐỘNG khác nhau, xem ghi chú ở đầu file.
    lim = _limiter(request)
    ip_key = _client_key(request)
    acct_key = "acct:" + (username or "").strip().lower()

    def _reset_limits() -> None:
        lim.reset(ip_key)
        lim.reset(acct_key)

    def _tra_form(loi: str, ma: int, *, kem_thach_do: bool):
        return templates.TemplateResponse(
            request, "login.html",
            {"csrf_token": issue_csrf_token(request), "error": loi, "next": next,
             "turnstile_site_key": turnstile.site_key() if kem_thach_do else ""},
            status_code=ma,
        )

    if not verify_csrf_token(request, csrf_token):
        return _tra_form("Phiên đăng nhập đã hết hạn, thử lại.", 400, kem_thach_do=False)

    so_ip = lim.so_lan(ip_key)
    so_acct = lim.so_lan(acct_key)

    # Chặn cứng CHỈ theo IP. Chặn cứng theo tài khoản = ai cũng khoá được khách.
    co_thach_do = turnstile.bat_buoc()
    if co_thach_do:
        # Có thách đố: chặn cứng CHỈ theo IP, ngưỡng cao. Tài khoản chỉ leo thang
        # sang thách đố → không ai khoá được tài khoản của người khác.
        if so_ip >= NGUONG_CHAN_CUNG:
            return _tra_form("Quá nhiều lần thử từ máy này — vui lòng đợi 1 phút.",
                             429, kem_thach_do=False)
    else:
        # Không có thách đố: lùi về hành vi cũ, gồm cả khoá theo tài khoản. Đây là
        # đường phòng thủ duy nhất còn lại cho kiểu dò một tài khoản từ nhiều IP.
        if (so_ip >= NGUONG_CHAN_CUNG_KHONG_THACH_DO
                or so_acct >= NGUONG_CHAN_CUNG_KHONG_THACH_DO):
            return _tra_form("Quá nhiều lần thử — vui lòng đợi 1 phút.", 429,
                             kem_thach_do=False)

    can_thach_do = co_thach_do and (so_ip >= NGUONG_THACH_DO
                                    or so_acct >= NGUONG_THACH_DO)
    if can_thach_do and not turnstile.xac_minh(cf_turnstile_response, remote_ip=ip_key):
        # CỐ Ý không tính đây là một lần thử: nếu tính, người thật giải hụt vài
        # lần sẽ tự đẩy mình tới ngưỡng chặn cứng. Bot cũng chẳng lợi gì — không
        # qua được thách đố thì không tới bước kiểm mật khẩu.
        return _tra_form("Vui lòng xác minh bạn không phải robot rồi thử lại.", 401,
                         kem_thach_do=True)

    lim.ghi_nhan(ip_key)
    lim.ghi_nhan(acct_key)

    # Đường 1 — người dùng trong CSDL (email + mật khẩu). Thử trước.
    # `username` cũng là ô nhập email; đường CSDL im lặng bỏ qua khi chưa có DB.
    with mo_db_optional() as db:
        if db is not None:
            from platform_core.users import tao_phien, xac_thuc
            user = xac_thuc(db, email=username, password=password)
            if user is not None:
                # Chưa xác thực email → KHÔNG cho vào (W1.4). Mật khẩu đúng nên
                # không phải brute-force → reset limiter, chỉ chặn vì chưa verify.
                if not user.is_verified:
                    _reset_limits()
                    return _tra_form(
                        "Tài khoản chưa xác thực email. Kiểm tra hộp thư "
                        "(hoặc mục spam) và bấm liên kết xác thực.",
                        403, kem_thach_do=False)
                sid = tao_phien(
                    db, user,
                    user_agent=request.headers.get("user-agent", ""),
                    ip=ip_key,
                )
                _reset_limits()
                log_in_db(request, sid)
                return RedirectResponse(safe_next(next), status_code=303)

    # Đường 2 — admin-từ-biến-môi-trường (đường lui, luôn còn kể cả khi DB hỏng).
    valid = (
        username == settings.admin_username
        and settings.admin_password_hash
        and verify_password(password, settings.admin_password_hash)
    )
    if not valid:
        # Lần thử vừa rồi đã được tính. Nếu nó đẩy qua ngưỡng thì kèm luôn thách
        # đố vào form, để lần sau người dùng có sẵn thứ cần giải.
        can_lan_sau = turnstile.bat_buoc() and (
            lim.so_lan(ip_key) >= NGUONG_THACH_DO
            or lim.so_lan(acct_key) >= NGUONG_THACH_DO)
        return _tra_form("Sai tên đăng nhập hoặc mật khẩu.", 401,
                         kem_thach_do=can_lan_sau)

    _reset_limits()
    log_in(request, username)
    return RedirectResponse(safe_next(next), status_code=303)


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form("")):
    # CSRF cho logout (W1.4): không cho request giả (từ site khác) ép đăng xuất.
    # Token sai/thiếu → KHÔNG đăng xuất, giữ nguyên phiên (kết quả an toàn).
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse("/", status_code=303)
    log_out(request)
    return RedirectResponse("/login", status_code=303)
