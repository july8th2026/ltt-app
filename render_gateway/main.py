"""
main.py — điểm khởi động của cổng render trên MÁY B.

    E:\\AI\\ltt_render\\venv\\Scripts\\python.exe -m render_gateway.main

Chạy dưới NSSM thành dịch vụ `LTTRenderGateway`, tự khởi động cùng máy và tự bật
lại khi chết — **có trần số lần restart**, không để rơi vào vòng lặp khởi động.

⛔ Mặc định chỉ nghe `127.0.0.1`. Muốn máy A gọi được thì đặt
   `LTT_RENDER_HOST=192.168.2.66` **và** mở tường lửa CHỈ cho 192.168.2.17.
   ComfyUI thì **không bao giờ** đổi khỏi `127.0.0.1` (Q102).
"""
from __future__ import annotations

import logging
import os
import pathlib
import sys

#: Tệp env của cổng, do `cai_dat_dich_vu.ps1` tạo và giữ bearer token.
TEP_ENV = pathlib.Path(r"C:\ProgramData\LTTRender\gateway.env")


def nap_env(tep: pathlib.Path = TEP_ENV) -> int:
    """Đọc `gateway.env` vào `os.environ`. Trả số biến vừa nạp.

    🔴 VÌ SAO CỔNG PHẢI TỰ ĐỌC, THAY VÌ TRÔNG VÀO NSSM.

       `cai_dat_dich_vu.ps1` nướng `gateway.env` vào `AppEnvironmentExtra` **lúc
       CÀI**. Nên sửa `gateway.env` rồi khởi động lại dịch vụ thì **KHÔNG ăn gì**:
       tiến trình lên lại với env CŨ, không lỗi nào báo, chỉ là cờ mới không có
       tác dụng.

       Cái bẫy đó đã cắn dự án này **hai lần** — một lần ở cổng VLM máy B, một lần
       ở `LTT_PUBLIC_API_TOOLS` trên máy A (nên mới có `setup/nap_lai_env.ps1`).
       Đọc tệp ở đây làm nó **không thể xảy ra lần thứ ba** cho cổng này.

    ⛔ KHÔNG ghi đè biến đã có trong `os.environ`. Nếu ai đó đặt biến ở cấp cao
       hơn (nssm, hay dòng lệnh khi gỡ lỗi) thì cái đó phải thắng — nếu không thì
       không còn cách nào ghi đè cấu hình để thử một lần chạy.

    ⛔ KHÔNG in giá trị nào ra log: tệp này giữ bearer token.
    """
    if not tep.exists():
        return 0
    so = 0
    # utf-8-sig: nuốt BOM nếu ai đó soạn tệp bằng công cụ chèn BOM. Quy tắc 1 của
    # CLAUDE.md nói đừng GHI BOM; đọc thì phải chịu được.
    for dong in tep.read_text(encoding="utf-8-sig").splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#") or "=" not in dong:
            continue
        ten, _, gia_tri = dong.partition("=")
        ten = ten.strip()
        if ten and ten not in os.environ:
            os.environ[ten] = gia_tri.strip()
            so += 1
    return so


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("render_gateway")

    from .api import create_app
    from .comfy import ComfyClient
    from .config import Config
    from .http import HttpxTransport

    # Nạp env TRƯỚC khi đọc cấu hình — xem `nap_env`.
    so_bien = nap_env()
    if so_bien:
        log.info("da nap %d bien tu %s", so_bien, TEP_ENV)

    cfg = Config.from_env()
    if not cfg.token:
        log.warning("LTT_RENDER_TOKEN chua dat — cong dang KHONG kiem tra token. "
                    "Chi chap nhan duoc khi host la 127.0.0.1.")
        if cfg.host not in ("127.0.0.1", "localhost"):
            log.error("TU CHOI khoi dong: nghe %s ma khong co token.", cfg.host)
            return 2

    comfy = ComfyClient(HttpxTransport(cfg.comfy_url))
    app = create_app(cfg, comfy)

    import uvicorn
    log.info("render gateway nghe %s:%d, ComfyUI o %s", cfg.host, cfg.port, cfg.comfy_url)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
