"""
Bản khai của app đang chạy thật: đăng bài Facebook + TikTok.

App này KHÔNG có `routes.py`, và đó là cố ý. Route của nó đã nằm ở
`server/routes/*` và đang chạy trên production ở các đường dẫn gốc
(`/facebook`, `/sheet/facebook`, `/manual/tiktok`, ...). Đổi đường dẫn bây giờ
sẽ phá 1.344 test đang xanh và phá cả Redirect URI OAuth đang chuẩn bị khai
báo ở Meta/TikTok Portal — cái giá không đáng, vì app đã chạy được.

Nên nó là app "được đặc cách": khai `nav` để hiện đúng trên trang chủ và
sidebar, còn route giữ nguyên chỗ cũ. Mọi app MỚI đi theo hợp đồng chuẩn — một
prefix riêng, xem `apps/demo/`.

Khi nào nên dọn: lúc nào cần đúng một prefix cho app này (ví dụ tách bán
riêng), thì đổi sang `/socialbot/...` và cập nhật Redirect URI cùng lúc. Ghi ở
đây để sau này không ai tưởng đó là thiết kế mẫu.
"""
from __future__ import annotations

from platform_core.registry import AppManifest, NavEntry

MANIFEST = AppManifest(
    slug="socialbot",
    display_name="Đăng bài Facebook + TikTok",
    route_prefix="/facebook",          # đường vào chính; các trang khác xem nav
    summary="Chạy hàng đợi từ Google Sheet, đăng thủ công, theo dõi token và "
            "kiểm tra điều kiện audit TikTok.",
    icon="📣",
    accent="#1565C0",

    nav=(
        NavEntry("Sheet FB",        "/sheet/facebook",  "📊", "sheet_fb"),
        NavEntry("Sheet TikTok",    "/sheet/tiktok",    "📊", "sheet_tiktok"),
        NavEntry("Manual FB",       "/manual/facebook", "⚙️", "manual_fb"),
        NavEntry("Manual TikTok",   "/manual/tiktok",   "🎵", "manual_tiktok"),
        NavEntry("Tài khoản FB",    "/facebook",        "🔐", "facebook"),
        NavEntry("Tài khoản TikTok", "/tiktok",         "🎵", "tiktok"),
        NavEntry("Monitor",         "/monitor",         "📈", "monitor"),
        NavEntry("TT Audit",        "/audit",           "📋", "audit"),
    ),

    # Chưa dùng hàng đợi job dùng chung — app này có runner riêng
    # (core/sheet_runner.py). Sẽ chuyển sang job_types khi hợp nhất hàng đợi.
    job_types=(),
    requires=("browser",),   # cần IP dân dụng: Meta/TikTok đánh dấu IP datacenter
    credit_cost=None,        # đang dùng nội bộ, chưa thu phí

    # Các mục doctor thuộc app này → nền tảng gắn badge "cần thiết lập" lên thẻ
    # app socialbot thay vì treo banner FB/TikTok toàn cục (H6.6). Tên phải khớp
    # đúng tiêu đề trong tools/doctor.py (check_tokens).
    blocker_titles=("Tài khoản Facebook", "Tài khoản TikTok"),

    enabled=True,
    group="Đăng bài",
    public=False,   # đóng băng (Q10) + cần OAuth/browser — ẩn khỏi catalog công khai (H6/Q30)
    notes="Đang chạy production. Route ở đường dẫn gốc vì lý do lịch sử — "
          "xem docstring của file này.",
)
