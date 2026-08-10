"""Registry pack/evaluator/model: thiếu duyệt thì không được chạy lặng lẽ."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from PIL import __version__ as PILLOW_VERSION

from platform_core.i18n import N_


@dataclass(frozen=True)
class Evaluator:
    key: str
    version: str
    license: str
    source: str
    enabled: bool
    needs_gpu: bool = False
    model_sha256: str = ""
    note: str = ""


EVALUATORS = {
    "pillow": Evaluator(
        key="pillow", version=PILLOW_VERSION, license="HPND",
        source="https://github.com/python-pillow/Pillow", enabled=True,
        note=N_("Giải mã và đọc contract ảnh; không phải metric cảm nhận."),
    ),
    "ffprobe": Evaluator(
        key="ffprobe", version="system", license=N_("LGPL/GPL theo build cài đặt"),
        source="https://ffmpeg.org/", enabled=True,
        note=N_("Phase foundation; deploy phải lưu ffprobe -version/configuration."),
    ),
    "ltt_subtitle_rules": Evaluator(
        key="ltt_subtitle_rules", version="1.0.0", license="LTT internal",
        source="apps/qualitylab/services/subtitle.py", enabled=True,
    ),
    "lpips": Evaluator(
        key="lpips", version="planned", license="BSD-2-Clause",
        source="https://github.com/richzhang/PerceptualSimilarity", enabled=False,
        needs_gpu=True, note=N_("H31.3: pin package/weights/hash trước khi bật."),
    ),
    "pyiqa": Evaluator(
        key="pyiqa", version="planned", license="review-required",
        source="https://github.com/chaofengc/IQA-PyTorch", enabled=False,
        needs_gpu=True, note=N_("H31.3: duyệt từng metric/weight, không duyệt theo repo chung."),
    ),
    "dover_mobile": Evaluator(
        key="dover_mobile", version="planned", license="review-required",
        source="https://github.com/VQAssessment/DOVER", enabled=False,
        needs_gpu=True, note=N_("H31.3: benchmark VRAM/runtime trên GPU 16 GB."),
    ),
    "whisperx": Evaluator(
        key="whisperx", version="planned", license="BSD-2-Clause",
        source="https://github.com/m-bain/whisperX", enabled=False,
        needs_gpu=True, note=N_("H31.4: model align theo ngôn ngữ và token diarization riêng."),
    ),
    "paddleocr": Evaluator(
        key="paddleocr", version="planned", license="Apache-2.0",
        source="https://github.com/PaddlePaddle/PaddleOCR", enabled=False,
        needs_gpu=True, note=N_("H31.4: pin model tiếng Việt + checksum trước khi bật."),
    ),
    "vbench": Evaluator(
        key="vbench", version="planned", license="review-required",
        source="https://github.com/Vchitect/VBench", enabled=False,
        needs_gpu=True, note=N_("H31.5: chỉ subset custom-input sau benchmark tài nguyên."),
    ),
}

PACKS = {
    "media_contract": {
        "label": N_("Media contract"),
        "accepts": ("image", "video", "audio"),
        "evaluators": ("pillow", "ffprobe"),
        "description": N_("Decode, stream, kích thước, duration, FPS và audio."),
    },
    "upscale_foundation": {
        "label": N_("Upscale foundation"),
        "accepts": ("image", "video"),
        "evaluators": ("pillow", "ffprobe"),
        "description": N_("Contract đầu ra Upscale; perceptual/temporal mở ở H31.3."),
    },
    "autosub_foundation": {
        "label": N_("AutoSub foundation"),
        "accepts": ("subtitle",),
        "evaluators": ("ltt_subtitle_rules",),
        "description": N_("Parse cue, timing, overlap, CPS, line và transcript error."),
    },
}


def enabled_pack(key: str) -> dict:
    pack = PACKS.get(key)
    if pack is None:
        raise ValueError(N_(f"Pack không tồn tại: {key}"))
    disabled = [name for name in pack["evaluators"] if not EVALUATORS[name].enabled]
    if disabled:
        raise RuntimeError(N_(f"Pack còn evaluator chưa duyệt: {', '.join(disabled)}"))
    return pack


def pack_evaluators(key: str) -> list[dict]:
    """Snapshot version/license/hash để report cũ không đổi khi registry đổi."""
    pack = enabled_pack(key)
    return [asdict(EVALUATORS[name]) for name in pack["evaluators"]]


def public_registry() -> dict:
    """Registry an toàn cho UI; không chứa đường dẫn model/cache hay cấu hình máy."""
    return {
        "packs": {key: dict(value) for key, value in PACKS.items()},
        "evaluators": {key: asdict(value) for key, value in EVALUATORS.items()},
    }
