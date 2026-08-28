"""
config.py — mọi tham số vận hành đọc từ biến môi trường, không hằng số nằm rải rác.

⛔ Không dùng `Path(__file__).parents[n]` để neo đường dẫn: đếm sai cấp thư mục
   ngay khi file đổi chỗ, và hỏng lặng lẽ (`AGENTS.md`).

⛔ FAIL-CLOSED như Q92: `LTT_LLM_MODELS` mặc định **rỗng**. Bật cờ một mình
   **không** mở model nào. Đây không phải sự cẩn thận thừa — Public API đã chốt
   nguyên tắc này và nó đã cứu một lần deploy.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(ten: str, mac_dinh: int) -> int:
    try:
        return int((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return mac_dinh


def _float(ten: str, mac_dinh: float) -> float:
    try:
        return float((os.environ.get(ten) or "").strip() or mac_dinh)
    except ValueError:
        return mac_dinh


def _danh_sach(ten: str) -> tuple[str, ...]:
    """Đọc danh sách phân tách bằng dấu phẩy. Rỗng → tuple rỗng (fail-closed)."""
    tho = (os.environ.get(ten) or "").strip()
    if not tho:
        return ()
    return tuple(x.strip() for x in tho.split(",") if x.strip())


@dataclass(frozen=True)
class Config:
    # ── Thượng nguồn: llama-swap ─────────────────────────────────────────────
    #: llama-swap nghe loopback. KHÔNG bao giờ trỏ ra LAN.
    upstream_url: str

    # ── Cổng VLM ─────────────────────────────────────────────────────────────
    host: str
    port: int
    token: str

    # ── Danh mục ─────────────────────────────────────────────────────────────
    #: Tên model được phép phục vụ. **Rỗng = không mở gì cả** (Q92 fail-closed).
    models_mo: tuple[str, ...]

    # ── Ngân sách — số CHÍNH THỨC điền sau khi P5 đo xong ─────────────────────
    #: Trần token đầu vào public API. Engine có cửa sổ 131.072; public giữ 65.000
    #: theo Q116 để còn biên prefill/Cloudflare sau biến thiên cold-load.
    max_input_tokens: int
    #: Trần token sinh ra mỗi yêu cầu.
    max_output_tokens: int
    #: Trần số ảnh mỗi yêu cầu. Mỗi ảnh nuốt hàng nghìn token ngữ cảnh.
    max_images: int
    #: Trần byte của một ảnh gửi kèm (base64 đã giải mã).
    max_image_bytes: int

    # ── Thời gian ────────────────────────────────────────────────────────────
    #: Chờ llama-swap nạp model. Nạp một GGUF 15 GiB từ page cache mất vài giây,
    #: từ đĩa lạnh lâu hơn. llama-swap có `healthCheckTimeout` riêng của nó.
    upstream_timeout_s: float
    #: Chờ token đầu tiên khi ngữ cảnh dài. Ở 200K, prefill có thể mất VÀI PHÚT
    #: (cộng đồng đo prefill ~1.000 tok/s ở đầu vào 100k). Đừng đặt thấp.
    stream_timeout_s: float

    # ── Trọng tài GPU ────────────────────────────────────────────────────────
    #: Ngưỡng RAM trống tối thiểu. LẤY TỪ SỰ CỐ THẬT của dự án video máy B:
    #: còn ~23 GB thì VRAM bị đẩy lên 98 %, còn ~4 GB thì Windows sập (19/08).
    #: Là LƯỢNG TUYỆT ĐỐI, không phải tỉ lệ — tỉ lệ đổi nghĩa mỗi lần nâng RAM.
    ram_trong_toi_thieu_gb: float
    #: Bật trọng tài. Tắt (0) chỉ dùng khi test trên máy không có GPU.
    trong_tai_bat: bool

    # ── Dọn card trước khi nạp (P6 — đo thật 22/08) ──────────────────────────
    #: ComfyUI giữ model thường trú **kể cả sau khi render xong**. Nạp model lên
    #: một card còn 6,2 GB bị chiếm ⇒ trọng số tràn sang RAM chủ qua PCIe ⇒
    #: **18,2 tok/s thay vì 63,3**, và KHÔNG có lỗi nào được báo.
    comfy_url: str
    #: Nền đo được: desktop 1.515–1.612 MiB · ComfyUI thường trú 6.211–16.620 MiB.
    #: 2.500 nằm gọn giữa hai vùng.
    vram_sach_mb: int
    #: Bật việc dọn. Tắt (0) khi test hoặc khi máy không chạy ComfyUI.
    don_dep_bat: bool

    # ── Hàng rào của riêng cổng (V9) ─────────────────────────────────────────
    #: Số lượt được chạy CÙNG LÚC. `llama-server` chạy `--parallel 1`, nên nhiều
    #: hơn 1 chỉ thành kết nối treo và một hàng đợi vô hình trong llama.cpp.
    #: Hàng đợi thật phải sống ở admission plane, có trạng thái/fairness/hủy;
    #: gateway này chỉ cho đúng một lượt chạm vào engine.
    max_dong_thoi: int
    #: Trần lượt mỗi phút. 0 = tắt. Chốt phụ — đồng thời mới là chốt chính.
    rpm: int

    # ── Nhịp tim SSE ─────────────────────────────────────────────────────────
    #: Chèn một dòng chú thích SSE mỗi khi luồng lặng quá số giây này. 0 = tắt.
    #:
    #: 🔴 KHÔNG TẮT KHI CÓ CODEX HAY CLAUDE CODE CẮM VÀO. Cả hai bỏ luồng sau
    #:    **300 giây im lặng**, mà `llama-server` không phát gì trong lúc prefill
    #:    — và prompt hệ thống của một CLI agent là ~22.000 token. Xem `nhip_tim`.
    nhip_tim_giay: float

    @staticmethod
    def from_env() -> "Config":
        return Config(
            upstream_url=(os.environ.get("LTT_LLM_UPSTREAM_URL")
                          or "http://127.0.0.1:8280").rstrip("/"),
            host=os.environ.get("LTT_LLM_HOST") or "127.0.0.1",
            port=_int("LTT_LLM_PORT", 8299),
            token=(os.environ.get("LTT_LLM_TOKEN") or "").strip(),
            models_mo=_danh_sach("LTT_LLM_MODELS"),
            max_input_tokens=_int("LTT_LLM_MAX_INPUT_TOKENS", 65_000),
            max_output_tokens=_int("LTT_LLM_MAX_OUTPUT_TOKENS", 32_768),
            max_images=_int("LTT_LLM_MAX_IMAGES", 4),
            max_image_bytes=_int("LTT_LLM_MAX_IMAGE_BYTES", 12 * 1024 * 1024),
            upstream_timeout_s=_float("LTT_LLM_UPSTREAM_TIMEOUT_S", 600.0),
            stream_timeout_s=_float("LTT_LLM_STREAM_TIMEOUT_S", 900.0),
            ram_trong_toi_thieu_gb=_float("LTT_LLM_RAM_TRONG_GB", 48.0),
            trong_tai_bat=(os.environ.get("LTT_LLM_TRONG_TAI") or "1").strip() != "0",
            comfy_url=(os.environ.get("LTT_LLM_COMFY_URL")
                       or "http://127.0.0.1:8188").rstrip("/"),
            vram_sach_mb=_int("LTT_LLM_VRAM_SACH_MB", 2500),
            don_dep_bat=(os.environ.get("LTT_LLM_DON_DEP") or "1").strip() != "0",
            max_dong_thoi=_int("LTT_LLM_MAX_DONG_THOI", 1),
            rpm=_int("LTT_LLM_RPM", 120),
            nhip_tim_giay=_float("LTT_LLM_NHIP_TIM_S", 15.0),
        )
