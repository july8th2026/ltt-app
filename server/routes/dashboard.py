"""Trang chủ — danh sách app, sinh từ apps/*/manifest.py.

Trước đây "/" chỉ hiện tóm tắt blocker của bot đăng bài. Giờ nó là cửa vào của
nền tảng nhiều app: catalog công khai cho khách chưa đăng nhập (Q30/H6), và
workspace có lịch sử dùng cho người đã đăng nhập.

Phần blocker đã gỡ 2026-08-25 cùng app socialbot — xem khối `app_setup` bên
dưới. Trang này không còn chạy `tools/doctor.py` mỗi lượt tải nữa.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from platform_core.i18n import N_
from platform_core.i18n import _ as _t
from server.auth.session import current_identity_optional
from server.templating import templates

router = APIRouter(tags=["home"])

_LIFECYCLE_UI = {
    "released": (N_("Đã phát hành"), 0),
    "development": (N_("Đang phát triển"), 1),
    "maintenance": (N_("Đang bảo trì"), 2),
    "internal": (N_("Nội bộ"), 3),
    "retired": (N_("Đã ngừng"), 4),
}


def _prepare_home_items(items: list) -> list[str]:
    """Gắn metadata trình bày chỉ từ manifest và trả taxonomy duy nhất.

    Không suy luận category từ slug/tên app. ``group`` chỉ là fallback tương
    thích cho manifest nội bộ cũ; mọi card customer H26 đều khai capabilities.
    """
    categories: list[str] = []
    for item in items:
        manifest = item.manifest
        capabilities = tuple(manifest.capabilities) or (manifest.group or "Utilities",)
        item.home_categories = capabilities
        item.home_category = capabilities[0]
        for category in capabilities:
            if category not in categories:
                categories.append(category)
        label, order = _LIFECYCLE_UI.get(
            manifest.lifecycle, (manifest.lifecycle, 99))
        item.home_lifecycle_label = label
        item.home_lifecycle_order = order
    items.sort(key=lambda item: (
        item.home_lifecycle_order,
        str(item.manifest.display_name).casefold(),
    ))
    return categories


def _workspace_data(visible: list, db_user) -> dict:
    """Dữ liệu dashboard owner-scoped, trừ aggregate Popular chỉ dùng để sort."""
    from platform_core.db import get_session
    from platform_core.models import JOB_QUEUED, JOB_RUNNING, Job
    from sqlalchemy import func, select

    result = {"popularity": {}, "recent": [], "running": [], "used_slugs": set()}
    if db_user is None:
        return result
    manifest_by_slug = {item.manifest.slug: item.manifest for item in visible}
    gen = get_session(); db = next(gen)
    try:
        rows = db.execute(select(Job.app_slug, func.count(Job.id)).group_by(Job.app_slug))
        result["popularity"] = {slug: int(count) for slug, count in rows
                                if slug in manifest_by_slug}
        result["recent"] = db.execute(
            select(Job).where(Job.user_id == db_user.id)
            .order_by(Job.created_at.desc()).limit(5)).scalars().all()
        result["running"] = db.execute(
            select(Job).where(Job.user_id == db_user.id,
                              Job.status.in_((JOB_QUEUED, JOB_RUNNING)))
            .order_by(Job.created_at.desc()).limit(5)).scalars().all()
        # "My Apps" là toàn bộ app user từng chạy, không phải chỉ app xuất hiện
        # trong 5 hoạt động gần nhất. Query riêng giữ recent rail nhỏ mà filter
        # launcher vẫn đúng theo toàn bộ lịch sử owner.
        result["used_slugs"] = set(db.execute(
            select(Job.app_slug).where(Job.user_id == db_user.id).distinct()
        ).scalars().all())
        detached: set[str] = set()
        for job in [*result["recent"], *result["running"]]:
            manifest = manifest_by_slug.get(job.app_slug)
            job.app_name = manifest.display_name if manifest else job.app_slug
            job.app_icon = manifest.icon if manifest else "✦"
            if job.id not in detached:
                db.expunge(job)
                detached.add(job.id)
    finally:
        try: next(gen)
        except StopIteration: pass
    return result


@router.get("/gia-api", response_class=HTMLResponse)
def gia_api(request: Request):
    """Bảng giá API — **CÔNG KHAI, không cần đăng nhập**.

    🔴 VÌ SAO PHẢI CÔNG KHAI. Trang giá đang có (`/developers/pricing`) nằm sau
       `require_account`: muốn biết giá thì phải đăng ký trước. Đó là thứ tự
       ngược, và nó chặn đúng người ta cần nhất — người đang **cân nhắc**. Không
       ai đăng ký một dịch vụ tính tiền để xem nó tính bao nhiêu.

    ⛔ SỐ LẤY TỪ `gia_token.bang_gia()`, KHÔNG GÕ LẠI VÀO TEMPLATE. Đó là chính
       hàm mà `tinh()` dùng để ra hoá đơn. Gõ lại là tạo ra một bảng giá thứ hai,
       và ngày hai bảng lệch nhau thì bảng nào cũng không đáng tin — cùng lý do
       `dev_pricing` đã ghi: *"what matters is what the customer will actually be
       billed, and that stays true only while one piece of code produces both
       numbers."*
    """
    from platform_core.llm import gia_token

    bang = gia_token.bang_gia()
    # Ba ví dụ chi phí THẬT, tính bằng đúng hàm ra hoá đơn. Một con số trừu tượng
    # ("400 credit mỗi triệu token") không nói cho ai biết một lượt chat tốn bao
    # nhiêu; ba ví dụ thì có.
    from platform_core.llm.cong_vlm import SuDung

    vi_du = []
    for ten, vao, ra in (
            (_t("Một câu hỏi ngắn"), 50, 150),
            (_t("Một lượt viết mã"), 2_000, 800),
            (_t("Một lượt agent có nhiều tool"), 22_000, 1_500)):
        cp = gia_token.tinh(SuDung(token_vao=vao, token_ra=ra, dang_tin=True))
        vi_du.append({"ten": ten, "vao": vao, "ra": ra,
                      "credit": cp.tong_credit_lam_tron_len,
                      "dong": cp.tong_credit_lam_tron_len * 100})
    # Ảnh model nhà (H37/L4). Trang này trước chỉ nói LLM, nên khách không có
    # cách nào biết giá ảnh trước khi đăng ký — cùng thứ tự ngược đã nói ở trên.
    from apps.anhnoibo import gia as gia_anh

    bang_anh = gia_anh.bang_gia()
    vi_du_anh = [
        {"ten": _t("Một ảnh từ mô tả"), "so": 1, "che_do": "t2i"},
        {"ten": _t("Bốn ảnh từ mô tả"), "so": 4, "che_do": "t2i"},
        {"ten": _t("Một ảnh có ảnh tham chiếu"), "so": 1, "che_do": "edit"},
    ]
    for v in vi_du_anh:
        v["credit"] = gia_anh.tinh(so_anh=v["so"], che_do=v["che_do"])
        v["dong"] = v["credit"] * 100

    # Giọng nói model nhà (V7). `gia.bang_gia()` đã tự viết trong docstring rằng
    # trang này phải đọc nó — chỉ là chưa ai nối dây, nên khách vẫn không có
    # cách nào biết giá tiếng nói trước khi đăng ký. Đúng thứ tự ngược đã nói ở
    # đầu hàm, lặp lại lần thứ ba với một đơn vị đo thứ ba.
    from apps.ltt_voice import gia as gia_tieng

    # ⛔ KHÔNG dựng thêm một danh sách ví dụ ở đây. `bang_gia()` đã tính sẵn ví
    #    dụ bằng chính `tinh()`, và thêm một danh sách thứ hai ở tầng route là
    #    tạo đúng cái "bảng giá thứ hai" mà cả hàm ấy lẫn đầu hàm này cảnh báo.
    bang_tieng = gia_tieng.bang_gia()

    return templates.TemplateResponse(request, "gia_api.html", {
        "bang": bang, "vi_du": vi_du,
        "bang_anh": bang_anh, "vi_du_anh": vi_du_anh,
        "bang_tieng": bang_tieng,
        "user": _user_hien_tai(request),
    })


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    """Trang chủ = CATALOG (H6/Q30).

    CÔNG KHAI: khách chưa đăng nhập vẫn xem được danh sách app (chỉ app
    `enabled and public`), bấm một app thì mới cần đăng nhập. Đã đăng nhập thì
    lọc theo quyền (AppAccess) và hiện blocker/app-lỗi như trước.
    """
    from platform_core.registry import discover, visible_on_surface
    from server.deps import is_operator

    user = current_identity_optional(request)
    authed = user is not None
    loaded = discover()
    ok_apps = [a for a in loaded if not a.error]

    if not authed:
        # Khách: chỉ hiện app self-serve công khai; KHÔNG lộ blocker/app-lỗi.
        visible = [a for a in ok_apps if a.manifest.enabled and
                   visible_on_surface(a.manifest, authenticated=False)]
        categories = _prepare_home_items(visible)
        return templates.TemplateResponse(request, "home.html", {
            "user": None, "authed": False, "nav": "home",
            "apps": visible, "broken": [], "app_setup": {},
            "home_categories": categories,
        })

    # Đã đăng nhập: lọc theo quyền (H1.4).
    # Bọc an toàn: DB trục trặc / admin-env thì hiện đủ, không để phân quyền làm
    # trang trắng.
    #
    # ⭐ KHÔNG còn gọi `doctor.run()` ở đây (bỏ 2026-08-25). Xem khối `app_setup`
    #    bên dưới để biết vì sao — và vì sao đó là một lượt tải trang nhanh hơn,
    #    không phải một tính năng bị mất.
    #
    # `enabled` phải lọc ở ĐÂY nữa, không chỉ ở nhánh ẩn danh bên trên.
    # Thiếu nó thì một app đang tắt cờ vẫn hiện thẻ cho người đã đăng nhập, mà
    # route của nó trả 404 — bấm vào là ngõ cụt. Thanh bên và header
    # (`server/templating.py`) đã lọc `enabled` từ trước, nên trang chủ còn là
    # chỗ DUY NHẤT nói khác; ba nơi mô tả cùng một danh sách thì phải nói giống
    # nhau. Đo 25/08: app `vps` (cờ `LTT_VPS` chưa đặt) lọt đúng kiểu này.
    visible = [a for a in ok_apps if a.manifest.enabled and visible_on_surface(
        a.manifest, authenticated=True, operator=is_operator(request))]
    db_user = None
    try:
        db_user = _user_hien_tai(request)
        if db_user is not None:
            from platform_core.app_access import loc_app_hien_thi
            from platform_core.db import get_session
            gen = get_session(); db = next(gen)
            try:
                visible = loc_app_hien_thi(db, db_user, visible)
            finally:
                try: next(gen)
                except StopIteration: pass
    except Exception:
        pass

    # ── Huy hiệu "cần thiết lập" trên thẻ app (H6.6): ĐÃ GỠ 2026-08-25 ───────
    #
    # Cơ chế cũ: `doctor.run()` sinh danh sách lỗi chặn, rồi khớp tiêu đề với
    # `manifest.blocker_titles` do app tự khai. Nó tồn tại để nền tảng gắn huy
    # hiệu lên ĐÚNG thẻ app mà không hardcode tên app nào.
    #
    # ⛔ Nhưng **chỉ socialbot khai `blocker_titles`** (đúng hai mục: "Tài khoản
    #    Facebook", "Tài khoản TikTok"), và cả hai mục sinh ra chúng trong
    #    `tools/doctor.py` đều đã bị gỡ cùng app đó. Nên vòng lặp này đã trở
    #    thành một vòng lặp luôn cho ra `{}` — trong khi vẫn bắt **mỗi lượt tải
    #    trang chủ của mỗi người dùng đã đăng nhập** trả giá một lượt chạy
    #    doctor.
    #
    # ⭐ Giữ `app_setup` trong ngữ cảnh template (rỗng) chứ không gỡ khỏi
    #    `home.html`: hợp đồng `AppManifest.blocker_titles` vẫn còn, nên app sau
    #    khai nó thì chỉ cần một nơi sinh dữ liệu là huy hiệu sống lại. Gỡ cả
    #    template là bắt người sau dựng lại phần đã đúng.
    app_setup: dict = {}

    # Dùng toàn bộ manifest đã nạp để lịch sử của mode ẩn trong catalog (ví dụ
    # Thumbnail) vẫn hiện đúng tên/icon; card chỉ lấy từ ``visible``.
    workspace = _workspace_data(ok_apps, db_user)
    categories = _prepare_home_items(visible)
    for item in visible:
        item.home_popularity = workspace["popularity"].get(item.manifest.slug, 0)
        item.home_used = item.manifest.slug in workspace["used_slugs"]

    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "authed": True,
        "nav": "home",
        "apps": visible,
        "broken": [a for a in loaded if a.error],
        "app_setup": app_setup,
        "home_workspace": True,
        "workspace": workspace,
        "home_categories": categories,
    })


def _user_hien_tai(request: Request):
    """User CSDL từ phiên, hoặc None (admin-env / ẩn danh / chưa có DB)."""
    try:
        sid = request.session.get("sid")
        if not sid:
            return None
        from platform_core.db import get_session
        from platform_core.users import lay_user_tu_phien
        gen = get_session(); db = next(gen)
        try:
            return lay_user_tu_phien(db, sid)
        finally:
            try: next(gen)
            except StopIteration: pass
    except Exception:
        return None
