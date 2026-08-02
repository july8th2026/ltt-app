"""Content classification engine v2.

Classifies each scene into content types based on combined signals
from scene, motion, speech, visual, and audio engines.

v2 changes:
- Config-driven thresholds (not hardcoded)
- Multi-signal weighted scoring replaces if-else chain
- Temporal smoothing: isolated misclassifications corrected by neighbors
- Audio spectral data used for music/voice discrimination
- Confidence scoring based on signal agreement (not arbitrary constants)
- SCREEN_SHARE detection via low motion + speech + no person
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from cutclipshort.analysis.base import BaseAnalysisEngine
from cutclipshort.types import ContentType, SourceAsset

logger = logging.getLogger(__name__)

# ── Default thresholds (overridable via config) ──────────────────────
_DEFAULTS = {
    "silence_motion_max": 2.0,
    "talking_head_motion_max": 20.0,
    "action_motion_min": 25.0,
    "broll_motion_max": 10.0,
    "temporal_smoothing_window": 3,  # scenes to consider for smoothing
    "min_confidence_for_override": 0.6,
}


class ContentEngine(BaseAnalysisEngine):
    """Weighted multi-signal content type classifier with temporal smoothing.

    Combines signals from other engines to classify each scene.
    Uses weighted scoring per content type instead of first-match rules.
    Applies temporal smoothing to prevent isolated misclassifications.
    """

    @property
    def name(self) -> str:
        return "content"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def depends_on(self) -> list[str]:
        return ["scene", "motion", "speech", "visual", "audio"]

    def _relevant_config_keys(self, config: dict[str, Any]) -> dict[str, Any]:
        return {
            k: config.get(k, v) for k, v in _DEFAULTS.items()
        }

    def run(
        self,
        source: Path,
        media_info: SourceAsset,
        config: dict[str, Any],
        cache_dir: Path,
        progress_callback: Callable[[float], None],
    ) -> dict[str, Any]:
        cached = self.load_cached(cache_dir)
        if cached is not None:
            return cached

        progress_callback(0.0)

        # Load dependency outputs + validate upstream health
        scenes = self._load_json(cache_dir / "scene.json").get("scenes", [])
        motion_data = self._load_json(cache_dir / "motion.json")
        motion_summary = motion_data.get("scene_summary", [])
        transcript = self._load_json(cache_dir / "speech.json")
        segments = transcript.get("segments", [])
        visual_data = self._load_json(cache_dir / "visual.json")
        detections = visual_data.get("detections", [])
        audio_data = self._load_json(cache_dir / "audio.json")
        spectral_curve = audio_data.get("spectral_curve", [])

        # Validate upstream data — log warnings for missing/failed stages
        upstream_warnings: list[str] = []
        if not scenes:
            upstream_warnings.append("scene detection returned 0 scenes")
            logger.warning("Content classification: no scenes available — results may be inaccurate")
        if not segments and transcript.get("status") == "unavailable":
            upstream_warnings.append("speech-to-text unavailable (no Whisper)")
            logger.warning("Content classification: speech data unavailable — speech-based signals disabled")
        if not detections and visual_data.get("warning"):
            upstream_warnings.append("visual detection unavailable (no YOLO)")
            logger.warning("Content classification: visual data unavailable — person detection disabled")
        if not motion_summary:
            upstream_warnings.append("motion analysis returned no data")
        self._upstream_warnings = upstream_warnings

        # Merge thresholds: config overrides defaults
        thresholds = {k: config.get(k, v) for k, v in _DEFAULTS.items()}

        # Build lookup maps
        motion_by_scene: dict[int, float] = {
            m["scene_id"]: m["motion_avg"] for m in motion_summary
        }
        person_by_scene: dict[int, bool] = {
            d["scene_id"]: len(d.get("persons", [])) > 0 for d in detections
        }
        person_count_by_scene: dict[int, int] = {
            d["scene_id"]: len(d.get("persons", [])) for d in detections
        }

        # Build spectral lookup (time → is_voice_band)
        voice_by_time: dict[float, bool] = {
            s["time_sec"]: s.get("is_voice_band", False)
            for s in spectral_curve
        }

        # Build audio energy lookup (time → energy)
        energy_curve = audio_data.get("energy_curve", [])
        energy_by_time: dict[float, float] = {
            e["time_sec"]: e.get("energy", 0.0) for e in energy_curve
        }

        # ── Phase 1: Score each scene against all content types ──────
        raw_classifications: list[dict[str, Any]] = []
        for i, scene in enumerate(scenes):
            sid = scene["id"]
            start = scene["start_time"]
            end = scene["end_time"]

            motion_avg = motion_by_scene.get(sid, 0.0)
            has_person = person_by_scene.get(sid, False)
            person_count = person_count_by_scene.get(sid, 0)

            # Speech overlap: compute ratio, not just boolean
            speech_sec = sum(
                min(seg["end"], end) - max(seg["start"], start)
                for seg in segments
                if seg["start"] < end and seg["end"] > start
            )
            scene_duration = max(0.1, end - start)
            speech_ratio = min(1.0, speech_sec / scene_duration)
            has_speech = speech_ratio > 0.1

            # Voice band ratio from spectral data
            voice_band_ratio = _voice_band_ratio(start, end, voice_by_time)

            # Audio energy for this scene
            scene_energy = _avg_energy_in_range(start, end, energy_by_time)

            # Score all content types
            scores = _score_all_types(
                has_speech=has_speech,
                speech_ratio=speech_ratio,
                has_person=has_person,
                person_count=person_count,
                motion_avg=motion_avg,
                voice_band_ratio=voice_band_ratio,
                audio_energy=scene_energy,
                thresholds=thresholds,
            )

            # Best type = highest score
            best_type = max(scores, key=scores.get)
            best_score = scores[best_type]

            # Confidence = margin between best and second-best
            sorted_scores = sorted(scores.values(), reverse=True)
            margin = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 1.0
            confidence = min(1.0, best_score * (0.5 + margin * 0.5))

            raw_classifications.append({
                "scene_id": sid,
                "content_type": best_type,
                "confidence": round(confidence, 3),
                "scores": {k: round(v, 3) for k, v in scores.items()},
                "signals": {
                    "has_speech": has_speech,
                    "speech_ratio": round(speech_ratio, 3),
                    "has_person": has_person,
                    "person_count": person_count,
                    "motion_avg": round(motion_avg, 2),
                    "voice_band_ratio": round(voice_band_ratio, 3),
                },
            })

            progress_callback(min(0.70, (i + 1) / max(1, len(scenes))))

        # ── Phase 2: Temporal smoothing ──────────────────────────────
        smoothing_window = thresholds.get("temporal_smoothing_window", 3)
        min_confidence = thresholds.get("min_confidence_for_override", 0.6)

        classifications = _apply_temporal_smoothing(
            raw_classifications, smoothing_window, min_confidence,
        )

        progress_callback(0.90)

        result: dict[str, Any] = {"classifications": classifications}
        if hasattr(self, '_upstream_warnings') and self._upstream_warnings:
            result["upstream_warnings"] = self._upstream_warnings
            result["warning"] = (
                "Phân loại nội dung có thể thiếu chính xác do: "
                + "; ".join(self._upstream_warnings)
            )
        self._save_cache(cache_dir, result)
        progress_callback(1.0)

        type_counts: dict[str, int] = {}
        for c in classifications:
            t = c["content_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
        logger.info("Content classification: %s", type_counts)
        return result

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("Thiếu file upstream: %s — bỏ qua", path.name)
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.warning("File JSON bị hỏng: %s — %s", path.name, e)
            return {}
        except OSError as e:
            logger.warning("Không thể đọc file: %s — %s", path.name, e)
            return {}


# ══════════════════════════════════════════════════════════════════════════
# PURE SCORING FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def _score_all_types(
    *,
    has_speech: bool,
    speech_ratio: float,
    has_person: bool,
    person_count: int,
    motion_avg: float,
    voice_band_ratio: float,
    audio_energy: float = 0.0,
    thresholds: dict[str, Any],
) -> dict[str, float]:
    """Score a scene against all content types. Returns {type_name: score}.

    Args:
        audio_energy: Average audio energy (0.0-1.0) for this scene.
                      Used to distinguish silence (no energy) from music (energy, no voice).
    """
    silence_max = thresholds["silence_motion_max"]
    th_motion_max = thresholds["talking_head_motion_max"]
    action_min = thresholds["action_motion_min"]
    broll_max = thresholds["broll_motion_max"]

    scores: dict[str, float] = {}

    # SILENCE: no speech, very low motion, LOW audio energy
    s_speech = 1.0 - speech_ratio  # less speech = more silence-like
    s_motion = max(0.0, 1.0 - motion_avg / max(1.0, silence_max * 2))
    s_person = 0.7 if not has_person else 0.2
    s_energy = max(0.0, 1.0 - audio_energy * 10)  # Low energy → high silence score
    scores[ContentType.SILENCE.value] = (
        s_speech * 0.35 + s_motion * 0.25 + s_person * 0.10 + s_energy * 0.30
    )

    # TALKING_HEAD: speech + person + low-moderate motion
    th_speech = speech_ratio
    th_person = 0.9 if has_person else 0.1
    th_motion = max(0.0, 1.0 - max(0.0, motion_avg - 5.0) / th_motion_max)
    th_voice = voice_band_ratio
    scores[ContentType.TALKING_HEAD.value] = (
        th_speech * 0.30 + th_person * 0.30 + th_motion * 0.20 + th_voice * 0.20
    )

    # B_ROLL: speech without person, or low motion without speech
    br_speech_no_person = speech_ratio * (0.8 if not has_person else 0.2)
    br_low_motion = max(0.0, 1.0 - motion_avg / max(1.0, broll_max * 2))
    br_no_speech = 1.0 - speech_ratio
    scores[ContentType.B_ROLL.value] = (
        br_speech_no_person * 0.4 + br_low_motion * 0.3 + br_no_speech * 0.3
    )

    # ACTION: high motion, minimal speech
    a_motion = max(0.0, min(1.0, (motion_avg - action_min * 0.5) / action_min))
    a_no_speech = max(0.0, 1.0 - speech_ratio * 2)
    scores[ContentType.ACTION.value] = a_motion * 0.6 + a_no_speech * 0.4

    # SCREEN_SHARE: low motion + speech + no person (typical tutorial/screen recording)
    ss_low_motion = max(0.0, 1.0 - motion_avg / 5.0)
    ss_speech = speech_ratio
    ss_no_person = 0.9 if not has_person else 0.1
    scores[ContentType.SCREEN_SHARE.value] = (
        ss_low_motion * 0.35 + ss_speech * 0.35 + ss_no_person * 0.30
    )

    # MUSIC: no speech, HAS audio energy, non-voice spectral, LOW motion
    m_no_speech = max(0.0, 1.0 - speech_ratio * 3)
    m_not_voice = max(0.0, 1.0 - voice_band_ratio)
    m_has_audio = min(1.0, audio_energy * 5)  # Must have actual audio energy
    m_low_motion = max(0.0, 1.0 - motion_avg / 15.0)  # Music → typically low motion
    scores[ContentType.MUSIC.value] = (
        m_no_speech * 0.30 + m_not_voice * 0.25 + m_has_audio * 0.25 + m_low_motion * 0.20
    )

    # UNKNOWN: low baseline (only wins if nothing else matches)
    scores[ContentType.UNKNOWN.value] = 0.15

    return scores


def _avg_energy_in_range(
    start: float, end: float, energy_by_time: dict[float, float],
) -> float:
    """Average audio energy within a time range."""
    if not energy_by_time:
        return 0.0
    in_range = [
        energy for t, energy in energy_by_time.items()
        if start <= t <= end
    ]
    if not in_range:
        return 0.0
    return sum(in_range) / len(in_range)


def _voice_band_ratio(
    start: float, end: float, voice_by_time: dict[float, bool],
) -> float:
    """Fraction of spectral windows in this scene that are voice-band."""
    if not voice_by_time:
        return 0.5  # No spectral data → neutral

    in_range = [
        is_voice for t, is_voice in voice_by_time.items()
        if start <= t <= end
    ]
    if not in_range:
        return 0.5

    return sum(1 for v in in_range if v) / len(in_range)


def _apply_temporal_smoothing(
    classifications: list[dict[str, Any]],
    window: int,
    min_confidence: float,
) -> list[dict[str, Any]]:
    """Smooth isolated misclassifications using neighbor consensus.

    If a scene's type differs from both its neighbors and confidence is low,
    adopt the neighbor consensus type.
    """
    if len(classifications) <= 2 or window < 1:
        return classifications

    smoothed = []
    n = len(classifications)

    for i, cls in enumerate(classifications):
        # High-confidence classifications are kept as-is
        if cls["confidence"] >= min_confidence:
            smoothed.append(cls)
            continue

        # Collect neighbor types within window
        neighbor_types: list[str] = []
        for j in range(max(0, i - window), min(n, i + window + 1)):
            if j != i:
                neighbor_types.append(classifications[j]["content_type"])

        if not neighbor_types:
            smoothed.append(cls)
            continue

        # Find consensus type among neighbors
        type_counts: dict[str, int] = {}
        for t in neighbor_types:
            type_counts[t] = type_counts.get(t, 0) + 1

        consensus_type = max(type_counts, key=type_counts.get)
        consensus_ratio = type_counts[consensus_type] / len(neighbor_types)

        current_type = cls["content_type"]

        # Override only if: current differs from consensus AND consensus is strong
        if current_type != consensus_type and consensus_ratio >= 0.6:
            updated = dict(cls)
            updated["content_type"] = consensus_type
            updated["confidence"] = round(cls["confidence"] * 0.8, 3)  # Slightly reduce confidence
            updated["smoothed_from"] = current_type
            smoothed.append(updated)
            logger.debug(
                "Temporal smoothing: scene %d %s → %s (consensus=%.0f%%)",
                cls["scene_id"], current_type, consensus_type, consensus_ratio * 100,
            )
        else:
            smoothed.append(cls)

    return smoothed
