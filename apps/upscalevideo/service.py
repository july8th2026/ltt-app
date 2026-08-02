"""
service.py — điểm DÙNG LẠI cho app khác (đặc biệt taovideo/seedance).

Yêu cầu người dùng: "upscale cho seedance lấy code từ app upscale". Thay vì nhân
đôi code Real-ESRGAN, taovideo gọi `submit_upscale_job()` để nộp một job
`upscalevideo.render` cho video đã có trong storage (vd video Seedance vừa tạo).
Nền tảng giữ chỗ credit + worker xử lý y hệt job upscale thường.
"""
from __future__ import annotations

from sqlalchemy.orm import Session as DbSession


def build_params(*, video_key: str, owner_id: str, preset: str = "fast",
                 target_height: int = 1080, codec: str = "h264",
                 preview: bool = False, duration_s: float = 0.0) -> dict:
    """Chuẩn hoá params cho job upscalevideo.render (dùng chung route + seedance)."""
    if target_height not in (1080, 1440, 2160):
        target_height = 1080
    if preset not in ("fast", "quality"):
        preset = "fast"
    if codec not in ("h264", "hevc"):
        codec = "h264"
    return {"video_key": video_key, "owner_id": owner_id, "preset": preset,
            "target_height": int(target_height), "codec": codec,
            "preview": bool(preview), "duration_s": float(duration_s or 0)}


def submit_upscale_job(db: DbSession, *, user_id: str, video_key: str,
                       preset: str = "fast", target_height: int = 1080,
                       codec: str = "h264", preview: bool = False,
                       duration_s: float = 0.0):
    """Nộp job nâng cấp cho một video ĐÃ có trong storage (giữ chỗ credit trong
    cùng transaction). Trả Job. Caller commit. Dùng bởi route /queue VÀ bởi
    taovideo (nút 'Nâng cấp 4K' video Seedance) — KHÔNG nhân đôi code engine."""
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    params = build_params(video_key=video_key, owner_id=user_id, preset=preset,
                          target_height=target_height, codec=codec,
                          preview=preview, duration_s=duration_s)
    return submit_with_credit(
        db, user_id=user_id, app_slug="upscalevideo",
        job_type="upscalevideo.render", params=params,
        dedupe_key=dedupe_key_for("upscalevideo.render", params))
