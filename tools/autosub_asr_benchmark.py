"""ASR A/B benchmark that records metrics only, never transcript content."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def _distance(left: list[str], right: list[str]) -> int:
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        next_row = [i]
        for j, b in enumerate(right, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1,
                                row[j - 1] + (a != b)))
        row = next_row
    return row[-1]


def _result_metrics(result: dict, *, reference: list[str], duration: float,
                    elapsed: float) -> dict:
    """Return transcript-free metrics; WER is unknown without ground truth."""
    segments = result.get("segments") or []
    hypothesis = _words(" ".join(str(item.get("text", "")) for item in segments))
    words = [word for segment in segments for word in (segment.get("words") or [])]
    monotonic = all(float(word["start"]) < float(word["end"]) for word in words)
    wer = (round(_distance(reference, hypothesis) / len(reference), 3)
           if reference else None)
    return {
        "engine": result.get("engine"),
        "alignment_status": result.get("alignment_status"),
        "detected_language": result.get("language"),
        "segments": len(segments),
        "aligned_words": len(words),
        "word_timing_monotonic": monotonic,
        "elapsed_seconds": round(elapsed, 3),
        "rtf": round(elapsed / max(duration, .001), 3),
        "word_error_rate": wer,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--language", required=True)
    parser.add_argument("--expected", default="",
                        help="Ground-truth transcript. Omit for smoke-only metrics.")
    parser.add_argument("--models", default="tiny,large-v3")
    parser.add_argument("--sidecar", default=r"D:\LTTWhisperX\Scripts\python.exe")
    parser.add_argument("--gpu-uuid", default="",
                        help="GPU UUID assigned to the benchmark subprocess.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.is_file() or not Path(args.sidecar).is_file():
        raise SystemExit("Source or WhisperX sidecar is missing.")
    os.environ["LTT_WHISPERX_PYTHON"] = args.sidecar
    from apps.autosubvideo.transcription import transcribe_file
    from platform_core.media import duration_seconds
    reference = _words(args.expected); duration = duration_seconds(str(args.source))
    rows = []
    for model in [item.strip() for item in args.models.split(",") if item.strip()]:
        started = time.perf_counter()
        result = transcribe_file(str(args.source), language=args.language,
                                 model_name=model, gpu_uuid=args.gpu_uuid)
        elapsed = time.perf_counter() - started
        rows.append({"model": model, **_result_metrics(
            result, reference=reference, duration=duration, elapsed=elapsed)})
    evidence={"source_name":args.source.name,"language":args.language,
        "duration_seconds":round(duration,3),"reference_supplied":bool(reference),
        "reference_word_count":len(reference),"gpu_uuid":args.gpu_uuid or None,"results":rows,
        "passed":all(row["segments"]>0 and row["word_timing_monotonic"] for row in rows)}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=True))
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
