"""Quality gate v3 — unified hard/soft rejection for all pipeline stages.

Used by:
  1. Preview gate (after editorial brain, before rendering)
  2. Pre-export gate (before batch render)

Hard reject (veto — CANNOT export):
  - Opening too weak (hook < 0.20)
  - No clear intent (unknown or confidence < 0.25)
  - Completion too low (< 0.20 — cut mid-word)
  - Duration too short (< 5s)
  - Duplicate cluster in top N

Soft warning (user can override):
  - Pacing below threshold
  - Payoff weak
  - Audio quality low
  - Risk flags present

Every decision produces structured gate_reason + risk_flags.
NOTHING passes silently — every clip gets an explicit verdict with reasoning.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GateCheck:
    """A single gate check result."""
    name: str            # e.g. "opening_strength", "intent_clarity"
    passed: bool
    severity: str        # "veto" | "warning" | "info"
    score: float         # 0.0-1.0
    reason: str          # Human-readable explanation
    suggestion: str = "" # Actionable fix if failed


@dataclass(frozen=True)
class GateResult:
    """Complete gate decision with all check details."""
    passed: bool                          # Can export (no veto, soft warnings OK)
    vetoed: bool                          # Hard rejection — CANNOT export
    checks: list[GateCheck] = field(default_factory=list)
    veto_reasons: list[str] = field(default_factory=list)
    soft_fail_reasons: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    score: float = 0.0                    # Overall gate score (0-100)
    gate_reason: str = ""                 # Summary explanation


# ══════════════════════════════════════════════════════════════════════
# QUALITY GATE
# ══════════════════════════════════════════════════════════════════════

class QualityGate:
    """Unified quality gate for candidate clips.

    Runs all checks and produces a structured GateResult.
    Every clip gets an explicit verdict — nothing passes silently.
    """

    def check(self, candidate: dict, seen_clusters: set[int] | None = None) -> GateResult:
        """Run all gate checks on a candidate dict.

        Args:
            candidate: Dict with score, duration, clip_intent, etc.
            seen_clusters: Set of cluster_ids already selected (for dedup).

        Returns:
            GateResult with full check details.
        """
        checks: list[GateCheck] = []

        # Detect no-speech mode (Whisper failed or video has no dialogue)
        has_speech = candidate.get("has_speech", True)

        # ── HARD VETO CHECKS ──────────────────────────────────────
        if has_speech:
            checks.append(self._check_opening(candidate))
            checks.append(self._check_completion(candidate))
        else:
            # No speech → downgrade opening/completion from veto to warning
            checks.append(self._check_opening_nospeech(candidate))
            checks.append(self._check_completion_nospeech(candidate))
        checks.append(self._check_intent(candidate))
        checks.append(self._check_duration(candidate))
        checks.append(self._check_cluster_dup(candidate, seen_clusters))

        # ── SOFT WARNING CHECKS ───────────────────────────────────
        checks.append(self._check_pacing(candidate))
        checks.append(self._check_payoff(candidate))
        checks.append(self._check_audio(candidate))
        checks.append(self._check_risk_flags(candidate))
        checks.append(self._check_score_minimum(candidate))

        # ── BUILD RESULT ──────────────────────────────────────────
        veto_reasons = [c.reason for c in checks if c.severity == "veto" and not c.passed]
        soft_reasons = [c.reason for c in checks if c.severity == "warning" and not c.passed]
        risk_flags = self._collect_risk_flags(checks, candidate)

        vetoed = len(veto_reasons) > 0
        passed = not vetoed and len(soft_reasons) <= 2  # Allow up to 2 warnings

        # Gate score: average of all check scores × 100
        scores = [c.score for c in checks if c.score >= 0]
        gate_score = (sum(scores) / max(1, len(scores))) * 100

        # Build summary reason
        if vetoed:
            gate_reason = f"VETOED: {'; '.join(veto_reasons)}"
        elif soft_reasons:
            gate_reason = f"SOFT FAIL ({len(soft_reasons)}): {'; '.join(soft_reasons[:3])}"
        else:
            gate_reason = "PASSED: all checks OK"

        # Log every decision (nothing silent)
        cid = candidate.get("candidate_id", "?")
        if vetoed:
            logger.warning("Gate VETO %s: %s", cid, gate_reason)
        elif not passed:
            logger.info("Gate SOFT-FAIL %s: %s", cid, gate_reason)
        else:
            logger.debug("Gate PASS %s (%.0f/100)", cid, gate_score)

        return GateResult(
            passed=passed,
            vetoed=vetoed,
            checks=checks,
            veto_reasons=veto_reasons,
            soft_fail_reasons=soft_reasons,
            risk_flags=risk_flags,
            score=round(gate_score, 1),
            gate_reason=gate_reason,
        )

    def batch_check(
        self, candidates: list[dict], enforce_cluster_unique: bool = True,
    ) -> dict[str, GateResult]:
        """Check multiple candidates. Tracks clusters across batch.

        Args:
            enforce_cluster_unique: If True, duplicate clusters in top N are vetoed.
        """
        results: dict[str, GateResult] = {}
        seen_clusters: set[int] = set()

        for c in candidates:
            cid = c.get("candidate_id", "?")
            result = self.check(c, seen_clusters if enforce_cluster_unique else None)
            results[cid] = result

            # Track cluster for dedup (only passed clips count)
            if result.passed and not result.vetoed:
                cluster = c.get("cluster_id", -1)
                if cluster >= 0:
                    seen_clusters.add(cluster)

        return results

    # ══════════════════════════════════════════════════════════════
    # HARD VETO CHECKS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _check_opening(c: dict) -> GateCheck:
        """Veto: opening hook too weak to retain viewers."""
        hook = (c.get("hook_score") or 50) / 100  # Normalize 0-100 to 0-1
        if hook < 0.20:
            return GateCheck(
                "opening_strength", False, "veto", hook,
                f"Opening qu\u00e1 y\u1ebfu (hook={hook*100:.0f}/100)",
                "C\u1ea7n m\u1edf \u0111\u1ea7u m\u1ea1nh h\u01a1n: c\u00e2u h\u1ecfi, s\u1ed1 li\u1ec7u, ho\u1eb7c tuy\u00ean b\u1ed1",
            )
        return GateCheck("opening_strength", True, "veto", hook, "Opening OK")

    @staticmethod
    def _check_intent(c: dict) -> GateCheck:
        """Veto: no clear editorial intent — clip has no purpose."""
        intent = c.get("clip_intent", "unknown")
        conf = c.get("intent_confidence", 0)
        if intent == "unknown" or conf < 0.25:
            return GateCheck(
                "intent_clarity", False, "veto", conf,
                f"Kh\u00f4ng r\u00f5 m\u1ee5c \u0111\u00edch (intent={intent}, conf={conf:.2f})",
                "Clip kh\u00f4ng c\u00f3 intent r\u00f5 r\u00e0ng \u2014 kh\u00f4ng ph\u00f9 h\u1ee3p xu\u1ea5t",
            )
        return GateCheck("intent_clarity", True, "veto", conf, f"Intent: {intent} ({conf:.0%})")

    @staticmethod
    def _check_completion(c: dict) -> GateCheck:
        """Veto: clip cut mid-word or sentence — unwatchable."""
        comp = c.get("completeness_score", 50) / 100
        if comp < 0.20:
            return GateCheck(
                "completion", False, "veto", comp,
                f"C\u1eaft gi\u1eefa ch\u1eebng (completion={comp*100:.0f}/100)",
                "C\u1ea7n snap v\u00e0o ranh gi\u1edbi c\u00e2u",
            )
        return GateCheck("completion", True, "veto", comp, "Completion OK")

    @staticmethod
    def _check_duration(c: dict) -> GateCheck:
        """Veto: too short to be a viable clip."""
        dur = c.get("duration", 0)
        if dur < 5:
            return GateCheck(
                "duration", False, "veto", dur / 60,
                f"Qu\u00e1 ng\u1eafn ({dur:.1f}s < 5s)",
                "C\u1ea7n \u00edt nh\u1ea5t 5 gi\u00e2y",
            )
        return GateCheck("duration", True, "veto", min(1.0, dur / 60), f"Duration: {dur:.0f}s")

    @staticmethod
    def _check_cluster_dup(c: dict, seen: set[int] | None) -> GateCheck:
        """Veto: duplicate cluster in top N — ensures diversity."""
        if seen is None:
            return GateCheck("cluster_unique", True, "info", 1.0, "Cluster check skipped")
        cluster = c.get("cluster_id", -1)
        if cluster >= 0 and cluster in seen:
            return GateCheck(
                "cluster_unique", False, "veto", 0.0,
                f"Tr\u00f9ng cluster #{cluster} \u2014 \u0111\u00e3 c\u00f3 clip t\u01b0\u01a1ng t\u1ef1",
                "Ch\u1ecdn clip t\u1eeb cluster kh\u00e1c",
            )
        return GateCheck("cluster_unique", True, "veto", 1.0, "Cluster unique")

    @staticmethod
    def _check_opening_nospeech(c: dict) -> GateCheck:
        """Warning (not veto) when no speech: opening hook based on visuals only."""
        hook = (c.get("hook_score") or 50) / 100
        if hook < 0.10:
            return GateCheck(
                "opening_strength", False, "warning", hook,
                f"Opening yếu — không có lời (hook={hook*100:.0f}/100)",
                "Video không có lời — đánh giá bằng hình ảnh",
            )
        return GateCheck("opening_strength", True, "warning", hook, "Opening OK (no speech)")

    @staticmethod
    def _check_completion_nospeech(c: dict) -> GateCheck:
        """Warning (not veto) when no speech: completion based on scene boundaries."""
        comp = c.get("completeness_score", 50) / 100
        if comp < 0.10:
            return GateCheck(
                "completion", False, "warning", comp,
                f"Cắt chưa tốt — không có lời (completion={comp*100:.0f}/100)",
                "Video không có lời — kiểm tra ranh giới cảnh",
            )
        return GateCheck("completion", True, "warning", comp, "Completion OK (no speech)")

    # ══════════════════════════════════════════════════════════════
    # SOFT WARNING CHECKS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _check_pacing(c: dict) -> GateCheck:
        """Warning: pacing issues (too fast, too slow, draggy)."""
        pacing = c.get("pacing_score", 50) / 100
        if pacing < 0.35:
            return GateCheck(
                "pacing", False, "warning", pacing,
                f"Nh\u1ecbp k\u00e9m (pacing={pacing*100:.0f}/100)",
                "Ki\u1ec3m tra t\u1ed1c \u0111\u1ed9 n\u00f3i v\u00e0 t\u1ec9 l\u1ec7 im l\u1eb7ng",
            )
        return GateCheck("pacing", True, "warning", pacing, "Pacing OK")

    @staticmethod
    def _check_payoff(c: dict) -> GateCheck:
        """Warning: weak ending — viewer may feel unsatisfied."""
        payoff = c.get("completeness_score", 50) / 100
        if payoff < 0.40:
            return GateCheck(
                "payoff", False, "warning", payoff,
                f"K\u1ebft th\u00fac y\u1ebfu (payoff={payoff*100:.0f}/100)",
                "Th\u00eam k\u1ebft lu\u1eadn ho\u1eb7c c\u00e2u ch\u1ed1t",
            )
        return GateCheck("payoff", True, "warning", payoff, "Payoff OK")

    @staticmethod
    def _check_audio(c: dict) -> GateCheck:
        """Warning: audio quality too low."""
        audio = c.get("audio_score", 50) / 100
        if audio < 0.30:
            return GateCheck(
                "audio_quality", False, "warning", audio,
                f"\u00c2m thanh y\u1ebfu ({audio*100:.0f}/100)",
                "Ki\u1ec3m tra ti\u1ebfng \u1ed3n n\u1ec1n v\u00e0 \u00e2m l\u01b0\u1ee3ng",
            )
        return GateCheck("audio_quality", True, "warning", audio, "Audio OK")

    @staticmethod
    def _check_risk_flags(c: dict) -> GateCheck:
        """Warning: risk flags detected."""
        flags = c.get("risk_flags", [])
        if flags:
            return GateCheck(
                "risk_flags", False, "warning", max(0.0, 1.0 - len(flags) * 0.2),
                f"R\u1ee7i ro: {', '.join(str(f) for f in flags[:3])}",
                "Xem chi ti\u1ebft r\u1ee7i ro trong panel",
            )
        return GateCheck("risk_flags", True, "info", 1.0, "No risk flags")

    @staticmethod
    def _check_score_minimum(c: dict) -> GateCheck:
        """Warning: overall score below viable threshold."""
        score = c.get("score", 0)
        if score < 35:
            return GateCheck(
                "score_minimum", False, "warning", score / 100,
                f"\u0110i\u1ec3m th\u1ea5p ({score:.0f}/100)",
                "Clip c\u00f3 ch\u1ea5t l\u01b0\u1ee3ng th\u1ea5p h\u01a1n mong \u0111\u1ee3i",
            )
        return GateCheck("score_minimum", True, "info", score / 100, f"Score: {score:.0f}")

    # ══════════════════════════════════════════════════════════════
    # RISK FLAGS
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _collect_risk_flags(checks: list[GateCheck], c: dict) -> list[str]:
        """Collect structured risk flags from checks + candidate data."""
        flags: list[str] = []
        for check in checks:
            if not check.passed:
                flags.append(f"{check.name}:{check.severity}")
        # Add any pre-existing flags
        for f in c.get("risk_flags", []):
            if isinstance(f, str) and f not in flags:
                flags.append(f)
        return flags
