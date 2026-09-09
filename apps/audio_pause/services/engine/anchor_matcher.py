from __future__ import annotations

import json
import re
import time
from typing import Optional, List, Dict
from rapidfuzz import fuzz

from .nhat_ky import info, debug

# Max seconds for a single anchor fuzzy search before giving up
_MATCH_TIMEOUT_S = 30.0


# ======================================================
# Normalization
# ======================================================

_PUNCT_RE = re.compile(r"[^\w\sÀ-ỹ]+", flags=re.UNICODE)
_WS_RE = re.compile(r"\s+", flags=re.UNICODE)

def normalize_text(s: str) -> str:
    """
    Normalize for matching:
    - lowercase
    - remove punctuation (keep Vietnamese letters)
    - collapse whitespace
    """
    s = (s or "").strip().lower()
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def tokenize(s: str) -> List[str]:
    s = normalize_text(s)
    return s.split() if s else []


# ======================================================
# Word extraction (from Whisper word_timestamps)
# ======================================================

def extract_words_from_transcript(transcript: dict) -> List[Dict]:
    words = []
    for seg in transcript.get("segments", []):
        for w in seg.get("words", []):
            words.append({
                "word": w.get("word", ""),
                "start": float(w.get("start", 0.0)),
                "end": float(w.get("end", 0.0)),
            })
    return words


def build_text(words: List[Dict], start: int, end: int) -> str:
    return " ".join(w["word"] for w in words[start:end])


def build_norm_text(words: List[Dict], start: int, end: int) -> str:
    return normalize_text(build_text(words, start, end))


# ======================================================
# Dynamic window fuzzy search (KEY FIX)
# ======================================================

def fuzzy_span_search(
    target_text: str,
    words: List[Dict],
    threshold: float,
    start_index: int = 0,
    slack_tokens: int = 6,
    _norm_words: Optional[List[str]] = None,
    return_best_on_fail: bool = False,
) -> Optional[Dict]:
    """
    Find best span whose length ~ token_count(target_text), not fixed 30.
    Optimized: pre-build normalized word list, early exit on near-perfect match.
    Pass _norm_words to avoid re-normalizing across multiple anchor searches.
    If return_best_on_fail=True, returns the best match even below threshold
    (with 'below_threshold'=True flag) for debug purposes.
    """

    tgt_tokens = tokenize(target_text)
    if not tgt_tokens:
        return None

    tgt_len = len(tgt_tokens)
    min_len = max(3, tgt_len - slack_tokens)
    max_len = tgt_len + slack_tokens

    best = None
    best_score = 0.0

    # Pre-normalize target once
    tgt_norm = normalize_text(target_text)
    n_words = len(words)

    # Reuse pre-built normalized words array if provided
    norm_words = _norm_words if _norm_words is not None else [normalize_text(w["word"]) for w in words]

    t0 = time.monotonic()

    for i in range(start_index, n_words):
        # early stop if remaining words too few for smallest window
        if i + min_len > n_words:
            break

        # Timeout protection: check every 100 iterations
        if (i - start_index) % 100 == 0 and (time.monotonic() - t0) > _MATCH_TIMEOUT_S:
            debug("fuzzy_search_timeout", target=tgt_norm[:60], elapsed_s=round(time.monotonic() - t0, 1))
            break

        for win in range(min_len, min(max_len + 1, n_words - i + 1)):
            j = i + win

            # Build span from pre-normalized words (much faster than re-normalizing)
            span_norm = " ".join(norm_words[i:j])
            if not span_norm:
                continue

            score = fuzz.ratio(tgt_norm, span_norm) / 100.0

            if score > best_score:
                best_score = score
                best = {
                    "start_idx": i,
                    "end_idx": j,
                    "start_time": words[i]["start"],
                    "end_time": words[j - 1]["end"],
                    "score": score,
                }

                # Early exit: near-perfect match found, no need to search further
                if best_score >= 0.98:
                    return best

    if best and best_score >= threshold:
        return best

    # Return best-effort match for debug even if below threshold
    if return_best_on_fail and best:
        best["below_threshold"] = True
        return best

    return None


