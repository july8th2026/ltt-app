"""Aggregator v2: merges all engine outputs into a unified AnalysisResult.

This is the bridge between analysis engines and the editorial layer.
Rebuilt in-memory from cached per-engine JSON files.

v2 changes:
- Configurable audio window size (was hardcoded 5s)
- Uses v2 visual engine data (presence_ratio, best person across samples)
- Uses v2 audio engine data (rms_db, spectral, loudness_stats)
- VAD-based has_speech detection (replaces naive energy > 0.02 threshold)
- Better person bbox extraction (best confidence across multi-sample)
- has_music detection from spectral data
"""

from __future__ import annotations

import logging
from typing import Any

from cutclipshort.types import (
    AnalysisResult,
    AudioSegment,
    ContentType,
    PersonDetection,
    SceneInfo,
    SourceAsset,
    TimeRange,
    TranscriptSegment,
    TranscriptWord,
    VisualSegment,
)

logger = logging.getLogger(__name__)

_DEFAULT_AUDIO_WINDOW_SEC = 5.0
_SPEECH_ENERGY_THRESHOLD = 0.02  # Fallback if no VAD data
_SPEECH_DB_THRESHOLD = -40.0  # dBFS — above this likely has speech


def load_analysis_from_cache(paths) -> AnalysisResult | None:
    """Rebuild AnalysisResult from cached JSON files on disk.

    Args:
        paths: ProjectPaths instance with resolved cache paths.

    Returns:
        AnalysisResult or None if essential files are missing.
    """
    import json

    # Load source asset
    if not paths.media_info_json.exists():
        logger.warning("media_info.json not found, cannot rebuild analysis")
        return None

    try:
        with open(paths.media_info_json, "r", encoding="utf-8") as f:
            source_data = json.load(f)
        source = SourceAsset(**source_data)
    except Exception as e:
        logger.error("Failed to load media_info.json: %s", e)
        return None

    # Load each engine's cached output
    engine_outputs: dict[str, dict] = {}

    cache_map = {
        "scene": paths.scenes_json,
        "speech": paths.transcript_json,
        "motion": paths.motion_summary_json,
        "visual": paths.visual_detections_json,
        "audio": paths.audio_profile_json,
        "content": paths.content_classification_json,
    }

    for engine_name, cache_path in cache_map.items():
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    engine_outputs[engine_name] = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load %s cache: %s", engine_name, e)
                engine_outputs[engine_name] = {}
        else:
            engine_outputs[engine_name] = {}

    return aggregate_results(source, engine_outputs)


def aggregate_results(
    source: SourceAsset,
    engine_outputs: dict[str, dict[str, Any]],
) -> AnalysisResult:
    """Merge all engine outputs into a unified AnalysisResult."""
    scenes = _parse_scenes(engine_outputs.get("scene", {}))
    transcript = _parse_transcript(engine_outputs.get("speech", {}))
    visual_segments = _build_visual_segments(
        scenes,
        engine_outputs.get("motion", {}),
        engine_outputs.get("visual", {}),
        engine_outputs.get("content", {}),
    )

    audio_data = engine_outputs.get("audio", {})
    audio_window = audio_data.get("window_sec", _DEFAULT_AUDIO_WINDOW_SEC)
    audio_segments = _build_audio_segments(audio_data, transcript, audio_window)

    engine_versions = {
        name: data.get("_engine_version", "unknown")
        for name, data in engine_outputs.items()
    }
    engine_config_hashes = {
        name: data.get("_config_hash", "")
        for name, data in engine_outputs.items()
    }

    # Collect warnings from engines (unavailable adapters, upstream issues)
    analysis_warnings: list[str] = []
    for name, data in engine_outputs.items():
        warning = data.get("warning")
        if warning:
            analysis_warnings.append(f"[{name}] {warning}")
            logger.warning("Engine '%s' warning: %s", name, warning)

    from datetime import datetime, timezone
    result = AnalysisResult(
        source=source,
        scenes=scenes,
        visual_segments=visual_segments,
        audio_segments=audio_segments,
        transcript=transcript,
        engine_versions=engine_versions,
        engine_config_hashes=engine_config_hashes,
        analysis_completed_at=datetime.now(timezone.utc).isoformat(),
    )

    # Attach warnings using object.__setattr__ (AnalysisResult is frozen dataclass)
    if analysis_warnings:
        object.__setattr__(result, 'warnings', analysis_warnings)
        for w in analysis_warnings:
            logger.warning("Analysis warning: %s", w)

    logger.info(
        "Aggregated: %d scenes, %d visual segments, %d audio segments, "
        "%d transcript segments, %d warnings",
        len(scenes), len(visual_segments), len(audio_segments),
        len(transcript), len(analysis_warnings),
    )
    return result


