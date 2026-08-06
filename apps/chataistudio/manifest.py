"""
App `chataistudio` — CHAT AI STUDIO. Di trú từ AI Creative Studio (module `codex`)
BOT GEMINI. Chat + tạo ảnh trong phiên, per-user, qua SIDECAR `LTTStudioCodex`.

KHÔNG khai `job_types`: chat chạy STREAMING trong tiến trình web (không qua hàng đợi
worker) → credit giữ chỗ/quyết toán ngay trong route. Slug là chuỗi riêng.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


MANIFEST = AppManifest(
    slug="chataistudio",
    display_name="Chat AI Studio",
    route_prefix="/chataistudio",
    summary=N_('Trò chuyện với AI (GPT-5) và tạo ảnh trực tiếp trong phiên chat. Lưu hội thoại riêng theo tài khoản.'),
    icon="💠",
    accent="#0A7E6B",

    nav=(NavEntry("Chat AI Studio", "/chataistudio", "💠", "chataistudio"),),

    job_types=(),               # chat streaming trong web, không dùng worker
    requires=("api",),
    credit_cost=None,           # tính credit ngay trong route (theo token thật + ảnh)

    enabled=True,
    public=True,
    group="Chat",
    badge="MỚI",
    notes="Di trú từ AI Creative Studio (codex). Qua sidecar LTTStudioCodex. Cần đăng nhập tài khoản ChatGPT ở admin.",
)
