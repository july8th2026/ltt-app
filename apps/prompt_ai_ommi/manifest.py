"""Manifest for PROMPT AI OMMI (Q65/H19)."""
from __future__ import annotations

from platform_core.i18n import N_
import math

from platform_core.registry import AppManifest, NavEntry, ToolSpec

# ⭐ Tran so canh doc TU HANG SO, khong go tay. `jobs.py` da doc no; mot ben
#    go tay la cach hai ben lech nhau (bat bien B-6, spec §8).
from apps.prompt_ai_ommi.project_schema import MAX_SCENES
from apps.prompt_ai_ommi.services import chia_lo as _chia_lo


def _director_cost(params: dict) -> int:
    try:
        scenes = max(1, min(MAX_SCENES, int(params.get("scene_count", 6))))
    except (TypeError, ValueError):
        scenes = 6
    return max(4, min(18, 2 + math.ceil(scenes / 3) * 2))


def _cost(params: dict) -> int:
    kind = str(params.get("operation") or "director")
    if kind == "storyboard":
        try:
            scenes = max(1, min(MAX_SCENES, int(params.get("scene_count", 6))))
        except (TypeError, ValueError):
            scenes = 6
        return max(3, min(12, 2 + math.ceil(scenes / 4) * 2))
    if kind == "batch":
        try:
            count = max(1, min(8, int(params.get("batch_count", 1))))
        except (TypeError, ValueError):
            count = 1
        return _director_cost(params) * count
    if kind == "iterate":
        # Sua mot kich ban DA CO: gui lai brief + feedback, khong dung lai tu
        # dau. Dat bang mot nua director, san 3..9.
        return max(3, min(9, math.ceil(_director_cost(params) / 2)))
    if kind == "character_lock":
        # Sinh MOT khoi chu co dinh cho nhan vat — khong lien quan so canh.
        return 3
    return _director_cost(params)


def _bao_tri() -> None:
    """Uy quyen cho `services.bao_tri.bao_tri`.

    ⛔ Import BEN TRONG ham, khong o dau tep: `manifest.py` duoc nap boi
       `registry.discover()` o MOI tien trinh — ke ca nhung tien trinh khong bao
       gio chay viec nay — va keo ca chuoi services (kem SQLAlchemy, kho luu
       tru) vao do la bat moi worker tra gia nap cho mot ham no khong goi.
    """
    from apps.prompt_ai_ommi.services.bao_tri import bao_tri

    bao_tri()


