"""
service.py — điểm DÙNG LẠI cho app khác (đặc biệt taovideo/seedance).

Yêu cầu người dùng: "upscale cho seedance lấy code từ app upscale". Thay vì nhân
đôi code Real-ESRGAN, taovideo gọi `submit_upscale_job()` để nộp một job
`upscalevideo.render` cho video đã có trong storage (vd video Seedance vừa tạo).
Nền tảng giữ chỗ credit + worker xử lý y hệt job upscale thường.
"""
from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy.orm import Session as DbSession


def build_params(*, video_key: str, owner_id: str, preset: str = "fast",
                 target_height: int = 1080, codec: str = "h264",
                 preview: bool = False, duration_s: float = 0.0,
                 preserve_fps: bool = True, preserve_audio: bool = True,
                 request_id: str = "", source_name: str = "") -> dict:
    """Chuẩn hoá params cho job upscalevideo.render (dùng chung route + seedance)."""
    if target_height not in (1080, 1440, 2160):
        target_height = 1080
    if preset not in ("fast", "quality"):
        preset = "fast"
    if codec not in ("h264", "hevc"):
        codec = "h264"
    return {"video_key": video_key, "owner_id": owner_id, "preset": preset,
            "target_height": int(target_height), "codec": codec,
            "preview": bool(preview), "duration_s": float(duration_s or 0),
            "preserve_fps": bool(preserve_fps),
            "preserve_audio": bool(preserve_audio),
            "request_id": str(request_id or "")[:96],
            "source_name": PurePosixPath(str(source_name or video_key)).name[:255]}


def submit_upscale_job(db: DbSession, *, user_id: str, video_key: str,
                       preset: str = "fast", target_height: int = 1080,
                       codec: str = "h264", preview: bool = False,
                       duration_s: float = 0.0, preserve_fps: bool = True,
                       preserve_audio: bool = True, request_id: str = "",
                       source_name: str = ""):
    """Nộp job nâng cấp cho một video ĐÃ có trong storage (giữ chỗ credit trong
    cùng transaction). Trả Job. Caller commit. Dùng bởi route /queue VÀ bởi
    taovideo (nút 'Nâng cấp 4K' video Seedance) — KHÔNG nhân đôi code engine."""
    from platform_core.job_submit import dedupe_key_for, submit_with_credit
    params = build_params(video_key=video_key, owner_id=user_id, preset=preset,
                          target_height=target_height, codec=codec,
                          preview=preview, duration_s=duration_s,
                          preserve_fps=preserve_fps, preserve_audio=preserve_audio,
                          request_id=request_id, source_name=source_name)
    dedupe_params = ({"owner_id": user_id, "request_id": request_id}
                     if request_id else params)
    return submit_with_credit(
        db, user_id=user_id, app_slug="upscalevideo",
        job_type="upscalevideo.render", params=params,
        dedupe_key=dedupe_key_for("upscalevideo.render", dedupe_params))


def submit_upscale_batch(db: DbSession, *, user_id: str, items: list[dict],
                         preset: str = "fast", target_height: int = 1080,
                         codec: str = "h264", preview: bool = False,
                         preserve_fps: bool = True,
                         preserve_audio: bool = True) -> list:
    """Nộp 1–3 job trong transaction do caller quản lý.

    Nếu bất kỳ item nào thiếu credit/không hợp lệ, exception làm caller rollback
    toàn bộ job và hold. ``request_id`` khóa double-submit cho từng item.
    """
    if not 1 <= len(items) <= 3:
        raise ValueError("Batch chỉ nhận từ 1 đến 3 video.")
    jobs = []
    seen = set()
    for index, item in enumerate(items):
        video_key = str(item.get("video_key") or "")
        request_id = str(item.get("request_id") or "")[:96]
        if not video_key or not request_id or request_id in seen:
            raise ValueError(f"Video {index + 1} thiếu định danh hợp lệ.")
        seen.add(request_id)
        jobs.append(submit_upscale_job(
            db, user_id=user_id, video_key=video_key, preset=preset,
            target_height=target_height, codec=codec, preview=preview,
            duration_s=float(item.get("duration_s") or 0),
            preserve_fps=preserve_fps, preserve_audio=preserve_audio,
            request_id=request_id, source_name=str(item.get("filename") or "")))
    return jobs
