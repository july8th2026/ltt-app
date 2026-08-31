"""
templating.py — the single Jinja2 environment for the whole app.

Every route module imported its own `Jinja2Templates(directory=...)`, which
meant a global (like the nav's "which pages are built yet" map) had to be
threaded through every single route context or the template would raise
UndefinedError. One shared instance with globals fixes that at the source.
"""
from __future__ import annotations

import pathlib

from fastapi.templating import Jinja2Templates

# Đường dẫn TUYỆT ĐỐI, suy ra từ vị trí chính file này.
#
# Trước đây là "server/templates" — tương đối theo thư mục làm việc. Nó chạy
# đúng chỉ vì NSSM đặt AppDirectory về gốc dự án. Ai chạy uvicorn từ thư mục
# khác là MỌI trang trả 500 vì không tìm thấy template, mà thông báo lỗi lại
# không nói gì về thư mục làm việc. Khi chuyển sang máy mới đây là bẫy dễ vấp
# nhất, nên chốt cứng theo vị trí file.
_TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent / "templates"

templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

# ── Cache-busting cho static (Đợt R — bài học: Cloudflare cache ltt.css cũ 4h,
# chip-opt không tới người dùng dù origin đã đúng). Đính hash NỘI DUNG ltt.css vào
# URL `?v=` → đổi CSS = đổi URL = CF/browser buộc tải mới ngay, không chờ TTL.
# Tính MỘT lần lúc import (mỗi lần deploy restart service → hash mới nếu CSS đổi).
_STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"


#: Mọi tài sản tĩnh có đính `?v={{ asset_ver }}`. Thêm tệp mới thì thêm vào đây.
#:
#: 🔴 TRƯỚC 25/08 HÀM NÀY CHỈ BĂM `ltt.css`. Nên một tệp JS mới, dù link có
#:    `?v=…`, sẽ mang **đúng con số của CSS** — đổi JS mà không đổi CSS thì URL
#:    không đổi, và Cloudflare tiếp tục phục vụ bản cũ tới khi hết TTL.
#:
#: ⛔ Đó chính là cái bẫy quy tắc 6 của `CLAUDE.md` mô tả, và nó đã xảy ra một
#:    lần với `ltt.css`: sửa xong ở origin mà người dùng vẫn nhận bản cũ 4 tiếng.
# 🔴 MọI TẬP Ở ĐÂY PHẢI LÀ MọI TẬP MANG `?v={{ asset_ver }}`.
#
#    Danh sách này **tính ra** hash, còn khuôn mẫu thì **đính** hash ấy vào bất cứ
#    tệp nào. Hai việc đó không có gì buộc phải khớp — và khi lệch, tệp bị bỏ
#    quên sẽ đổi nội dung mà **URL không đổi**, nên Cloudflare phục vụ bản cũ
#    tới hết TTL, không lỗi nào báo.
#
# ⛔ `voice.js` và `dev_playground.js` đã thiếu ở đây một thời gian. Chúng không
#    nổ vì mọi đợt đều đổi `ltt.css` cùng lúc nên hash vẫn nhảy. Cái lỗ chỉ lộ
#    ra ở đúng hình dạng của một **đợt sửa lỗi**: chạm mỗi JavaScript, không
#    chạm CSS — tức nằm im cho tới lần deploy cần nó nhất.
#
#    `tests/test_369_asset_ver_day_du.py` nay đọc khuôn mẫu để biết tệp nào đang
#    được đính version, rồi đòi danh sách này phủ hết. Thêm tệp mới mà quên khai
#    là đỏ ngay — một luật cho cả lớp, không phải một danh sách được nhớ tay.
TAI_SAN_CO_VERSION = ("ltt.css", "sao_chep.js", "cam_chon.js", "chon_tep.js",
                      "voice.js", "dev_playground.js")


def _tinh_asset_ver() -> str:
    import hashlib
    h = hashlib.md5()
    try:
        for ten in TAI_SAN_CO_VERSION:
            h.update((_STATIC_DIR / ten).read_bytes())
        return h.hexdigest()[:8]
    except Exception:
        return "0"


