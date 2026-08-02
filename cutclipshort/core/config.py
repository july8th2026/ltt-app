"""App configuration loader.

Loads YAML config with env variable overrides and defaults merge.
Config hierarchy: defaults → app_config.yaml → env vars → runtime overrides.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from cutclipshort.constants import APP_CONFIG_PATH, APP_DATA_DIR
from cutclipshort.errors import ConfigError

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG: dict[str, Any] = {
    "quality_tier": "balanced",  # fast | balanced | high_quality
    "analysis": {
        "scene_threshold": 25.0,
        "min_scene_len_sec": 1.0,
        "motion_sample_fps": 6,
        "motion_resize_w": 384,
        "motion_resize_h": 216,
        "whisper_model": "large-v3",     # large-v3 = best Vietnamese accuracy; auto-downgrades if VRAM < 4GB
        "whisper_language": "auto",      # Auto-detect language (supports Vietnamese + English + others)
        "whisper_compute_type": "float16",
        "whisper_beam_size": 5,          # Higher beam = more accurate
        "yolo_model": "yolov8s.pt",      # small = better person detection than nano
        "yolo_conf": 0.30,
        "yolo_imgsz": 640,
        "yolo_sample_every_n": 8,
    },
    "editorial": {
        "min_clip_duration_sec": 15.0,
        "max_clip_duration_sec": 60.0,
        "target_clip_count": 5,
        "default_genre": "talking_head",
        # ── Candidate generation thresholds ──
        "emotional_spike_min_intensity": 0.35,
        "temporal_overlap_max": 0.40,
        "semantic_overlap_max": 0.60,
        "coverage_gap_min_ratio": 0.30,
        "speech_ratio_min_for_gap_fill": 0.30,
        # ── Hook detection thresholds ──
        "hook_keyword_threshold": 0.30,
        "hook_energy_strong": 0.60,
        "hook_silence_penalty_threshold": 0.10,
        "hook_strong_score": 0.70,
        "hook_decent_score": 0.50,
        "hook_weak_score": 0.30,
        # ── Payoff detection thresholds ──
        "payoff_keyword_threshold": 0.30,
        "payoff_sentence_complete_threshold": 0.50,
        "payoff_strong_score": 0.70,
        "payoff_decent_score": 0.60,
        "payoff_weak_score": 0.40,
        "payoff_energy_drop_threshold": 0.50,
        "payoff_trailing_pause_threshold": 0.30,
        # ── Scoring thresholds ──
        "semantic_score_bonus_threshold": 0.60,
        "semantic_hook_bonus_threshold": 0.50,
        "filler_heavy_threshold": 0.15,
        "filler_moderate_threshold": 0.10,
        "speech_ratio_low": 0.30,
        # ── Ranking thresholds ──
        "rank_hook_type_dominance_max": 0.50,
        "rank_zone_coverage_low": 0.10,
        "rank_zone_coverage_med": 0.50,
        "rank_visual_person_threshold": 0.60,
        "rank_speech_presence_threshold": 0.10,
        # ── Intent classification thresholds ──
        "intent_viral_emotion": 0.70,
        "intent_viral_hook": 0.50,
        "intent_controversial_emotion": 0.50,
        "intent_hook_score_strong": 0.60,
        "intent_hook_score_very_strong": 0.70,
        "intent_story_completeness": 0.50,
        "intent_payoff_strong": 0.70,
        "intent_min_confidence": 0.25,
        # ── Coherence thresholds ──
        "coherence_keyword_threshold": 0.30,
        "coherence_distance_penalty_threshold": 0.05,
    },
    "render": {
        "prefer_nvenc": True,
        "nvenc_preset": "p6",            # NVENC quality preset: p1 (fastest) → p7 (best)
        "x264_preset": "slow",           # Better compression at same CRF vs "medium"
        "crf": "17",
        "preview_crf": "26",
        "preview_height": 540,
        "audio_bitrate": "256k",
        "audio_sample_rate": 48000,      # 48kHz standard for video production
        "audio_channels": 2,
        "xfade_duration": 0.3,
    },
    "audio": {
        "loudnorm_lufs": -14.0,
        "loudnorm_true_peak_db": -1.5,
        "demucs_model": "htdemucs_ft",   # Fine-tuned model — better vocal separation
        "demucs_enabled": True,
    },
    "framing": {
        "person_target_fraction": 0.70,
        "smooth_alpha": 0.07,
        "max_pan_px_per_sec": 900.0,
    },
    "evaluation": {
        "quality_gate_threshold": 50.0,
    },
    "adapters": {
        "ffmpeg_path": None,  # auto-detect
        "ffprobe_path": None,  # auto-detect
        "demucs_path": None,  # auto-detect
    },
    "job_queue": {
        "max_workers": 4,
        "io_workers": 2,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _apply_env_overrides(config: dict) -> dict:
    """Apply environment variable overrides.

    Env var format: CUTCLIPSHORT_{SECTION}_{KEY} (uppercase)
    Example: CUTCLIPSHORT_RENDER_CRF=20
    """
    prefix = "CUTCLIPSHORT_"
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(prefix):
            continue
        parts = env_key[len(prefix):].lower().split("_", 1)
        if len(parts) != 2:
            continue
        section, key = parts
        if section in config and key in config[section]:
            existing = config[section][key]
            # Type coerce based on existing value type
            try:
                if isinstance(existing, bool):
                    config[section][key] = env_value.lower() in ("true", "1", "yes")
                elif isinstance(existing, int):
                    config[section][key] = int(env_value)
                elif isinstance(existing, float):
                    config[section][key] = float(env_value)
                else:
                    config[section][key] = env_value
                logger.debug("Config override from env: %s.%s = %s", section, key, env_value)
            except (ValueError, TypeError):
                logger.warning("Invalid env override: %s=%s", env_key, env_value)
    return config


class AppConfig:
    """Application configuration manager.

    Loads config from YAML file with defaults and env overrides.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path or APP_CONFIG_PATH
        self._config = self._load()

    def _load(self) -> dict[str, Any]:
        """Load config: defaults → tier overrides → file → env overrides."""
        config = _deep_merge({}, _DEFAULT_CONFIG)

        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                if isinstance(file_config, dict):
                    config = _deep_merge(config, file_config)
                    logger.info("Loaded config from %s", self._config_path)
            except yaml.YAMLError as e:
                raise ConfigError(
                    f"Invalid YAML in config file: {self._config_path}",
                    details=str(e),
                )
        else:
            logger.info("No config file found at %s, using defaults", self._config_path)

        config = _apply_env_overrides(config)

        # Apply quality tier overrides (tier sets defaults, user overrides win)
        self._apply_tier(config)

        return config

    def _apply_tier(self, config: dict) -> None:
        """Apply quality tier overrides to config.

        Two-step process:
        1. Apply tier base config (whisper model, CRF, etc.)
        2. Apply hardware adaptation (VRAM scaling, CPU fallback, parallel clips)

        User overrides in YAML/env always take precedence.
        """
        from cutclipshort.core.quality_tiers import (
            get_tier, tier_to_config_overrides, adapt_tier_to_hardware,
        )

        tier_name = config.get("quality_tier", "balanced")
        tier = get_tier(tier_name)
        overrides = tier_to_config_overrides(tier)

        # Step 1: Apply tier base overrides
        for section, values in overrides.items():
            if section not in config:
                config[section] = {}
            for key, val in values.items():
                if key not in config[section] or config[section][key] == _DEFAULT_CONFIG.get(section, {}).get(key):
                    config[section][key] = val

        # Step 2: Apply hardware adaptation (VRAM scaling, CPU mode, etc.)
        hw_overrides = adapt_tier_to_hardware(tier)
        if hw_overrides:
            # Map flat overrides to config sections
            hw_section_map = {
                "render_parallel_clips": ("render", "render_parallel_clips"),
                "prefer_gpu": ("render", "prefer_nvenc"),
                "whisper_compute_type": ("analysis", "whisper_compute_type"),
                "whisper_model": ("analysis", "whisper_model"),
                "yolo_sample_every_n": ("analysis", "yolo_sample_every_n"),
            }
            for hw_key, hw_val in hw_overrides.items():
                mapping = hw_section_map.get(hw_key)
                if mapping:
                    section, key = mapping
                    if section not in config:
                        config[section] = {}
                    config[section][key] = hw_val

            logger.info("Hardware adaptation applied: %s", hw_overrides)

        logger.info("Quality tier '%s' applied (%s)", tier.name, tier.display_name)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """Get a config value by section and key."""
        return self._config.get(section, {}).get(key, default)

    def get_section(self, section: str) -> dict[str, Any]:
        """Get an entire config section."""
        return dict(self._config.get(section, {}))

    def set(self, section: str, key: str, value: Any) -> None:
        """Set a config value (in memory only)."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value

    def save(self) -> None:
        """Save current config to YAML file."""
        self._config_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        tmp_path = self._config_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
            os.replace(tmp_path, self._config_path)
            logger.info("Config saved to %s", self._config_path)
        except OSError as e:
            raise ConfigError(
                f"Failed to save config: {e}",
                details=str(e),
            )

    @property
    def quality_tier(self) -> str:
        """Current quality tier name."""
        return self._config.get("quality_tier", "balanced")

    def set_quality_tier(self, tier_name: str) -> None:
        """Switch quality tier and re-apply overrides.

        This updates all tier-controlled keys + hardware adaptation.
        User customizations for non-tier keys are preserved.
        """
        from cutclipshort.core.quality_tiers import (
            get_tier, tier_to_config_overrides, adapt_tier_to_hardware,
        )

        tier = get_tier(tier_name)
        self._config["quality_tier"] = tier.name

        # Force-apply all tier values
        overrides = tier_to_config_overrides(tier)
        for section, values in overrides.items():
            if section not in self._config:
                self._config[section] = {}
            for key, val in values.items():
                self._config[section][key] = val

        # Apply hardware adaptation on top
        hw_overrides = adapt_tier_to_hardware(tier)
        hw_section_map = {
            "render_parallel_clips": ("render", "render_parallel_clips"),
            "prefer_gpu": ("render", "prefer_nvenc"),
            "whisper_compute_type": ("analysis", "whisper_compute_type"),
            "whisper_model": ("analysis", "whisper_model"),
            "yolo_sample_every_n": ("analysis", "yolo_sample_every_n"),
        }
        for hw_key, hw_val in hw_overrides.items():
            mapping = hw_section_map.get(hw_key)
            if mapping:
                section, key = mapping
                if section not in self._config:
                    self._config[section] = {}
                self._config[section][key] = hw_val

        logger.info("Switched to quality tier: %s (hw adapted: %s)",
                     tier.display_name, hw_overrides or "none")

    @property
    def raw(self) -> dict[str, Any]:
        """Access the full config dict (read-only use recommended)."""
        return self._config
