"""JSON artifact schema documentation and serialization helpers.

This module documents the exact JSON format for every artifact file.
It also provides serialize/deserialize functions for complex types.

═══════════════════════════════════════════════════════════════════════
ARTIFACT MAP — Which model lives in which file
═══════════════════════════════════════════════════════════════════════

  FILE                                    MODEL                  MUTABILITY
  ─────────────────────────────────────── ────────────────────── ──────────
  project.json                            Project                Mutable
  source/media_info.json                  SourceAsset            Immutable
  cache/analysis_manifest.json            (engine tracking)      Append-only
  cache/scenes.json                       list[SceneInfo]        Immutable*
  cache/transcript.json                   list[TranscriptSeg]    Immutable*
  cache/visual_segments.json              list[VisualSegment]    Immutable*
  cache/audio_profile.json                list[AudioSegment]     Immutable*
  cache/motion.csv                        (time,score) pairs     Immutable*
  candidates/index.json                   (summary list)         Regenerated
  candidates/{id}/candidate.json          CandidateClip          Immutable
  candidates/{id}/score.json              ClipScore              Append (versions)
  candidates/{id}/quality_report.json     QualityReport          Append (versions)
  candidates/{id}/renders/{vid}.json      RenderVariant          Mutable (status)
  plans/plan_v{NNN}.json                  EditPlan               Immutable (versioned)
  plans/plan_current.json                 EditPlan               Replaced on save
  renders/job_{uuid}.json                 RenderJob              Mutable (status)
  exports/manifest_{ts}.json              ExportManifest         Immutable

  * "Immutable" = once written by analysis, not changed.
    Re-running analysis with different config = overwrite.

═══════════════════════════════════════════════════════════════════════
RE-RENDER WITHOUT RE-ANALYZE — How it works in the schema
═══════════════════════════════════════════════════════════════════════

  1. Analysis writes cache/*.json files. These are keyed by
     (source_hash, engine_version, config_hash) in analysis_manifest.json.

  2. Editorial reads cache → generates candidates/ and plans/.
     The EditPlan contains self-contained ClipSpec objects.

  3. ClipSpec carries a render_hash = deterministic hash of all
     render-affecting fields (source_range, speed, color, framing,
     audio, captions, resolution).

  4. When user edits a clip (trim, speed, color change):
     - EditPlan.version increments, new plan_v{N}.json written
     - Only the changed ClipSpec gets a new render_hash
     - Render engine compares render_hash against existing
       RenderVariant files in candidates/{id}/renders/
     - Only clips with changed render_hash get re-rendered
     - Analysis cache is NEVER consulted by render

  5. When user changes genre/strategy:
     - Pipeline re-runs editorial (reads existing cache/)
     - New candidates generated (may overlap with old ones)
     - New EditPlan generated
     - All analysis cache reused — zero re-analysis cost

═══════════════════════════════════════════════════════════════════════
MULTI-VERSION SUPPORT — How render variants work
═══════════════════════════════════════════════════════════════════════

  Each candidate can have multiple rendered outputs:

  candidates/c001/renders/
  ├── preview_v001.json    # Auto-generated preview (480p)
  ├── preview_v001.mp4
  ├── preview_v002.json    # Re-preview after user trim
  ├── preview_v002.mp4
  ├── final_9x16_v001.json # Final TikTok export
  ├── final_9x16_v001.mp4
  ├── final_1x1_v001.json  # Final Instagram square export
  └── final_1x1_v001.mp4

  variant_id naming: {type}_{aspect}_{version}
    preview_v001, preview_v002
    final_9x16_v001, final_1x1_v001, final_16x9_v001

  Each .json sidecar tracks: status, spec hash, timing, file info.
  The latest variant for each type+aspect is the "active" one.

═══════════════════════════════════════════════════════════════════════
MULTI-ASPECT-RATIO SUPPORT — How framing_variants work
═══════════════════════════════════════════════════════════════════════

  ClipSpec.primary_aspect_ratio = the main output (e.g. 9:16)
  ClipSpec.primary_framing = FramingParams for that ratio

  ClipSpec.framing_variants = {
    "1:1":  FramingParams for square crop,
    "16:9": FramingParams for landscape (may be identity/no-crop),
  }

  At render time:
  - Primary always rendered
  - Variants rendered if user selected multi-export
  - Same analysis, same plan, different FramingParams per ratio
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════════
# JSON SCHEMA EXAMPLES
# ═══════════════════════════════════════════════════════════════════════

PROJECT_JSON_EXAMPLE = """\
{
  "schema_version": 2,
  "project_id": "proj_a1b2c3d4",
  "name": "Marketing Podcast Ep42",
  "source": {
    "original_path": "D:/Videos/podcast_ep42.mp4",
    "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015...",
    "file_name": "podcast_ep42.mp4",
    "file_size_bytes": 524288000,
    "duration_sec": 3847.5,
    "width": 1920,
    "height": 1080,
    "fps": 30.0,
    "video_codec": "h264",
    "pixel_format": "yuv420p",
    "bitrate_kbps": 8000,
    "audio_codec": "aac",
    "audio_sample_rate": 48000,
    "audio_channels": 2,
    "audio_bitrate_kbps": 192
  },
  "genre": "podcast",
  "strategy_name": "podcast",
  "state": "awaiting_review",
  "state_message": "5 clips ready for review",
  "state_progress": 1.0,
  "analysis_engines": {
    "scene": "done",
    "motion": "done",
    "speech": "done",
    "audio": "done",
    "visual": "done",
    "content": "done"
  },
  "candidate_count": 8,
  "candidates_generation": 1,
  "current_plan_version": 2,
  "total_plan_versions": 2,
  "export_count": 0,
  "last_export_at": "",
  "export_manifest_ids": [],
  "created_at": "2026-03-23T10:30:00+07:00",
  "modified_at": "2026-03-23T10:45:22+07:00",
  "last_opened_at": "2026-03-23T10:45:22+07:00",
  "last_error": "",
  "last_error_detail": ""
}
"""

SOURCE_ASSET_JSON_EXAMPLE = """\
{
  "original_path": "D:/Videos/podcast_ep42.mp4",
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "file_name": "podcast_ep42.mp4",
  "file_size_bytes": 524288000,
  "duration_sec": 3847.5,
  "width": 1920,
  "height": 1080,
  "fps": 30.0,
  "video_codec": "h264",
  "pixel_format": "yuv420p",
  "bitrate_kbps": 8000,
  "audio_codec": "aac",
  "audio_sample_rate": 48000,
  "audio_channels": 2,
  "audio_bitrate_kbps": 192
}
"""

CANDIDATE_JSON_EXAMPLE = """\
{
  "candidate_id": "c001",
  "time_range": {
    "start": 245.3,
    "end": 289.7
  },
  "score": {
    "overall": 0.82,
    "hook_strength": 0.91,
    "pacing": 0.78,
    "completeness": 0.85,
    "visual_quality": 0.80,
    "audio_quality": 0.76,
    "topic_coherence": 0.0
  },
  "content_type": "talking_head",
  "genre_fit": 0.88,
  "motion_avg": 14.2,
  "has_speech": true,
  "speech_text_preview": "The biggest mistake people make when starting a business is they don't validate their idea first...",
  "transcript_segment_ids": [42, 43, 44, 45],
  "has_person": true,
  "person_count": 1,
  "dominant_person_bbox": {
    "x": 620.0,
    "y": 120.0,
    "w": 680.0,
    "h": 840.0,
    "confidence": 0.94
  },
  "tags": ["key_insight", "high_energy", "actionable_advice"],
  "hook_text": "The biggest mistake people make when starting a business",
  "suggested_hook_type": "statement",
  "strategy_name": "podcast",
  "strategy_reasoning": "High speech energy (0.91) at sentence start, complete topic segment about business validation, strong closing pause at 289.7s"
}
"""

SCORE_JSON_EXAMPLE = """\
{
  "candidate_id": "c001",
  "render_variant_id": "final_9x16_v001",
  "composite_score": 78.5,
  "metrics": [
    {
      "evaluator_name": "pacing",
      "score": 0.82,
      "weight": 0.20,
      "passed": true,
      "diagnostics": {
        "avg_segment_duration_sec": 4.2,
        "variance": 1.8,
        "speed_consistency": 0.95
      }
    },
    {
      "evaluator_name": "audio_loudness",
      "score": 0.90,
      "weight": 0.20,
      "passed": true,
      "diagnostics": {
        "measured_lufs": -14.2,
        "target_lufs": -14.0,
        "true_peak_db": -1.8,
        "clipping_detected": false,
        "silence_ratio": 0.03
      }
    },
    {
      "evaluator_name": "visual_quality",
      "score": 0.75,
      "weight": 0.15,
      "passed": true,
      "diagnostics": {
        "black_frame_count": 0,
        "blur_score_avg": 0.12,
        "aspect_ratio_correct": true,
        "resolution": "1080x1920"
      }
    },
    {
      "evaluator_name": "content_completeness",
      "score": 0.68,
      "weight": 0.25,
      "passed": true,
      "diagnostics": {
        "starts_mid_sentence": false,
        "ends_mid_sentence": false,
        "has_natural_pause_at_end": true,
        "hook_present_in_first_3s": true,
        "idea_closure_detected": true
      }
    },
    {
      "evaluator_name": "completion",
      "score": 0.72,
      "weight": 0.20,
      "passed": true,
      "diagnostics": {
        "duration_within_bounds": true,
        "actual_duration_sec": 44.4,
        "target_min_sec": 15.0,
        "target_max_sec": 60.0
      }
    }
  ],
  "gate_passed": true,
  "evaluated_at": "2026-03-23T10:48:15+07:00"
}
"""

EDIT_PLAN_JSON_EXAMPLE = """\
{
  "plan_id": "plan_f8a2b1c3",
  "version": 2,
  "strategy_name": "podcast",
  "genre": "podcast",
  "constraints": {
    "min_clip_duration_sec": 20.0,
    "max_clip_duration_sec": 60.0,
    "target_clip_count": 5,
    "max_clip_count": 20,
    "platform": "tiktok",
    "aspect_ratio": "9:16",
    "target_width": 1080,
    "target_height": 1920,
    "additional_aspect_ratios": ["1:1"]
  },
  "clips": [
    {
      "clip_id": "c001",
      "source_range": {"start": 245.3, "end": 289.7},
      "speed_factor": 1.0,
      "color_preset_name": "original",
      "color_config": {
        "film_enabled": false,
        "eq_contrast": 1.0,
        "eq_saturation": 1.0,
        "eq_brightness": 0.0,
        "unsharp_luma": 0.0
      },
      "primary_aspect_ratio": "9:16",
      "primary_framing": {
        "cx_start": 960.0,
        "cy_start": 540.0,
        "cx_end": 960.0,
        "cy_end": 540.0,
        "zoom_start": 1.3,
        "zoom_end": 1.3,
        "smooth_alpha": 0.07,
        "max_pan_px_per_sec": 900.0,
        "person_target_fraction": 0.70
      },
      "framing_variants": {
        "1:1": {
          "cx_start": 960.0,
          "cy_start": 540.0,
          "cx_end": 960.0,
          "cy_end": 540.0,
          "zoom_start": 1.0,
          "zoom_end": 1.0,
          "smooth_alpha": 0.07,
          "max_pan_px_per_sec": 900.0,
          "person_target_fraction": 0.70
        }
      },
      "target_width": 1080,
      "target_height": 1920,
      "audio_config": {
        "demucs_enabled": false,
        "demucs_model": "htdemucs",
        "stem_gains": {"vocals": 1.0, "drums": 0.7, "bass": 0.0, "other": 0.0},
        "loudnorm_enabled": true,
        "loudnorm_lufs": -14.0,
        "loudnorm_true_peak_db": -1.5,
        "sfx_path": null,
        "sfx_gain_db": -6.0,
        "sfx_position": "start"
      },
      "caption_enabled": true,
      "caption_style": {
        "preset_name": "minimal",
        "font_family": "Inter",
        "font_size": 48,
        "font_color": "#FFFFFF",
        "active_word_color": "#FFDD00",
        "outline_color": "#000000",
        "outline_width": 2,
        "shadow_enabled": true,
        "shadow_color": "#00000080",
        "bg_box_enabled": false,
        "bg_box_color": "#00000099",
        "position": "bottom",
        "animation": "word_highlight",
        "max_chars_per_line": 35
      },
      "caption_segments": [
        {
          "id": 42,
          "start": 245.3,
          "end": 249.1,
          "text": "The biggest mistake people make when starting a business",
          "words": [
            {"word": "The", "start": 245.3, "end": 245.5, "confidence": 0.98},
            {"word": "biggest", "start": 245.5, "end": 245.9, "confidence": 0.97},
            {"word": "mistake", "start": 245.9, "end": 246.4, "confidence": 0.99}
          ],
          "speaker": "SPEAKER_00",
          "language": "en"
        }
      ],
      "render_hash": "a3f2c1d8b7e6f504"
    }
  ],
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015...",
  "analysis_versions": {
    "scene": "1.0.0",
    "speech": "1.2.0",
    "motion": "1.0.0"
  },
  "color_preset_name": "original",
  "caption_preset_name": "minimal",
  "user_modified_clip_ids": ["c003"],
  "created_at": "2026-03-23T10:42:00+07:00",
  "modified_at": "2026-03-23T10:44:30+07:00",
  "metadata": {
    "total_candidates_considered": 8,
    "auto_selected": 5
  }
}
"""

QUALITY_REPORT_JSON_EXAMPLE = """\
{
  "candidate_id": "c001",
  "render_variant_id": "final_9x16_v001",
  "clip_score": {
    "candidate_id": "c001",
    "render_variant_id": "final_9x16_v001",
    "composite_score": 78.5,
    "metrics": [
      {"evaluator_name": "pacing", "score": 0.82, "weight": 0.20, "passed": true, "diagnostics": {}},
      {"evaluator_name": "audio_loudness", "score": 0.90, "weight": 0.20, "passed": true, "diagnostics": {}},
      {"evaluator_name": "visual_quality", "score": 0.75, "weight": 0.15, "passed": true, "diagnostics": {}},
      {"evaluator_name": "content_completeness", "score": 0.68, "weight": 0.25, "passed": true, "diagnostics": {}},
      {"evaluator_name": "completion", "score": 0.72, "weight": 0.20, "passed": true, "diagnostics": {}}
    ],
    "gate_passed": true,
    "evaluated_at": "2026-03-23T10:48:15+07:00"
  },
  "issues": [],
  "suggestions": [
    "Consider extending end by 0.3s for a more natural pause"
  ],
  "output_duration_sec": 44.4,
  "output_file_size_bytes": 18500000,
  "output_resolution": "1080x1920",
  "output_fps": 30.0,
  "output_bitrate_kbps": 3200,
  "reported_at": "2026-03-23T10:48:16+07:00"
}
"""

RENDER_VARIANT_JSON_EXAMPLE = """\
{
  "variant_id": "preview_v002",
  "variant_type": "preview",
  "aspect_ratio": "9:16",
  "status": "completed",
  "clip_spec_hash": "a3f2c1d8b7e6f504",
  "plan_version": 2,
  "output_path": "candidates/c001/renders/preview_v002.mp4",
  "thumbnail_path": "candidates/c001/thumbnails/hook_frame.jpg",
  "file_size_bytes": 2400000,
  "duration_sec": 44.4,
  "resolution": "480x854",
  "encoder": "libx264",
  "crf": "28",
  "preset": "veryfast",
  "queued_at": "2026-03-23T10:44:31+07:00",
  "started_at": "2026-03-23T10:44:31+07:00",
  "completed_at": "2026-03-23T10:44:35+07:00",
  "elapsed_sec": 3.8,
  "error_message": "",
  "error_detail": "",
  "retry_count": 0
}
"""

RENDER_JOB_JSON_EXAMPLE = """\
{
  "job_id": "rj_e5f6a7b8",
  "job_type": "final",
  "plan_version": 2,
  "status": "completed",
  "total_clips": 5,
  "completed_clips": 5,
  "failed_clips": 0,
  "clip_variant_ids": [
    "final_9x16_v001",
    "final_9x16_v001",
    "final_9x16_v001",
    "final_9x16_v001",
    "final_9x16_v001"
  ],
  "export_profile_name": "tiktok",
  "target_aspect_ratio": "9:16",
  "created_at": "2026-03-23T10:46:00+07:00",
  "started_at": "2026-03-23T10:46:01+07:00",
  "completed_at": "2026-03-23T10:49:30+07:00",
  "total_elapsed_sec": 209.0,
  "error_message": ""
}
"""

EXPORT_MANIFEST_JSON_EXAMPLE = """\
{
  "manifest_id": "exp_c9d0e1f2",
  "project_name": "Marketing Podcast Ep42",
  "exported_at": "2026-03-23T10:49:30+07:00",
  "profile_name": "tiktok",
  "plan_version": 2,
  "clips": [
    {
      "candidate_id": "c001",
      "variant_id": "final_9x16_v001",
      "profile_name": "tiktok",
      "output_path": "exports/Marketing_Podcast_Ep42_c001_tiktok.mp4",
      "duration_sec": 44.4,
      "file_size_bytes": 18500000,
      "composite_score": 78.5,
      "exported_at": "2026-03-23T10:49:30+07:00"
    },
    {
      "candidate_id": "c002",
      "variant_id": "final_9x16_v001",
      "profile_name": "tiktok",
      "output_path": "exports/Marketing_Podcast_Ep42_c002_tiktok.mp4",
      "duration_sec": 38.2,
      "file_size_bytes": 15200000,
      "composite_score": 72.1,
      "exported_at": "2026-03-23T10:49:30+07:00"
    }
  ],
  "total_clips": 5,
  "passed_clips": 5,
  "failed_clips": 0,
  "total_duration_sec": 198.6,
  "total_file_size_bytes": 82400000
}
"""

CANDIDATES_INDEX_JSON_EXAMPLE = """\
{
  "generation": 1,
  "strategy_name": "podcast",
  "generated_at": "2026-03-23T10:42:00+07:00",
  "total_candidates": 8,
  "candidates": [
    {
      "candidate_id": "c001",
      "time_range": {"start": 245.3, "end": 289.7},
      "overall_score": 0.82,
      "content_type": "talking_head",
      "speech_preview": "The biggest mistake people make...",
      "tags": ["key_insight", "high_energy"],
      "has_preview": true,
      "has_final": false,
      "latest_preview_variant": "preview_v002",
      "gate_passed": null
    },
    {
      "candidate_id": "c002",
      "time_range": {"start": 512.0, "end": 550.2},
      "overall_score": 0.76,
      "content_type": "talking_head",
      "speech_preview": "Here is what actually works...",
      "tags": ["actionable_advice"],
      "has_preview": true,
      "has_final": false,
      "latest_preview_variant": "preview_v001",
      "gate_passed": null
    }
  ]
}
"""

ANALYSIS_MANIFEST_JSON_EXAMPLE = """\
{
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015...",
  "engines": {
    "scene": {
      "engine_version": "1.0.0",
      "config_hash": "a1b2c3d4",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 2.1,
      "output_file": "scene.json",
      "completed_at": "2026-03-23T10:31:02+07:00"
    },
    "motion": {
      "engine_version": "1.0.0",
      "config_hash": "e5f6a7b8",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 8.3,
      "output_file": "motion.csv",
      "completed_at": "2026-03-23T10:31:10+07:00"
    },
    "speech": {
      "engine_version": "1.2.0",
      "config_hash": "c9d0e1f2",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 45.7,
      "output_file": "speech.json",
      "completed_at": "2026-03-23T10:31:56+07:00"
    },
    "audio": {
      "engine_version": "1.0.0",
      "config_hash": "f3a4b5c6",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 5.2,
      "output_file": "audio.json",
      "completed_at": "2026-03-23T10:32:01+07:00"
    },
    "visual": {
      "engine_version": "1.0.0",
      "config_hash": "d7e8f9a0",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 32.1,
      "output_file": "visual.json",
      "completed_at": "2026-03-23T10:32:33+07:00"
    },
    "content": {
      "engine_version": "1.0.0",
      "config_hash": "b1c2d3e4",
      "source_hash": "sha256:9f86d08188...",
      "status": "done",
      "elapsed_sec": 1.8,
      "output_file": "content_classification.json",
      "completed_at": "2026-03-23T10:32:35+07:00"
    }
  },
  "total_elapsed_sec": 95.2,
  "completed_at": "2026-03-23T10:32:35+07:00"
}
"""

# ═══════════════════════════════════════════════════════════════════════
# JOB STATE TRANSITIONS
# ═══════════════════════════════════════════════════════════════════════

JOB_STATE_TRANSITIONS = """\
State Machine:

  IDLE
    ├──→ IMPORTING                (user imports video)
    └──→ GENERATING_CANDIDATES    (open existing project with analysis done)

  IMPORTING
    └──→ ANALYZING                (import complete, auto-start)

  ANALYZING
    └──→ GENERATING_CANDIDATES    (all engines done)

  GENERATING_CANDIDATES
    ├──→ PREVIEW_RENDERING        (candidates found, auto-preview)
    └──→ GENERATING_CANDIDATES    (user changes genre → re-run with cached analysis)

  PREVIEW_RENDERING
    └──→ AWAITING_REVIEW          (all previews done)

  AWAITING_REVIEW
    ├──→ PREVIEW_RENDERING        (user edits clip → re-preview changed only)
    ├──→ FINAL_RENDERING          (user accepts → export)
    └──→ GENERATING_CANDIDATES    (user changes genre/strategy)

  FINAL_RENDERING
    └──→ COMPLETED                (all clips rendered + scored)

  COMPLETED
    ├──→ AWAITING_REVIEW          (user wants to modify)
    ├──→ FINAL_RENDERING          (re-export with different profile)
    └──→ IDLE                     (close project)

  FAILED
    ├──→ ANALYZING                (retry from analysis)
    ├──→ GENERATING_CANDIDATES    (retry from editorial)
    ├──→ FINAL_RENDERING          (retry from render)
    └──→ IDLE                     (give up)

  CANCELLED
    └──→ IDLE                     (reset)

  Any active state → FAILED       (on unrecoverable error)
  Any active state → CANCELLED    (on user cancel)
"""
