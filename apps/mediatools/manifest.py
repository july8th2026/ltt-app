from __future__ import annotations

from platform_core.registry import AppManifest, ToolSpec


def _cost(params: dict) -> int:
    if "url" in params:
        return 1
    if "text" in params:
        return max(1, (len(str(params.get("text") or "")) + 999) // 1000 * 2)
    if "interval_sec" in params:
        return 1
    if "images" in params or "videos" in params:
        return 1
    return 0


MANIFEST = AppManifest(
    slug="mediatools", display_name="Media Tools", route_prefix="/mediatools",
    summary="Các primitive asset, tách frame và ghép media cho Agent Canvas.",
    job_types=("mediatools.process",), requires=("ffmpeg",), credit_cost=_cost,
    tools=(
        ToolSpec(name="asset.image", job_type="mediatools.process",
                 description="Đưa một ảnh đã tải lên vào workflow với provenance thuộc tài khoản.",
                 params_schema={"image_key": {"type": "image", "required": True}},
                 returns={"image_key": "image"}),
        ToolSpec(name="asset.video", job_type="mediatools.process",
                 description="Đưa một video đã tải lên vào workflow với provenance thuộc tài khoản.",
                 params_schema={"video_key": {"type": "video", "required": True}},
                 returns={"video_key": "video"}),
        ToolSpec(name="asset.audio", job_type="mediatools.process",
                 description="Đưa một audio đã tải lên vào workflow với provenance thuộc tài khoản.",
                 params_schema={"audio_key": {"type": "audio", "required": True}},
                 returns={"audio_key": "audio"}),
        ToolSpec(name="audio.generate", job_type="mediatools.process",
                 description="Sinh giọng đọc có điều khiển phong cách bằng Gemini TTS.",
                 params_schema={
                     "text": {"type": "string", "required": True, "max_length": 12000},
                     "model": {"type": "model_ref", "category": "audio", "providers": ["gemini"]},
                     "voice": {"type": "enum", "values": ["Kore", "Puck", "Charon", "Zephyr", "Fenrir", "Leda", "Orus", "Aoede"], "default": "Kore"},
                     "style": {"type": "string", "max_length": 500, "default": "Natural, clear studio narration"},
                 }, returns={"audio_key": "audio"}, verifiable=("technical",)),
        ToolSpec(name="video.extract_frames", job_type="mediatools.process",
                 description="Tách frame đều theo thời gian từ video bằng FFmpeg.",
                 params_schema={
                     "video_key": {"type": "video", "required": True},
                     "interval_sec": {"type": "number", "min": 0.25, "max": 60, "default": 2},
                     "max_frames": {"type": "int", "min": 1, "max": 60, "default": 12},
                 }, returns={"image_keys": "image[]"}, verifiable=("technical",)),
        ToolSpec(name="media.merge_image", job_type="mediatools.process",
                 description="Ghép 2–12 ảnh thành một contact sheet ngang, dọc hoặc dạng lưới.",
                 params_schema={
                     "images": {"type": "image[]", "required": True},
                     "layout": {"type": "enum", "values": ["grid", "horizontal", "vertical"], "default": "grid"},
                 }, returns={"image_key": "image"}, verifiable=("technical",)),
        ToolSpec(name="media.merge_video", job_type="mediatools.process",
                 description="Nối 2–12 video theo thứ tự thành một MP4 chuẩn H.264.",
                 params_schema={
                     "videos": {"type": "video[]", "required": True},
                     "transition": {"type": "enum", "values": ["cut"], "default": "cut"},
                 }, returns={"video_key": "video"}, verifiable=("technical",)),
        ToolSpec(name="video.social_import", job_type="mediatools.process",
                 description="Nhập URL HTTPS trực tiếp tới video mà bạn sở hữu; chặn trang nền tảng và mạng nội bộ.",
                 params_schema={
                     "url": {"type": "string", "required": True, "max_length": 2048},
                     "confirm_rights": {"type": "bool", "required": True},
                 }, returns={"video_key": "video"}, verifiable=("technical",)),
    ), enabled=True, public=False, group="Hạ tầng",
    notes="Không có UI độc lập; dùng qua /agent/canvas. Xử lý cục bộ bằng Pillow/FFmpeg.",
)
