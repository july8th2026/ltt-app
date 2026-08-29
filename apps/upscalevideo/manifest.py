"""
App `upscalevideo` — Nâng cấp video (Real-ESRGAN NCNN ×4), di trú từ BOT GEMINI
`video_upscale` (Đợt C, nhóm GPU). Vendor engine (exe+model ~49MB) copy trong
`apps/upscalevideo/vendor/engine/` (gitignored) — nền tảng cũng chạy Windows nên
dùng thẳng binary Windows.

Bản chất: tách frame → Real-ESRGAN ×4 → encode lại (NVENC, fallback CPU) → giữ
tỉ lệ/FPS/audio. Giá theo phút × độ phân giải × preset (người dùng chốt 2026-08-01).

Slug `upscalevideo` (chuỗi riêng). Upload video lớn đi thẳng browser→R2 (P1).
Dùng chung `platform_core.media` + hạ tầng video của autosubvideo.

**Điểm dùng lại cho seedance**: `apps.upscalevideo.service.submit_upscale_job()` —
taovideo sẽ gọi để "Nâng cấp 4K" video Seedance mà KHÔNG nhân đôi code (theo yêu
cầu người dùng: "upscale cho seedance lấy code từ app upscale").
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ theo thời lượng client khai; worker đo lại thật + nâng giữ chỗ."""
    if params.get("image_key"):
        return 4 if str(params.get("preset", "fast")) == "quality" else 2
    from apps.upscalevideo.cost import uoc_luong_credit
    try:
        dur = float(params.get("duration_s", 0) or 0)
    except (TypeError, ValueError):
        dur = 0.0
    return uoc_luong_credit(dur, int(params.get("target_height", 1080) or 1080),
                            str(params.get("preset", "fast")),
                            bool(params.get("preview")),
                            bool(params.get("stabilize")),
                            bool(params.get("smooth_motion")))