def _parse_scenes(data: dict[str, Any]) -> list[SceneInfo]:
    scenes = []
    motion_summary = data.get("scene_summary", [])
    motion_by_id = (
        {m.get("scene_id"): m for m in motion_summary}
        if isinstance(motion_summary, list)
        else {}
    )

    for s in data.get("scenes", []):
        sid = s["id"]
        motion_info = motion_by_id.get(sid, {})
        scenes.append(SceneInfo(
            id=sid,
            time_range=TimeRange(start=s["start_time"], end=s["end_time"]),
            motion_avg=motion_info.get("motion_avg", 0.0),
            motion_max=motion_info.get("motion_max", 0.0),
        ))
    return scenes


def _parse_transcript(data: dict[str, Any]) -> list[TranscriptSegment]:
    segments = []
    for i, seg in enumerate(data.get("segments", [])):
        # Validate required fields
        if "start" not in seg or "end" not in seg or "text" not in seg:
            logger.warning("Transcript segment %d missing required fields, skipping", i)
            continue

        words = [
            TranscriptWord(
                word=w.get("word", ""), start=w.get("start", 0.0),
                end=w.get("end", 0.0), confidence=w.get("confidence", 0.0),
            )
            for w in seg.get("words", [])
            if "word" in w
        ]
        segments.append(TranscriptSegment(
            id=int(seg.get("id", i)),
            start=float(seg["start"]),
            end=float(seg["end"]),
            text=str(seg["text"]),
            words=words,
            speaker=seg.get("speaker"),
            language=data.get("language", "en"),
        ))
    return segments


def _build_visual_segments(
    scenes: list[SceneInfo],
    motion_data: dict[str, Any],
    visual_data: dict[str, Any],
    content_data: dict[str, Any],
) -> list[VisualSegment]:
    """Build enriched visual segments from multiple engine outputs.

    v2: Uses presence_ratio and best-confidence person from multi-sample data.
    """
    detections_by_scene: dict[int, list] = {}
    for det in visual_data.get("detections", []):
        sid = det.get("scene_id")
        if sid is not None:
            detections_by_scene.setdefault(sid, []).append(det)

    content_by_scene: dict[int, dict] = {}
    for cls in content_data.get("classifications", []):
        content_by_scene[cls.get("scene_id")] = cls

    segments = []
    for i, scene in enumerate(scenes):
        det_list = detections_by_scene.get(scene.id, [])
        content_info = content_by_scene.get(scene.id, {})

        # v2: Use presence_ratio if available, fall back to binary check
        presence_ratio = 0.0
        has_person = False
        max_persons = 0

        # [Phase4] Aggregate across ALL detection entries per scene (v2 multi-sample)
        if det_list:
            # Aggregate presence_ratio: use max across all entries
            all_presence = [d.get("presence_ratio", 0.0) for d in det_list]
            presence_ratio = max(all_presence) if all_presence else 0.0

            # Aggregate person count: use max avg across entries
            all_avg_count = [d.get("avg_person_count", 0) for d in det_list]
            all_person_lists = [d.get("persons", []) for d in det_list]
            max_persons = max(
                max(all_avg_count) if all_avg_count else 0,
                max(len(pl) for pl in all_person_lists) if all_person_lists else 0,
            )

            has_person = presence_ratio > 0.3 or any(
                bool(d.get("persons")) for d in det_list
            )

            # Fallback for v1 data without presence_ratio
            if all(("presence_ratio" not in d) for d in det_list):
                if any(d.get("persons") for d in det_list):
                    has_person = True
                    presence_ratio = 1.0

        # Parse best person bbox — aggregate across ALL entries
        person_start = None
        person_end = None
        if det_list:
            all_persons = []
            for d in det_list:
                all_persons.extend(d.get("persons", []))
            if all_persons:
                # Pick highest confidence person across all samples
                best = max(all_persons, key=lambda p: p.get("confidence", 0))
                person_start = PersonDetection(
                    x=best["x"], y=best["y"],
                    w=best["w"], h=best["h"],
                    confidence=best["confidence"],
                )
                person_end = person_start

        ct_str = content_info.get("content_type", "unknown")
        try:
            ct = ContentType(ct_str)
        except ValueError:
            ct = ContentType.UNKNOWN

        segments.append(VisualSegment(
            id=i,
            time_range=scene.time_range,
            scene_id=scene.id,
            content_type=ct,
            content_type_confidence=content_info.get("confidence", 0.0),
            motion_avg=scene.motion_avg,
            motion_max=scene.motion_max,
            has_person=has_person,
            person_count_max=max_persons,
            person_bbox_start=person_start,
            person_bbox_end=person_end,
            is_static=scene.motion_avg < 2.0,
        ))

    return segments


