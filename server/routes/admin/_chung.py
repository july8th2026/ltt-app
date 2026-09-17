"""Nguồn điều hướng DUY NHẤT của khu quản trị.

Trước đợt này có **ba** danh sách điều hướng sống song song:

  1. `server/admin.py:_ADM_NAV`          13 mục + 4 dòng nhóm
  2. `server/admin_api.py:NAV`           12 mục "API — ..." chèn vào (1)
  3. `server/admin_templates/sqladmin/base.html`  5 thẻ <a> viết tay

Ba danh sách cho một cây điều hướng nghĩa là bản thứ hai và thứ ba luôn là bản
bị quên khi thêm trang — và trang SQLAdmin thật sự đã có một bộ điều hướng khác
hẳn 25 mục của trang tự viết. Tệp này thay cả ba.

Khuôn lấy nguyên từ `server/routes/developer/_chung.py` (khu `/developers`, đã
chạy production và có test chốt trần). Bốn cấu trúc, cùng tên, cùng ngữ nghĩa —
người đọc một khu là hiểu khu kia. Khác biệt duy nhất: không bọc nhãn bằng
`N_()`, vì khu quản trị là tiếng Việt cứng và không có yêu cầu đa ngữ.

Hợp đồng đầy đủ: `docs/admin_mvp_v3/04_EXTENSION_CONTRACT.md`.
Bố cục đã đóng băng: `docs/admin_mvp_v3/03_IA_FREEZE.md`.
"""

from __future__ import annotations

from contextvars import ContextVar

_REQUEST_APPS: ContextVar[tuple] = ContextVar("admin_navigation_apps", default=())


