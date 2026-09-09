"""App `lttvideo` — video AI chạy trên C-CLOUD bằng **WanGP làm engine duy nhất**.

Kiến trúc đã khoá: `docs/VIDEO_AI_V2/FINAL_MINIMAL_LTT_WANGP_ARCHITECTURE.md`.

⭐ VÌ SAO APP NÀY MỎNG ĐẾN THẾ

   Lượt trích xuất WanGP (`WANGP_ARCHITECTURE_EXTRACTION.md`) tìm ra **12
   abstraction** mà kế hoạch cũ định xây và **cả 12 đều đã có trong WanGP**:
   khám phá model, schema năng lực, vai media, chuẩn hoá job, hàng đợi thực thi,
   tiến độ/preview/huỷ, template, tiền/hậu xử lý…

   Nên app này **không có** `ModelRegistry`, `IntentResolver`, `CapabilityResolver`,
   `VideoTemplateManager`, `VideoQueue`, `VideoAgent`. Nó chỉ có bốn thứ mà WanGP
   **không có khái niệm**: quyền, tiền, sở hữu, và giao diện tiếng Việt.

⛔ BỐN CỔNG ĐÓNG — cố ý, đừng "sửa":
     `surface="admin"` · `public=False` · `api_exposed` không khai · `lifecycle`
   Baseline chạy **nội bộ**. Và lần này cổng đóng không chỉ vì thận trọng: giấy
   phép `WanGP Community License 2.0` §5.2(g) **cấm** *"exposing the Software to
   customers or end users as a paid feature"* nếu không có giấy phép thương mại
   riêng. Xem `P01_UPSTREAM_PIN.md` mục 2.

⛔ GIÁ KHÔNG Ở FILE NÀY — nó ở `cost.py`, một mức **phẳng** chỉnh được
   (`CREDIT_MOI_GIAY_VIDEO`). `credit_cost` dưới đây là khoản **giữ chỗ**; số
   thật do `jobs.handle` báo về theo **số giây video đã giao** — và bằng 0 khi
   không giao được gì.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry

from . import cost


def _gia(params: dict) -> int:
    """Trần ước cao để giữ chỗ, **không phải giá cuối**."""
    try:
        giay = float(params.get("duration_s") or 5)
    except (TypeError, ValueError):
        giay = 5.0
    return cost.uoc_credit(giay_video=max(giay, 1.0))


MANIFEST = AppManifest(
    slug="lttvideo",
    display_name=N_('Video AI (máy nhà)'),
    route_prefix="/lttvideo",
    summary=N_('Tạo video từ mô tả bằng model chạy trên máy thuê của LTT Studios.'),
    icon="🎬",
    accent="#7C3AED",

    # Nội bộ: `surface="admin"` nghĩa là `server/access_middleware.py:71` trả
    # **404** cho mọi tài khoản có `role != "admin"` — không phải "ẩn khỏi
    # trang chủ", mà là không tồn tại với người khác. 404 chứ không 403: 403
    # xác nhận app có thật.
    surface="admin",
    public=False,
    lifecycle="development",

    nav=(NavEntry(label=N_('Video AI'), path="/lttvideo", icon="🎬"),),

    job_types=("lttvideo.tao",),
    # Worker chỉ gọi HTTP sang C-CLOUD — không cần GPU trên máy chạy worker.
    requires=("api",),
    credit_cost=_gia,

    # ⛔ Không khai `tools=(...)`: mở `/api/v1` là việc của cổng thương mại, và
    #    cổng đó đang ĐÓNG vì giấy phép. Thêm ToolSpec ở đây là mở một đường mà
    #    §5.2(g) chưa cho phép.
    notes=(
        "Engine: WanGP @ 1e1dd2757f24923f008593d9d4ec09062234be20. "
        "Giấy phép WanGP Community License 2.0 — nội bộ được, bán ra ngoài cần "
        "giấy phép thương mại riêng."
    ),
)
