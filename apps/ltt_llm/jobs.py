"""
jobs.py — handler chạy trong worker, cho **cửa bất đồng bộ**. (H38)

    POST /api/v1/jobs {"tool": "text.chat", ...}  ->  worker  ->  handle()

⭐ Cửa này có được **miễn phí** nhờ khai `text.chat` trong manifest. Nó là đường
   lui khi prompt quá dài cho trần 125 giây mặc định của Cloudflare. Canary API
   thật gần public cap đã tốn 102 giây; phiên agent dài hoặc lượt sinh nhiều
   nghìn token vẫn có thể vượt dù engine chịu được cửa sổ 131K.

⛔ HANDLER KHÔNG TRỪ CREDIT. Nền tảng đã giữ chỗ theo `credit_cost` lúc submit và
   sẽ quyết toán quanh job. Trừ thêm ở đây là thu hai lần.

⛔ HANDLER KHÔNG CHỨA NGHIỆP VỤ. Nó chỉ mở phiên CSDL, gọi `features.chay`, và
   dịch kết quả — `AGENTS.md` mục 8.
"""
from __future__ import annotations

from apps.ltt_llm import features


def handle(params: dict, ctx=None) -> dict:
    """Một lượt sinh văn bản. Trả về đúng hình dạng `returns` của ToolSpec."""
    from platform_core.db import get_session

    if ctx is not None:
        ctx.progress(5, "dang goi model")

    gen = get_session()
    db = next(gen)
    try:
        kq = features.chay(
            db, params,
            on_dispatch=(ctx.provider_dispatched if ctx is not None else None),
            on_rejected=(ctx.provider_rejected if ctx is not None else None))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass

    if ctx is not None:
        ctx.progress(100, "xong")

    # `usage` đi kèm kết quả là **có chủ ý** — xem `KetQua.as_result`. Không báo
    # thì `public_api/costing.py` không quy được token về job này.
    return kq.as_result()