def _build_audio_segments(
    data: dict[str, Any],
    transcript: list[TranscriptSegment],
    window_sec: float,
) -> list[AudioSegment]:
    """Build audio segments from audio engine output.

    v2: Uses rms_db for speech detection, spectral data for music detection,
    and cross-references transcript for speech verification.
    """
    energy_curve = data.get("energy_curve", [])
    silence_ranges = data.get("silence_ranges", [])
    spectral_curve = data.get("spectral_curve", [])
    loudness_stats = data.get("loudness_stats", {})

    if not energy_curve:
        return []

    # Build spectral lookup
    spectral_by_time: dict[float, dict] = {
        s["time_sec"]: s for s in spectral_curve
    }

    # Adaptive speech threshold based on noise floor
    noise_floor = loudness_stats.get("noise_floor", _SPEECH_ENERGY_THRESHOLD)
    speech_energy_min = max(_SPEECH_ENERGY_THRESHOLD, noise_floor * 3.0)

    # Group energy points into configurable windows
    segments = []
    i = 0
    seg_id = 0

    # Determine video duration for window clamping
    video_duration = energy_curve[-1]["time_sec"] + window_sec if energy_curve else 0.0

    while i < len(energy_curve):
        start_time = energy_curve[i]["time_sec"]
        end_time = min(start_time + window_sec, video_duration)  # Clamp to video end
        window_points_energy: list[float] = []
        window_points_db: list[float] = []
        window_voice_count = 0
        window_total_spectral = 0

        while i < len(energy_curve) and energy_curve[i]["time_sec"] < end_time:
            pt = energy_curve[i]
            window_points_energy.append(pt["energy"])
            window_points_db.append(pt.get("rms_db", -96.0))

            # Check spectral data
            spec = spectral_by_time.get(pt["time_sec"])
            if spec is not None:
                window_total_spectral += 1
                if spec.get("is_voice_band", False):
                    window_voice_count += 1

            i += 1

        if not window_points_energy:
            break

        avg_energy = sum(window_points_energy) / len(window_points_energy)
        max_energy = max(window_points_energy)
        avg_db = sum(window_points_db) / len(window_points_db)

        # Silence detection
        silence_in_window = sum(
            min(s["end"], end_time) - max(s["start"], start_time)
            for s in silence_ranges
            if s["start"] < end_time and s["end"] > start_time
        )
        silence_ratio = min(1.0, silence_in_window / window_sec)

        # Speech detection: multi-signal
        # 1. Energy above adaptive threshold
        energy_speech = avg_energy > speech_energy_min
        # 2. dB above speech floor
        db_speech = avg_db > _SPEECH_DB_THRESHOLD
        # 3. Transcript overlap (most reliable)
        transcript_speech = any(
            seg.start < end_time and seg.end > start_time
            for seg in transcript
        )
        # 4. Voice band ratio from spectral
        voice_ratio = (
            window_voice_count / window_total_spectral
            if window_total_spectral > 0
            else 0.5
        )

        # Combine: transcript is ground truth, others are supporting signals
        has_speech = transcript_speech or (energy_speech and db_speech and voice_ratio > 0.3)

        # Music detection: audio energy but NOT voice band and no speech
        has_music = (
            avg_energy > speech_energy_min
            and voice_ratio < 0.3
            and not transcript_speech
        )

        segments.append(AudioSegment(
            id=seg_id,
            time_range=TimeRange(start=start_time, end=end_time),
            energy_avg=round(avg_energy, 4),
            energy_max=round(max_energy, 4),
            has_speech=has_speech,
            has_silence=silence_ratio > 0.3,
            silence_ratio=round(silence_ratio, 3),
            has_music=has_music,
        ))
        seg_id += 1

    return segments
