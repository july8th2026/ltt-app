"""CUT CLIP SHORT type system — 7 domain modules with flat re-exports.

Architecture (dependency order):
  base       → (no deps)           Enums, TimeRange, PersonDetection
  analysis   → base                SourceAsset, AnalysisResult, TranscriptSegment
  semantic   → base                SemanticContext, TopicSegment, EmotionalSpike
  editorial  → base                EditorialIntent, CandidateClip, ClipExplanation
  evaluation → editorial           EvalMetric, ClipScore, QualityReport
  render     → base, analysis      ClipSpec, ExportProfile, RenderSettings
  project    → base, render        EditConstraints, EditPlan, Project

Import patterns:
  from cutclipshort.types import TimeRange              # Quick (flat)
  from cutclipshort.types.editorial import CandidateClip  # Domain-specific
"""

# ── base (no deps) ──────────────────────────────────────────────────
from cutclipshort.types.base import (
    Genre, ContentType, AspectRatio, JobState,
    AnalysisEngineStatus, RenderVariantType, RenderJobStatus,
    NarrativeStage, TimeRange, PersonDetection,
)

# ── analysis (→ base) ───────────────────────────────────────────────
from cutclipshort.types.analysis import (
    SourceAsset, TranscriptWord, TranscriptSegment,
    SceneInfo, SceneDetections, VisualSegment, AudioSegment,
    AnalysisResult,
)

# ── semantic (→ base) ───────────────────────────────────────────────
from cutclipshort.types.semantic import (
    TopicSegment, NarrativeArc, EmotionalSpike,
    ConceptCluster, SemanticContext,
)

# ── editorial (→ base) ──────────────────────────────────────────────
from cutclipshort.types.editorial import (
    EditorialIntent, CandidateScore, StrengthWeakness,
    ClipExplanation, CandidateClip,
)

# ── evaluation (→ editorial) ────────────────────────────────────────
from cutclipshort.types.evaluation import (
    EvalMetric, ClipScore, QualityReport,
)

# ── render (→ base, analysis) ───────────────────────────────────────
from cutclipshort.types.render import (
    FramingParams, AudioConfig, CaptionStyle, ClipSpec,
    RenderSettings, RenderVariant, RenderJob,
    ExportProfile, ExportedClip, ExportManifest,
)

# ── project (→ base, render) ────────────────────────────────────────
from cutclipshort.types.project import (
    EditConstraints, EditPlan, Project,
    AdapterSettings, AnalysisSettings, RenderDefaults,
    UISettings, AppSettings,
)

# ── Legacy alias ────────────────────────────────────────────────────
ClipIntent = EditorialIntent  # Deprecated: use EditorialIntent

__all__ = [
    # base
    "Genre", "ContentType", "AspectRatio", "JobState",
    "AnalysisEngineStatus", "RenderVariantType", "RenderJobStatus",
    "NarrativeStage", "TimeRange", "PersonDetection",
    # analysis
    "SourceAsset", "TranscriptWord", "TranscriptSegment",
    "SceneInfo", "SceneDetections", "VisualSegment", "AudioSegment",
    "AnalysisResult",
    # semantic
    "TopicSegment", "NarrativeArc", "EmotionalSpike",
    "ConceptCluster", "SemanticContext",
    # editorial
    "EditorialIntent", "CandidateScore", "StrengthWeakness",
    "ClipExplanation", "CandidateClip",
    # evaluation
    "EvalMetric", "ClipScore", "QualityReport",
    # render
    "FramingParams", "AudioConfig", "CaptionStyle", "ClipSpec",
    "RenderSettings", "RenderVariant", "RenderJob",
    "ExportProfile", "ExportedClip", "ExportManifest",
    # project
    "EditConstraints", "EditPlan", "Project",
    "AdapterSettings", "AnalysisSettings", "RenderDefaults",
    "UISettings", "AppSettings",
    # legacy
    "ClipIntent",
]
