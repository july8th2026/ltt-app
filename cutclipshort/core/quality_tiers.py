"""Quality tier system V2 — controls EVERY layer of the pipeline.

Three tiers:
  fast         — CPU-friendly, minimal scoring, quick turnaround
  balanced     — Good quality, full scoring, moderate GPU (DEFAULT)
  high_quality — Best models, deepest analysis, highest render quality

V2: Now controls 5 layers (was 2):
  1. Analysis:   model sizes, sample rates, thresholds
  2. Semantic:   which semantic modules run, depth
  3. Editorial:  candidate count, scoring passes, strategies
  4. Evaluation: which evaluators run, gate strictness
  5. Render:     CRF, preset, resolution, audio bitrate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TierSpec:
    """Complete specification for one quality tier across all layers."""

    name: str
    display_name: str
    description: str

    # ═══════════════════════════════════════════════════════════════
    # 1. ANALYSIS LAYER
    # ═══════════════════════════════════════════════════════════════

    # ASR (Speech-to-Text)
    whisper_model: str
    whisper_compute_type: str
    whisper_beam_size: int

    # Person Detection
    yolo_model: str
    yolo_conf: float
    yolo_imgsz: int
    yolo_sample_every_n: int

    # Scene Detection
    scene_threshold: float
    min_scene_len_sec: float

    # Motion Analysis
    motion_sample_fps: int
    motion_resize: tuple[int, int]

    # Audio Analysis
    demucs_model: str
    demucs_enabled: bool

    # Visual Engine
    samples_per_scene: int = 3          # V2: 1 (fast) / 3 (balanced) / 5 (HQ)

    # ═══════════════════════════════════════════════════════════════
    # 2. SEMANTIC LAYER (V2)
    # ═══════════════════════════════════════════════════════════════

    semantic_enabled: bool = True        # Enable semantic layer at all
    semantic_topic_segmentation: bool = True
    semantic_narrative_detection: bool = True
    semantic_emotion_mapping: bool = True
    semantic_concept_clustering: bool = True
    semantic_similarity_threshold: float = 0.30  # Topic boundary sensitivity

    # ═══════════════════════════════════════════════════════════════
    # 3. EDITORIAL LAYER (V2)
    # ═══════════════════════════════════════════════════════════════

    target_clip_count: int = 5           # Default target clips
    max_clip_count: int = 20             # Max candidates to consider
    candidate_generation_passes: int = 4 # 1=hooks only, 4=all passes
    scoring_use_semantic: bool = True    # Use semantic scorer in composite
    scoring_use_coherence: bool = True   # Use coherence checker
    scoring_use_genre_cues: bool = True  # Use genre-specific detectors
    intent_classification: bool = True   # Classify clip intent
    coverage_gap_scan: bool = True       # Scan for uncovered regions
    ranking_objectives: int = 4          # 1=score-only, 4=full tournament

    # ═══════════════════════════════════════════════════════════════
    # 4. EVALUATION LAYER (V2)
    # ═══════════════════════════════════════════════════════════════

    eval_core_evaluators: bool = True    # pacing + audio + visual + content
    eval_opening_strength: bool = True   # Opening 3s evaluator
    eval_retention_potential: bool = True # Retention curve evaluator
    eval_semantic_completeness: bool = True
    eval_subtitle_density: bool = True
    eval_probe_rendered_file: bool = True # Actually ffprobe the output
    quality_gate_threshold: float = 50.0
    quality_gate_max_soft_failures: int = 2

    # ═══════════════════════════════════════════════════════════════
    # 5. RENDER LAYER
    # ═══════════════════════════════════════════════════════════════

    render_crf: str = "18"
    preview_crf: str = "28"
    preview_height: int = 480
    x264_preset: str = "medium"
    nvenc_preset: str = "p5"             # NVENC quality: p1 (fastest) → p7 (best)
    audio_bitrate: str = "192k"
    render_parallel_clips: int = 2       # V2: concurrent clip renders

    # ═══════════════════════════════════════════════════════════════
    # HARDWARE
    # ═══════════════════════════════════════════════════════════════

    min_vram_gb: float = 0
    prefer_gpu: bool = False
    estimated_speed: str = ""


# ═══════════════════════════════════════════════════════════════════════
# TIER DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════

TIER_FAST = TierSpec(
    name="fast",
    display_name="Nhanh",
    description="Thân thiện CPU, kết quả nhanh, phù hợp thử nghiệm",

    # Analysis: fast but still reasonable for Vietnamese
    whisper_model="base",
    whisper_compute_type="int8",
    whisper_beam_size=3,
    yolo_model="yolov8n.pt",
    yolo_conf=0.40,
    yolo_imgsz=320,
    yolo_sample_every_n=30,
    scene_threshold=30.0,
    min_scene_len_sec=2.0,
    motion_sample_fps=3,
    motion_resize=(240, 135),
    demucs_model="htdemucs",
    demucs_enabled=False,
    samples_per_scene=1,

    # Semantic: disabled (too slow for fast mode)
    semantic_enabled=False,
    semantic_topic_segmentation=False,
    semantic_narrative_detection=False,
    semantic_emotion_mapping=False,
    semantic_concept_clustering=False,

    # Editorial: minimal
    target_clip_count=3,
    max_clip_count=10,
    candidate_generation_passes=2,      # hooks + stories only
    scoring_use_semantic=False,
    scoring_use_coherence=False,
    scoring_use_genre_cues=False,
    intent_classification=False,
    coverage_gap_scan=False,
    ranking_objectives=1,               # Score-only greedy

    # Evaluation: core only
    eval_core_evaluators=True,
    eval_opening_strength=False,
    eval_retention_potential=False,
    eval_semantic_completeness=False,
    eval_subtitle_density=False,
    eval_probe_rendered_file=False,
    quality_gate_threshold=35.0,
    quality_gate_max_soft_failures=3,

    # Render: fast but not ugly
    render_crf="21",        # Was 23 — too aggressive with veryfast preset
    preview_crf="30",       # Was 32 — too blocky for preview
    preview_height=360,
    x264_preset="fast",     # Was "veryfast" — "fast" is 30% slower but much better quality
    nvenc_preset="p4",      # Fast but acceptable NVENC quality
    audio_bitrate="192k",
    render_parallel_clips=1,

    min_vram_gb=0,
    prefer_gpu=False,
    estimated_speed="~2x realtime on CPU",
)


TIER_BALANCED = TierSpec(
    name="balanced",
    display_name="Cân bằng",
    description="Chất lượng cao, GPU tốt — khuyên dùng cho RTX 3060+ (4GB+ VRAM)",

    # Analysis: high quality for Vietnamese — large-v3 auto-downgrades to medium if VRAM < 4GB
    whisper_model="large-v3",
    whisper_compute_type="float16",
    whisper_beam_size=5,
    yolo_model="yolov8s.pt",
    yolo_conf=0.30,
    yolo_imgsz=640,
    yolo_sample_every_n=8,
    scene_threshold=25.0,
    min_scene_len_sec=1.0,
    motion_sample_fps=6,
    motion_resize=(384, 216),
    demucs_model="htdemucs_ft",
    demucs_enabled=True,
    samples_per_scene=3,

    # Semantic: full
    semantic_enabled=True,
    semantic_topic_segmentation=True,
    semantic_narrative_detection=True,
    semantic_emotion_mapping=True,
    semantic_concept_clustering=True,
    semantic_similarity_threshold=0.30,

    # Editorial: full
    target_clip_count=5,
    max_clip_count=20,
    candidate_generation_passes=4,
    scoring_use_semantic=True,
    scoring_use_coherence=True,
    scoring_use_genre_cues=True,
    intent_classification=True,
    coverage_gap_scan=True,
    ranking_objectives=4,

    # Evaluation: full
    eval_core_evaluators=True,
    eval_opening_strength=True,
    eval_retention_potential=True,
    eval_semantic_completeness=True,
    eval_subtitle_density=True,
    eval_probe_rendered_file=True,
    quality_gate_threshold=50.0,
    quality_gate_max_soft_failures=2,

    # Render: high quality
    render_crf="17",
    preview_crf="26",
    preview_height=540,
    x264_preset="slow",
    nvenc_preset="p6",
    audio_bitrate="256k",
    render_parallel_clips=2,

    min_vram_gb=4.0,  # large-v3 needs 4GB usable; hardware adaptation downgrades if < 4GB
    prefer_gpu=True,
    estimated_speed="~3-5x realtime tùy GPU",
)


TIER_HIGH_QUALITY = TierSpec(
    name="high_quality",
    display_name="Chất lượng cao",
    description="Model tốt nhất, kết quả tốt nhất — cần 6GB+ VRAM",

    # Analysis: highest quality Vietnamese transcription
    whisper_model="large-v3",
    whisper_compute_type="float16",
    whisper_beam_size=5,
    yolo_model="yolov8s.pt",
    yolo_conf=0.30,
    yolo_imgsz=640,
    yolo_sample_every_n=5,
    scene_threshold=24.0,
    min_scene_len_sec=1.0,
    motion_sample_fps=8,
    motion_resize=(480, 270),
    demucs_model="htdemucs_ft",
    demucs_enabled=True,
    samples_per_scene=5,

    # Semantic: full + sensitive
    semantic_enabled=True,
    semantic_topic_segmentation=True,
    semantic_narrative_detection=True,
    semantic_emotion_mapping=True,
    semantic_concept_clustering=True,
    semantic_similarity_threshold=0.25,  # More sensitive boundaries

    # Editorial: maximum — 6 passes (all intents including payoff + loop)
    target_clip_count=8,
    max_clip_count=30,
    candidate_generation_passes=6,  # Raised from 4: adds payoff + loop passes
    scoring_use_semantic=True,
    scoring_use_coherence=True,
    scoring_use_genre_cues=True,
    intent_classification=True,
    coverage_gap_scan=True,
    ranking_objectives=4,

    # Evaluation: full + strict
    eval_core_evaluators=True,
    eval_opening_strength=True,
    eval_retention_potential=True,
    eval_semantic_completeness=True,
    eval_subtitle_density=True,
    eval_probe_rendered_file=True,
    quality_gate_threshold=55.0,
    quality_gate_max_soft_failures=1,   # Stricter

    # Render: best
    render_crf="16",
    preview_crf="24",
    preview_height=720,
    x264_preset="slow",
    nvenc_preset="p7",
    audio_bitrate="256k",
    render_parallel_clips=2,

    min_vram_gb=5.5,  # Usable VRAM after 1.5GB reserve (was 6)
    prefer_gpu=True,
    estimated_speed="~2-4x realtime tùy GPU",
)


# ═══════════════════════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════════════════════

ALL_TIERS: dict[str, TierSpec] = {
    "fast": TIER_FAST,
    "balanced": TIER_BALANCED,
    "high_quality": TIER_HIGH_QUALITY,
}

DEFAULT_TIER = "balanced"


_VALID_AUDIO_BITRATES = {"64k", "96k", "128k", "192k", "256k", "320k"}
_VALID_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}


def get_tier(name: str) -> TierSpec:
    """Get a tier by name. Falls back to balanced if not found."""
    tier = ALL_TIERS.get(name, TIER_BALANCED)
    # Validate render values
    if tier.audio_bitrate not in _VALID_AUDIO_BITRATES:
        import logging
        logging.getLogger(__name__).warning(
            "Invalid audio_bitrate '%s' in tier '%s', valid: %s",
            tier.audio_bitrate, tier.name, _VALID_AUDIO_BITRATES,
        )
    if tier.x264_preset not in _VALID_PRESETS:
        import logging
        logging.getLogger(__name__).warning(
            "Invalid x264_preset '%s' in tier '%s', valid: %s",
            tier.x264_preset, tier.name, _VALID_PRESETS,
        )
    return tier


def list_tiers() -> list[dict[str, str]]:
    """List available tiers for GUI display."""
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "min_vram_gb": str(t.min_vram_gb),
            "estimated_speed": t.estimated_speed,
        }
        for t in ALL_TIERS.values()
    ]


def tier_to_config_overrides(tier: TierSpec) -> dict[str, dict[str, Any]]:
    """Convert a TierSpec into config section overrides.

    V2: Now includes editorial, semantic, and evaluation sections.
    Only overrides keys the tier controls — preserves user customizations.
    """
    return {
        # Layer 1: Analysis
        "analysis": {
            "whisper_model": tier.whisper_model,
            "whisper_compute_type": tier.whisper_compute_type,
            "whisper_beam_size": tier.whisper_beam_size,
            "yolo_model": tier.yolo_model,
            "yolo_conf": tier.yolo_conf,
            "yolo_imgsz": tier.yolo_imgsz,
            "yolo_sample_every_n": tier.yolo_sample_every_n,
            "scene_threshold": tier.scene_threshold,
            "min_scene_len_sec": tier.min_scene_len_sec,
            "motion_sample_fps": tier.motion_sample_fps,
            "motion_resize_w": tier.motion_resize[0],
            "motion_resize_h": tier.motion_resize[1],
            "samples_per_scene": tier.samples_per_scene,
        },

        # Layer 2: Semantic
        "semantic": {
            "enabled": tier.semantic_enabled,
            "topic_segmentation": tier.semantic_topic_segmentation,
            "narrative_detection": tier.semantic_narrative_detection,
            "emotion_mapping": tier.semantic_emotion_mapping,
            "concept_clustering": tier.semantic_concept_clustering,
            "similarity_threshold": tier.semantic_similarity_threshold,
        },

        # Layer 3: Editorial
        "editorial": {
            "target_clip_count": tier.target_clip_count,
            "max_clip_count": tier.max_clip_count,
            "candidate_generation_passes": tier.candidate_generation_passes,
            "scoring_use_semantic": tier.scoring_use_semantic,
            "scoring_use_coherence": tier.scoring_use_coherence,
            "scoring_use_genre_cues": tier.scoring_use_genre_cues,
            "intent_classification": tier.intent_classification,
            "coverage_gap_scan": tier.coverage_gap_scan,
            "ranking_objectives": tier.ranking_objectives,
        },

        # Layer 4: Evaluation
        "evaluation": {
            "quality_gate_threshold": tier.quality_gate_threshold,
            "quality_gate_max_soft_failures": tier.quality_gate_max_soft_failures,
            "eval_core_evaluators": tier.eval_core_evaluators,
            "eval_opening_strength": tier.eval_opening_strength,
            "eval_retention_potential": tier.eval_retention_potential,
            "eval_semantic_completeness": tier.eval_semantic_completeness,
            "eval_subtitle_density": tier.eval_subtitle_density,
            "eval_probe_rendered_file": tier.eval_probe_rendered_file,
        },

        # Layer 5: Render + Audio
        "render": {
            "crf": tier.render_crf,
            "preview_crf": tier.preview_crf,
            "preview_height": tier.preview_height,
            "x264_preset": tier.x264_preset,
            "nvenc_preset": tier.nvenc_preset,
            "audio_bitrate": tier.audio_bitrate,
            "prefer_nvenc": tier.prefer_gpu,
            "render_parallel_clips": tier.render_parallel_clips,
        },
        "audio": {
            "demucs_model": tier.demucs_model,
            "demucs_enabled": tier.demucs_enabled,
        },
    }


def detect_hardware() -> dict:
    """Detect CPU, RAM, GPU, and VRAM for tier recommendation.

    Returns dict with: cpu_cores, ram_gb, gpu_available, vram_total_gb,
    vram_usable_gb (after OS/driver reserve), gpu_name.
    """
    import os
    cpu_cores = os.cpu_count() or 2
    # Estimate RAM from CPU cores if detection fails: 2GB per core is conservative
    ram_fallback = max(4.0, cpu_cores * 2.0)
    info: dict = {
        "cpu_cores": cpu_cores,
        "ram_gb": ram_fallback,
        "gpu_available": False,
        "vram_total_gb": 0.0,
        "vram_usable_gb": 0.0,
        "gpu_name": "",
    }

    # RAM detection
    try:
        import psutil
        info["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except ImportError:
        # Fallback: try Windows API
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            c_ulong = ctypes.c_ulonglong
            class MEMSTATEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", c_ulong),
                    ("ullAvailPhys", c_ulong),
                    ("ullTotalPageFile", c_ulong),
                    ("ullAvailPageFile", c_ulong),
                    ("ullTotalVirtual", c_ulong),
                    ("ullAvailVirtual", c_ulong),
                    ("ullAvailExtendedVirtual", c_ulong),
                ]
            stat = MEMSTATEX()
            stat.dwLength = ctypes.sizeof(stat)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            info["ram_gb"] = round(stat.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass

    # GPU detection
    try:
        import torch
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram_total = getattr(props, 'total_memory', getattr(props, 'total_mem', 0)) / (1024 ** 3)
            # Reserve ~1.5GB for OS/driver/CUDA context
            vram_usable = max(0.0, vram_total - 1.5)
            info["gpu_available"] = True
            info["vram_total_gb"] = round(vram_total, 1)
            info["vram_usable_gb"] = round(vram_usable, 1)
            info["gpu_name"] = props.name
    except (ImportError, RuntimeError):
        pass

    return info


def detect_recommended_tier() -> str:
    """Auto-detect best tier based on available hardware.

    Decision matrix:
      GPU + usable VRAM >= 5.5GB  → high_quality
      GPU + usable VRAM >= 3.0GB  → balanced
      No GPU + 8+ cores + 8+ RAM → balanced (CPU mode)
      Otherwise                   → fast
    """
    hw = detect_hardware()

    if hw["gpu_available"]:
        if hw["vram_usable_gb"] >= 5.5:
            return "high_quality"
        elif hw["vram_usable_gb"] >= 3.0:
            return "balanced"
        else:
            return "fast"
    else:
        # CPU-only: check if powerful enough for balanced
        if hw["cpu_cores"] >= 8 and hw["ram_gb"] >= 8.0:
            return "balanced"  # CPU can handle medium whisper
        return "fast"


def get_whisper_fallback(model: str) -> str | None:
    """Get fallback Whisper model if primary fails (OOM or missing).

    Chain: large-v3 → medium → base → tiny → None (give up).
    """
    chain = {
        "large-v3": "medium",
        "large-v2": "medium",
        "medium": "base",
        "base": "tiny",
        "tiny": None,
    }
    return chain.get(model)


def adapt_tier_to_hardware(tier: TierSpec) -> dict[str, Any]:
    """Adapt tier settings based on actual detected hardware.

    Returns dict of overrides to apply on top of tier config.
    Handles: VRAM scaling, CPU-only mode, parallel clip count.
    """
    hw = detect_hardware()
    overrides: dict[str, Any] = {}

    if hw["gpu_available"]:
        vram = hw["vram_usable_gb"]
        # Scale parallel render clips by usable VRAM
        # Note: 16GB cards report ~14.4GB usable (after 1.5GB OS reserve), so we use 14.0
        # threshold instead of 16.0 to ensure 16GB-class cards (5060 Ti, 4060 Ti, 4080) hit
        # the 8-clip tier as intended.
        if vram >= 14.0:
            overrides["render_parallel_clips"] = 8
        elif vram >= 8:
            overrides["render_parallel_clips"] = 4
        elif vram >= 4:
            overrides["render_parallel_clips"] = 2
        else:
            overrides["render_parallel_clips"] = 1

        # Whisper model check: downgrade if VRAM too small
        model_vram_needs = {
            "large-v3": 4.0, "medium": 1.5, "base": 0.5, "tiny": 0.2,
        }
        needed = model_vram_needs.get(tier.whisper_model, 1.0)
        if vram < needed:
            fallback = get_whisper_fallback(tier.whisper_model)
            if fallback:
                overrides["whisper_model"] = fallback

        # YOLO model check: downgrade if VRAM tight (shared with Whisper)
        yolo_vram = {"yolov8s.pt": 0.3, "yolov8n.pt": 0.1}
        whisper_used = model_vram_needs.get(
            overrides.get("whisper_model", tier.whisper_model), 1.0
        )
        remaining = vram - whisper_used
        if remaining < yolo_vram.get(tier.yolo_model, 0.1):
            overrides["yolo_model"] = "yolov8n.pt"  # Downgrade to nano
    else:
        # CPU-only mode
        overrides["render_parallel_clips"] = 1
        overrides["prefer_gpu"] = False
        # Whisper: use int8 on CPU for speed (float16 not supported on CPU)
        overrides["whisper_compute_type"] = "int8"
        # YOLO: skip or reduce on CPU (too slow)
        if tier.name == "fast":
            overrides["yolo_sample_every_n"] = 60  # Minimal sampling
        elif hw["cpu_cores"] < 8:
            overrides["yolo_sample_every_n"] = 30  # Reduce on weak CPU

    return overrides


def get_tier_comparison() -> list[dict[str, Any]]:
    """Get comparison table data for GUI display."""
    rows = []
    for tier in ALL_TIERS.values():
        rows.append({
            "name": tier.name,
            "display": tier.display_name,
            "description": tier.description,
            "analysis": {
                "whisper": tier.whisper_model,
                "yolo": tier.yolo_model,
                "scene_sensitivity": "Low" if tier.scene_threshold >= 30 else "Medium" if tier.scene_threshold >= 27 else "High",
                "visual_samples": f"{tier.samples_per_scene}/scene",
            },
            "semantic": "Off" if not tier.semantic_enabled else "Full",
            "editorial": {
                "target_clips": tier.target_clip_count,
                "passes": tier.candidate_generation_passes,
                "intent": "Yes" if tier.intent_classification else "No",
                "coherence": "Yes" if tier.scoring_use_coherence else "No",
                "coverage_scan": "Yes" if tier.coverage_gap_scan else "No",
            },
            "evaluation": {
                "evaluators": sum([
                    tier.eval_core_evaluators * 4,
                    tier.eval_opening_strength,
                    tier.eval_retention_potential,
                    tier.eval_semantic_completeness,
                    tier.eval_subtitle_density,
                ]),
                "gate_threshold": tier.quality_gate_threshold,
                "probe_file": "Yes" if tier.eval_probe_rendered_file else "No",
            },
            "render": {
                "crf": tier.render_crf,
                "preset": tier.x264_preset,
                "audio": tier.audio_bitrate,
                "parallel": tier.render_parallel_clips,
            },
            "speed": tier.estimated_speed,
        })
    return rows
