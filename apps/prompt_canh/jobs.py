"""Handler chạy trong worker cho `gem.run`.

Nó làm đúng một việc mà service không làm được: **nối service với
`runtime_noi_bo`**. Service nhận `goi_model` như một tham số, nên nó kiểm được
mà không cần model thật và không cần CSDL — cùng khuôn `apps/chatltt`.

⛔ Không khai `credit_cost` trong kết quả. Mọi credit của lượt này đã chảy qua
   `runtime_noi_bo` theo từng lượt model; thêm một số ở đây là thu HAI LẦN.
"""
from __future__ import annotations

import logging

from .services import kich_ban

log = logging.getLogger("apps.prompt_canh.jobs")


class LoiPromptCanh(RuntimeError):
    """Lỗi nghiệp vụ — worker biến thành job `error`."""


def _goi_model(db, *, user_id: str, model_alias: str, correlation_id: str):
    """`goi_model(nhac) -> str`, đi qua cửa gọi nội bộ của nền tảng.

    ⭐ Ba thứ đi kèm miễn phí, và cả ba là thứ bot legacy **không có**: giành
       suất (admission), kế toán token thật (giữ → đếm → quyết toán), và alias
       model chỉ dịch sang id thật **ngay trước khi ra khỏi nền tảng**.
    """
    from platform_core.runtime_noi_bo import luong as L

    def goi(nhac: str) -> str:
        than = {"model": model_alias,
                "messages": [{"role": "user", "content": str(nhac or "")}]}
        manh: list[str] = []
        try:
            for sk in L.mo_luong(db, user_id=user_id, tool_name=kich_ban.TOOL_LLM,
                                 params=than, correlation_id=correlation_id):
                loai = sk.get("type")
                if loai == "response.delta":
                    manh.append(str(sk.get("text") or ""))
                elif loai == "response.failed":
                    # 🔴 Job HỎNG, không phải "xong với kết quả rỗng". Một bước
                    #    hỏng giữa ba bước để lại một bộ prompt thiếu cảnh, và
                    #    thiếu ở giữa thì không ai nhìn ra.
                    raise LoiPromptCanh(
                        f"model khong tra loi duoc: {sk.get('code') or ''}")
        except L.LoiCuaLuong as e:
            raise LoiPromptCanh(str(e)) from e
        return "".join(manh)

    return goi


def handle(params: dict, ctx=None) -> dict:
    from platform_core.db import get_session

    yc = kich_ban.chuan_hoa(params)
    user_id = str((params or {}).get("owner_id") or "")
    if not user_id:
        raise LoiPromptCanh("thieu `owner_id` — khong biet tinh tien cho ai")

    def tien_do(pt: int, mo_ta: str) -> None:
        if ctx is not None and hasattr(ctx, "progress"):
            ctx.progress(pt, mo_ta)

    gen = get_session()
    db = next(gen)
    try:
        goi = _goi_model(db, user_id=user_id, model_alias=yc.model,
                         correlation_id=str(getattr(ctx, "job_id", "") or ""))
        try:
            ket = kich_ban.chay(yc, goi, tien_do=tien_do)
        except kich_ban.LoiKichBan as e:
            raise LoiPromptCanh(str(e)) from e
    finally:
        db.close()

    log.info("prompt_canh xong job=%s canh=%d prompt=%d luot_model=%d",
             getattr(ctx, "job_id", "?"), len(ket.canh), len(ket.prompt_json),
             ket.so_luot_model)
    return ket.as_result()