# ======================================================
# Boundary anchor matcher (fixed placement)
# ======================================================

def match_boundary_anchor(item: dict, transcript: dict, threshold: float,
                          _words: Optional[List[Dict]] = None,
                          _norm_words: Optional[List[str]] = None) -> Optional[dict]:
    words = _words or extract_words_from_transcript(transcript)
    if not words:
        return None

    ba = item.get("boundary_anchor") or {}
    before_text = (ba.get("before_text") or "").strip()
    after_text = (ba.get("after_text") or "").strip()

    if not before_text:
        return None

    # 1) match BEFORE with dynamic span length
    before_hit = fuzzy_span_search(
        before_text,
        words,
        threshold=threshold,
        start_index=0,
        slack_tokens=8,
        _norm_words=_norm_words,
        return_best_on_fail=True,
    )
    if not before_hit:
        debug("boundary_before_not_found", id=item.get("id"), text=before_text[:80])
        return {
            "_failed": True,
            "id": item.get("id"),
            "input_text": f"boundary before='{before_text}' after='{after_text}'",
            "best_matched_text": "",
            "best_score": 0.0,
            "reason": "before_text not found at all",
        }

    if before_hit.get("below_threshold"):
        debug("boundary_before_below_threshold", id=item.get("id"),
              score=round(before_hit["score"], 4), text=before_text[:80])
        return {
            "_failed": True,
            "id": item.get("id"),
            "input_text": f"boundary before='{before_text}' after='{after_text}'",
            "best_matched_text": build_text(words, before_hit["start_idx"], before_hit["end_idx"]),
            "best_score": round(before_hit["score"], 4),
            "reason": f"before score {before_hit['score']:.2%} < threshold",
        }

    # 2) match AFTER starting near end of before to avoid picking earlier duplicates
    after_hit = None
    if after_text:
        after_hit = fuzzy_span_search(
            after_text,
            words,
            threshold=threshold,
            start_index=max(0, before_hit["end_idx"] - 3),
            slack_tokens=8,
            _norm_words=_norm_words,
        )
        if not after_hit:
            debug("boundary_after_not_found", id=item.get("id"), text=after_text[:80])
            # fallback: chèn ngay sau BEFORE (after_hit stays None)

    # 3) IMPORTANT: place pause at END of BEFORE sentence span (not midpoint)
    before_end = float(before_hit["end_time"])

    if after_hit:
        after_start = float(after_hit["start_time"])
        gap = after_start - before_end
        if gap >= 0.10:
            # Normal case: enough room for epsilon offset
            at_sec = before_end + 0.05
        elif gap > 0:
            # Tight gap: place at midpoint between words
            at_sec = before_end + gap / 2.0
        else:
            # Zero or negative gap (Whisper overlap): place exactly at before_end
            at_sec = before_end
    else:
        # No after_hit: use standard epsilon
        at_sec = before_end + 0.05

    return {
        "id": item.get("id"),
        "start_time": at_sec,
        "pause_ms": int(item.get("silence_ms", item.get("pause_ms", 1000))),
        "priority": int(item.get("priority", 3)),
        "similarity": float(min(before_hit["score"], after_hit["score"] if after_hit else 1.0)),
        # Debug context for tracing pause placement
        "input_text": f"boundary before='{before_text}' after='{after_text}'",
        "matched_before_text": build_text(words, before_hit["start_idx"], before_hit["end_idx"]),
        "matched_after_text": build_text(words, after_hit["start_idx"], after_hit["end_idx"]) if after_hit else "",
        "word_before": _word_context(words, before_hit["end_idx"] - 1),
        "word_after": _word_context(words, before_hit["end_idx"]),
        "debug_span": {
            "before": {
                "start_idx": before_hit["start_idx"],
                "end_idx": before_hit["end_idx"],
                "score": before_hit["score"],
            },
            "after": None if not after_hit else {
                "start_idx": after_hit["start_idx"],
                "end_idx": after_hit["end_idx"],
                "score": after_hit["score"],
            }
        }
    }


