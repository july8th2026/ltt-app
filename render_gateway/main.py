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
import sys


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log = logging.getLogger("render_gateway")

    from .api import create_app
    from .comfy import ComfyClient
    from .config import Config
    from .http import HttpxTransport

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