ASSET_VER = _tinh_asset_ver()
templates.env.globals["asset_ver"] = ASSET_VER

# ── Đa ngôn ngữ (H24) ────────────────────────────────────────────────────────
# `_()` dịch, `u()` sinh link mang đúng tiền tố ngôn ngữ.
#
# Mọi link nội bộ trong template PHẢI đi qua `u()`. Viết thẳng href="/nap" thì
# người đang ở bản tiếng Anh bấm vào sẽ rơi về bản tiếng Việt — và lỗi đó không
# làm trang vỡ, chỉ âm thầm đổi ngôn ngữ giữa chừng. Có scanner trong gate chặn.
from platform_core import i18n as _i18n  # noqa: E402


def _u(path: str) -> str:
    """Link nội bộ mang tiền tố ngôn ngữ hiện tại. Đường miễn trừ giữ nguyên."""
    return _i18n.them_tien_to(path, _i18n.ngon_ngu_hien_tai())


templates.env.add_extension("jinja2.ext.i18n")   # phải nạp TRƯỚC install_*
templates.env.install_gettext_callables(          # bật cú pháp {% trans %}
    gettext=_i18n._, ngettext=_i18n._n, newstyle=True)


def _t(msg, **bien):
    """`_()` cho template — KHÔNG áp định dạng `%` khi không có biến.

    Bản `newstyle` của Jinja luôn chạy `rv % variables`, kể cả `variables` rỗng.
    Nên mọi chuỗi chứa dấu `%` VĂN XUÔI đều nổ `ValueError: incomplete format` —
    ví dụ thật: "Ổn định hai pass bằng libvidstab · +20%." làm trang Nâng cấp
    video trả 500. Lỗi chỉ lộ khi trang đó được render, không lộ lúc dịch.

    Trả `Markup` vì chuỗi dịch có thực thể HTML (`&larr;`, `&amp;`); để Jinja tự
    escape thì chúng hiện ra thành `&amp;larr;` trên màn hình.
    """
    from markupsafe import Markup
    s = _i18n._(msg)
    return Markup(s % bien if bien else s)


templates.env.globals["_"] = _t
templates.env.globals["gettext"] = _t
templates.env.globals["u"] = _u
templates.env.globals["lang_hien_tai"] = _i18n.ngon_ngu_hien_tai
templates.env.globals["NGON_NGU"] = _i18n.NGON_NGU

# Q59 — public website is WordPress and owns these pretty URLs. Keep the
# integration surface centralized so auth, apps and commerce never drift back
# to legacy .html pages. OAuth callback URLs are intentionally not included:
# providers require their exact legacy paths.
PUBLIC_LINKS = {
    "website": "https://lttstudios.com/",
    "applications": "https://lttstudios.com/applications/",
    "support": "https://lttstudios.com/faq/",
    "contact": "https://lttstudios.com/contact/",
    "privacy": "https://lttstudios.com/privacy-policy/",
    "terms": "https://lttstudios.com/terms/",
    "data_deletion": "https://lttstudios.com/data-deletion/",
    # Điều khoản RIÊNG của LTT VPS. Tách khỏi `terms` chung vì nó mang
    # những con số vận hành cụ thể (chu kỳ 30 ngày, ân hạn 7 ngày, hạn
    # mức băng thông) mà `test_294` chốt phải khớp mã nguồn.
}
def _tien_vnd(so) -> str:
    """`149000` → `149.000đ`. Một chỗ duy nhất định dạng tiền cho template.

    Trước đây mỗi nơi tự viết `"{:,}".format(x).replace(",", ".") + "đ"`. Ba bản
    sao của cùng một phép, và ký tự `đ` nằm rải trong template — thứ khiến bánh
    cóc i18n báo động đúng, vì nó không phân biệt được một ký hiệu tiền tệ với
    một câu chưa dịch.

    Định dạng tiền là **quy ước hiển thị**, không phải chuỗi cần dịch: một người
    đọc bản tiếng Anh vẫn trả bằng đồng.
    """
    try:
        return f"{int(so):,}".replace(",", ".") + "đ"
    except (TypeError, ValueError):
        return str(so)


