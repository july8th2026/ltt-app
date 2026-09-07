"""
main.py — điểm khởi động cổng VLM trên máy B.

    python -m llm_gateway.main

⛔ Mặc định nghe `127.0.0.1`. Muốn máy A gọi được thì đặt `LTT_LLM_HOST=0.0.0.0`
   **và** mở tường lửa **chỉ cho `192.168.2.17`**. Đừng làm một nửa: mở host mà
   quên tường lửa là phơi model nhà ra cả LAN.

⛔ `llama-swap` và `llama-server` **giữ nguyên `127.0.0.1`**, vĩnh viễn. Chúng
   không có xác thực.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .api import create_app
from .config import Config
from .upstream import HttpxUpstream

#: Tệp cấu hình vận hành trên máy B. `deploy.ps1` sinh ra nó, người vận hành sửa nó.
TEP_ENV = Path(os.environ.get("LTT_LLM_ENV_FILE")
               or r"C:\ProgramData\LTTLlm\gateway.env")


def nap_env(tep: Path = TEP_ENV) -> int:
    """Đọc `gateway.env` vào môi trường tiến trình. Trả về số biến đã nạp.

    🔴 VÌ SAO CẦN: `nssm` **nướng cứng** biến môi trường vào cấu hình dịch vụ lúc
       CÀI. Sửa `gateway.env` rồi `Restart-Service` thì **không có tác dụng gì** —
       dịch vụ vẫn chạy với bộ biến của lần cài đầu tiên.

       Đã dính thật 22/08: đổi `LTT_LLM_MODELS`, khởi động lại, và `/v1/models`
       trả **rỗng** — trông y như fail-closed đang chặn, thật ra là dịch vụ chưa
       bao giờ thấy giá trị mới. Mất mười phút đi tìm nhầm chỗ.

       Đọc tệp ở đây làm cho "sửa cấu hình rồi khởi động lại" thành thao tác đúng
       như mọi người vẫn tưởng.

    ⭐ TỆP THẮNG. Nó là nơi người vận hành sửa; giá trị `nssm` mang theo chỉ là
       ảnh chụp cũ của chính tệp này.
    """
    if not tep.exists():
        return 0
    dem = 0
    for dong in tep.read_text(encoding="utf-8", errors="replace").splitlines():
        d = dong.strip()
        if not d or d.startswith("#") or "=" not in d:
            continue
        ten, _, gt = d.partition("=")
        ten = ten.strip()
        if not ten.startswith("LTT_LLM_"):
            continue
        os.environ[ten] = gt.strip()
        dem += 1
    return dem


def _ai_dang_nghe(host: str, port: int) -> str | None:
    """PID đang nghe `port`, hoặc None nếu cổng trống.

    Dò bằng **connect**, không phải bind: bind rồi đóng để nhường cho uvicorn là
    một cuộc đua. Connect được nghĩa là có người đang nghe, và đó là tất cả những
    gì ta cần biết.
    """
    import socket
    import subprocess
    dich = "127.0.0.1" if host in ("0.0.0.0", "::", "") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.5)
        if s.connect_ex((dich, port)) != 0:
            return None
    try:
        r = subprocess.run(["netstat", "-ano", "-p", "TCP"],
                           capture_output=True, text=True, timeout=20)
        for d in r.stdout.splitlines():
            p = d.split()
            if len(p) >= 5 and p[3] == "LISTENING" and p[1].endswith(f":{port}"):
                return p[4]
    except (OSError, subprocess.SubprocessError):
        pass
    return "?"


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    log = logging.getLogger("llm_gateway")

    # Đọc tệp TRƯỚC `Config.from_env()` — xem `nap_env` để biết vì sao.
    n = nap_env()
    if n:
        log.info("nap %d bien tu %s", n, TEP_ENV)

    cfg = Config.from_env()

    if not cfg.models_mo:
        # Không phải lỗi — fail-closed của Q92 đang làm đúng việc. Nhưng phải nói
        # to, vì "GET /v1/models trả rỗng" rất dễ bị hiểu nhầm thành cổng hỏng.
        log.warning("LTT_LLM_MODELS rong -> KHONG mo model nao. "
                    "Dat vi du: LTT_LLM_MODELS=qwen38-api,qwen38-vision")
    if not cfg.token:
        log.warning("LTT_LLM_TOKEN rong -> KHONG kiem tra bearer. "
                    "Chi chap nhan duoc khi host van la 127.0.0.1")

    # 🔴 CỔNG ĐÃ CÓ NGƯỜI GIỮ = DỪNG NGAY, NÓI TO, ĐỪNG THỬ BIND.
    #
    #    Đo 01/09 trên máy B: dừng vỏ bọc `nssm.exe` thì tiến trình con **sống sót
    #    mồ côi** và vẫn giữ 8299. SCM dựng dịch vụ dậy, bản mới không bind được,
    #    dịch vụ đứng ở `Paused` — và trong suốt 99 giây đó `/health` vẫn trả
    #    **200**, vì chính con mồ côi phục vụ nó.
    #
    # ⛔ Đó là health XANH GIẢ, và nó giả **theo cấu trúc**: một endpoint sức khoẻ
    #    do chính thứ cần kiểm phục vụ thì không bao giờ nói được "tôi là tiến
    #    trình không nên tồn tại". Không sửa được bằng cách thêm trường vào
    #    `/health`.
    #
    # ⭐ Chỗ này không sửa được cái giả đó — `/health` vẫn sẽ xanh. Nó sửa thứ
    #    khác: biến một `Paused` câm thành một dòng log gọi đúng tên thủ phạm.
    #    Người trực đọc log biết phải làm gì; đọc `Paused` thì không.
    #    Việc phát hiện thuộc về chốt hai nguồn ở `tools/soi_cong_llm.py`.
    giu = _ai_dang_nghe(cfg.host, cfg.port)
    if giu is not None:
        log.error("CONG %s DA CO NGUOI GIU (pid %s) -- KHONG khoi dong.",
                  cfg.port, giu)
        log.error("Nhieu kha nang la mot tien trinh MO COI song sot sau khi vo "
                  "boc NSSM chet. `/health` cua no VAN XANH, dung tin.")
        log.error("Xu ly: Stop-Process -Id %s -Force  roi  "
                  "Start-Service LTTLlmGateway", giu)
        raise SystemExit(2)

    app = create_app(cfg, HttpxUpstream(cfg.upstream_url))

    import uvicorn
    log.info("cong VLM nghe %s:%s -> thuong nguon %s",
             cfg.host, cfg.port, cfg.upstream_url)
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
