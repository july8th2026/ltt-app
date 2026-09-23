"""
App `autosubvideo` — Khắc phụ đề vào video (di trú từ BOT GEMINI `auto_sub_video`,
Đợt B). Nhóm `ffmpeg`: burn ASS bằng ffmpeg + libass, có fallback CPU libx264.

Bản chất theo Q50: hỗ trợ cả Quick import và Full Editor; WhisperX là đường ASR
mặc định, import transcript vẫn là fallback không phụ thuộc model.

Slug đặt `autosubvideo` (chuỗi riêng, không trùng brand/model) theo bài học slug.
Upload video lớn đi thẳng browser→R2 (presigned PUT, P1) — né trần 100MB Cloudflare.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ = ước tính theo thời lượng client khai + mức chất lượng.
    Worker đo lại thời lượng THẬT, nâng giữ chỗ nếu thiếu rồi quyết toán đúng giá
    thật (chống khai gian thời lượng để trả rẻ)."""
    # Chỉ các operation server tự đặt dưới đây được miễn phí theo Q50. Render
    # thiếu/giả operation vẫn đi qua giá bình thường, không có default-free.
    if str(params.get("operation", "")) in {
            "transcribe", "diarize", "translate", "preview"}:
        return 0
    from apps.autosubvideo.cost import uoc_luong_credit
    try:
        dur = float(params.get("duration_s", 0) or 0)
    except (TypeError, ValueError):
        dur = 0.0
    quality = str(params.get("quality", "standard"))
    return uoc_luong_credit(dur, quality)


