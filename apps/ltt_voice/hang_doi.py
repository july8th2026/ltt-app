"""hang_doi.py — tuổi hàng đợi của một job Voice, MỘT chỗ cho mọi màn (GUI-D005/D015).

🔴 VÌ SAO (đo 13–16/09/2026): `LTT_WORKER_POOLS` thiếu làn `voice` làm job nằm
   `queued` ba ngày. Studio nói "Đang xếp hàng…", Lịch sử gắn badge "Đang chờ" —
   job ba ngày tuổi trông y hệt job vừa nộp. Hai màn cần CÙNG một ngưỡng, nên
   ngưỡng nằm ở đây, không ở route của một màn.

⛔ Không bịa trạng thái ("đang tìm máy", "đang vào GPU") — CSDL không có dữ liệu
   riêng cho từng giai đoạn đó. Chỉ nói job đã nằm bao lâu, và từ ngưỡng nào thì
   đó là bất thường.
"""
from __future__ import annotations

from datetime import datetime, timezone

#: Job Voice thật xong trong ~10–35 giây kể cả lúc chạy (đo 16/09: nhặt sau
#: 0,9 s, xong sau 21 s) ⇒ còn `queued` quá 60 s là BẤT THƯỜNG.
NGUONG_CHO_MAY_S = 10
NGUONG_CHO_LAU_S = 60


def tuoi_hang_doi_s(tao_luc) -> int:
    """Giây từ lúc tạo tới bây giờ, theo đồng hồ MÁY CHỦ. Cột thiếu múi giờ
    (SQLite) coi là UTC — cùng quy ước lưu của nền tảng."""
    if tao_luc is None:
        return 0
    if tao_luc.tzinfo is None:
        tao_luc = tao_luc.replace(tzinfo=timezone.utc)
    return max(0, int((datetime.now(timezone.utc) - tao_luc).total_seconds()))


def muc_cho(tuoi_s: int) -> str:
    """`moi` < 10 s ≤ `cho_may` ≤ 60 s < `lau`."""
    if tuoi_s > NGUONG_CHO_LAU_S:
        return "lau"
    if tuoi_s >= NGUONG_CHO_MAY_S:
        return "cho_may"
    return "moi"
