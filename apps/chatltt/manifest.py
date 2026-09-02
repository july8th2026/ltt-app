"""
ChatLTT — sản phẩm hội thoại LTT-native trên ba model nhà. (H43, 2026-09)

## Vì sao là một APP mà không phải một platform capability

Nó là **một bề mặt khách ở một đường dẫn** (`/chatltt`, Q30). Nó không mount
ngoài `route_prefix`, không cấp credential toàn hệ thống — hai lý do khiến Public
API (Q92) và Nexus (Q93) phải là capability. Xem `docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md` D1.

## Vì sao KHÔNG có job_types / credit_cost / tools

ChatLTT là **client** của ba năng lực đã có giá, đã có job, đã có admission:
`text.chat` (`apps/ltt_llm`), `image.ltt` (`apps/anhnoibo`), `speech.ltt`
(`apps/ltt_voice`). Nó gọi qua `platform_core.runtime_noi_bo` — không tự tính
giá, không tự dựng hàng đợi, không import ba app kia (test_147/test_308 chốt).
Khai `job_types` ở đây là mời một sổ tiền thứ hai.

## Trạng thái

`enabled=False`, `public=False` cho tới khi Phase 13 của H43 PASS: không lên
catalog, không lên header; route vẫn được gắn để trang giữ chỗ trả 200 cho
người đã đăng nhập (bẫy link 404 trong header — `AGENTS.md` §8.2c).
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

MANIFEST = AppManifest(
    slug="chatltt",
    display_name="ChatLTT",
    route_prefix="/chatltt",
    summary=N_('Trò chuyện với model của LTT: văn bản, ảnh và giọng nói trong một hội thoại.'),
    icon="💬",
    accent="#0F62FE",

    job_types=(),
    requires=(),
    credit_cost=None,

    enabled=False,
    public=False,
    surface="customer",
    lifecycle="development",
    group="Chat",
    badge=N_('MỚI'),
    capabilities=("Chat", "AI Text", "audio"),
    # Bảng CSDL riêng của app (Phase 07): `chatltt_conversations`, `chatltt_messages`,
    # `chatltt_executions` — trong `apps/chatltt/tables.py`.
    table_prefix="chatltt",
    notes=("Client noi bo cua text.chat / image.ltt / speech.ltt qua "
           "platform_core.runtime_noi_bo. Khong goi /api/v1, khong biet URL may B."),
)
