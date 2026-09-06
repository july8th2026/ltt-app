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

`enabled=True`, `public=True` từ **03/09/2026**, khi Phase 13 của H43 PASS.

Trước đó app chạy `enabled=False, public=False`: route vẫn được gắn (để trang
giữ chỗ trả 200 cho người đã đăng nhập — bẫy link 404 trong header,
`AGENTS.md` §8.2c) nhưng không lên catalog và không lên header.

⭐ Bằng chứng bật cờ, không phải "thấy chạy được": tám hành trình A–H chạy lại
   **tươi** trên trình duyệt thật (CSDL mới, hai người dùng, model và worker
   giả), `docs/CHATLTT/reports/13_nghiem_thu.md`. Hành trình B (vision) trượt ở
   lượt đầu và được xây xong trong chính pha đó — `MVP_ACCEPTANCE.md` ghi
   *"vision if advertised"*, và catalog thì đang quảng cáo `reads_images`.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest

from apps.chatltt import gia_trich as _gia_trich
from apps.chatltt.services import hoi_thoai as _hoi_thoai

MANIFEST = AppManifest(
    slug="chatltt",
    display_name="ChatLTT",
    route_prefix="/chatltt",
    summary=N_('Trò chuyện với model của LTT: văn bản, ảnh và giọng nói trong một hội thoại.'),
    icon="💬",
    accent="#0F62FE",

    # ⚠️ CAP NHAT 06/09 (H44 P06 buoc 3). Truoc do la `()`: ChatLTT chi NOP job
    #    sang app khac (`anhnoibo`, `ltt_voice`) qua `tao_media`. `trich_tep` la
    #    viec DAU TIEN app nay tu chay trong worker — nen no them mot thu
    #    `job_runner` biet chay, tuc mot be mat moi cho `leases` va cho so tien.
    #
    # ⛔ No CHUA duoc mo cho model goi. `chinh_sach.CONG_CU_CHO_PHEP` va
    #    `chieu_tool.CHO_MODEL_GOI` van dong — buoc 6 moi mo, theo dung §4.
    job_types=("chatltt.trich_tep",),
    requires=(),
    # ⛔ GIA CHUA CHOT — `gia_trich.credit_cost` NEM cho toi khi chu du an dat
    #    so. Fail-closed co chu dich: mot gia 0 tam thoi CHINH LA cai lo ma
    #    cua credit cua `upload_sessions` sinh ra de bit, chi khac la no trong
    #    nhu mot mac dinh vo hai. Xem `apps/chatltt/gia_trich.py`.
    credit_cost=_gia_trich.credit_cost,

    enabled=True,
    public=True,
    surface="customer",
    lifecycle="development",
    group="Chat",
    badge=N_('MỚI'),
    capabilities=("Chat", "AI Text", "audio"),
    # Bảng CSDL riêng của app (Phase 07): `chatltt_conversations`, `chatltt_messages`,
    # `chatltt_executions` — trong `apps/chatltt/tables.py`.
    table_prefix="chatltt",

    # Viec dinh ky: don that nhung hoi thoai da xoa mem qua 30 ngay. Chay duoi
    # lease cua nen tang nen dung MOT lan tren ca cum (khuon `apps/vps/bao_tri`).
    bao_tri=_hoi_thoai.bao_tri,
    bao_tri_moi_giay=6 * 3600,
    notes=("Client noi bo cua text.chat / image.ltt / speech.ltt qua "
           "platform_core.runtime_noi_bo. Khong goi /api/v1, khong biet URL may B."),
)