MANIFEST = AppManifest(
    slug="autosubvideo",
    display_name=N_('AutoSub Video'),
    route_prefix="/autosubvideo",
    summary=N_('Nạp video + transcript (.srt/.json), chọn kiểu chữ, khắc phụ đề đẹp vào video.'),
    icon="💬",
    accent="#0E7C86",

    nav=(NavEntry("AutoSub Video", "/autosubvideo", "💬", "autosubvideo"),),

    job_types=("autosubvideo.render", "autosubvideo.transcribe",
               "autosubvideo.diarize", "autosubvideo.translate"),
    requires=("ffmpeg",),
    # Chỉ hai loại job này chạm GPU. `render` là FFmpeg thuần nên để 0 —
    # khai thừa sẽ bắt job khắc phụ đề chờ một card trống mà nó không cần.
    # whisperx large-v3 float16 + model align ~6 GB; pyannote nhẹ hơn nhiều.
    gpu_vram_mb={"autosubvideo.transcribe": 6000, "autosubvideo.diarize": 2000},
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.subtitle", job_type="autosubvideo.render",
        description=N_('Khắc transcript có sẵn vào video bằng preset phụ đề và FFmpeg.'),
        params_schema={
            "video_key": {"type": "video", "required": True},
            # `json[]` chu khong phai `json`: handler doc `params["transcript"]`
            # nhu MOT DANH SACH doan (`jobs.py`). Ban khai cu ghi `json`, va tang
            # public chieu no thanh `object` — nen mot khach gui dung hinh dang
            # ma worker can se an 400. Khong ai thay vi tool nay chua tung mo.
            "transcript": {"type": "json[]", "required": True},
            "style_id": {"type": "enum", "values": ["default", "tiktok_bold", "reels_clean", "cinematic", "meme_punch", "kids_color", "punchline", "word_emphasis"], "default": "default"},
            "segment_mode": {"type": "enum", "values": ["sentence", "phrase", "short_form", "punchline", "word_emphasis"], "default": "sentence"},
            "quality": {"type": "enum", "values": ["draft", "standard", "high"], "default": "standard"},
            "output_format": {"type": "enum", "values": ["mp4", "mkv", "webm"], "default": "mp4"},
            "export_srt": {"type": "bool", "default": True},
            # Máy chủ đo từ chính tệp đã tải lên; số người gọi khai không chạm
            # vào giá (Q84, H35.10a).
            "duration_s": {"type": "number", "min": 0,
                           "measured_from": "video_key"},
        },
        returns={"video_key": "video", "srt_key": "text", "ass_key": "text"},
        verifiable=("technical",),

        side_effect="external",
        # 🔴 `class="cpu"` DÙ `burn.py` CÓ DÙNG NVENC. Bản đầu của plan 02 khai
        #    `"gpu"` với lập luận *"class = node có chạm card hay không"* —
        #    `burn.py` dòng 135-149 gọi `media.detect_gpu_encoder()` rồi lấy
        #    `h264_nvenc`/`h264_qsv` khi có, nên "có chạm". Lập luận ấy đọc
        #    trường này theo NGHĨA TỰ SUY, và mã thật nói nghĩa khác:
        #
        #      `AppManifest.vram_for()` (`registry.py:881`) HỢP NHẤT
        #      `gpu_vram_mb[job_type]` với `resource["vram_min_mb"]`, và
        #      `test_1112` chốt bất biến `class="gpu"` ⇒ `vram_for() != 0`.
        #      Nghĩa là trong kho này `class="gpu"` = **GIỮ MỘT LEASE CARD**,
        #      không phải "có chạm card". Bất biến ấy ra đời từ một sự cố thật
        #      (`8fbf7aed`, Phase 13): ba App GPU chạy KHÔNG lease và đè lên
        #      `taoclipngan`/`upscalevideo` trên cùng một card.
        #
        #    `autosubvideo.render` cố ý KHÔNG giữ lease (dòng 47-51: khai thừa
        #    sẽ bắt job khắc phụ đề chờ một card trống nó không cần). Vậy theo
        #    từ vựng của kho, nó là `cpu`. Khai `"gpu"` mà không có VRAM là
        #    dựng lại đúng hình dạng sự cố Phase 13 trong một bản khai.
        # ⚠️ NỢ THẬT, KHÔNG PHẢI LỖI CHỮ: `RESOURCE_CLASS` (`workflow/nut.py`)
        #    chỉ có `cpu|gpu|api` — không có mức "ưu tiên GPU, lui về CPU, không
        #    giữ lease". NVENC của `render` vẫn chạy ngoài mọi lease (tình trạng
        #    CÓ TRƯỚC plan 02, plan 02 không được lặng lẽ đổi lịch card của một
        #    App đang bán). Muốn đóng nợ thì thêm một mức vào `RESOURCE_CLASS`
        #    và đo VRAM phiên NVENC — cả hai nằm ngoài phạm vi plan 02.
        # ⛔ `slots` không khai: không có bản khai nào trong kho sinh ra con số
        #    đó cho `autosubvideo.render` (không `admission_*`, không lane).
        resource={"class": "cpu"},
        # ⛔ `duration_s` KHÔNG vào khoá: nền tảng tự đo bằng ffprobe
        #    (`measured_from`), nên nó đổi giữa hai lượt gọi giống hệt nhau và
        #    làm khử trùng KHÔNG BAO GIỜ khớp (`registry.py` §idempotency).
        idempotency={"key_fields": ("video_key", "transcript", "style_id",
                                    "segment_mode", "output_format", "quality",
                                    "export_srt")},

        # ── Public API (H35.10, mở 2026-08-29) ───────────────────────────────
        # Mở được nhờ H35.10a: `duration_s` khai `measured_from` ở trên, nên máy
        # chủ đo từ chính tệp đã tải lên TRƯỚC khi tính giá. Trước đó giá tin
        # con số người gọi khai, và với máy gọi máy thì đó là phá lời hứa của
        # một báo giá đã ký (Q84).
        api_exposed=True,
        api_contract={
            "scopes": ("jobs:create",),
            "description": ("Burn a transcript you already have into a video "
                            "as styled subtitles. Costs 5 credits per minute "
                            "at standard quality; draft costs 0.6x and high "
                            "costs 1.5x. The duration is measured from the "
                            "file you upload, not from anything you send."),
            "hidden": ("duration_s",),
            "params": {
                "video_key": {
                    "description": ("The video to subtitle, given as the id of "
                                    "an upload you confirmed or of an artifact "
                                    "from an earlier job."),
                    "example": "upl_from_POST_/api/v1/uploads",
                },
                "transcript": {
                    "description": ("The words to burn in, as a list of "
                                    "segments with `start`, `end` and `text`. "
                                    "This tool does not transcribe for you."),
                    "example": [{"start": 0.0, "end": 1.8, "text": "Xin chao"}],
                },
                "style_id": {
                    "description": ("Look of the subtitles: font, colour and "
                                    "outline. Does not change the price."),
                    "example": "default",
                },
                "segment_mode": {
                    "description": ("How the transcript is cut into on-screen "
                                    "lines — whole sentences, shorter phrases, "
                                    "or one emphasised word at a time."),
                    "example": "sentence",
                },
                "quality": {
                    "description": ("Encoding quality of the finished video. "
                                    "`draft` costs 0.6 times the standard "
                                    "price and `high` costs 1.5 times."),
                    "example": "standard",
                },
                "output_format": {
                    "description": "Container of the finished video file.",
                    "example": "mp4",
                },
                "export_srt": {
                    "description": ("Also return the subtitles as a separate "
                                    ".srt file alongside the video."),
                    "example": True,
                },
            },
        },
    ),),

    enabled=True,
    lifecycle="development",
    capabilities=("AI Video", "Utilities"),
    group="Video",
    badge="MỚI",
    notes="Quick import + Full Studio; WhisperX/faster-whisper + burn ffmpeg/libass.",
)