def _so(gt) -> str:
    """`50000` → `50.000`. Anh em của `tien_vnd`, chỉ khác là **không** có `đ`.

    🔴 VÌ SAO CẦN MỘT FILTER RIÊNG. Không phải mọi con số đều là tiền: credit,
       token, số request đều cần dấu phân cách nghìn nhưng **không** phải hậu tố
       tiền tệ. Thiếu filter này thì template hoặc viết
       `"{:,}".format(x)` rải rác — đúng thứ chú thích của `tien_vnd` nói là
       đừng làm — hoặc bỏ luôn dấu phân cách.

    ⛔ ĐO 25/08: khu API hiện `50000 credit` trong khi trang VPS hiện `149.000`.
       Cùng một sản phẩm, hai quy ước đọc số. `50000` là con số mắt phải đếm chữ
       số mới đọc được, và đọc nhầm một bậc là hiểu sai giá gấp mười lần.

    ⚠️ Dấu chấm chứ không phải dấu phẩy: đây là quy ước Việt Nam, và nó **không**
       phải chuỗi cần dịch — cùng lý do đã ghi ở `tien_vnd`.

    ⭐ HỎI TRƯỚC, KHÔNG BẮT NGOẠI LỆ. `tien_vnd` bọc `try/except` và điều đó làm
       bánh cóc `check_silent_except` đỏ khi thêm cái thứ hai — đúng việc của nó.
       Một filter hiển thị chỉ có hai ca (số / không phải số), và cả hai đều hỏi
       được bằng `isinstance`. Bắt ngoại lệ ở đây là dùng cơ chế báo lỗi để làm
       việc của một câu `if`.
    """
    if isinstance(gt, str):
        rut = gt.strip()
        if not rut.lstrip("-").isdigit():
            return str(gt)
        gt = int(rut)
    # `bool` là con của `int`: để lọt thì `True` hiện ra thành `1`.
    if isinstance(gt, bool) or not isinstance(gt, (int, float)):
        return str(gt)
    return f"{int(gt):,}".replace(",", ".")


templates.env.filters["tien_vnd"] = _tien_vnd
templates.env.filters["so"] = _so
templates.env.globals["public_links"] = PUBLIC_LINKS

# Hợp đồng app (H5): app được mang template RIÊNG trong `apps/<slug>/templates/`
# để tự dựng UI (extends base.html) MÀ KHÔNG phải bỏ file vào server/templates/.
# Không có phần này thì "thêm app = thêm thư mục" chỉ đúng với phần xử lý, còn
# giao diện vẫn buộc chạm server/ — đúng lỗ hổng H5 phải lấp. server/templates/
# đứng TRƯỚC nên nền tảng luôn thắng khi trùng tên (app không ghi đè được vỏ).
_APPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "apps"
_app_template_dirs = sorted(
    str(p) for p in _APPS_DIR.glob("*/templates") if p.is_dir()
)
if _app_template_dirs:
    from jinja2 import ChoiceLoader, FileSystemLoader
    templates.env.loader = ChoiceLoader(
        [FileSystemLoader(str(_TEMPLATE_DIR))]
        + [FileSystemLoader(d) for d in _app_template_dirs]
    )

# Which desktop tabs have a real web page yet. The sidebar reads this to
# show an honest "đang xây" badge instead of pretending a link is finished.
# Flip a value to True in the same commit that lands the real page.
BUILT_PAGES = {
    "sheet_fb":      True,
    "sheet_tiktok":  True,
    "manual_fb":     True,
    "manual_tiktok": True,
    "facebook":      True,
    "tiktok":        True,
    "monitor":       True,
    "audit":         True,
    "settings":      True,
    "status":        True,
}

try:
    from version import APP_VERSION_SHORT as _VER
except Exception:
    _VER = ""

templates.env.globals["built"] = BUILT_PAGES