MANIFEST = AppManifest(
    slug="prompt_ai_ommi",
    display_name="Prompt AI",
    route_prefix="/prompt-ai-ommi",
    summary=("Studio AI biến brief và tài sản tham chiếu thành prompt nhiều cảnh, "
             "storyboard và gói sản xuất nhất quán."),
    icon="✦",
    accent="#E53935",
    nav=(NavEntry("Prompt AI", "/prompt-ai-ommi", "✦", "prompt_ai_ommi"),),
    job_types=("prompt_ai_ommi.generate", "prompt_ai_ommi.import_zip"),
    requires=("api",),
    # 🔴 TRAN THOI GIAN, SUY tu `chia_lo` — ⛔ KHONG go lai con so.
    #
    #    Pha 6 chia mot luot sinh canh thanh nhieu LO, nen so luot goi LLM nhan
    #    len: 20 canh di tu **1** luot thanh **ceil(20/5) = 4** luot. Mot tran von
    #    vua du co the thanh khong du, va `prompt_canh` da ghi dung hau qua vao
    #    manifest cua no: *"chet o tran nghia la khach DA TRA ma khong nhan gi"*.
    #
    # ⭐ Suy tu `chia_lo` chu khong go `240`: doi `LO_CANH` thi tran tu di theo.
    #    Cung ly le voi `prompt_canh.manifest` **nhap** `TRAN_SO_CANH` thay vi go
    #    `500`. `tests/test_5572` chot bat dang thuc de hai so khong troi khoi nhau.
    #
    # ⚠️ `NGAN_SACH_MOI_LUOT_S = 60` van la mot **GIA THIET** (suy tu `prompt_canh`:
    #    3600/76 ≈ 47 s, cong bien vi lo cua ta lon hon). Ai do that tren may B thi
    #    sua o `chia_lo` — MOT cho — va con so nay tu dung theo.
    max_runtime_s={
        "prompt_ai_ommi.generate":
            _chia_lo.so_luot_goi(MAX_SCENES) * _chia_lo.NGAN_SACH_MOI_LUOT_S,
    },
    credit_cost=_cost,
    tools=(
        ToolSpec(
            name="text.prompt_package",
            job_type="prompt_ai_ommi.generate",
            description=("Chuyển brief thành gói prompt nhiều cảnh có camera, ánh sáng, "
                         "continuity và negative prompt."),
            ten_ngan=N_('Soạn gói prompt nhiều cảnh'),
            params_schema={
                "operation": {"type": "enum", "values": ["director"],
                              "default": "director"},
                "title": {"type": "string", "required": True, "max_length": 160},
                "story": {"type": "text", "required": True, "max_length": 12000},
                "scene_count": {"type": "int", "min": 1, "max": MAX_SCENES, "default": 6},
                "duration_seconds": {"type": "int", "min": 3, "max": 600,
                                     "default": 30},
                "aspect_ratio": {"type": "enum",
                                 "values": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                                 "default": "16:9"},
                "style": {"type": "string", "max_length": 500},
                "audience": {"type": "string", "max_length": 300},
                "language": {"type": "enum", "values": ["vi", "en"], "default": "vi"},
                "resources": {"type": "json"},
                # 🔴 Pha 05.5 đổi động cơ sang LTT_LLM nhưng **quên dòng
                #    này** — bảng chọn model vẫn khai một nhà đã ngừng, và
                #    hệ quả là enum rỗng ⇒ tool không chọn được model nào.
                "model": {"type": "model_ref", "category": "chat",
                          "providers": ["ltt_llm"]},
            },
            returns={"prompt_package": "json", "master_prompt": "text"},
            verifiable=("structural",),

            side_effect="external",
            # `slots: 0` truy về một VẮNG MẶT có chủ ý: manifest này không khai
            # `admission_*` hay `gpu_vram_mb` nào — việc nằm trọn ở provider
            # ngoài, máy A không có tài nguyên nào để giành.
            resource={"class": "api", "slots": 0},
            idempotency={"key_fields": ("operation", "title", "story", "style",
                                        "aspect_ratio", "scene_count", "model",
                                        "audience", "language",
                                        "duration_seconds", "resources")},

            # ── Public API (Q92, wave 3) ─────────────────────────────────────
            # Priced from `scene_count` alone — no client-declared duration, so
            # no run-time top-up, so a signed quote stays true (unlike the
            # duration-priced video tools deferred in waves 2 and 3).
            api_exposed=True,
            api_contract={
                "scopes": ("jobs:create",),
                "description": ("Turn a story brief into a structured prompt "
                                "package: one prompt per scene plus a master "
                                "prompt. Priced by scene count."),
                # `operation` is how the app routes internally between its two
                # generators; a public caller picks a tool, not an internal
                # branch. `model` is hidden because the price does not depend on
                # it — publishing the choice would sell the dearest model at the
                # cheapest price. `resources` is a free-form JSON blob the
                # project schema interprets, references included; until it has a
                # public, owner-checked shape it stays out.
                "hidden": ("operation", "model", "resources"),
                "params": {
                    "title": {
                        "description": ("Working title of the piece. Used for "
                                        "tone and for naming the result."),
                        "example": "The last train home",
                    },
                    "story": {
                        "description": ("The story or brief, in prose. This is "
                                        "the source everything else is derived "
                                        "from."),
                        "example": ("A courier misses the last train and walks "
                                    "the city until dawn."),
                    },
                    "scene_count": {
                        "description": ("How many scenes to produce. This is "
                                        "what the price depends on."),
                        "example": 6,
                    },
                    "aspect_ratio": {
                        "description": ("Shape the scenes are written for; it "
                                        "changes framing advice, not the file."),
                        "example": "16:9",
                    },
                    "style": {
                        "description": ("Visual or narrative style to aim for, "
                                        "in your own words."),
                        "example": "neo-noir, heavy rain, neon reflections",
                    },
                    "duration_seconds": {
                        "description": ("Target length of the finished piece. "
                                        "Scenes are paced to fit it."),
                        "example": 45,
                    },
                    "audience": {
                        "description": "Who the piece is for.",
                        "example": "people who commute late at night",
                    },
                    "language": {
                        "description": "Language the prompts are written in.",
                        "example": "en",
                    },
                },
            },
        ),
        ToolSpec(
            name="story.storyboard",
            job_type="prompt_ai_ommi.generate",
            description=("Phân rã câu chuyện thành storyboard shot list có bố cục, "
                         "camera, continuity và prompt hình ảnh."),
            ten_ngan=N_('Dựng storyboard câu chuyện'),
            params_schema={
                "operation": {"type": "enum", "values": ["storyboard"],
                              "default": "storyboard"},
                "title": {"type": "string", "required": True, "max_length": 160},
                "story": {"type": "text", "required": True, "max_length": 12000},
                "scene_count": {"type": "int", "min": 1, "max": MAX_SCENES, "default": 6},
                "aspect_ratio": {"type": "enum",
                                 "values": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
                                 "default": "16:9"},
                "style": {"type": "string", "max_length": 500},
                "resources": {"type": "json"},
                "model": {"type": "model_ref", "category": "chat",
                          "providers": ["ltt_llm"]},
            },
            returns={"storyboard": "json", "master_prompt": "text"},
            verifiable=("structural",),

            side_effect="external",
            # `slots: 0` truy về một VẮNG MẶT có chủ ý: manifest này không khai
            # `admission_*` hay `gpu_vram_mb` nào — việc nằm trọn ở provider
            # ngoài, máy A không có tài nguyên nào để giành.
            resource={"class": "api", "slots": 0},
            idempotency={"key_fields": ("operation", "title", "story", "style",
                                        "aspect_ratio", "scene_count", "model",
                                        "resources")},

            # ── Public API (Q92, wave 3) ─────────────────────────────────────
            # Priced from `scene_count` alone — no client-declared duration, so
            # no run-time top-up, so a signed quote stays true (unlike the
            # duration-priced video tools deferred in waves 2 and 3).
            api_exposed=True,
            api_contract={
                "scopes": ("jobs:create",),
                "description": ("Turn a story brief into a storyboard: one shot "
                                "description per scene plus a master prompt. "
                                "Priced by scene count."),
                # `operation` is how the app routes internally between its two
                # generators; a public caller picks a tool, not an internal
                # branch. `model` is hidden because the price does not depend on
                # it — publishing the choice would sell the dearest model at the
                # cheapest price. `resources` is a free-form JSON blob the
                # project schema interprets, references included; until it has a
                # public, owner-checked shape it stays out.
                "hidden": ("operation", "model", "resources"),
                "params": {
                    "title": {
                        "description": ("Working title of the piece. Used for "
                                        "tone and for naming the result."),
                        "example": "The last train home",
                    },
                    "story": {
                        "description": ("The story or brief, in prose. This is "
                                        "the source everything else is derived "
                                        "from."),
                        "example": ("A courier misses the last train and walks "
                                    "the city until dawn."),
                    },
                    "scene_count": {
                        "description": ("How many scenes to produce. This is "
                                        "what the price depends on."),
                        "example": 6,
                    },
                    "aspect_ratio": {
                        "description": ("Shape the scenes are written for; it "
                                        "changes framing advice, not the file."),
                        "example": "16:9",
                    },
                    "style": {
                        "description": ("Visual or narrative style to aim for, "
                                        "in your own words."),
                        "example": "neo-noir, heavy rain, neon reflections",
                    },
                },
            },
        ),
    ),
    # Kho tài nguyên và thư viện prompt dùng chung giữa nhiều project nên không
    # vừa trong `AppProject` JSON — app sở hữu bảng riêng, xem `tables.py`.
    table_prefix="ommi",
    # ⭐ NGUOI GOI cho hai chinh sach han luu da co ma truoc 28/09 khong ai
    #    chay: `ommi_trash.purge_after` (30 ngay) va `ommi_handoff.expires_at`
    #    (30 phut). Xem `services/bao_tri.py`.
    bao_tri=_bao_tri,
    enabled=True,
    public=True,
    lifecycle="released",
    capabilities=("Chat & Prompt", "Automation"),
    group="AI Studio",
    badge="MỚI",
    notes="H19/Q65: replatform Prompt Seedance Studio trên AppProject/Job/Credit/Storage.",
)

