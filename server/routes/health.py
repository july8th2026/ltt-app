"""Health/readiness/version endpoints (P3). No authentication required —
these are meant to be probed by the reverse proxy / service manager."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

from platform_core import to_tien

try:
    from version import APP_VERSION_SHORT as _APP_VERSION
except ImportError:
    _APP_VERSION = "unknown"

log = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict:
    """Process is up and able to answer HTTP requests. Never checks
    dependencies — that's /ready's job. A monitor that gets anything other
    than 200 here should restart the process, not wait."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> dict:
    """Process is up AND its dependencies are actually reachable.

    The database check is deliberately a real round-trip (`SELECT 1`), not a
    "was a connection string configured" check. A configured-but-unreachable
    database is exactly the state that makes an application look healthy while
    every request fails.

    `reason` always names *what* is wrong. Any database error passes through
    `che_mat_khau()` first — driver messages routinely embed the whole
    connection string, and this endpoint is unauthenticated by design so the
    reverse proxy can probe it.

    ⭐ Từ 2026-08-25 hàm này **không còn đọc tệp cấu hình nào**. Trước đó nó trả
       503 "config not loaded" khi `data/config.json` hỏng — mà tệp đó là cấu
       hình của app socialbot, nay đã gỡ. Nghĩa là suốt thời gian ấy một app
       đóng băng quyết định được nền tảng có sẵn sàng hay không, và nssm khởi
       động lại tiến trình theo câu trả lời đó. Sự cố BOM ghi ở `AGENTS.md`
       mục 5 đi đúng đường này.

       Hồ sơ môi trường nay lấy từ `LTT_ENV` (đã nằm sẵn trong
       `server_settings`, không phải một lượt đọc đĩa), nên "sẵn sàng" chỉ còn
       đúng một nghĩa: **CSDL nối được**.
    """
    server_settings = getattr(request.app.state, "server_settings", None)
    environment = (server_settings.environment.value
                   if server_settings is not None else "unknown")

    db_ok, db_reason = _kiem_tra_csdl()
    if not db_ok:
        response.status_code = 503
        return {
            "status": "not_ready",
            "reason": f"database: {db_reason}",
            "environment": environment,
        }

    return {
        "status": "ready",
        "environment": environment,
        "database": "ok",
        # 🔴 "Sẵn sàng" trả lời *"tôi có phục vụ được không"*. Trường này trả lời
        #    một câu KHÁC: *"tôi có NÊN đang chạy không"* — và hai câu đó tách ra
        #    khi tiến trình sống sót mồ côi sau khi vỏ bọc NSSM chết.
        #
        #    Đo trên máy B 01/09: `/health` trả 200 suốt **99 giây** trong khi
        #    `Get-Service` nói `Stopped` và không ai dựng dậy nữa. Máy A đo cùng
        #    ngày có **cùng lỗ** (không dịch vụ nào có `FAILURE_ACTIONS`), chỉ
        #    khác là ở đây nó nằm trên máy đang phục vụ khách thật.
        #
        # ⛔ CỐ Ý KHÔNG đổi `status` thành `not_ready` khi mồ côi. Tiến trình mồ
        #    côi **vẫn phục vụ được**; trả 503 sẽ khiến proxy ngắt một dịch vụ
        #    đang chạy tốt và biến một sự cố vận hành thành một sự cố ngừng
        #    dịch vụ. Việc của trường này là làm sự cố **nhìn thấy được**.
        "duoi_dich_vu": to_tien.trang_thai(),
    }


def _kiem_tra_csdl() -> tuple[bool, str]:
    """Thử kết nối CSDL. Tách ra để test thay thế được dễ dàng.

    Chưa cấu hình CSDL **không** bị coi là lỗi trong giai đoạn chuyển tiếp:
    H1.1 vừa dựng lớp CSDL, nhưng chưa phần nào của ứng dụng phụ thuộc vào nó.
    Bắt `/health/ready` trả 503 ngay bây giờ sẽ làm dịch vụ đang chạy bị trình
    quản lý khởi động lại liên tục vì một phụ thuộc chưa ai dùng tới.

    Khi H1.2 đưa bảng người dùng vào, đổi nhánh này thành lỗi thật — và đổi cả
    test đi kèm trong cùng một lần.
    """
    try:
        from platform_core.db import DatabaseNotConfigured, kiem_tra_ket_noi
        try:
            from platform_core.db import database_url
            database_url()
        except DatabaseNotConfigured:
            return True, ""      # chua cau hinh -> chua phai loi (xem docstring)
        return kiem_tra_ket_noi()
    except Exception as exc:      # pragma: no cover - loi ngoai du kien
        return False, f"{type(exc).__name__}"


