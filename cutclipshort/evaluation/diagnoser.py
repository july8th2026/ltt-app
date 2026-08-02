"""Evidence-Based Video Diagnostic Engine (VDE).

Architecture: Rule Engine + Evidence-Based Reasoning

Design principles:
  1. Every diagnosis MUST have evidence (metric + threshold + actual value)
  2. Multiple weak signals → confirmed diagnosis (correlation, not single if)
  3. Root cause is layered: dataset → reference → pipeline → inference
  4. Primary vs secondary findings (not flat list)
  5. Confidence is COMPUTED from evidence strength, not guessed

Compatible with:
  - CompositeScorer (post-render evaluators)
  - PreExportChecker (pre-render checks)
  - QualityGate (veto/soft decisions)
  - Explainability engine

Usage:
    diagnoser = EvidenceBasedDiagnoser()
    report = diagnoser.diagnose(eval_metrics, pre_export_report, clip_spec, analysis)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from cutclipshort.types import AnalysisResult, ClipSpec, EvalMetric

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════
# ENUMS & TYPES
# ══════════════════════════════════════════════════════════════════════════

class RootCauseLayer(Enum):
    """Where the problem originates in the pipeline."""
    DATASET = "dataset"          # Source video quality / content issue
    REFERENCE = "reference"      # Config, style, constraints misconfiguration
    PIPELINE = "pipeline"        # Analysis / editorial / render bug
    INFERENCE = "inference"      # Whisper / YOLO / scoring model error


class Severity(Enum):
    """Diagnosis severity level."""
    CRITICAL = "critical"   # Must fix — output is broken
    HIGH = "high"           # Should fix — noticeable quality loss
    MEDIUM = "medium"       # Consider fixing — minor quality issue
    LOW = "low"             # Informational — no action needed


class FindingType(Enum):
    """Primary vs secondary finding."""
    PRIMARY = "primary"       # Root cause diagnosis
    SECONDARY = "secondary"   # Symptom or downstream effect


# ══════════════════════════════════════════════════════════════════════════
# EVIDENCE
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Evidence:
    """A single piece of measured evidence supporting a diagnosis.

    Example:
        Evidence(
            metric="overall_wps",
            source="subtitle_density",
            expected_range=(1.5, 3.5),
            actual_value=4.8,
            description="Words per second exceeds readable threshold",
        )
    """
    metric: str                          # The metric name ("overall_wps", "hook_strength")
    source: str                          # Which evaluator/checker produced it
    expected_range: tuple[float, float]  # (min, max) acceptable range
    actual_value: float                  # Measured value
    description: str                     # Human-readable what this means
    weight: float = 1.0                  # How important this evidence is (0-1)

    @property
    def deviation(self) -> float:
        """How far outside the expected range (0 = within range)."""
        lo, hi = self.expected_range
        if self.actual_value < lo:
            return (lo - self.actual_value) / max(abs(lo), 0.001)
        elif self.actual_value > hi:
            return (self.actual_value - hi) / max(abs(hi), 0.001)
        return 0.0

    @property
    def is_anomalous(self) -> bool:
        """Is the actual value outside the expected range?"""
        return self.deviation > 0.0


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Diagnosis:
    """A single proven diagnosis with evidence chain.

    Every field is COMPUTED, not guessed:
      - confidence from evidence strength
      - severity from deviation magnitude
      - root_cause_layer from rule classification
    """
    rule_id: str                         # "R001_subtitle_desync"
    title: str                           # "Subtitle timing desync"
    description: str                     # Detailed explanation
    root_cause_layer: RootCauseLayer     # Where the problem is
    finding_type: FindingType            # Primary or secondary
    severity: Severity                   # How bad
    confidence: float                    # 0.0-1.0, computed from evidence
    evidence: list[Evidence]             # Supporting measurements
    suggested_fix: str                   # Actionable remediation
    related_rules: list[str] = field(default_factory=list)  # Cross-references

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)

    @property
    def max_deviation(self) -> float:
        return max((e.deviation for e in self.evidence), default=0.0)


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSIS REPORT
# ══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DiagnosisReport:
    """Complete diagnostic report for a clip."""
    clip_id: str
    primary_findings: list[Diagnosis]     # Root causes
    secondary_findings: list[Diagnosis]   # Symptoms / downstream effects
    all_evidence: list[Evidence]           # Raw evidence pool
    overall_health: str                    # "healthy" / "degraded" / "critical"
    confidence_summary: float             # Average confidence across findings
    rules_evaluated: int                  # Total rules checked
    rules_triggered: int                  # Rules that produced findings

    @property
    def total_findings(self) -> int:
        return len(self.primary_findings) + len(self.secondary_findings)

    @property
    def critical_count(self) -> int:
        return sum(1 for d in self.primary_findings if d.severity == Severity.CRITICAL)

    def to_summary(self) -> str:
        """Human-readable summary."""
        parts = [f"Health: {self.overall_health.upper()}"]
        if self.primary_findings:
            parts.append(f"Primary: {len(self.primary_findings)} issue(s)")
            for d in self.primary_findings:
                parts.append(f"  [{d.severity.value}] {d.title} (conf={d.confidence:.0%})")
        if self.secondary_findings:
            parts.append(f"Secondary: {len(self.secondary_findings)} symptom(s)")
        parts.append(f"Rules: {self.rules_triggered}/{self.rules_evaluated} triggered")
        return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════
# RULE PROTOCOL
# ══════════════════════════════════════════════════════════════════════════

@runtime_checkable
class DiagnosticRule(Protocol):
    """Protocol for a single diagnostic rule.

    Each rule:
      1. Collects evidence from evaluator metrics
      2. Checks if evidence pattern matches its condition
      3. Returns Diagnosis if triggered, None otherwise
    """

    @property
    def rule_id(self) -> str:
        """Unique rule identifier (e.g., 'R001_subtitle_desync')."""
        ...

    @property
    def root_cause_layer(self) -> RootCauseLayer:
        """Which pipeline layer this rule diagnoses."""
        ...

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        """Evaluate evidence and return diagnosis if triggered."""
        ...


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC CONTEXT (shared input to all rules)
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class DiagnosticContext:
    """All data available to diagnostic rules.

    Rules read from this — never modify it.
    """
    clip_id: str
    eval_metrics: list[EvalMetric]        # Post-render evaluator results
    clip_spec: ClipSpec | None = None
    analysis: AnalysisResult | None = None
    pre_export_checks: list[Any] = field(default_factory=list)

    # Convenience lookups (populated by diagnoser)
    _metric_by_name: dict[str, EvalMetric] = field(default_factory=dict)
    _diag_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_metric(self, evaluator_name: str) -> EvalMetric | None:
        """Get evaluator result by name."""
        return self._metric_by_name.get(evaluator_name)

    def get_score(self, evaluator_name: str) -> float | None:
        """Get evaluator score by name. Returns None if not found."""
        m = self._metric_by_name.get(evaluator_name)
        return m.score if m else None

    def get_diag(self, evaluator_name: str, key: str, default: Any = None) -> Any:
        """Get a specific diagnostic value from an evaluator."""
        cache = self._diag_cache.get(evaluator_name)
        if cache is not None:
            return cache.get(key, default)
        return default

    def get_diag_float(self, evaluator_name: str, key: str, default: float = 0.0) -> float:
        """Get diagnostic as float (safe cast)."""
        val = self.get_diag(evaluator_name, key, default)
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    def get_diag_bool(self, evaluator_name: str, key: str, default: bool = False) -> bool:
        """Get diagnostic as bool (safe cast)."""
        val = self.get_diag(evaluator_name, key, default)
        return bool(val)


# ══════════════════════════════════════════════════════════════════════════
# CONFIDENCE COMPUTATION
# ══════════════════════════════════════════════════════════════════════════

def compute_confidence(evidence_list: list[Evidence]) -> float:
    """Compute diagnosis confidence from evidence.

    Formula:
      base = weighted average of evidence deviations (capped at 1.0)
      bonus = +0.1 per additional corroborating evidence (max +0.3)
      result = min(1.0, base + bonus)

    Single evidence → max 0.7 confidence (needs corroboration)
    Two corroborating → max 0.9
    Three+ → can reach 1.0
    """
    if not evidence_list:
        return 0.0

    anomalous = [e for e in evidence_list if e.is_anomalous]
    if not anomalous:
        return 0.0

    # Weighted deviation average
    total_weight = sum(e.weight for e in anomalous)
    if total_weight == 0:
        return 0.0

    weighted_dev = sum(e.deviation * e.weight for e in anomalous) / total_weight
    base = min(0.7, weighted_dev)  # Cap base at 0.7

    # Corroboration bonus
    corroboration_bonus = min(0.3, (len(anomalous) - 1) * 0.1)

    return round(min(1.0, base + corroboration_bonus), 3)


def compute_severity(evidence_list: list[Evidence]) -> Severity:
    """Compute severity from evidence deviation magnitude.

    - Any deviation > 1.0 → CRITICAL
    - Max deviation > 0.5 → HIGH
    - Max deviation > 0.2 → MEDIUM
    - Otherwise → LOW
    """
    if not evidence_list:
        return Severity.LOW

    max_dev = max((e.deviation for e in evidence_list if e.is_anomalous), default=0.0)

    if max_dev > 1.0:
        return Severity.CRITICAL
    elif max_dev > 0.5:
        return Severity.HIGH
    elif max_dev > 0.2:
        return Severity.MEDIUM
    return Severity.LOW


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC RULES — DATASET LAYER
# ══════════════════════════════════════════════════════════════════════════

class R001_NoSpeechContent:
    """Source video has no detectable speech."""
    rule_id = "R001_no_speech"
    root_cause_layer = RootCauseLayer.DATASET

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        # Evidence 1: transcript is empty
        if ctx.analysis:
            seg_count = len(ctx.analysis.transcript)
            evidence.append(Evidence(
                metric="transcript_segments", source="speech_engine",
                expected_range=(3, 999), actual_value=seg_count,
                description=f"Only {seg_count} transcript segments found",
            ))

        # Evidence 2: subtitle evaluator says no content
        sub_segs = ctx.get_diag("subtitle_density", "total_segments", -1)
        if sub_segs is not None and sub_segs >= 0:
            evidence.append(Evidence(
                metric="total_segments", source="subtitle_density",
                expected_range=(2, 999), actual_value=float(sub_segs),
                description=f"Subtitle evaluator found {sub_segs} segments",
            ))

        # Evidence 3: content evaluator WPM
        wpm = ctx.get_diag_float("content_quality", "wpm", -1)
        if wpm >= 0:
            evidence.append(Evidence(
                metric="wpm", source="content_quality",
                expected_range=(50, 300), actual_value=wpm,
                description=f"Speech pace {wpm:.0f} WPM",
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if len(anomalous) < 2:  # Need at least 2 corroborating signals
            return None

        conf = compute_confidence(evidence)
        if conf < 0.3:
            return None

        return Diagnosis(
            rule_id=self.rule_id,
            title="No speech content in source",
            description="Source video appears to have little or no speech, "
                        "making subtitle generation unreliable.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Check source video has audible speech. "
                          "If music-only, disable captions for this tab profile.",
        )


class R002_LowAudioQuality:
    """Source audio is degraded (clipping, low bitrate, noise)."""
    rule_id = "R002_low_audio_quality"
    root_cause_layer = RootCauseLayer.DATASET

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        clipping = ctx.get_diag_bool("audio_loudness", "clipping_detected")
        if clipping:
            evidence.append(Evidence(
                metric="clipping_detected", source="audio_loudness",
                expected_range=(0, 0), actual_value=1.0,
                description="Audio clipping detected — peaks exceed 0dBFS",
                weight=1.2,
            ))

        true_peak = ctx.get_diag_float("audio_loudness", "true_peak_dbtp", -1.0)
        if true_peak > -0.5:
            evidence.append(Evidence(
                metric="true_peak_dbtp", source="audio_loudness",
                expected_range=(-20.0, -1.0), actual_value=true_peak,
                description=f"True peak {true_peak:.1f} dBTP is dangerously high",
            ))

        audio_score = ctx.get_score("audio_loudness")
        if audio_score is not None and audio_score < 0.4:
            evidence.append(Evidence(
                metric="audio_score", source="audio_loudness",
                expected_range=(0.5, 1.0), actual_value=audio_score,
                description=f"Audio quality score {audio_score:.0%} below threshold",
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if not anomalous:
            return None

        conf = compute_confidence(evidence)
        return Diagnosis(
            rule_id=self.rule_id,
            title="Low audio quality in source",
            description="Source audio shows quality issues that affect "
                        "both playback and speech recognition accuracy.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Enable demucs vocal separation to clean audio. "
                          "Check source recording quality.",
            related_rules=["R005_whisper_hallucination"],
        )


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC RULES — REFERENCE LAYER (Config / Style)
# ══════════════════════════════════════════════════════════════════════════

class R003_SubtitleTooFast:
    """Caption display speed exceeds readability threshold."""
    rule_id = "R003_subtitle_too_fast"
    root_cause_layer = RootCauseLayer.REFERENCE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        wps = ctx.get_diag_float("subtitle_density", "overall_wps")
        if wps > 0:
            evidence.append(Evidence(
                metric="overall_wps", source="subtitle_density",
                expected_range=(1.0, 3.5), actual_value=wps,
                description=f"{wps:.1f} words/sec displayed",
            ))

        cps = ctx.get_diag_float("subtitle_density", "overall_cps")
        if cps > 0:
            evidence.append(Evidence(
                metric="overall_cps", source="subtitle_density",
                expected_range=(5.0, 18.0), actual_value=cps,
                description=f"{cps:.1f} chars/sec displayed",
            ))

        burst = ctx.get_diag_float("subtitle_density", "burst_chunks", 0)
        total = ctx.get_diag_float("subtitle_density", "total_chunks", 1)
        if total > 0 and burst > 0:
            burst_ratio = burst / total
            evidence.append(Evidence(
                metric="burst_ratio", source="subtitle_density",
                expected_range=(0, 0.1), actual_value=burst_ratio,
                description=f"{burst:.0f}/{total:.0f} chunks exceed speed limit",
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if not anomalous:
            return None

        conf = compute_confidence(evidence)
        if conf < 0.3:
            return None

        return Diagnosis(
            rule_id=self.rule_id,
            title="Subtitles too fast to read",
            description="Caption display speed exceeds comfortable reading pace. "
                        "Viewers cannot absorb text before it changes.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Increase max_chars_per_line in caption style, "
                          "or switch to a style with larger font (fewer words visible).",
        )


class R004_WeakOpening:
    """Clip opening fails to hook viewer attention."""
    rule_id = "R004_weak_opening"
    root_cause_layer = RootCauseLayer.REFERENCE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        opening_score = ctx.get_score("opening_strength")
        if opening_score is not None:
            evidence.append(Evidence(
                metric="opening_score", source="opening_strength",
                expected_range=(0.4, 1.0), actual_value=opening_score,
                description=f"Opening strength {opening_score:.0%}",
            ))

        has_filler = ctx.get_diag_bool("opening_strength", "has_filler")
        if has_filler:
            evidence.append(Evidence(
                metric="has_filler_start", source="opening_strength",
                expected_range=(0, 0), actual_value=1.0,
                description="Opening starts with filler word (um, uh, etc.)",
                weight=0.8,
            ))

        content_score = ctx.get_score("content_quality")
        if content_score is not None and content_score < 0.4:
            evidence.append(Evidence(
                metric="content_score", source="content_quality",
                expected_range=(0.4, 1.0), actual_value=content_score,
                description=f"Content quality {content_score:.0%} suggests weak material",
                weight=0.6,
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if not anomalous:
            return None

        conf = compute_confidence(evidence)
        if conf < 0.25:
            return None

        return Diagnosis(
            rule_id=self.rule_id,
            title="Weak clip opening",
            description="Clip does not start with a compelling hook. "
                        "Viewers are likely to scroll past in first 2 seconds.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Trim first 1-3 seconds to start at a stronger sentence. "
                          "Or adjust editorial hook_detection thresholds.",
            related_rules=["R007_incomplete_clip"],
        )


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC RULES — PIPELINE LAYER
# ══════════════════════════════════════════════════════════════════════════

class R005_WhisperHallucination:
    """Whisper produced hallucinated/repeated text."""
    rule_id = "R005_whisper_hallucination"
    root_cause_layer = RootCauseLayer.PIPELINE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        if not ctx.analysis:
            return None

        evidence = []
        transcript = ctx.analysis.transcript

        # Check for repeated text across segments
        texts = [s.text.strip().lower() for s in transcript if s.text.strip()]
        if len(texts) >= 3:
            unique_ratio = len(set(texts)) / len(texts)
            if unique_ratio < 0.8:
                evidence.append(Evidence(
                    metric="unique_segment_ratio", source="transcript_analysis",
                    expected_range=(0.8, 1.0), actual_value=unique_ratio,
                    description=f"Only {unique_ratio:.0%} unique segments — "
                                f"likely hallucination/repetition",
                    weight=1.5,
                ))

        # Check for very low confidence words
        low_conf_count = 0
        total_words = 0
        for seg in transcript:
            for w in (seg.words or []):
                total_words += 1
                if w.confidence < 0.3:
                    low_conf_count += 1

        if total_words > 10:
            low_conf_ratio = low_conf_count / total_words
            if low_conf_ratio > 0.15:
                evidence.append(Evidence(
                    metric="low_confidence_word_ratio", source="transcript_analysis",
                    expected_range=(0, 0.15), actual_value=low_conf_ratio,
                    description=f"{low_conf_ratio:.0%} of words have < 30% confidence",
                ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if not anomalous:
            return None

        conf = compute_confidence(evidence)
        return Diagnosis(
            rule_id=self.rule_id,
            title="Whisper hallucination detected",
            description="Speech recognition produced unreliable output — "
                        "repeated phrases or low-confidence words.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Switch to larger Whisper model (medium → large-v3). "
                          "Check audio quality. Increase beam_size.",
            related_rules=["R002_low_audio_quality", "R003_subtitle_too_fast"],
        )


class R006_RenderQualityDrop:
    """Rendered output has lower quality than expected."""
    rule_id = "R006_render_quality_drop"
    root_cause_layer = RootCauseLayer.PIPELINE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        bitrate = ctx.get_diag_float("visual_quality", "bitrate_kbps")
        if bitrate > 0 and bitrate < 1000:
            evidence.append(Evidence(
                metric="bitrate_kbps", source="visual_quality",
                expected_range=(1000, 20000), actual_value=bitrate,
                description=f"Output bitrate {bitrate:.0f} kbps is very low",
            ))

        visual_score = ctx.get_score("visual_quality")
        if visual_score is not None and visual_score < 0.5:
            evidence.append(Evidence(
                metric="visual_score", source="visual_quality",
                expected_range=(0.5, 1.0), actual_value=visual_score,
                description=f"Visual quality {visual_score:.0%}",
            ))

        blur = ctx.get_diag_float("visual_quality", "blur_score", 1.0)
        if blur < 0.5:
            evidence.append(Evidence(
                metric="blur_score", source="visual_quality",
                expected_range=(0.5, 1.0), actual_value=blur,
                description=f"Blur score {blur:.0%} — image is soft/blurry",
            ))

        dur_mismatch = ctx.get_diag_float("pacing", "duration_mismatch", 0)
        if abs(dur_mismatch) > 2.0:
            evidence.append(Evidence(
                metric="duration_mismatch", source="pacing",
                expected_range=(-1.0, 1.0), actual_value=dur_mismatch,
                description=f"Duration mismatch {dur_mismatch:.1f}s vs expected",
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if not anomalous:
            return None

        conf = compute_confidence(evidence)
        return Diagnosis(
            rule_id=self.rule_id,
            title="Render quality degraded",
            description="Rendered output shows quality issues — "
                        "low bitrate, blur, or duration mismatch.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Check CRF setting (lower = better quality). "
                          "Verify source resolution matches target. "
                          "Check disk space during render.",
        )


# ══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC RULES — INFERENCE LAYER
# ══════════════════════════════════════════════════════════════════════════

class R007_IncompleteClip:
    """Clip feels cut mid-thought — no narrative resolution."""
    rule_id = "R007_incomplete_clip"
    root_cause_layer = RootCauseLayer.INFERENCE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        sem_score = ctx.get_score("semantic_completeness")
        if sem_score is not None:
            evidence.append(Evidence(
                metric="semantic_score", source="semantic_completeness",
                expected_range=(0.5, 1.0), actual_value=sem_score,
                description=f"Semantic completeness {sem_score:.0%}",
            ))

        has_punct = ctx.get_diag_bool("semantic_completeness", "ends_with_punctuation")
        if not has_punct:
            evidence.append(Evidence(
                metric="ends_with_punctuation", source="semantic_completeness",
                expected_range=(1, 1), actual_value=0.0,
                description="Clip does not end with sentence-ending punctuation",
            ))

        has_resolution = ctx.get_diag_bool("semantic_completeness", "has_resolution")
        if not has_resolution:
            evidence.append(Evidence(
                metric="has_resolution", source="semantic_completeness",
                expected_range=(1, 1), actual_value=0.0,
                description="No narrative resolution detected",
                weight=0.7,
            ))

        retention = ctx.get_score("retention_potential")
        ending_energy = ctx.get_diag_float("retention_potential", "sub_ending_energy", 1.0)
        if ending_energy < 0.3:
            evidence.append(Evidence(
                metric="ending_energy", source="retention_potential",
                expected_range=(0.3, 1.0), actual_value=ending_energy,
                description=f"Ending energy {ending_energy:.0%} — clip fizzles out",
                weight=0.6,
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if len(anomalous) < 2:  # Need corroboration
            return None

        conf = compute_confidence(evidence)
        if conf < 0.3:
            return None

        return Diagnosis(
            rule_id=self.rule_id,
            title="Clip feels incomplete",
            description="Clip appears to end mid-thought without narrative resolution. "
                        "Viewer will feel unsatisfied.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.PRIMARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Extend clip end by 2-5 seconds to capture payoff. "
                          "Or adjust payoff_detection sensitivity.",
            related_rules=["R004_weak_opening"],
        )


class R008_RetentionRisk:
    """Clip has poor viewer retention profile."""
    rule_id = "R008_retention_risk"
    root_cause_layer = RootCauseLayer.INFERENCE

    def evaluate(self, ctx: DiagnosticContext) -> Diagnosis | None:
        evidence = []

        retention_score = ctx.get_score("retention_potential")
        if retention_score is not None:
            evidence.append(Evidence(
                metric="retention_score", source="retention_potential",
                expected_range=(0.4, 1.0), actual_value=retention_score,
                description=f"Retention potential {retention_score:.0%}",
            ))

        sustained = ctx.get_diag_float("retention_potential", "sub_sustained_speech", 1.0)
        if sustained < 0.5:
            evidence.append(Evidence(
                metric="sustained_speech", source="retention_potential",
                expected_range=(0.5, 1.0), actual_value=sustained,
                description=f"Sustained speech {sustained:.0%} — mid-clip silence risk",
            ))

        energy_arc = ctx.get_diag_float("retention_potential", "sub_energy_arc", 1.0)
        if energy_arc < 0.4:
            evidence.append(Evidence(
                metric="energy_arc", source="retention_potential",
                expected_range=(0.4, 1.0), actual_value=energy_arc,
                description=f"Energy arc {energy_arc:.0%} — flat/declining energy",
            ))

        pacing_score = ctx.get_score("pacing")
        if pacing_score is not None and pacing_score < 0.4:
            evidence.append(Evidence(
                metric="pacing_score", source="pacing",
                expected_range=(0.4, 1.0), actual_value=pacing_score,
                description=f"Pacing score {pacing_score:.0%}",
                weight=0.6,
            ))

        anomalous = [e for e in evidence if e.is_anomalous]
        if len(anomalous) < 2:
            return None

        conf = compute_confidence(evidence)
        if conf < 0.3:
            return None

        return Diagnosis(
            rule_id=self.rule_id,
            title="Poor viewer retention profile",
            description="Clip has flat energy, mid-clip silence, or declining engagement — "
                        "viewers likely to drop off early.",
            root_cause_layer=self.root_cause_layer,
            finding_type=FindingType.SECONDARY,
            severity=compute_severity(evidence),
            confidence=conf,
            evidence=evidence,
            suggested_fix="Select clips with stronger energy arc. "
                          "Consider speed_factor increase for slow sections.",
            related_rules=["R004_weak_opening", "R007_incomplete_clip"],
        )


# ══════════════════════════════════════════════════════════════════════════
# RULE ENGINE
# ══════════════════════════════════════════════════════════════════════════

# All diagnostic rules
ALL_RULES: list[DiagnosticRule] = [
    R001_NoSpeechContent(),
    R002_LowAudioQuality(),
    R003_SubtitleTooFast(),
    R004_WeakOpening(),
    R005_WhisperHallucination(),
    R006_RenderQualityDrop(),
    R007_IncompleteClip(),
    R008_RetentionRisk(),
]


class RuleEngine:
    """Executes diagnostic rules with cross-correlation and deduplication.

    Key behaviors:
      1. Runs ALL rules (no short-circuit)
      2. Collects all evidence into a shared pool
      3. Cross-correlates: if Rule A and Rule B share evidence → link them
      4. Deduplicates: secondary finding that's caused by a primary → mark related
      5. Sorts by confidence (highest first)
    """

    def __init__(self, rules: list[DiagnosticRule] | None = None) -> None:
        self._rules = rules or list(ALL_RULES)

    def run(self, ctx: DiagnosticContext) -> DiagnosisReport:
        """Execute all rules and produce a diagnosis report."""
        # Build lookup caches in context
        ctx._metric_by_name = {m.evaluator_name: m for m in ctx.eval_metrics}
        ctx._diag_cache = {
            m.evaluator_name: (m.diagnostics or {})
            for m in ctx.eval_metrics
        }

        # Run all rules
        findings: list[Diagnosis] = []
        all_evidence: list[Evidence] = []

        for rule in self._rules:
            try:
                result = rule.evaluate(ctx)
                if result is not None:
                    findings.append(result)
                    all_evidence.extend(result.evidence)
            except Exception as e:
                logger.warning("Rule %s failed: %s", rule.rule_id, e)

        # Cross-correlate: detect secondary findings caused by primary
        findings = self._cross_correlate(findings)

        # Sort by confidence (highest first), then severity
        severity_order = {Severity.CRITICAL: 0, Severity.HIGH: 1,
                          Severity.MEDIUM: 2, Severity.LOW: 3}
        findings.sort(key=lambda d: (-d.confidence, severity_order.get(d.severity, 9)))

        # Split primary vs secondary
        primary = [d for d in findings if d.finding_type == FindingType.PRIMARY]
        secondary = [d for d in findings if d.finding_type == FindingType.SECONDARY]

        # Overall health
        if any(d.severity == Severity.CRITICAL for d in primary):
            health = "critical"
        elif primary:
            health = "degraded"
        else:
            health = "healthy"

        avg_conf = (
            sum(d.confidence for d in findings) / len(findings)
            if findings else 0.0
        )

        report = DiagnosisReport(
            clip_id=ctx.clip_id,
            primary_findings=primary,
            secondary_findings=secondary,
            all_evidence=all_evidence,
            overall_health=health,
            confidence_summary=round(avg_conf, 3),
            rules_evaluated=len(self._rules),
            rules_triggered=len(findings),
        )

        logger.info(
            "Diagnosis [%s]: health=%s, %d primary, %d secondary, %d/%d rules",
            ctx.clip_id, health, len(primary), len(secondary),
            len(findings), len(self._rules),
        )

        return report

    def _cross_correlate(self, findings: list[Diagnosis]) -> list[Diagnosis]:
        """Link related findings and promote/demote based on evidence overlap.

        If a SECONDARY finding shares evidence sources with a PRIMARY finding,
        they are likely caused by the same root issue → link them.
        """
        if len(findings) <= 1:
            return findings

        # Build evidence source map per finding
        finding_sources: dict[str, set[str]] = {}
        for d in findings:
            sources = {e.source for e in d.evidence}
            finding_sources[d.rule_id] = sources

        # Check for shared sources between findings
        result = []
        for d in findings:
            # Find all rules that reference this rule
            related = set(d.related_rules)
            for other in findings:
                if other.rule_id == d.rule_id:
                    continue
                # Shared evidence sources → related
                overlap = finding_sources[d.rule_id] & finding_sources[other.rule_id]
                if overlap:
                    related.add(other.rule_id)

            if related != set(d.related_rules):
                # Rebuild with updated related_rules (frozen dataclass)
                d = Diagnosis(
                    rule_id=d.rule_id,
                    title=d.title,
                    description=d.description,
                    root_cause_layer=d.root_cause_layer,
                    finding_type=d.finding_type,
                    severity=d.severity,
                    confidence=d.confidence,
                    evidence=d.evidence,
                    suggested_fix=d.suggested_fix,
                    related_rules=sorted(related),
                )
            result.append(d)

        return result


# ══════════════════════════════════════════════════════════════════════════
# PUBLIC API — EvidenceBasedDiagnoser
# ══════════════════════════════════════════════════════════════════════════

class EvidenceBasedDiagnoser:
    """Top-level diagnostic API.

    Integrates with:
      - CompositeScorer (eval_metrics from post-render)
      - PreExportChecker (pre-render checks)
      - ClipSpec + AnalysisResult (pipeline context)

    Usage:
        diagnoser = EvidenceBasedDiagnoser()
        report = diagnoser.diagnose(
            clip_id="c001",
            eval_metrics=composite_scorer_results,
            clip_spec=clip_spec,
            analysis=analysis_result,
        )
        print(report.to_summary())
    """

    def __init__(self, rules: list[DiagnosticRule] | None = None) -> None:
        self._engine = RuleEngine(rules)

    def diagnose(
        self,
        clip_id: str,
        eval_metrics: list[EvalMetric],
        clip_spec: ClipSpec | None = None,
        analysis: AnalysisResult | None = None,
        pre_export_checks: list[Any] | None = None,
    ) -> DiagnosisReport:
        """Run full evidence-based diagnosis.

        Args:
            clip_id: Clip identifier.
            eval_metrics: Results from CompositeScorer evaluators.
            clip_spec: Render specification (for config checks).
            analysis: Full analysis result (for dataset checks).
            pre_export_checks: Results from PreExportChecker.

        Returns:
            DiagnosisReport with primary/secondary findings.
        """
        ctx = DiagnosticContext(
            clip_id=clip_id,
            eval_metrics=eval_metrics,
            clip_spec=clip_spec,
            analysis=analysis,
            pre_export_checks=pre_export_checks or [],
        )

        return self._engine.run(ctx)