def _nav_apps(request=None):
    """Danh sách app cho sidebar. Quét mỗi lần render là đủ nhanh (chỉ đọc
    module đã cache trong sys.modules), và nhờ vậy thêm app không cần restart
    lúc phát triển.

    Nhận `request` để lọc app `hidden` theo người dùng (H1.4) — sidebar phải
    khớp với trang chủ, nếu không app bị ẩn vẫn hiện ở thanh bên. Bọc an toàn:
    lỗi lọc (chưa có CSDL, admin-env) thì hiện đủ, không làm sập trang."""
    try:
        from platform_core.registry import discover, visible_on_surface
        loaded = [a for a in discover() if a.manifest.enabled and not a.error]
    except Exception:
        # Sidebar lỗi không được làm sập trang. Trả rỗng còn hơn 500.
        return []

    authed = _da_dang_nhap(request) if request is not None else False
    operator = False
    if authed and request is not None:
        from server.deps import is_operator
        operator = is_operator(request)
    loaded = [a for a in loaded if visible_on_surface(
        a.manifest, authenticated=authed, operator=operator)]
    if request is None:
        return loaded
    try:
        sid = request.session.get("sid")
        if not sid:
            return loaded      # admin-env / ẩn danh → không lọc ở đây
        from platform_core.app_access import loc_app_hien_thi
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            user = lay_user_tu_phien(db, sid)
            return loc_app_hien_thi(db, user, loaded) if user else loaded
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return loaded


templates.env.globals["nav_apps"] = _nav_apps
templates.env.globals["app_version"] = _VER


def _so_du_credit(request=None):
    """Số dư credit của người dùng CSDL đang đăng nhập, hoặc None (H6).

    None khi: chưa đăng nhập bằng phiên CSDL (admin-env / ẩn danh), chưa có CSDL,
    hay bất kỳ lỗi nào — vỏ chỉ hiện badge khi có số thật, không làm sập trang.
    """
    if request is None:
        return None
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.credit import so_du
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            u = lay_user_tu_phien(db, sid)
            return so_du(db, u.id) if u else None
        finally:
            try:
                next(gen)
            except StopIteration:
                pass
    except Exception:
        return None


templates.env.globals["so_du_credit"] = _so_du_credit


def _active_app(request=None):
    """Slug của app mà đường dẫn hiện tại thuộc về, hoặc None (H6.6).

    Vỏ hai tầng: sidebar hiện MỖI APP MỘT DÒNG (launcher); trang con của app chỉ
    bung ra khi đang ở TRONG app đó. Dùng app_cho_path (khớp tiền tố dài nhất
    trên route_prefix + nav) nên không hardcode tên app. Bọc an toàn."""
    if request is None:
        return None
    try:
        from platform_core.app_access import app_cho_path
        from platform_core.registry import discover
        return app_cho_path(request.url.path, discover())
    except Exception:
        return None


def _is_admin(request=None):
    """True cho operator (admin-env hoặc admin CSDL); một nguồn với route guard."""
    if request is None:
        return False
    try:
        from server.deps import is_operator
        return is_operator(request)
    except Exception:
        return False


templates.env.globals["active_app"] = _active_app


def _nexus_bat() -> bool:
    """Cờ LTT Nexus có bật không — menu "Máy của tôi" chỉ hiện khi bật.

    Đọc cờ mỗi lần render (không cache) vì cờ đổi bằng biến môi trường
    lúc chạy; cache lại thì bật/tắt phải khởi động lại mới thấy.
    """
    from platform_core import nexus

    return nexus.enabled()


templates.env.globals["nexus_bat"] = _nexus_bat
templates.env.globals["is_admin"] = _is_admin


def _csrf_token(request=None):
    """Token CSRF của phiên cho các form nhỏ dựng thẳng trong base (vd nút Đăng
    xuất). `issue_csrf_token` idempotent nên nhiều form trên cùng trang dùng
    chung một token — không ghi đè nhau."""
    if request is None:
        return ""
    try:
        from server.auth.csrf import issue_csrf_token
        return issue_csrf_token(request)
    except Exception:
        return ""


