"""
App `taovideo` — Tạo video AI (BytePlus ModelArk / Seedance 2.0). Di trú từ BOT
GEMINI `seedance_video` (Đợt A2). App VIDEO đầu tiên: async submit→poll, giá theo
token thật (giữ chỗ ước tính → quyết toán chính xác).

Slug đặt `taovideo` (không phải "seedance") vì "seedance" là brand model xuất hiện
trong `platform_core/providers.py` (byteplus) → test_60 chống hardcode-slug báo
nhầm. Bài học lặp lại: slug app phải là chuỗi RIÊNG, không trùng brand/model.

Pha 1 (bản này): text→video + ảnh tham chiếu inline (≤8MB), đủ model/độ phân giải/
thời lượng/tỉ lệ/audio + giá thật + serve video theo HTTP Range (né trần 100MB CF).
Pha 2 (sau): asset:// (ảnh/video lớn + người thật) + kiểm duyệt mặt tự động.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry, ToolSpec


def _hop_dong_api() -> dict:
    """Hợp đồng công khai của `video.generate` — **sinh từ `models.py`**.

    🔴 KHÔNG GÕ LẠI MỘT CON SỐ NÀO Ở ĐÂY. `apps/taovideo/models.py` đã giữ đủ
       ràng buộc theo từng model. Chép chúng sang đây là tạo bản sao thứ hai của
       sự thật, và bản sao sẽ lệch đúng vào hôm ta thêm một model.
       (`USER_DECISIONS.md` §7 của gói API Expansion V2 cấm đúng việc này.)

    ⭐ BA THỨ ĐI RA BA ĐƯỜNG KHÁC NHAU, và phân biệt được chúng là cả bài toán:

       · `constraints`  -> CÔNG BỐ qua `PublicModel.to_public_dict()`. Đây là
         thứ khách cần để biết tổ hợp nào hợp lệ **trước khi gọi**.
       · `id`           -> KHAI nhưng KHÔNG công bố. `ToolView.to_public_dict()`
         là danh sách trắng nên nó không có đường ra; và khai nó chính là cách
         `test_212::test_no_vendor_model_id_reaches_a_customer_surface` biết
         phải săn chuỗi nào. Giấu đi thì phép kiểm **mất mục tiêu**.
       · `endpoint`     -> KHÔNG đi đâu cả. Địa chỉ hạ tầng, không phải thuộc
         tính sản phẩm.

    ⚠️ `enums` phải là **hợp** của mọi model, vì registry đòi một danh sách
       phẳng cho mỗi enum lấy giá trị từ nguồn nội bộ. Hợp trả lời *"giá trị nào
       tồn tại"*; `constraints` trả lời *"model này nhận giá trị nào"*. Thiếu vế
       thứ hai thì khách phải thử rồi ăn lỗi — đó là lý do phải có cả hai.
    """
    from apps.taovideo import models as _m

    hoat_dong = {ten: c for ten, c in _m.MODELS.items() if c.get("active")}

    def _hop(truong: str) -> list:
        gop: list = []
        for c in hoat_dong.values():
            for v in c.get(truong) or ():
                if v not in gop:
                    gop.append(v)
        return gop

    return {
        "scopes": ("jobs:create",),
        "description": ("Generate video from a text prompt, optionally guided "
                        "by reference media. Valid resolution, duration and "
                        "aspect ratio depend on the model — see each model's "
                        "`constraints` in GET /api/v1/models."),
        "models": {
            ten: {
                "id": c["provider_model_id"],
                "description": c.get("label") or ten,
                "stability": "stable",
                "constraints": {
                    "resolutions": list(c.get("resolutions") or ()),
                    "durations": list(c.get("durations") or ()),
                    "aspect_ratios": list(c.get("aspects") or ()),
                    "supports_seed": bool(c.get("supports_seed")),
                    "prompt_controls": list(c.get("prompt_controls") or ()),
                },
            }
            for ten, c in hoat_dong.items()
        },
        "enums": {
            "resolution": _hop("resolutions"),
            "duration": _hop("durations"),
            "aspect_ratio": _hop("aspects"),
        },
        # ⛔ HOÃN CÓ GHI, không phải bỏ qua kiểm. Bốn đường tham chiếu dưới đây
        #    chưa chứng minh được ownership + vòng đời qua `upload_sessions` ở
        #    đường API, và một tham chiếu mở mà chưa kiểm ownership là đường để
        #    khách A đọc tệp của khách B. Mở từng cái khi có bằng chứng.
        "hidden": ("image_keys", "video_key", "audio_key", "refs"),
        # ⭐ MO TA CHO TUNG THAM SO — `test_198` doi, va no doi dung.
        #
        #    Mot tham so cong khai khong co mo ta la mot tham so khach phai
        #    DOAN. Voi tool nay thi doan sai co gia that: `duration` doan nham
        #    don vi la tra tien cho video dai gap ba lan.
        "params": {
            "prompt": {
                "description": ("What the video should show. Write it in any "
                                "language; longer and more specific prompts "
                                "give steadier results than short ones."),
                "example": "A calico cat stretching on a sunlit windowsill",
            },
            "resolution": {
                "description": ("Output resolution. Valid values depend on the "
                                "model — read `constraints.resolutions` for the "
                                "model you picked. Higher costs more."),
                "example": "720p",
            },
            "duration": {
                "description": ("Video length in **seconds**, not frames. "
                                "Valid values depend on the model — read "
                                "`constraints.durations`. Price scales with it."),
                "example": 5,
            },
            "aspect_ratio": {
                "description": ("Frame shape. Valid values depend on the model "
                                "— read `constraints.aspect_ratios`."),
                "example": "16:9",
            },
            "generate_audio": {
                "description": ("Whether the model also generates a soundtrack. "
                                "Leave it on unless you are supplying your own."),
                "example": True,
            },
            "camera": {
                "description": ("Camera movement. Empty means the model "
                                "decides."),
                "example": "dolly_in",
            },
            "motion": {
                "description": "How much the subject moves. Empty means default.",
                "example": "subtle",
            },
            "visual_style": {
                "description": ("Overall look. Empty means the model follows "
                                "the prompt alone."),
                "example": "cinematic",
            },
            "seed": {
                "description": ("Repeat a previous result. The same seed with "
                                "the same input gives the same video; omit it "
                                "for a new one each time."),
                "example": 12345,
            },
            "model": {
                "description": ("Which model renders the video. Each one "
                                "accepts a different set of resolutions and "
                                "durations — see GET /api/v1/models."),
                "example": "seedance-2.0-mini",
            },
            "image_key": {
                "description": ("Upload id of one reference image to guide the "
                                "first frame. Optional."),
                "example": "up_...",
            },
        },
    }


def _cost(params: dict) -> int:
    """Giá GIỮ CHỖ = ước tính theo model/độ phân giải/thời lượng (token→VND→credit).
    Quyết toán chính xác theo token thật ở handler (worker hoàn phần dư)."""
    from apps.taovideo.cost import customer_charge_cap
    return customer_charge_cap(params)


MANIFEST = AppManifest(
    slug="taovideo",
    display_name=N_('Tạo Video Seedance'),
    route_prefix="/taovideo",
    summary=N_('Tạo video Seedance từ mô tả và tài sản tham chiếu. Tính phí theo token thật.'),
    icon="🎬",
    accent="#6A0DAD",

    nav=(NavEntry("Tạo Video Seedance", "/taovideo", "🎬", "taovideo"),),

    job_types=("taovideo.generate",),
    requires=("api",),
    credit_cost=_cost,
    tools=(ToolSpec(
        name="video.generate", job_type="taovideo.generate",
        description=N_('Sinh video Seedance từ mô tả và các tài sản tham chiếu tùy chọn.'),
        params_schema={
            "prompt": {"type": "string", "required": True, "max_length": 10000},
            "model": {"type": "model_ref", "category": "video", "providers": ["byteplus"]},
            "resolution": {"type": "enum", "depends_on": "model", "field": "resolutions"},
            "duration": {"type": "enum", "depends_on": "model", "field": "durations"},
            "aspect_ratio": {"type": "enum", "depends_on": "model", "field": "aspects"},
            "generate_audio": {"type": "bool", "default": True},
            "camera": {"type": "enum", "values": ["", "static", "dolly_in", "tracking", "orbit", "aerial", "handheld"], "default": ""},
            "motion": {"type": "enum", "values": ["", "subtle", "dynamic", "cinematic"], "default": ""},
            "visual_style": {"type": "enum", "values": ["", "realistic", "cinematic", "anime", "product"], "default": ""},
            "seed": {"type": "number", "min": 0, "max": 2147483647},
            "image_key": {"type": "image"},
            "image_keys": {"type": "image[]"},
            "video_key": {"type": "video"},
            "audio_key": {"type": "audio"},
            "refs": {"type": "json"},
        },
        returns={"video_key": "video"},
        verifiable=("technical", "vlm_judge"),
        # ⭐ `api_exposed` la MOT LOI KHAI ("hop dong nay da viet xong"), khong
        #    phai cong tac mo hang. Thu mo hang la `LTT_PUBLIC_API_TOOLS` cua
        #    operator — fail-closed cua Q92 van nguyen: bat co nay mot minh
        #    KHONG mo tool nao.
        # ⛔ Va registry tu choi nua voi: co hop dong ma khong khai la loi nap.
        api_exposed=True,
        api_contract=_hop_dong_api(),
    ),),

    enabled=True,
    lifecycle="released",
    capabilities=("AI Video",),
    group="Video",
    badge="MỚI",
    notes="Di trú A2 từ seedance_video. Key qua APIKEYS (provider byteplus, category video).",
)
