"""Quy tắc nghiệp vụ customer-facing của AutoSub Studio."""
from __future__ import annotations


def render_preflight(project, tracks) -> dict:
    """Audit selected tracks without copying transcript text into evidence.

    Empty/overlap/out-of-source cues make a paid render invalid. Reading-speed,
    short-duration and line-budget findings remain warnings the customer may
    accept after seeing them in the confirmation dialog.
    """
    issues: list[dict] = []
    source_duration = float(project.source.duration_s or 0)
    line_budget = max(1, int(project.style.max_chars_per_line)) * max(
        1, int(project.style.max_lines))
    for track in tracks:
        sorted_cues = sorted(track.cues, key=lambda cue: (cue.start, cue.end, cue.id))
        for index, cue in enumerate(sorted_cues):
            duration = max(.01, float(cue.end) - float(cue.start))
            chars = len(cue.text.strip())
            if not chars:
                issues.append(_issue(track.id, cue.id, "error", "empty"))
            if index and cue.start < sorted_cues[index - 1].end:
                issues.append(_issue(track.id, cue.id, "error", "overlap"))
            if source_duration > 0 and cue.end > source_duration + .05:
                issues.append(_issue(track.id, cue.id, "error", "outside_source"))
            if duration < .5:
                issues.append(_issue(track.id, cue.id, "warning", "short"))
            if chars / duration > 20:
                issues.append(_issue(track.id, cue.id, "warning", "speed"))
            if chars > line_budget:
                issues.append(_issue(track.id, cue.id, "warning", "length"))
    errors = sum(item["severity"] == "error" for item in issues)
    warnings = sum(item["severity"] == "warning" for item in issues)
    return {
        "score": max(0, 100 - errors * 15 - warnings * 5),
        "error_count": errors,
        "warning_count": warnings,
        "issue_codes": sorted({item["code"] for item in issues}),
    }


def _issue(track_id: str, cue_id: str, severity: str, code: str) -> dict:
    return {"track_id": track_id, "cue_id": cue_id,
            "severity": severity, "code": code}
