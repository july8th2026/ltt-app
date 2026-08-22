"""
config.py — mọi tham số vận hành đọc từ biến môi trường, không hằng số nằm rải rác.

⛔ Không dùng `Path(__file__).parents[n]` để neo đường dẫn: đếm sai cấp thư mục
   ngay khi file đổi chỗ, và hỏng lặng lẽ (`AGENTS.md`).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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


@dataclass(frozen=True)
class Config:
    # ── ComfyUI ──────────────────────────────────────────────────────────────
    comfy_url: str
    #: Thư mục `input` của ComfyUI — ảnh tham chiếu tải về phải nằm ở đây thì node
    #: `LoadImage` mới thấy.
    comfy_input_dir: Path

    # ── Cổng render ──────────────────────────────────────────────────────────
    host: str
    port: int
    token: str

    # ── Hàng đợi và thời gian ────────────────────────────────────────────────
    #: Một GPU = một việc. Đổi số này là mời OOM (D-005).
    max_concurrent: int
    #: ⚠️ THANG PHÚT, không phải giây. Một ảnh ở cấu hình chất lượng mất 2,5–6 phút
    #: (D-010). Trần cũ theo giây của bản kế hoạch 1 là sai.
    job_timeout_s: float
    #: Ngưỡng RAM trống tối thiểu — LẤY TỪ SỰ CỐ THẬT của dự án video máy B:
    #: còn ~23 GB thì VRAM bị đẩy lên 98 %, còn ~4 GB thì Windows sập (19/08).
    #: Là LƯỢNG TUYỆT ĐỐI, không phải tỉ lệ — tỉ lệ đổi nghĩa mỗi lần nâng RAM.
    ram_trong_toi_thieu_gb: float

    # ── Thư mục làm việc ─────────────────────────────────────────────────────
    work_dir: Path

    @staticmethod
    def from_env() -> "Config":
        return Config(
            comfy_url=(os.environ.get("LTT_COMFY_URL") or "http://127.0.0.1:8188").rstrip("/"),
            comfy_input_dir=Path(os.environ.get("LTT_COMFY_INPUT_DIR") or r"E:\AI\ComfyUI\input"),
            host=os.environ.get("LTT_RENDER_HOST") or "127.0.0.1",
            port=_int("LTT_RENDER_PORT", 8199),
            token=(os.environ.get("LTT_RENDER_TOKEN") or "").strip(),
            max_concurrent=_int("LTT_RENDER_MAX_CONCURRENT", 1),
            job_timeout_s=_float("LTT_RENDER_JOB_TIMEOUT_S", 900.0),
            ram_trong_toi_thieu_gb=_float("LTT_RENDER_RAM_TRONG_GB", 48.0),
            work_dir=Path(os.environ.get("LTT_RENDER_WORK_DIR") or r"E:\AI\ltt_render\work"),
        )