# ======================================================
# Legacy single anchor (kept for backward compat)
# ======================================================

def _word_context(words: List[Dict], idx: int) -> Optional[Dict]:
    """Get word + timestamp at index, or None if out of bounds."""
    if 0 <= idx < len(words):
        w = words[idx]
        return {"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)}
    return None


def match_single_anchor(item: dict, transcript: dict, threshold: float,
                        _words: Optional[List[Dict]] = None,
                        _norm_words: Optional[List[str]] = None) -> Optional[dict]:
    anchor_text = (item.get("anchor_text") or "").strip()
    if not anchor_text:
        return None

    words = _words or extract_words_from_transcript(transcript)
    if not words:
        return None

    hit = fuzzy_span_search(anchor_text, words, threshold=threshold, start_index=0,
                            slack_tokens=10, _norm_words=_norm_words, return_best_on_fail=True)
    if not hit:
        return None

    # Below threshold → return as failed with debug info
    if hit.get("below_threshold"):
        return {
            "_failed": True,
            "id": item.get("id"),
            "input_text": anchor_text,
            "best_matched_text": build_text(words, hit["start_idx"], hit["end_idx"]),
            "best_score": round(hit["score"], 4),
            "reason": f"score {hit['score']:.2%} < threshold",
        }

    # single anchor: place at end of matched span with smart epsilon
    end_time = float(hit["end_time"])
    next_word = _word_context(words, hit["end_idx"])
    if next_word:
        gap = next_word["start"] - end_time
        if gap >= 0.10:
            at_sec = end_time + 0.05
        elif gap > 0:
            at_sec = end_time + gap / 2.0
        else:
            at_sec = end_time
    else:
        at_sec = end_time + 0.05

    return {
        "id": item.get("id"),
        "start_time": at_sec,
        "pause_ms": int(item.get("pause_ms", 1000)),
        "priority": int(item.get("priority", 3)),
        "similarity": float(hit["score"]),
        # Debug context for tracing pause placement
        "input_text": anchor_text,
        "matched_text": build_text(words, hit["start_idx"], hit["end_idx"]),
        "word_before": _word_context(words, hit["end_idx"] - 1),
        "word_after": _word_context(words, hit["end_idx"]),
        "debug_span": {
            "start_idx": hit["start_idx"],
            "end_idx": hit["end_idx"],
            "score": hit["score"],
        },
    }


# ======================================================
# Public API
# ======================================================

def match_all_anchors(pause_plan: list[dict], transcript: dict, threshold: float = 0.72) -> dict:
    matched = []
    failed = []

    # Extract words ONCE and pre-normalize ONCE — pass to all matchers
    words = extract_words_from_transcript(transcript)
    norm_words = [normalize_text(w["word"]) for w in words]

    for item in pause_plan:
        if "boundary_anchor" in item:
            hit = match_boundary_anchor(item, transcript, threshold, _words=words, _norm_words=norm_words)
        else:
            hit = match_single_anchor(item, transcript, threshold, _words=words, _norm_words=norm_words)

        if hit is None:
            # No match at all (empty anchor text etc.)
            failed.append({
                "id": item.get("id"),
                "reason": "no match found",
                "input_text": _anchor_input_text(item),
                "best_score": 0.0,
                "best_matched_text": "",
            })
        elif hit.get("_failed"):
            # Below threshold — rich debug info already in hit
            del hit["_failed"]
            failed.append(hit)
        else:
            matched.append(hit)

    info("anchor_match_done", total=len(pause_plan), matched=len(matched), failed=len(failed))
    return {"matched": matched, "failed": failed}


def _anchor_input_text(item: dict) -> str:
    """Extract readable input text description from a pause plan item."""
    if "boundary_anchor" in item:
        ba = item.get("boundary_anchor") or {}
        return f"boundary before='{ba.get('before_text', '')}' after='{ba.get('after_text', '')}'"
    return item.get("anchor_text", "")


def save_anchor_map(anchor_map: dict, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(anchor_map, f, ensure_ascii=False, indent=2)
    debug("anchor_map_saved", path=path)
    return path
