"""Bộ đo SRT deterministic: cue, timing, readability và transcript error."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from apps.qualitylab.contracts import Dimension, Metric
from platform_core.i18n import N_

_TIME = re.compile(
    r"(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})[,.](?P<ms>\d{3})")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(part.strip() for part in self.lines if part.strip())


def _seconds(value: str) -> float:
    match = _TIME.fullmatch(value.strip())
    if not match:
        raise ValueError(N_("timestamp không hợp lệ"))
    return (int(match["h"]) * 3600 + int(match["m"]) * 60 + int(match["s"])
            + int(match["ms"]) / 1000.0)


def parse_srt(text: str) -> list[Cue]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise ValueError(N_("subtitle rỗng"))
    cues: list[Cue] = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.rstrip() for line in block.splitlines()]
        timing_index = next((index for index, line in enumerate(lines) if "-->" in line), -1)
        if timing_index < 0:
            raise ValueError(N_("cue thiếu dòng thời gian"))
        sides = [part.strip() for part in lines[timing_index].split("-->", 1)]
        cue = Cue(_seconds(sides[0]), _seconds(sides[1]),
                  tuple(line for line in lines[timing_index + 1:] if line.strip()))
        if not cue.lines:
            raise ValueError(N_("cue không có nội dung"))
        cues.append(cue)
    return cues


def _normalize(text: str) -> list[str]:
    value = unicodedata.normalize("NFKC", text).casefold()
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return [part for part in value.split() if part]


def _distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, lvalue in enumerate(left, 1):
        current = [i]
        for j, rvalue in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (lvalue != rvalue)))
        previous = current
    return previous[-1]


def inspect_subtitle(text: str, expected_text: str = "") -> tuple[list[Dimension], dict]:
    try:
        cues = parse_srt(text)
    except ValueError as exc:
        metric = Metric("parseable", N_("SRT đọc được"), False, verdict="FAIL",
                        evidence={"reason": str(exc)[:120]})
        return [Dimension("technical", N_("Kỹ thuật"), "FAIL", (metric,))], {}

    invalid_duration = sum(1 for cue in cues if cue.end <= cue.start)
    overlaps = sum(1 for prev, cue in zip(cues, cues[1:]) if cue.start < prev.end)
    non_monotonic = sum(1 for prev, cue in zip(cues, cues[1:])
                        if cue.start < prev.start)
    max_lines = max(len(cue.lines) for cue in cues)
    max_chars = max(len(line) for cue in cues for line in cue.lines)
    cps_values = [len(cue.text) / max(cue.end - cue.start, 0.001) for cue in cues]
    max_cps = max(cps_values)
    technical_verdict = ("FAIL" if invalid_duration or non_monotonic else
                         ("WARN" if overlaps else "PASS"))
    technical = Dimension("technical", N_("Kỹ thuật"), technical_verdict, (
        Metric("parseable", N_("SRT đọc được"), True, verdict="PASS"),
        Metric("cue_count", N_("Số cue"), len(cues), verdict="PASS"),
        Metric("invalid_duration", N_("Cue có duration sai"), invalid_duration,
               verdict="PASS" if invalid_duration == 0 else "FAIL", threshold="= 0"),
        Metric("non_monotonic", N_("Timestamp không tăng"), non_monotonic,
               verdict="PASS" if non_monotonic == 0 else "FAIL", threshold="= 0"),
        Metric("overlaps", N_("Cue chồng nhau"), overlaps,
               verdict="PASS" if overlaps == 0 else "WARN", threshold="= 0"),
    ))
    readability_warn = max_lines > 2 or max_chars > 42 or max_cps > 20
    readability = Dimension("readability", N_("Khả năng đọc"),
                            "WARN" if readability_warn else "PASS", (
        Metric("max_lines", N_("Số dòng tối đa"), max_lines, "line",
               "PASS" if max_lines <= 2 else "WARN", threshold="≤ 2"),
        Metric("max_chars_per_line", N_("Ký tự tối đa mỗi dòng"), max_chars, "char",
               "PASS" if max_chars <= 42 else "WARN", threshold="≤ 42"),
        Metric("max_cps", N_("Tốc độ đọc cao nhất"), round(max_cps, 2), "char/s",
               "PASS" if max_cps <= 20 else "WARN", threshold="≤ 20"),
    ))
    dimensions = [technical, readability]
    summary = {"cue_count": len(cues), "invalid_duration": invalid_duration,
               "overlaps": overlaps, "max_lines": max_lines,
               "max_chars_per_line": max_chars, "max_cps": round(max_cps, 2)}
    expected_words = _normalize(expected_text)
    if expected_words:
        actual_words = _normalize(" ".join(cue.text for cue in cues))
        edits = _distance(expected_words, actual_words)
        wer = edits / len(expected_words)
        dimensions.append(Dimension("content", N_("Nội dung"), "UNKNOWN", (
            Metric("wer", "Word error rate", round(wer, 4), "ratio", "UNKNOWN",
                   threshold=N_("Chưa calibrated — chỉ chẩn đoán"),
                   evidence={"reference_words": len(expected_words),
                             "hypothesis_words": len(actual_words), "edits": edits}),
        )))
        summary["wer"] = round(wer, 4)
    else:
        dimensions.append(Dimension("content", N_("Nội dung"), "UNKNOWN", (
            Metric("wer", "Word error rate", None, verdict="UNKNOWN",
                   threshold=N_("Cần transcript chuẩn")),
        )))
    return dimensions, summary