MANIFEST = AppManifest(
    slug="upscalevideo",
    display_name=N_('Upscale Video'),
    route_prefix="/upscalevideo",
    summary=N_('Nâng nét 1080p/2K/4K, chống rung và nội suy FPS. Giữ tỉ lệ, FPS, âm thanh.'),
    icon="🔍",
    accent="#B4530A",

    nav=(NavEntry("Upscale Video", "/upscalevideo", "🔍", "upscalevideo"),),

    # ``render`` is the compatibility lane for already-queued jobs and the
    # static Agent ToolSpec contract. Customer submissions use the preset-
    # specific lanes below so Fast no longer reserves Quality's measured peak.
    job_types=("upscalevideo.render", "upscalevideo.render.fast",
               "upscalevideo.render.quality"),
    requires=("gpu", "ffmpeg"),
    # H32.6 runtime evidence on RTX 5060 Ti: Fast peak delta 848 MB, Quality
    # x4plus 11,176 MB. Fast receives >2x headroom; Quality and the legacy lane
    # remain at the measured worst-case ceiling rounded up to 12 GB.
    gpu_vram_mb={
        "upscalevideo.render": 12000,
        "upscalevideo.render.fast": 2000,
        "upscalevideo.render.quality": 12000,
    },
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.upscale", job_type="upscalevideo.render",
        description=N_('Nâng độ nét video lên 1080p, 2K hoặc 4K bằng Real-ESRGAN.'),
        params_schema={
            "video_key": {"type": "video", "required": True},
            "preset": {"type": "enum", "values": ["fast", "quality"], "default": "fast"},
            "target_height": {"type": "enum", "values": [1080, 1440, 2160], "default": 1080},
            "codec": {"type": "enum", "values": ["h264", "hevc"], "default": "h264"},
            "preview": {"type": "bool", "default": False},
            "preserve_fps": {"type": "bool", "default": True},
            "preserve_audio": {"type": "bool", "default": True},
            "stabilize": {"type": "bool", "default": False},
            "smooth_motion": {"type": "bool", "default": False},
            # Máy chủ đo từ chính tệp đã tải lên; số người gọi khai không chạm
            # vào giá (Q84, H35.10a).
            "duration_s": {"type": "number", "min": 0,
                           "measured_from": "video_key"},
        },
        returns={"video_key": "video"},
        verifiable=("technical",),

        # ── Public API (H35.10, mở 2026-08-29) ───────────────────────────────
        # Trước 2026-08-29 tool này CỐ Ý đóng, và lý do vẫn đáng đọc: giá phụ
        # thuộc `duration_s` do người gọi khai, còn worker nâng giữ chỗ khi đo
        # được số thật — với máy gọi máy thì đó là phá lời hứa của một báo giá
        # đã ký (Q84, sự cố Seedance giữ 29 thu 78).
        #
        # H35.10a đóng đúng lỗ đó: `duration_s` khai `measured_from` ở trên, nên
        # máy chủ đo từ chính tệp đã tải lên TRƯỚC khi tính giá, và tham số này
        # nằm trong `hidden` — khách không gửi nó được nữa.
        #
        # ⚠️ Còn nợ H35.10b: `_dam_bao_giu_cho` vẫn nâng giữ chỗ nếu worker tính
        #    ra số khác. Quote nay ĐÚNG, chưa phải KHÔNG THỂ SAI.
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Upscale a video to 1080p, 1440p or 4K. Costs 30 "
                            "credits per minute at 1080p on the fast preset; "
                            "1440p costs 1.8x, 4K costs 4x, and the quality "
                            "preset costs 2.5x. The duration is measured from "
                            "the file you upload, not from anything you send."),
            # Khách không khai thời lượng: máy chủ đo. Ẩn nó đi là phần thi hành
            # của lời hứa đó — một tham số vẫn gửi được là một tham số vẫn cãi
            # được với con số thật.
            "hidden": ("duration_s",),
            "params": {
                "video_key": {
                    "description": ("The video to enlarge, given as the id of "
                                    "an upload you confirmed or of an artifact "
                                    "from an earlier job."),
                    "example": "upl_from_POST_/api/v1/uploads",
                },
                "preset": {
                    "description": ("How hard to work on the result. `quality` "
                                    "costs 2.5 times as much as `fast` and "
                                    "takes longer."),
                    "example": "fast",
                },
                "target_height": {
                    "description": ("Height of the finished video in pixels. "
                                    "1440 costs 1.8 times the 1080 price and "
                                    "2160 costs 4 times."),
                    "example": 1080,
                },
                "codec": {
                    "description": ("Video codec of the finished file. `hevc` "
                                    "makes a smaller file that fewer players "
                                    "open."),
                    "example": "h264",
                },
                "preview": {
                    "description": ("Render only the first 8 seconds, and "
                                    "charge only for them. Use it to check the "
                                    "settings before paying for the whole "
                                    "video."),
                    "example": False,
                },
                "preserve_fps": {
                    "description": ("Keep the original frame rate instead of "
                                    "letting the encoder choose one."),
                    "example": True,
                },
                "preserve_audio": {
                    "description": "Copy the original audio track across.",
                    "example": True,
                },
                "stabilize": {
                    "description": ("Reduce camera shake. Costs 1.2 times the "
                                    "price without it."),
                    "example": False,
                },
                "smooth_motion": {
                    "description": ("Interpolate frames for smoother motion. "
                                    "Costs 2.2 times the price without it, and "
                                    "combines with `stabilize`."),
                    "example": False,
                },
            },
        },
    ), ToolSpec(
        name="image.upscale", job_type="upscalevideo.render",
        description=N_('Nâng chi tiết ảnh ×4 bằng Real-ESRGAN trên GPU cục bộ.'),
        params_schema={
            "image_key": {"type": "image", "required": True},
            "preset": {"type": "enum", "values": ["fast", "quality"], "default": "fast"},
        }, returns={"image_key": "image"}, verifiable=("technical", "vlm_judge"),

        # ── Public API (Q92, wave 2) ─────────────────────────────────────────
        # This is the GPU workload wave 2 opens. Its price is a flat 2/4 credits
        # by preset, decided before the job starts, so a signed quote stays true
        # from quote to settlement.
        #
        # Its sibling `video.upscale` is deliberately NOT exposed: its price
        # depends on `duration_s` declared by the caller, and the worker tops the
        # hold up when it measures the real duration (`_dam_bao_giu_cho` in
        # jobs.py). That is fine for the UI, where a person picked a file they
        # can see — but for a machine caller it breaks the promise a signed quote
        # makes (Q84: never charge past the confirmed hold). Exposing it needs
        # the duration measured server-side from the uploaded asset at quote
        # time, or the top-up capped for API jobs. Tracked in PROGRESS as R25.
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            # No infrastructure in the description: a customer buys a
            # larger image, not a sentence about our hardware.
            "description": ("Upscale an image to four times its original size. "
                            "Costs 2 credits at the fast preset and 4 at the "
                            "quality preset."),
            "params": {
                "image_key": {
                    "description": ("The image to enlarge, given as the id of "
                                    "an upload you confirmed or of an artifact "
                                    "from an earlier job."),
                    "example": "upl_from_POST_/api/v1/uploads",
                },
                "preset": {
                    "description": ("How hard to work on the result. `fast` "
                                    "costs 2 credits, `quality` costs 4 and "
                                    "takes longer."),
                    "example": "fast",
                },
            },
        },
    )),

    enabled=True,
    lifecycle="released",
    capabilities=("AI Video",),
    group="Video",
    badge="MỚI",
    notes="Di trú Đợt C từ video_upscale. Cần GPU NVIDIA + vendor engine. Job GPU dài.",
)