@router.get("/version")
def version() -> dict:
    """Bản ĐANG CHẠY là bản nào — commit, tài sản tĩnh, và trần của Voice.

    🔴 VÌ SAO HÀM NÀY KHÔNG CÒN CHỈ TRẢ MỘT CHUỖI HẰNG.

       Nó từng trả `{"version": "v1.0"}`, đọc từ `version.py` — một tệp của
       **LTTStudios VideoBot**, ghim `APP_VERSION = "1.0.0"` bằng tay từ 2025.
       Con số ấy không đổi qua một lần deploy nào, nên nó trả lời được đúng
       một câu hỏi: *"tiến trình có sống không"* — mà `/health/live` đã trả
       lời rồi.

    ⭐ Ngày 05/09/2026 câu hỏi thật sự cần hỏi là một câu khác: *"mã đang phục
       vụ khách có phải mã tôi đang nhìn không?"* Hôm ấy câu trả lời là
       **không** — bản deploy đứng ở thời `master` trong khi nhánh làm việc đã
       đi trước 94 commit — và để biết điều đó phải so `md5sum` của
       `/static/voice.js` giữa hai thư mục. Không có endpoint nào nói ra.

    ⭐ BA TRƯỜNG, VÀ MỖI TRƯỜNG BẮT MỘT KIỂU TRÔI KHÁC NHAU:

         `commit`     — mã nguồn trôi   (bản deploy cũ hơn kho)
         `asset_ver`  — tài sản tĩnh trôi (CSS/JS cũ qua Cloudflare)
         `ltt_voice`  — hợp đồng trôi   (trần sản phẩm nói một đằng, chạy một nẻo)

       Ba thứ ấy hỏng **độc lập với nhau**: deploy đúng mà CF giữ CSS cũ là một
       ca; deploy cũ mà CF sạch là một ca khác. Một trường gộp sẽ không phân
       biệt được, và phân biệt chính là toàn bộ giá trị của endpoint này.

    ⚠️ `version` giữ nguyên tên khoá cho thứ đang đọc nó (`docs/QUALITY_LAB/`,
       `docs/PUBLIC_API/TEST_STRATEGY_V1.md`). Đừng bỏ nó đi để cho gọn.

    ⛔ Endpoint này KHÔNG có xác thực. Xem `platform_core/dau_van_tay.py` về
       việc cái gì được phép nằm ở đây — tóm tắt: chỉ những thứ đã công khai ở
       chỗ khác, và không bao giờ là tên nhánh hay đường dẫn.
    """
    from platform_core import dau_van_tay
    from server.templating import ASSET_VER

    # 🔴 ĐỌC QUA REGISTRY, KHÔNG IMPORT TÊN APP NÀO.
    #
    #    Bản vá đầu viết `from apps.ltt_voice.tham_so_cong_khai import ...`.
    #    `tests/test_147_layering.py` đỏ ngay, và nó đúng: *"Nền tảng KHÔNG được
    #    biết tên app nào tồn tại."*
    #
    # ⭐ Và phép kiểm ấy không chỉ chặn — nó chỉ ra bản sửa TỐT HƠN. Một endpoint
    #    biết tên `ltt_voice` là một endpoint phải sửa mỗi lần thêm app. Đọc qua
    #    `hop_dong_cong_khai` thì app nào khai, app ấy hiện ra — kể cả app viết
    #    sau tệp này.
    #
    # ⚠️ Bọc an toàn: một app hỏng bản khai không được phép làm câm luôn phần
    #    `commit`/`asset_ver`, vì đó chính là hai thứ ta cần nhất lúc đi tìm
    #    xem app kia hỏng vì sao.
    try:
        from platform_core.registry import discover
        # ⚠️ `discover()` trả `LoadedApp`, KHÔNG phải `AppManifest` — nó bọc
        #    thêm router + lỗi nạp. `LoadedApp.slug` là một `@property` uỷ
        #    quyền, nên `m.slug` chạy được và khiến `m.hop_dong_cong_khai`
        #    **trông như** cũng chạy được. Nó không: `getattr` trả `None`
        #    lặng lẽ, và endpoint báo "không app nào khai" một cách rất tự tin.
        #    Phải đi qua `.manifest`.
        # ⛔ App nạp LỖI vẫn có `manifest` (một bản tối thiểu do `discover`
        #    dựng) nhưng không có hợp đồng — `if` bên dưới lọc nó ra.
        hop_dong = {a.slug: dict(a.manifest.hop_dong_cong_khai)
                    for a in discover()
                    if getattr(a.manifest, "hop_dong_cong_khai", None)}
    except Exception:  # noqa: BLE001
        log.exception("khong doc duoc hop dong cong khai tu registry")
        hop_dong = None

    # ⛔ `doc_da_cache`, KHÔNG `doc()`. Endpoint này không có xác thực và
    #    `doc()` có thể fork `git`; xem docstring của nó về vì sao cache ở đây
    #    còn LÀM TĂNG độ chính xác chứ không đánh đổi.
    van_tay = dict(dau_van_tay.doc_da_cache())
    return {
        "version": _APP_VERSION,
        "commit": van_tay["commit"],
        "commit_nguon": van_tay["nguon"],
        "build_luc": van_tay["luc"],
        "asset_ver": ASSET_VER,
        # `{}` nghĩa là KHÔNG app nào khai; `None` nghĩa là ĐỌC HỎNG. Hai câu
        # trả lời khác nhau, và gộp chúng thành `{}` là biến một sự cố thành
        # một trạng thái bình thường.
        "hop_dong": hop_dong,
    }
