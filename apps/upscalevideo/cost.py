"""
cost.py — giá credit cho UPSCALE VIDEO.

Module gốc BOT GEMINI không tính tiền. Mô hình MỚI: theo **phút video × độ phân
giải đích × preset** (chi phí ~ thời gian GPU ~ số frame × diện tích × độ nặng model).

Đơn giá người dùng chốt 2026-08-01: ~30 credit/phút @1080p Fast.
  hệ_số_res: 1080=1.0 · 1440=1.8 · 2160(4K)=4.0
  hệ_số_preset: fast=1.0 · quality=2.5
  motion: stabilize=1.2 · smooth_motion_2x=2.2 (benchmark 2026-08-03)
Tỉ giá Q31: 1 credit = 100đ. Preview (~8s đầu) tính theo thời lượng thực (nhỏ).

⚠️ SỐ ĐO 2026-09-27 — đọc trước khi chỉnh hệ số. ⛔ KHÔNG đổi giá ở lượt này;
chủ dự án chốt giữ nguyên và sẽ điều chỉnh theo thực tế sau.

Câu "chi phí ~ thời gian GPU" ở trên **bị số đo bác**. Đo trên v3 (836×576,
3205 khung, preset fast, 3 lượt/đích, trung vị):

    đích    thời gian GPU   kích thước ra        hệ số giá
    1080      321,4 s  1,00x   164,8 MB  1,00x       1,0
    1440      345,4 s  1,07x   264,9 MB  1,61x       1,8
    2160      330,7 s  1,03x   518,9 MB  3,15x       4,0

⭐ Thời gian GPU gần như PHẲNG (±4 %, và 1440 còn *chậm hơn* 2160) vì
`ENGINE_SCALE = 4`: engine LUÔN upscale ×4 từ **nguồn** bất kể đích, đích chỉ đổi
khâu co lại + encode. ⇒ chi phí GPU tỉ lệ với **NGUỒN**, ⛔ không phải **ĐÍCH**.

Hệ số giá bám sát **kích thước đầu ra** hơn nhiều — tức lưu trữ + băng thông, một
chi phí có thật và CÓ tỉ lệ với đích. ⚠️ Nhưng tương quan ⛔ không chứng minh ý
định: chỉ chủ dự án mới chốt được cơ sở thật.

Toàn văn + xuất xứ: `docs/UPSCALE_V2_CORRECTION/08_BENCHMARK_RESULTS.md` §G.
"""
from __future__ import annotations

import math

CREDIT_PER_MINUTE = 30         # @1080p Fast, chốt 2026-08-01
MIN_CREDIT = 1

_RES_MULT = {1080: 1.0, 1440: 1.8, 2160: 4.0}
_PRESET_MULT = {"fast": 1.0, "quality": 2.5}
_ENHANCEMENT_MULT = {"stabilize": 1.2, "smooth_motion": 2.2}
_PREVIEW_SECONDS = 8.0


def he_so_res(target_height: int) -> float:
    return _RES_MULT.get(int(target_height), 1.0)


def he_so_preset(preset: str) -> float:
    return _PRESET_MULT.get(preset, 1.0)


def uoc_luong_credit(duration_s: float, target_height: int = 1080,
                     preset: str = "fast", preview: bool = False,
                     stabilize: bool = False, smooth_motion: bool = False) -> int:
    dur = min(float(duration_s or 0), _PREVIEW_SECONDS) if preview else float(duration_s or 0)
    minutes = max(0.0, dur) / 60.0
    enhancement = ((_ENHANCEMENT_MULT["stabilize"] if stabilize else 1.0) *
                   (_ENHANCEMENT_MULT["smooth_motion"] if smooth_motion else 1.0))
    raw = (minutes * he_so_res(target_height) * he_so_preset(preset) *
           CREDIT_PER_MINUTE * enhancement)
    return max(MIN_CREDIT, math.ceil(raw))


def uoc_luong(duration_s: float, target_height: int = 1080, preset: str = "fast",
              preview: bool = False, stabilize: bool = False,
              smooth_motion: bool = False) -> dict:
    credit = uoc_luong_credit(duration_s, target_height, preset, preview,
                              stabilize, smooth_motion)
    dur = min(float(duration_s or 0), _PREVIEW_SECONDS) if preview else float(duration_s or 0)
    return {"credit": credit, "vnd": credit * 100,
            "minutes": round(max(0.0, dur) / 60.0, 2),
            "target_height": target_height, "preset": preset, "preview": preview,
            "stabilize": bool(stabilize), "smooth_motion": bool(smooth_motion)}
