"""Phiên đăng nhập (H1.2).

Có HAI đường đăng nhập chạy **song song** trong giai đoạn này, cố ý:

1. **admin-từ-biến-môi-trường** (đường cũ, đang chạy production): cookie ký của
   Starlette mang `session["user"] = username`. Không chạm CSDL. Đây là đường
   lui — luôn còn một cách vào kể cả khi CSDL hỏng.

2. **người dùng trong CSDL** (đường mới, H1.2): cookie ký mang
   `session["sid"] = <session_id>`, trỏ tới một dòng trong bảng `sessions`.
   Thu hồi được (xoá dòng), nên "đăng xuất khỏi mọi thiết bị" và "đổi mật khẩu
   đá mọi phiên" mới làm được — cookie ký thuần không có id để thu hồi.

`require_login` nhận diện cả hai và luôn trả về một chuỗi định danh (username
hoặc email), nên **không route nào đang dùng nó phải đổi**. Đường CSDL thất bại
im lặng khi CSDL chưa cấu hình, để hàng trăm test không dựng PostgreSQL vẫn
chạy đường admin-env bình thường.

Khi gỡ đường admin-env (cuối H1), xoá nhánh `session["user"]` và cập nhật test.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote

from fastapi import HTTPException
from starlette.requests import Request

from platform_core.i18n import _ as _t
from server.loai_request import la_dieu_huong_html

_SESSION_USER_KEY = "user"   # duong admin-env (cu)
_SESSION_SID_KEY = "sid"     # duong nguoi dung CSDL (moi)


# ── Đường admin-từ-biến-môi-trường (giữ nguyên hành vi cũ) ────────────────────

def current_user(request: Request) -> Optional[str]:
    """Chỉ đường admin-env. Giữ nguyên để test và code cũ không đổi nghĩa."""
    return request.session.get(_SESSION_USER_KEY)


def log_in(request: Request, username: str) -> None:
    # Xoá mọi khoá phiên trước-đăng-nhập (vd token CSRF cấp cho khách ẩn danh)
    # thay vì mang chúng vào phiên đã đăng nhập — giảm nhẹ session fixation.
    request.session.clear()
    request.session[_SESSION_USER_KEY] = username


def log_out(request: Request) -> None:
    """Xoá cookie phiên, và nếu là phiên CSDL thì thu hồi luôn ở máy chủ."""
    sid = request.session.get(_SESSION_SID_KEY)
    if sid:
        _thu_hoi_sid_an_toan(sid)
    request.session.clear()


# ── Đường người dùng CSDL (mới) ───────────────────────────────────────────────

def log_in_db(request: Request, sid: str) -> None:
    """Ghi nhận một phiên CSDL vào cookie. `sid` do `users.tao_phien` cấp."""
    request.session.clear()
    request.session[_SESSION_SID_KEY] = sid


def current_sid(request: Request) -> Optional[str]:
    return request.session.get(_SESSION_SID_KEY)


def _resolve_sid(sid: str) -> Optional[str]:
    """Đổi sid lấy email, mở một phiên CSDL ngắn. None nếu sai/hết hạn/chưa có DB.

    Bọc toàn bộ trong try/except: khi CSDL chưa cấu hình (nhiều test), đường này
    phải **thất bại im lặng** để đường admin-env vẫn phục vụ được.
    """
    try:
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session()
        db = next(gen)
        try:
            user = lay_user_tu_phien(db, sid)
            db.commit()      # lay_user_tu_phien co the xoa phien het han
            return user.email if user else None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return None


def _thu_hoi_sid_an_toan(sid: str) -> None:
    try:
        from platform_core.db import get_session
        from platform_core.users import thu_hoi_phien
        gen = get_session()
        db = next(gen)
        try:
            thu_hoi_phien(db, sid)
            db.commit()
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        pass


# ── Dependency dùng chung ─────────────────────────────────────────────────────

def current_identity_optional(request: Request) -> Optional[str]:
    """Định danh hiện tại (username admin-env HOẶC email CSDL) hoặc None.

    KHÔNG raise — dùng cho trang CÔNG KHAI (catalog) cần biết đã đăng nhập chưa
    mà không đá khách về /login. `require_login` vẫn dùng cho route app.
    """
    u = request.session.get(_SESSION_USER_KEY)
    if u:
        return u
    sid = request.session.get(_SESSION_SID_KEY)
    if sid:
        return _resolve_sid(sid)
    return None


def client_ip(request: Request) -> str:
    """IP THẬT của khách — nền tảng của rate-limit và antifraud.

    Sau Cloudflare Tunnel, `cloudflared` mở kết nối tới origin qua LOOPBACK, nên
    `request.client.host` là `127.0.0.1` cho MỌI khách. Nếu key rate-limit/
    antifraud theo đó thì: 5 lần login sai của một người khoá TẤT CẢ mọi người
    (DoS toàn hệ thống), và cap đăng ký theo IP chặn cả nền tảng sau vài lượt.

    `cloudflared` đặt `CF-Connecting-IP` = IP thật của khách. Origin ở đây CHỈ
    nhận kết nối loopback từ cloudflared (không mở cổng ra ngoài — xem
    docs/04 + nghiệm thu setup), nên header này đáng tin trong mô hình này.
    Fallback về peer khi không có header (chạy local/test trực tiếp).
    """
    cf = request.headers.get("cf-connecting-ip")
    if cf and cf.strip():
        return cf.strip()
    return request.client.host if request.client else "unknown"


def safe_next(raw: Optional[str]) -> str:
    """Chỉ chấp nhận đường dẫn NỘI BỘ tương đối — chống open-redirect.

    Click app khi chưa đăng nhập sẽ mang `?next=<đường-dẫn>` để quay lại đúng
    app. Nếu không lọc, kẻ xấu gài `next=https://lua-dao` để cướp phiên sau đăng
    nhập. Chỉ nhận thứ bắt đầu bằng '/' và không phải '//', không có scheme.
    """
    if not raw:
        return "/"
    raw = raw.strip()
    if (not raw.startswith("/") or raw.startswith("//")
            or "://" in raw or "\\" in raw or "\n" in raw or "\r" in raw):
        return "/"
    return raw


def require_login(request: Request) -> str:
    """FastAPI dependency: 303 về /login?next=<đường-dẫn> khi chưa đăng nhập.

    Trả về chuỗi định danh (username của admin-env, hoặc email của user CSDL).
    Chữ ký không đổi so với bản cũ, nên mọi route `Depends(require_login)` giữ
    nguyên. Thêm `?next=` để đăng nhập xong quay lại đúng trang đang mở (H6).

    ## ⭐ Lời gọi dữ liệu trong trang nhận 401 + JSON, KHÔNG phải 303

    303 tồn tại để **trình duyệt mở trang đăng nhập**. `fetch()` không mở
    trang: nó ĐI THEO chuyển hướng, nhận HTML của `/login` với `status: 200`,
    rồi `response.json()` nổ ở dòng sau với một thông điệp không dính dáng gì
    tới nguyên nhân thật. Phiên hết hạn giữa lúc vòng poll Canvas đang chạy ⇒
    người dùng thấy một lỗi cú pháp JSON thay vì "phiên đã hết hạn, đăng nhập
    lại". Client không có cách nào phân biệt — 200 + HTML trông y hệt thành
    công cho tới lúc parse.

    Tiêu chí "điều hướng hay lời gọi dữ liệu" là của cả trang web và **đã có
    một nguồn**: `server/loai_request.la_dieu_huong_html` (Fetch Metadata, lùi
    về `Accept`, KHÔNG có bằng chứng ⇒ giữ hành vi cũ). Middleware ngôn ngữ hỏi
    đúng hàm đó cho quyết định 302 của nó — hai nơi hỏi một chỗ, cố ý.
    """
    u = request.session.get(_SESSION_USER_KEY)
    if u:
        return u

    sid = request.session.get(_SESSION_SID_KEY)
    if sid:
        email = _resolve_sid(sid)
        if email:
            return email

    if not la_dieu_huong_html(request):
        # `ma` đọc được bằng máy: client phân biệt "hết phiên" với mọi lỗi
        # khác mà không phải đoán từ chuỗi thông điệp (đã dịch theo ngôn ngữ).
        raise HTTPException(status_code=401, detail={
            "ma": "chua_dang_nhap",
            "thong_diep": _t('Phiên đã hết hạn. Vui lòng đăng nhập lại.')})

    nxt = quote(request.url.path or "/", safe="/")
    raise HTTPException(status_code=303, headers={"Location": f"/login?next={nxt}"})
