"""Centralized path resolver for all project artifacts.

Every file path in a project goes through this module.
Prevents scattered path construction across the codebase.

Disk layout:

  {project}/
  ├── project.json                          # Project master file
  ├── source/
  │   ├── media_info.json                   # SourceAsset
  │   └── source.sha256
  ├── cache/                                # Analysis outputs (re-generable)
  │   ├── analysis_manifest.json
  │   ├── scene.json              ← engine name = "scene"
  │   ├── motion.csv
  │   ├── motion.json             ← engine name = "motion"
  │   ├── speech.json             ← engine name = "speech"
  │   ├── audio.json              ← engine name = "audio"
  │   ├── visual_segments.json
  │   ├── visual.json             ← engine name = "visual"
  │   └── content.json            ← engine name = "content"
  ├── candidates/                           # Per-candidate artifacts
  │   ├── index.json                        # Candidate index/summary
  │   ├── c001/
  │   │   ├── candidate.json                # CandidateClip
  │   │   ├── score.json                    # ClipScore (post-render)
  │   │   ├── quality_report.json           # QualityReport
  │   │   ├── renders/
  │   │   │   ├── preview_v001.json         # RenderVariant metadata
  │   │   │   ├── preview_v001.mp4          # Preview video
  │   │   │   ├── preview_v002.json         # After user edit
  │   │   │   ├── preview_v002.mp4
  │   │   │   ├── final_9x16_v001.json
  │   │   │   ├── final_9x16_v001.mp4
  │   │   │   ├── final_1x1_v001.json
  │   │   │   └── final_1x1_v001.mp4
  │   │   └── thumbnails/
  │   │       ├── hook_frame.jpg            # Best frame from first 3s
  │   │       └── keyframe.jpg              # Representative frame
  │   ├── c002/
  │   │   └── ...
  │   └── c003/
  │       └── ...
  ├── plans/
  │   ├── plan_current.json
  │   ├── plan_v001.json
  │   └── plan_v002.json
  ├── renders/                              # Render job tracking
  │   └── job_{uuid}.json
  ├── exports/
  │   ├── manifest_{timestamp}.json
  │   ├── MyVideo_c001_tiktok.mp4
  │   └── MyVideo_c002_tiktok.mp4
  ├── audio/                                # Audio intermediates
  │   ├── source_audio.wav
  │   └── demucs_out/
  └── logs/
      ├── run_{timestamp}.log
      └── run_{timestamp}_summary.json
"""

from __future__ import annotations

from pathlib import Path

from cutclipshort.constants import PROJECT_FILE


