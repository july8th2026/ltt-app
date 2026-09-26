"""Kiểu dữ liệu upscalevideo (di trú trung thành từ BOT GEMINI video_upscale)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Preset(str, Enum):
    fast = "fast"        # realesr-general-x4v3 — nhanh, ~1GB VRAM, mặc định
    quality = "quality"  # realesrgan-x4plus   — nét hơn, cần ~10-15GB VRAM


PRESET_MODEL = {
    Preset.fast:    "realesr-general-x4v3",
    Preset.quality: "realesrgan-x4plus",
}
ENGINE_SCALE = 4  # cả 2 model đều x4; hạ về target_height ở khâu encode


class Codec(str, Enum):
    h264 = "h264"
    hevc = "hevc"       # H.265 — file nhỏ hơn ở cùng chất lượng (CHƯA ĐO ở đây)


# Encoder phần cứng app này biết dựng tham số cho: **NVENC, và chỉ NVENC.**
#
# ⛔ `ENCODER_QSV` / `ENCODER_AMD` đã bị XOÁ (2026-09-26). Lý do là một phép đo,
#    không phải một sở thích: trên máy production này `ffmpeg -encoders` LIỆT KÊ
#    `h264_qsv`/`hevc_qsv`/`h264_amf`/`hevc_amf`, nhưng cả bốn đều **CHẾT lúc
#    chạy** ("Nothing was written into output file") trên một encode thử
#    256x256. Hai dict đó không có caller nào trong kho (chỉ `docs/UPSCALE_V2/`
#    nhắc tên) ⇒ giữ lại chỉ là mời người sau tin vào một đường không chạy.
#    ⚠️ Bài học chung: một bản LIỆT KÊ năng lực (`-encoders`) ⛔ KHÔNG BAO GIỜ
#    được coi là một phép DÒ năng lực (`platform_core.media._test_encoder`).
ENCODER = {Codec.h264: "h264_nvenc", Codec.hevc: "hevc_nvenc"}
# ⭐ Đường CPU phải TÔN TRỌNG codec khách xin. Bản cũ trả thẳng chuỗi
#    `"libx264"` cho MỌI codec, nên một yêu cầu HEVC rơi về CPU thành H.264 —
#    mà kết quả vẫn khai `codec: "hevc"` (ISSUE J).
# ⚠️ Nhưng `ENCODER_CPU[Codec.hevc]` (libx265) ⛔ KHÔNG nằm trên đường job
#    KHÁCH: `jobs._resolve_encoder` NÉM khi khách xin HEVC mà máy không có
#    NVENC-HEVC, vì libx265 `-preset medium` ở 2160p là hàng GIỜ CPU và worker
#    bị `os._exit()` ở `job_runner.RUNTIME_LIMIT_S`. Ô này còn ở đây cho đường
#    ngoại tuyến/benchmark (`ff._venc_args` vẫn hiểu `libx265`).
ENCODER_CPU = {Codec.h264: "libx264", Codec.hevc: "libx265"}
ALLOWED_HEIGHTS = (1080, 1440, 2160)


class TuneResult(BaseModel):
    """Kết quả autotune cho 1 lần chạy."""
    model: str
    tile: int
    threads: str                        # "load:proc:save"
    est_alloc_mb: int
    free_mb: int
    budget_mb: int
    fast_path: bool
    warning: str = ""
    # ⭐ `est_alloc_mb` là LƯỢNG VRAM cấu hình này CẦN (đo được), ⛔ không phải
    #    lượng nó ĐƯỢC PHÉP dùng. Khi budget tụt xuống dưới sàn của dải nhỏ nhất
    #    ta đo được thì hai con số đó KHÁC NHAU, và cờ này nói ra điều đó thay vì
    #    để `est_alloc_mb` im lặng khai một khoản budget không đài thọ nổi.
    #    `False` ⇒ `est_alloc_mb > budget_mb`: chạy được nhưng có thể OOM/rất chậm.
    budget_du_cho_est: bool = True
