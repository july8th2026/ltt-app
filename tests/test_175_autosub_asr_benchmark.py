"""R3: benchmark ASR không được bịa WER khi chưa có ground truth."""
from __future__ import annotations

from tools.autosub_asr_benchmark import _result_metrics, _words


def _sample_result() -> dict:
    return {
        "engine": "whisperx",
        "alignment_status": "aligned",
        "language": "vi",
        "segments": [{
            "start": 0.0,
            "end": 1.0,
            "text": "xin chao",
            "words": [
                {"start": 0.0, "end": 0.4, "text": "xin"},
                {"start": 0.5, "end": 1.0, "text": "chao"},
            ],
        }],
    }


def test_smoke_without_ground_truth_keeps_wer_unknown():
    metrics = _result_metrics(_sample_result(), reference=[], duration=2, elapsed=1)
    assert metrics["segments"] == 1
    assert metrics["aligned_words"] == 2
    assert metrics["word_timing_monotonic"] is True
    assert metrics["word_error_rate"] is None


def test_ground_truth_still_produces_real_wer():
    exact = _result_metrics(
        _sample_result(), reference=_words("xin chao"), duration=2, elapsed=1)
    different = _result_metrics(
        _sample_result(), reference=_words("xin tam biet"), duration=2, elapsed=1)
    assert exact["word_error_rate"] == 0.0
    assert different["word_error_rate"] > 0