class ProjectPaths:
    """Resolves all paths within a project directory."""

    def __init__(self, project_dir: Path) -> None:
        self._root = project_dir

    @property
    def root(self) -> Path:
        """Return the project root directory."""
        return self._root

    # ── Top-level ────────────────────────────────────────────────────

    @property
    def project_json(self) -> Path:
        """Return path to project.json."""
        return self._root / PROJECT_FILE

    # ── Source ───────────────────────────────────────────────────────

    @property
    def source_dir(self) -> Path:
        """Return path to source directory."""
        return self._root / "source"

    @property
    def media_info_json(self) -> Path:
        """Return path to media_info.json."""
        return self.source_dir / "media_info.json"

    @property
    def source_hash_file(self) -> Path:
        """Return path to source hash file."""
        return self.source_dir / "source.sha256"

    # ── Cache (analysis outputs) ─────────────────────────────────────

    @property
    def cache_dir(self) -> Path:
        """Return path to analysis cache directory."""
        return self._root / "cache"

    @property
    def analysis_manifest(self) -> Path:
        """Return path to analysis_manifest.json."""
        return self.cache_dir / "analysis_manifest.json"

    @property
    def scenes_json(self) -> Path:
        """Return path to scene detection results."""
        return self.cache_dir / "scene.json"

    @property
    def motion_csv(self) -> Path:
        """Return path to motion scores CSV."""
        return self.cache_dir / "motion.csv"

    @property
    def motion_summary_json(self) -> Path:
        """Return path to motion summary JSON."""
        return self.cache_dir / "motion.json"

    @property
    def transcript_json(self) -> Path:
        """Return path to speech transcript JSON."""
        return self.cache_dir / "speech.json"

    @property
    def audio_profile_json(self) -> Path:
        """Return path to audio profile JSON."""
        return self.cache_dir / "audio.json"

    @property
    def visual_segments_json(self) -> Path:
        """Return path to visual segments JSON."""
        return self.cache_dir / "visual_segments.json"

    @property
    def visual_detections_json(self) -> Path:
        """Return path to visual detections JSON."""
        return self.cache_dir / "visual.json"

    @property
    def content_classification_json(self) -> Path:
        """Return path to content classification JSON."""
        return self.cache_dir / "content.json"

    # ── Candidates (per-candidate folders) ───────────────────────────

    @property
    def candidates_dir(self) -> Path:
        """Return path to candidates directory."""
        return self._root / "candidates"

    @property
    def candidates_index(self) -> Path:
        """Return path to candidates index.json."""
        return self.candidates_dir / "index.json"

    def candidate_dir(self, candidate_id: str) -> Path:
        """Return path to a specific candidate's directory."""
        return self.candidates_dir / candidate_id

    def candidate_json(self, candidate_id: str) -> Path:
        """Return path to a candidate's metadata JSON."""
        return self.candidate_dir(candidate_id) / "candidate.json"

    def candidate_score_json(self, candidate_id: str) -> Path:
        """Return path to a candidate's score JSON."""
        return self.candidate_dir(candidate_id) / "score.json"

    def candidate_quality_report(self, candidate_id: str) -> Path:
        """Return path to a candidate's quality report JSON."""
        return self.candidate_dir(candidate_id) / "quality_report.json"

    def candidate_renders_dir(self, candidate_id: str) -> Path:
        """Return path to a candidate's renders directory."""
        return self.candidate_dir(candidate_id) / "renders"

    def candidate_thumbnails_dir(self, candidate_id: str) -> Path:
        """Return path to a candidate's thumbnails directory."""
        return self.candidate_dir(candidate_id) / "thumbnails"

    def render_variant_json(self, candidate_id: str, variant_id: str) -> Path:
        """Return path to a render variant's metadata JSON."""
        return self.candidate_renders_dir(candidate_id) / f"{variant_id}.json"

    def render_variant_video(self, candidate_id: str, variant_id: str) -> Path:
        """Return path to a render variant's video file."""
        return self.candidate_renders_dir(candidate_id) / f"{variant_id}.mp4"

    def candidate_hook_thumb(self, candidate_id: str) -> Path:
        """Return path to a candidate's hook frame thumbnail."""
        return self.candidate_thumbnails_dir(candidate_id) / "hook_frame.jpg"

    def candidate_keyframe_thumb(self, candidate_id: str) -> Path:
        """Return path to a candidate's keyframe thumbnail."""
        return self.candidate_thumbnails_dir(candidate_id) / "keyframe.jpg"

    # ── Plans ────────────────────────────────────────────────────────

    @property
    def plans_dir(self) -> Path:
        """Return path to plans directory."""
        return self._root / "plans"

    @property
    def plan_current(self) -> Path:
        """Return path to current edit plan JSON."""
        return self.plans_dir / "plan_current.json"

    def plan_version(self, version: int) -> Path:
        """Return path to a specific plan version JSON."""
        return self.plans_dir / f"plan_v{version:03d}.json"

    # ── Render Jobs ──────────────────────────────────────────────────

    @property
    def render_jobs_dir(self) -> Path:
        """Return path to render jobs directory."""
        return self._root / "renders"

    def render_job_json(self, job_id: str) -> Path:
        """Return path to a render job's metadata JSON."""
        return self.render_jobs_dir / f"job_{job_id}.json"

    # ── Audio intermediates ──────────────────────────────────────────

    @property
    def audio_dir(self) -> Path:
        """Return path to audio intermediates directory."""
        return self._root / "audio"

    @property
    def source_audio_wav(self) -> Path:
        """Return path to extracted source audio WAV."""
        return self.audio_dir / "source_audio.wav"

    @property
    def demucs_out_dir(self) -> Path:
        """Return path to Demucs stem separation output directory."""
        return self.audio_dir / "demucs_out"

    # ── Exports ──────────────────────────────────────────────────────

    @property
    def exports_dir(self) -> Path:
        """Return path to exports directory."""
        return self._root / "exports"

    def export_manifest_json(self, timestamp: str) -> Path:
        """Return path to an export manifest JSON by timestamp."""
        return self.exports_dir / f"manifest_{timestamp}.json"

    def export_clip(
        self, project_name: str, candidate_id: str, profile: str,
        seo_slug: str = "",
    ) -> Path:
        """Build export filename in default exports/ dir."""
        return self.export_clip_to(
            self.exports_dir, project_name, candidate_id, profile, seo_slug,
        )

    def export_clip_to(
        self, output_dir: Path, project_name: str, candidate_id: str,
        profile: str, seo_slug: str = "",
    ) -> Path:
        """Build export filename in a custom output directory."""
        name_part = seo_slug if seo_slug else candidate_id
        # Sanitize for filesystem
        safe_name = "".join(
            c if (c.isalnum() or c in "-_") else "_"
            for c in name_part
        ).strip("_")[:60]
        return output_dir / f"{project_name}_{safe_name}_{profile}.mp4"

    # ── Logs ─────────────────────────────────────────────────────────

    @property
    def logs_dir(self) -> Path:
        """Return path to logs directory."""
        return self._root / "logs"

    def run_log(self, timestamp: str) -> Path:
        """Return path to a run log file by timestamp."""
        return self.logs_dir / f"run_{timestamp}.log"

    def run_summary(self, timestamp: str) -> Path:
        """Return path to a run summary JSON by timestamp."""
        return self.logs_dir / f"run_{timestamp}_summary.json"

    @property
    def latest_log(self) -> Path:
        """Return path to the latest log symlink."""
        return self.logs_dir / "latest.log"

    # ── Directory Creation ───────────────────────────────────────────

    def create_all(self) -> None:
        """Create all top-level project directories."""
        for d in (
            self.source_dir,
            self.cache_dir,
            self.candidates_dir,
            self.plans_dir,
            self.render_jobs_dir,
            self.audio_dir,
            self.exports_dir,
            self.logs_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def create_candidate_dirs(self, candidate_id: str) -> None:
        """Create directories for a specific candidate."""
        self.candidate_dir(candidate_id).mkdir(parents=True, exist_ok=True)
        self.candidate_renders_dir(candidate_id).mkdir(parents=True, exist_ok=True)
        self.candidate_thumbnails_dir(candidate_id).mkdir(parents=True, exist_ok=True)