# Tên KHÁC `csrf_token` vì nhiều route truyền biến context tên `csrf_token` (một
# CHUỖI) — trùng tên sẽ che global và `{{ csrf_token(request) }}` gọi chuỗi → lỗi.
templates.env.globals["phien_csrf"] = _csrf_token


def _da_dang_nhap(request) -> bool:
    try:
        s = request.session
        return bool(s.get("sid") or s.get("user"))
    except Exception:
        return False


def _nav_groups(request=None):
    """App gom theo `group` cho HEADER (UX Pha 2). Khách: chỉ app public; đã đăng
    nhập: lọc theo quyền. Trả dict {group: [LoadedApp]} — bọc an toàn, lỗi trả {}."""
    try:
        from platform_core.registry import discover, visible_on_surface
        loaded = [a for a in discover() if a.manifest.enabled and not a.error]
    except Exception:
        return {}

    authed = _da_dang_nhap(request)
    operator = False
    if authed and request is not None:
        from server.deps import is_operator
        operator = is_operator(request)
    loaded = [a for a in loaded if visible_on_surface(
        a.manifest, authenticated=authed, operator=operator)]
    sid = None
    try:
        sid = request.session.get("sid") if request is not None else None
    except Exception:
        sid = None
    if sid:
        try:
            from platform_core.app_access import loc_app_hien_thi
            from platform_core.db import get_session
            from platform_core.users import lay_user_tu_phien
            gen = get_session(); db = next(gen)
            try:
                u = lay_user_tu_phien(db, sid)
                if u is not None:
                    loaded = loc_app_hien_thi(db, u, loaded)
            finally:
                try: next(gen)
                except StopIteration: pass
        except Exception:
            pass
    groups: dict = {}
    for a in loaded:
        groups.setdefault(a.manifest.group or "Ứng dụng", []).append(a)
    # Sắp thứ tự nhóm cho header: nhóm năng lực chính trước, "Khác/Ứng dụng" cuối.
    _uu_tien = {"Ảnh": 0, "Video": 1, "Giọng nói": 2, "Đăng bài": 3, "Workflow": 4}
    def _khoa(g):
        if g in ("Khác", "Ứng dụng"):
            return (2, g)
        return (0, _uu_tien.get(g, 1)) if g in _uu_tien else (1, g)
    return {g: groups[g] for g in sorted(groups, key=_khoa)}


def _tai_khoan(request=None):
    """Dữ liệu tài khoản cho avatar-menu (UX Pha 2), hoặc None nếu chưa đăng nhập.
    Không lộ gì nhạy cảm — chỉ tên/email/vai trò để hiển thị."""
    if request is None:
        return None
    try:
        env_user = request.session.get("user")
        if env_user:
            return {"name": env_user, "email": "", "role": "admin",
                    "initial": env_user[:2].upper()}
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            u = lay_user_tu_phien(db, sid)
            if u is None:
                return None
            return {"name": u.display_name or u.email, "email": u.email,
                    "role": u.role, "initial": (u.email or "?")[:2].upper()}
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return None


def _app_tabs(request=None):
    """Nav NỘI BỘ của app đang mở (nếu app có >1 trang) — thay sub-nav sidebar cũ.
    Trả list NavEntry, hoặc [] nếu không ở trong app / app một trang."""
    if request is None:
        return []
    try:
        from platform_core.app_access import app_cho_path
        from platform_core.registry import discover
        loaded = discover()
        slug = app_cho_path(request.url.path, loaded)
        if not slug:
            return []
        for a in loaded:
            if a.manifest.slug == slug:
                entries = a.manifest.nav_entries()
                return entries if len(entries) > 1 else []
    except Exception:
        return []
    return []


templates.env.globals["nav_groups"] = _nav_groups
templates.env.globals["tai_khoan"] = _tai_khoan
templates.env.globals["app_tabs"] = _app_tabs
templates.env.globals["da_dang_nhap"] = _da_dang_nhap