class AdminNavigationContextMiddleware:
    """Bind navigation to the serving app, including concurrent test apps."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        serving_app = scope.get("app")
        state = getattr(serving_app, "state", None)
        token = _REQUEST_APPS.set(tuple(getattr(state, "loaded_apps", ()) or ()))
        try:
            await self.app(scope, receive, send)
        finally:
            _REQUEST_APPS.reset(token)

# ── Trần chống phình ─────────────────────────────────────────────────────────
# Đây là CHỐT, không phải lời khuyên: `test_317` đọc hai hằng này. Muốn vượt
# trần thì phải sửa `03_IA_FREEZE.md` trước, không phải sửa số ở đây.
TRAN_MUC_CHA = 7
TRAN_MUC_CON = 6


#: `khoá → đường dẫn → nhãn`. MỌI trang quản trị phải có một dòng ở đây, kể cả
#: trang không lên thanh bên (hành động theo ngữ cảnh, tab cấp ba). Không có
#: dòng ở đây thì `CHA_CUA` không biết mục cha nào phải sáng, và người vận hành
#: mở trang đó sẽ thấy thanh bên không có gì sáng cả.
SECTIONS = (
    # ── Tổng quan ────────────────────────────────────────────────────────────
    ("tong_quan",      "/admin/",                   "Tổng quan"),

    # ── Khách hàng ───────────────────────────────────────────────────────────
    ("khach_hang",     "/admin/khach-hang",         "Khách hàng"),
    ("ho_so_360",      "/admin/nguoi-dung",         "Hồ sơ 360"),
    # Cửa vào, không phải nơi chốn — ô tìm ở thanh trên dẫn tới đây, nên nó
    # KHÔNG lên thanh bên. Vẫn phải có dòng ở đây, nếu không mở `/admin/tim`
    # sẽ không mục nào sáng.
    ("tim_kiem",       "/admin/tim",                "Tìm"),

    # ── Tài chính ────────────────────────────────────────────────────────────
    ("tai_chinh",      "/admin/doanh-thu",          "Tài chính"),
    ("don_hang",       "/admin/don",                "Đơn hàng"),
    ("so_credit",      "/admin/credit-entry/list",  "Sổ credit"),
    ("goi_nap",        "/admin/goi",                "Gói nạp"),
    # Hành động, không phải nơi chốn — rời thanh bên (02_DEEP_AUDIT A-02).
    ("cap_credit",     "/admin/grant-credit",       "Cấp credit"),

    # ── API Platform ─────────────────────────────────────────────────────────
    # 12 mục ngang cấp cũ gom thành 1 mục cha + 5 mục con. Không URL nào đổi.
    ("api_overview",   "/admin/api-tong-quan",      "API Platform"),
    ("api_access",     "/admin/api-tai-khoan",      "Access"),
    ("api_khoa",       "/admin/api-khoa",           "Khoá của khách"),
    ("api_governance", "/admin/api-cong-cu",        "Governance"),
    ("api_policy",     "/admin/api-chinh-sach",     "Chính sách"),
    ("api_kill",       "/admin/api-kill-switch",    "Kill switch"),
    ("api_ops",        "/admin/api-request",        "Operations"),
    ("api_job",        "/admin/api-job",            "Job API"),
    ("api_security",   "/admin/api-bao-mat",        "Bảo mật"),
    ("api_trace",      "/admin/api-trace",          "Truy vết"),
    ("api_economics",  "/admin/api-gia",            "Economics"),
    ("api_margin",     "/admin/api-margin",         "Margin"),

    # ── Vận hành ─────────────────────────────────────────────────────────────
    # ⚠️ Nhãn là "Provider Credentials", KHÔNG phải "APIKEYS". Ngày 23/08 chủ dự
    #    án vào nhầm bảng thô vì hai mục từng cùng tên (xem `server/admin.py`
    #    khối chú thích trên `ApiKeyAdmin`). Ở đây có BA thứ mang chữ "key":
    #    credential của NỀN TẢNG (mục này), bảng thô của nó (Nâng cao), và khoá
    #    API của KHÁCH (API Platform → Access). Nhãn phải tách chúng ra.
    ("van_hanh",       "/admin/apikeys",            "Vận hành"),
    ("provider_them",  "/admin/api-key-them",       "Thêm credential"),
    ("provider_sua",   "/admin/api-key-sua",        "Sửa credential"),
    ("provider_test",  "/admin/api-key-test",       "Thử credential"),
    ("models",         "/admin/api-models",         "Model"),
    ("job",            "/admin/job/list",           "Job"),

    # ── Hệ thống ─────────────────────────────────────────────────────────────
    ("he_thong",       "/admin/he-thong",           "Hệ thống"),
    ("nhat_ky",        "/admin/nhat-ky-admin/list", "Nhật ký admin"),
    ("nang_cao",       "/admin/nang-cao",           "Nâng cao / Data Explorer"),
    ("tinh_trang",     "/status",                   "Tình trạng"),
)

#: Nhóm → các khoá lên thanh bên. SÁU mục cha, không hơn.
#:
#: 🔴 VÌ SAO ĐỔI. Hai mươi lăm mục phẳng không phải điều hướng, nó là một danh
#:    mục route. Và 12 trong số đó cùng tiền tố "API — ", tức MỘT miền chiếm
#:    48% thanh bên. Người xử sự cố phải tự đoán trong 12 mục cùng tên cái nào
#:    chứa câu trả lời, và không có gì nói cho họ biết `api-request`,
#:    `api-job`, `api-trace` là ba lát cắt của cùng một dòng chảy.
#:
#: ⚠️ MỤC BỊ HẠ KHỎI THANH BÊN VẪN CÒN NGUYÊN ROUTE. Chúng thành mục con hoặc
#:    hành động theo ngữ cảnh (xem `CHA_CUA`). Một URL đã vào dấu trang và tin
#:    nhắn hỗ trợ thì việc nó 404 là thiệt hại thật; việc nó rời thanh điều
#:    hướng thì không. Số route bị xoá trong đợt này: 0.
NHOM_NAV = (
    ("tong_quan", "khach_hang", "tai_chinh", "api_overview", "van_hanh", "he_thong"),
)

#: Mục con → mục cha. Mở một mục con thì mục cha sáng.
#: BẮT BUỘC có dòng cho cả trang tab lẫn trang hành động — nếu không, mở
#: `/admin/api-kill-switch` sẽ không mục nào sáng.
CHA_CUA = {
    # Khách hàng
    "ho_so_360": "khach_hang",
    "tim_kiem": "khach_hang",
    # Tài chính
    "don_hang": "tai_chinh",
    "so_credit": "tai_chinh",
    "goi_nap": "tai_chinh",
    "cap_credit": "tai_chinh",
    # API Platform
    "api_access": "api_overview",
    "api_khoa": "api_overview",
    "api_governance": "api_overview",
    "api_policy": "api_overview",
    "api_kill": "api_overview",
    "api_ops": "api_overview",
    "api_job": "api_overview",
    "api_security": "api_overview",
    "api_trace": "api_overview",
    "api_economics": "api_overview",
    "api_margin": "api_overview",
    # Vận hành
    "provider_them": "van_hanh",
    "provider_sua": "van_hanh",
    "provider_test": "van_hanh",
    "models": "van_hanh",
    "job": "van_hanh",
    # Hệ thống
    "nhat_ky": "he_thong",
    "nang_cao": "he_thong",
    "tinh_trang": "he_thong",
}

#: Mục cha → dải mục con hiện BÊN TRONG trang cha.
#:
#: ⭐ Nhãn ở đây là nhãn TRONG NGỮ CẢNH của cha, nên nó khác nhãn ở `SECTIONS`:
#:    đứng trong "API Platform" thì mục con tên "Access" là đủ.
#:
#: Trang hành động (`cap_credit`, `provider_them/sua/test`, `api_trace`) cố ý
#: KHÔNG có mặt ở đây: chúng vào được từ ngữ cảnh của đối tượng bị tác động,
#: không phải từ một dải tab.
MUC_CON = {
    "khach_hang": (
        ("khach_hang", "Danh sách"),
        ("ho_so_360", "Hồ sơ 360"),
    ),
    "tai_chinh": (
        ("tai_chinh", "Tổng quan"),
        ("don_hang", "Đơn hàng"),
        ("so_credit", "Sổ credit"),
        ("goi_nap", "Gói nạp"),
    ),
    "api_overview": (
        ("api_overview", "Tổng quan"),
        ("api_access", "Truy cập"),
        ("api_governance", "Quản trị"),
        ("api_ops", "Vận hành"),
        ("api_economics", "Kinh tế"),
    ),
    "van_hanh": (
        ("van_hanh", "Provider Credentials"),
        ("models", "Model"),
        ("job", "Job"),
    ),
    "he_thong": (
        ("he_thong", "Tình trạng nền tảng"),
        ("nhat_ky", "Nhật ký admin"),
        ("nang_cao", "Nâng cao / Data Explorer"),
    ),
}

#: Tab cấp ba: hiện trong một mục con, dưới dải `MUC_CON`. Chỉ dùng khi một mục
#: con thật sự gom nhiều trang đã có từ trước.
TAB_CUA = {
    "api_access": (("api_access", "Tài khoản"), ("api_khoa", "Khoá của khách")),
    "api_khoa": (("api_access", "Tài khoản"), ("api_khoa", "Khoá của khách")),
    "api_governance": (("api_governance", "Công cụ"), ("api_policy", "Chính sách"),
                       ("api_kill", "Kill switch")),
    "api_policy": (("api_governance", "Công cụ"), ("api_policy", "Chính sách"),
                   ("api_kill", "Kill switch")),
    "api_kill": (("api_governance", "Công cụ"), ("api_policy", "Chính sách"),
                 ("api_kill", "Kill switch")),
    "api_ops": (("api_ops", "Request"), ("api_job", "Job"), ("api_security", "Bảo mật")),
    "api_job": (("api_ops", "Request"), ("api_job", "Job"), ("api_security", "Bảo mật")),
    "api_security": (("api_ops", "Request"), ("api_job", "Job"),
                     ("api_security", "Bảo mật")),
    "api_economics": (("api_economics", "Giá"), ("api_margin", "Margin")),
    "api_margin": (("api_economics", "Giá"), ("api_margin", "Margin")),
}


# ── Dẫn xuất ─────────────────────────────────────────────────────────────────

_HREF = {khoa: href for khoa, href, _ in SECTIONS}
_NHAN = {khoa: nhan for khoa, _, nhan in SECTIONS}


def href_cua(khoa: str) -> str:
    """Đường dẫn của một khoá. Ném `KeyError` nếu khoá chưa khai ở `SECTIONS` —
    im lặng trả rỗng sẽ sinh ra `<a href="">` trông như một link sống."""
    return _HREF[khoa]


def _cha(khoa: str) -> str:
    return CHA_CUA.get(khoa, khoa)


def dieu_huong(active: str, *, apps=None) -> dict:
    """Dựng toàn bộ dữ liệu điều hướng cho một trang.

    `active` là khoá của trang đang mở. Trả về thanh bên, dải mục con, dải tab
    và mẩu bánh mì — bốn thứ dựng từ **một** cây, nên chúng không thể lệch nhau.
    """
    from platform_core.registry import _validate_admin_nav

    href = dict(_HREF)
    labels = dict(_NHAN)
    parents = dict(CHA_CUA)
    children = dict(MUC_CON)
    roots = [key for group in NHOM_NAV for key in group]
    for item in (_REQUEST_APPS.get() if apps is None else apps):
        manifest = item.manifest
        if item.error or not manifest.enabled or not manifest.admin_nav:
            continue
        _validate_admin_nav(manifest)
        keys = [f"app_{manifest.slug}_{entry.nav_key}" for entry in manifest.admin_nav]
        root = keys[0]
        roots.append(root)
        for key, entry in zip(keys, manifest.admin_nav, strict=True):
            if key in href:
                raise ValueError("duplicate app admin navigation key")
            href[key] = entry.path
            labels[key] = entry.label
            if key != root:
                parents[key] = root
        children[root] = tuple((key, entry.label) for key, entry in
                               zip(keys[1:], manifest.admin_nav[1:], strict=True))
    if len(roots) > TRAN_MUC_CHA:
        raise ValueError("admin parent navigation exceeds approved capacity")
    cha = parents.get(active, active)

    thanh_ben = [
        {"khoa": k, "href": href[k], "nhan": labels[k], "active": k == cha}
        for k in roots
    ]

    muc_con = [
        {"href": href[k], "nhan": nhan, "active": k == active}
        for k, nhan in children.get(cha, ())
    ]
    # Mục con nào đang mở: khớp trực tiếp, hoặc là mục con chứa tab đang mở.
    if muc_con:
        khoa_muc_con = [k for k, _ in children[cha]]
        dang_mo = active if active in khoa_muc_con else None
        if dang_mo is None:
            for k in khoa_muc_con:
                if active in [t for t, _ in TAB_CUA.get(k, ())]:
                    dang_mo = k
                    break
        for i, k in enumerate(khoa_muc_con):
            muc_con[i]["active"] = (k == dang_mo)

    tab = [
        {"href": href[k], "nhan": nhan, "active": k == active}
        for k, nhan in TAB_CUA.get(active, ())
    ]

    banh_mi = []
    if cha != active:
        banh_mi = [{"href": href[cha], "nhan": labels[cha]}]

    return {
        "thanh_ben": thanh_ben,
        "muc_con": muc_con,
        "tab": tab,
        "banh_mi": banh_mi,
        "nhan_trang": labels.get(active, ""),
        "co_tab_hoac_con": bool(muc_con or tab),
    }


# ── An trang nghiep vu khoi thanh ben cua SQLAdmin ───────────────────────────

class AnTrongMenuSqlAdmin:
    """Trang nghiệp vụ tự viết KHÔNG xuất hiện trong thanh bên của SQLAdmin.

    SQLAdmin dựng thanh bên riêng từ danh sách view đã đăng ký — đó là **nguồn
    điều hướng thứ tư** của khu quản trị, sau `_ADM_NAV`, `admin_api.NAV` và
    thanh `.ltt-adminbar` viết tay. Nó liệt kê cả 31 view theo thứ tự đăng ký,
    nên nửa SQLAdmin của khu quản trị vẫn là một danh sách phẳng 31 mục trong
    khi nửa kia đã là cây sáu miền.

    ⛔ `is_visible` chỉ ẩn khỏi MENU. Route vẫn sống, URL vẫn mở được, dấu trang
       vẫn chạy — đúng luật L1 của `03_IA_FREEZE.md`: hạ khỏi thanh bên không
       phải là xoá.

    Bảng thô (`ModelView`) KHÔNG dùng lớp này: thanh bên của SQLAdmin **chính
    là** khu Data Explorer, và tám cái tên bảng ở đó là nội dung đúng của nó.

    Lớp này sống ở đây chứ không ở `server/admin.py` để chiều phụ thuộc luôn là
    miền → registry. `server/admin_api.py` từng phải import ngược lên tệp nền
    chỉ để lấy một mixin, và một phụ thuộc ngược chiều là thứ `02_DEEP_AUDIT.md`
    C-03 đã ghi nhận.
    """

    def is_visible(self, request) -> bool:   # noqa: ARG002 - chu ky cua sqladmin
        return False
