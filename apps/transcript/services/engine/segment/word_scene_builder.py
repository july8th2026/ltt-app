"""
Word-First Scene Builder

Build timeline scenes directly from Whisper word-level timestamps.
Words are the SOLE source of truth for text and timing.

Flow:
  1. Build speech candidates from words (cut at punctuation/pause/boundary)
  2. Repair speech scenes (merge short, split long)
  3. Normalize silence (absorb micro-pause, mark residual)
  4. Generate B-ROLL from residual silence only
  5. Assemble final timeline

Rules:
  - Speech scene target: 3.0-6.0s (exception < 3s allowed, marked)
  - Silence >= 2.0s after normalization → B-ROLL
  - No word loss, no word duplication
  - No fake timestamps (no emergency_extend)
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .constants import HARD_MIN, HARD_MAX, SOFT_MIN, W_PUNCT, W_PAUSE, W_LEN
from .word_utils import (
    extract_words_from_segment,
    punct_strength,
    choose_word_cut_index,
)
from .text_utils import clean_text
from .silence import smart_silence_tag
from ..nhat_ky import info


# ============================================================
# PUBLIC API
# ============================================================

def build_word_scenes(
    all_words: List[Dict],
    audio_duration: float,
    *,
    target_min: float = 3.0,
    target_max: float = 6.0,
    hard_min: float = HARD_MIN,
    silence_threshold: float = 2.0,
    silence_chunk_min: float = 3.0,
    silence_chunk_max: float = 6.0,
    silence_text: str = "[B-ROLL: PAUSE]",
) -> List[Dict]:
    """
    Build complete timeline from flat word list.
    Returns list of scenes with type="speech" or "silence", each with words[].
    """
    if not all_words:
        return []

    # STEP 1: Build raw speech candidates
    speech_scenes = _build_speech_candidates(all_words, target_min, target_max)
    info("word_builder_step1", speech_scenes=len(speech_scenes))

    # STEP 2: Repair speech (merge short, split long)
    speech_scenes = _repair_speech_scenes(speech_scenes, target_min, target_max, hard_min)
    info("word_builder_step2", speech_scenes=len(speech_scenes))

    # STEP 3: Normalize silence — measure gaps, absorb micro-pause
    speech_scenes, residual_gaps = _normalize_silence(
        speech_scenes, target_max, silence_threshold
    )
    info("word_builder_step3", speech_scenes=len(speech_scenes), residual_gaps=len(residual_gaps))

    # STEP 4: Generate B-ROLL from residual gaps
    silence_scenes = _generate_broll(
        residual_gaps, speech_scenes,
        silence_chunk_min, silence_chunk_max, silence_text,
    )
    info("word_builder_step4", silence_scenes=len(silence_scenes))

    # STEP 5: Assemble final timeline
    timeline = _assemble_timeline(speech_scenes, silence_scenes, audio_duration)
    info("word_builder_done", total=len(timeline),
         speech=sum(1 for s in timeline if s["type"] == "speech"),
         silence=sum(1 for s in timeline if s["type"] == "silence"))

    return timeline


def flatten_words(segments: List[Dict]) -> List[Dict]:
    """
    Extract all words from segments into a flat sorted list.
    Each word: {word: str, start: float, end: float}
    """
    all_words = []
    for seg in segments:
        words = seg.get("words", [])
        for w in words:
            word_text = clean_text(str(w.get("word", "")))
            if not word_text:
                continue
            try:
                st = float(w["start"])
                en = float(w["end"])
                if en > st:
                    all_words.append({"word": word_text, "start": st, "end": en})
            except (KeyError, ValueError, TypeError):
                continue
    all_words.sort(key=lambda w: w["start"])
    return all_words


# ============================================================
# STEP 1: Build speech candidates from words
# ============================================================

def _build_speech_candidates(
    words: List[Dict],
    target_min: float,
    target_max: float,
) -> List[Dict]:
    """
    Group words into speech scene candidates.
    Cut at: punctuation > natural pause > target_max boundary.
    """
    scenes: List[Dict] = []
    buf_words: List[Dict] = []
    buf_start: Optional[float] = None

    for i, w in enumerate(words):
        word_start = w["start"]
        word_end = w["end"]

        # Check gap from previous word
        if buf_words:
            gap = word_start - buf_words[-1]["end"]

            # Large gap (>= 2.0s) → force flush, this will become silence later
            if gap >= 2.0:
                if buf_words:
                    scenes.append(_make_speech_scene(buf_words, buf_start))
                buf_words = [w]
                buf_start = word_start
                continue

            # Natural break: gap >= 0.5s AND last word has punctuation AND scene >= target_min
            # AND last word is NOT a connector (avoid bad scene endings)
            if gap >= 0.5 and buf_words:
                last_punct = punct_strength(buf_words[-1]["word"])
                scene_dur = buf_words[-1]["end"] - buf_start
                if last_punct > 0 and scene_dur >= target_min and not _ends_with_connector(buf_words):
                    scenes.append(_make_speech_scene(buf_words, buf_start))
                    buf_words = [w]
                    buf_start = word_start
                    continue

        # Start new buffer if empty
        if not buf_words:
            buf_words = [w]
            buf_start = word_start
            continue

        # Add word to buffer
        buf_words.append(w)
        scene_dur = word_end - buf_start

        # Check if scene exceeds target_max → must split
        if scene_dur > target_max:
            # Find best cut point within buffer
            cut_result = _find_best_cut_in_buffer(buf_words, buf_start, target_min, target_max)

            if cut_result is not None:
                left_words, right_words = cut_result
                scenes.append(_make_speech_scene(left_words, buf_start))
                buf_words = right_words
                buf_start = right_words[0]["start"] if right_words else word_start
            else:
                # Can't find good cut — flush everything as one scene (will be split in repair)
                scenes.append(_make_speech_scene(buf_words, buf_start))
                buf_words = []
                buf_start = None

    # Flush remaining
    if buf_words:
        scenes.append(_make_speech_scene(buf_words, buf_start))

    return scenes


_CONNECTOR_WORDS = frozenset([
    # English
    "a", "an", "the", "and", "or", "but", "so", "with", "from", "to", "of", "in", "on", "at", "for",
    "is", "are", "was", "were", "be", "been", "am",
    "it", "he", "she", "we", "they", "my", "his", "her", "its", "our", "their", "your",
    "if", "as", "by", "up", "no", "not", "do", "did", "has", "had", "have", "will", "can", "may",
    "this", "that", "these", "those", "into", "onto", "upon", "than", "who", "which", "what",
    # Vietnamese
    "và", "va", "hay", "hoặc", "nhưng", "mà", "với", "của", "từ", "cho", "về", "trong",
    "là", "có", "được", "bị", "một", "các", "những", "này", "đó", "thì", "cũng", "đã", "sẽ",
    "để", "vì", "nên", "như", "khi", "nếu", "tại", "bởi", "theo",
])


def _make_speech_scene(words: List[Dict], start: float) -> Dict:
    """Create a speech scene dict from word list."""
    text = " ".join(w["word"] for w in words)
    return {
        "start": round(start, 2),
        "end": round(words[-1]["end"], 2),
        "text": clean_text(text),
        "type": "speech",
        "words": list(words),
    }


def _ends_with_connector(words: List[Dict]) -> bool:
    """Check if last word is a connector (bad scene ending)."""
    if not words:
        return False
    last = words[-1]["word"].lower().rstrip(".,!?;:")
    return last in _CONNECTOR_WORDS


def _find_best_cut_in_buffer(
    words: List[Dict],
    buf_start: float,
    target_min: float,
    target_max: float,
) -> Optional[Tuple[List[Dict], List[Dict]]]:
    """
    Find best word index to split buffer. Returns (left_words, right_words) or None.
    Uses scoring from word_utils: punctuation + pause - length deviation.
    """
    if len(words) < 2:
        return None

    seg_end = words[-1]["end"]
    cut_idx = choose_word_cut_index(
        words,
        seg_start=buf_start,
        seg_end=seg_end,
        max_s=target_max,
        min_chunk1=target_min,
        min_chunk2=target_min,
    )

    if cut_idx is not None:
        left = words[:cut_idx + 1]
        right = words[cut_idx + 1:]
        if left and right:
            return left, right

    # Fallback: try with hard_min
    cut_idx = choose_word_cut_index(
        words,
        seg_start=buf_start,
        seg_end=seg_end,
        max_s=target_max,
        min_chunk1=HARD_MIN,
        min_chunk2=HARD_MIN,
    )

    if cut_idx is not None:
        left = words[:cut_idx + 1]
        right = words[cut_idx + 1:]
        if left and right:
            return left, right

    return None


# ============================================================
# STEP 2: Repair speech scenes
# ============================================================

def _repair_speech_scenes(
    scenes: List[Dict],
    target_min: float,
    target_max: float,
    hard_min: float,
) -> List[Dict]:
    """
    Repair speech scenes:
    - Scene < target_min: try merge with neighbor (if total <= target_max)
    - Scene > target_max: split at word boundary
    - Scene < hard_min and can't merge: mark exception (keep as-is)
    """
    if not scenes:
        return scenes

    # Pass A: Split long scenes (> target_max)
    split_result = []
    for scene in scenes:
        dur = scene["end"] - scene["start"]
        if dur > target_max + 0.01:
            chunks = _split_scene_at_words(scene, target_min, target_max)
            split_result.extend(chunks)
        else:
            split_result.append(scene)

    scenes = split_result

    # Pass B: Merge short scenes (< target_min) with neighbors
    # Very short scenes (< hard_min) get more aggressive gap tolerance
    merged = True
    max_passes = 3
    for _ in range(max_passes):
        if not merged:
            break
        merged = False
        new_scenes = []
        i = 0
        while i < len(scenes):
            scene = scenes[i]
            dur = scene["end"] - scene["start"]

            # Gap tolerance: stricter for near-target, more lenient for very short
            max_gap = 1.0 if dur >= hard_min else 3.0

            if dur < target_min and i + 1 < len(scenes):
                next_scene = scenes[i + 1]
                gap = next_scene["start"] - scene["end"]
                merged_dur = next_scene["end"] - scene["start"]

                if gap < max_gap and merged_dur <= target_max:
                    combined = _merge_two_scenes(scene, next_scene)
                    new_scenes.append(combined)
                    merged = True
                    i += 2
                    continue

            # Try merge with previous
            if dur < target_min and new_scenes:
                prev_scene = new_scenes[-1]
                gap = scene["start"] - prev_scene["end"]
                merged_dur = scene["end"] - prev_scene["start"]

                if gap < max_gap and merged_dur <= target_max:
                    combined = _merge_two_scenes(prev_scene, scene)
                    new_scenes[-1] = combined
                    merged = True
                    i += 1
                    continue

            new_scenes.append(scene)
            i += 1

        scenes = new_scenes

    # Mark exceptions (scenes that are still < hard_min and couldn't be fixed)
    for scene in scenes:
        dur = scene["end"] - scene["start"]
        if dur < hard_min:
            scene["exception"] = True

    return scenes


def _split_scene_at_words(
    scene: Dict,
    target_min: float,
    target_max: float,
) -> List[Dict]:
    """Split a long scene into chunks at word boundaries."""
    words = scene.get("words", [])
    if not words or len(words) < 2:
        return [scene]

    chunks = []
    remaining_words = list(words)
    remaining_start = scene["start"]

    while remaining_words:
        remaining_dur = remaining_words[-1]["end"] - remaining_start
        if remaining_dur <= target_max + 0.01:
            # Remaining fits in one scene
            chunks.append(_make_speech_scene(remaining_words, remaining_start))
            break

        # Find cut point
        cut_result = _find_best_cut_in_buffer(
            remaining_words, remaining_start, target_min, target_max
        )

        if cut_result:
            left, right = cut_result
            chunks.append(_make_speech_scene(left, remaining_start))
            remaining_words = right
            remaining_start = right[0]["start"]
        else:
            # Can't split well — take first target_max worth of words
            # Find last word that fits within target_max
            cut_i = 0
            for j, w in enumerate(remaining_words):
                if w["end"] - remaining_start <= target_max:
                    cut_i = j
                else:
                    break

            if cut_i > 0:
                left = remaining_words[:cut_i + 1]
                right = remaining_words[cut_i + 1:]
                chunks.append(_make_speech_scene(left, remaining_start))
                if right:
                    remaining_words = right
                    remaining_start = right[0]["start"]
                else:
                    break
            else:
                # Single word > target_max (very rare)
                chunks.append(_make_speech_scene(remaining_words, remaining_start))
                break

    return chunks


def _merge_two_scenes(a: Dict, b: Dict) -> Dict:
    """Merge two speech scenes, combining words."""
    words_a = a.get("words", [])
    words_b = b.get("words", [])
    all_words = words_a + words_b
    text = " ".join(w["word"] for w in all_words)
    return {
        "start": a["start"],
        "end": b["end"],
        "text": clean_text(text),
        "type": "speech",
        "words": all_words,
    }


# ============================================================
# STEP 3: Normalize silence
# ============================================================

def _normalize_silence(
    speech_scenes: List[Dict],
    target_max: float,
    silence_threshold: float,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Measure gaps between speech scenes.
    - Tiny gap (<0.05s): snap (end[i] = start[i+1])
    - Micro-pause (<silence_threshold): absorb into adjacent scene if scene_span <= target_max
    - Residual (>=silence_threshold): mark for B-ROLL

    Returns: (updated_speech_scenes, residual_gaps)
    """
    if len(speech_scenes) < 2:
        return speech_scenes, []

    speech_scenes = sorted(speech_scenes, key=lambda s: s["start"])
    residual_gaps = []

    for i in range(len(speech_scenes) - 1):
        cur = speech_scenes[i]
        nxt = speech_scenes[i + 1]
        gap_start = cur["end"]
        gap_end = nxt["start"]
        gap_dur = gap_end - gap_start

        if gap_dur < 0.05:
            # Tiny gap — snap
            nxt["start"] = cur["end"]

        elif gap_dur < silence_threshold:
            # Micro-pause — try absorb
            # Try absorb into current (extend cur.end)
            cur_new_dur = gap_end - cur["start"]
            if cur_new_dur <= target_max:
                cur["end"] = gap_end
                continue

            # Try absorb into next (move nxt.start earlier)
            nxt_new_dur = nxt["end"] - gap_start
            if nxt_new_dur <= target_max:
                nxt["start"] = gap_start
                continue

            # Can't absorb — becomes residual if >= silence_threshold after partial absorb
            # Try partial absorb: extend cur.end as far as possible
            max_cur_end = cur["start"] + target_max
            if max_cur_end > gap_start and max_cur_end < gap_end:
                cur["end"] = round(max_cur_end, 2)
                remaining_gap = gap_end - max_cur_end
                if remaining_gap >= silence_threshold:
                    residual_gaps.append({"start": max_cur_end, "end": gap_end})
                else:
                    # Remaining is small — try absorb into next
                    nxt_new_dur = nxt["end"] - max_cur_end
                    if nxt_new_dur <= target_max:
                        nxt["start"] = max_cur_end
                    # else: small gap remains, that's ok
            else:
                # Can't extend cur at all — leave gap as-is
                # If gap >= silence_threshold, it's residual
                if gap_dur >= silence_threshold:
                    residual_gaps.append({"start": gap_start, "end": gap_end})

        else:
            # Gap >= silence_threshold → residual for B-ROLL
            residual_gaps.append({"start": gap_start, "end": gap_end})

    return speech_scenes, residual_gaps


# ============================================================
# STEP 4: Generate B-ROLL
# ============================================================

def _generate_broll(
    residual_gaps: List[Dict],
    speech_scenes: List[Dict],
    chunk_min: float,
    chunk_max: float,
    silence_text: str,
) -> List[Dict]:
    """Generate B-ROLL silence scenes from residual gaps."""
    silence_scenes = []

    SILENCE_MIN = 2.0  # Minimum silence duration for b-roll (from spec)

    for gap in residual_gaps:
        gap_start = gap["start"]
        gap_end = gap["end"]
        gap_dur = gap_end - gap_start

        if gap_dur < SILENCE_MIN:
            continue

        # Short silence (2-6s): single b-roll scene
        # Long silence (>6s): split into 3-6s random chunks
        if gap_dur <= 6.0:
            chunks = [(round(gap_start, 2), round(gap_end, 2))]
        else:
            chunks = _split_silence_into_chunks(gap_start, gap_end, chunk_min, chunk_max)

        # Find surrounding speech for smart tagging
        prev_text = ""
        next_text = ""
        for sc in speech_scenes:
            if sc["end"] <= gap_start + 0.1:
                prev_text = sc.get("text", "")
            if sc["start"] >= gap_end - 0.1 and not next_text:
                next_text = sc.get("text", "")

        for chunk_start, chunk_end in chunks:
            tag = smart_silence_tag(prev_text, next_text, chunk_end - chunk_start, silence_text)
            silence_scenes.append({
                "start": round(chunk_start, 2),
                "end": round(chunk_end, 2),
                "text": tag,
                "type": "silence",
            })

    return silence_scenes


def _split_silence_into_chunks(
    start: float,
    end: float,
    chunk_min: float,
    chunk_max: float,
) -> List[Tuple[float, float]]:
    """Split a silence gap into random chunks of chunk_min to chunk_max seconds.
    Remainder >= 2.0s is kept as-is (valid short b-roll). < 2.0s merged into last chunk."""
    ABSOLUTE_MIN = 2.0  # silence spec minimum
    chunks = []
    cur = start

    while cur < end - 0.01:
        remain = end - cur
        if remain <= chunk_max * 1.2:
            # Last piece
            if remain >= ABSOLUTE_MIN:
                chunks.append((round(cur, 2), round(end, 2)))
            elif chunks:
                # Too short — extend previous chunk
                prev_start, _ = chunks[-1]
                chunks[-1] = (prev_start, round(end, 2))
            break
        else:
            chunk_dur = random.uniform(chunk_min, chunk_max)
            chunk_end = cur + chunk_dur
            chunks.append((round(cur, 2), round(chunk_end, 2)))
            cur = chunk_end

    return chunks


# ============================================================
# STEP 5: Assemble timeline
# ============================================================

def _assemble_timeline(
    speech_scenes: List[Dict],
    silence_scenes: List[Dict],
    audio_duration: float,
) -> List[Dict]:
    """
    Merge speech + silence into final timeline.
    Sort, assign scene_id and index. Enforce continuity.
    Ensures timeline covers [0.0, audio_duration] — leading/trailing gaps
    are filled with silence scenes.
    """
    timeline = speech_scenes + silence_scenes
    timeline.sort(key=lambda s: (s["start"], s["end"]))

    # ── Leading silence: [0.0 → first_scene.start] ──
    if timeline and timeline[0]["start"] > 0.05:
        first_start = timeline[0]["start"]
        next_text = timeline[0].get("text", "")
        tag = smart_silence_tag("", next_text, first_start, "[B-ROLL: INTRO]")
        timeline.insert(0, {
            "start": 0.0,
            "end": round(first_start, 2),
            "text": tag,
            "type": "silence",
        })

    # ── Trailing silence: [last_scene.end → audio_duration] ──
    if timeline and audio_duration > 0:
        last_end = timeline[-1]["end"]
        trailing_gap = audio_duration - last_end
        if trailing_gap > 0.05:
            prev_text = timeline[-1].get("text", "")
            tag = smart_silence_tag(prev_text, "", trailing_gap, "[B-ROLL: OUTRO]")
            timeline.append({
                "start": round(last_end, 2),
                "end": round(audio_duration, 2),
                "text": tag,
                "type": "silence",
            })

    # Enforce strict continuity: no overlaps, snap tiny gaps
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        cur = timeline[i]
        gap = cur["start"] - prev["end"]
        if gap < 0:
            # Overlap → clamp
            cur["start"] = prev["end"]
        elif 0 < gap <= 0.05:
            # Tiny gap (≤50ms) → snap by extending prev.end to cur.start
            # Nhỏ đến mức không đáng tạo silence scene, chỉ cần đóng kín
            mid = (prev["end"] + cur["start"]) / 2
            prev["end"] = mid
            cur["start"] = mid
        if cur["end"] <= cur["start"]:
            cur["end"] = cur["start"] + 0.01  # minimal

    # ── Fill dead gaps ──
    # Gaps giữa scenes mà _normalize_silence không absorb được.
    # Strategy:
    #   gap < 1s → absorb vào speech kế cận (cho phép tới SOFT_MAX 6.5s)
    #              vì silence <1s tạo B-ROLL chớp nhoáng, rất xấu khi render
    #   gap >= 1s → fill bằng silence scene (khoảng nghỉ đủ dài cho B-ROLL)
    _ABSORB_THRESHOLD = 1.0   # Gaps nhỏ hơn giá trị này sẽ được absorb
    _ABSORB_MAX_DUR   = 6.0   # HARD_MAX — absorb KHÔNG vượt quy tắc 6s

    filled: List[Dict] = []
    for i, scene in enumerate(timeline):
        if i > 0 and filled:
            prev_end = filled[-1]["end"]
            gap = scene["start"] - prev_end
            if gap > 0.05:
                if gap < _ABSORB_THRESHOLD:
                    # Micro-gap → absorb vào speech kế cận
                    prev = filled[-1]
                    prev_dur = prev["end"] - prev["start"]
                    next_dur = scene["end"] - scene["start"]
                    prev_is_speech = prev["type"] == "speech"
                    next_is_speech = scene["type"] == "speech"
                    prev_room = (_ABSORB_MAX_DUR - prev_dur) if prev_is_speech else 0
                    next_room = (_ABSORB_MAX_DUR - next_dur) if next_is_speech else 0

                    if prev_room >= gap and prev_room >= next_room:
                        # Extend prev.end → close gap
                        prev["end"] = scene["start"]
                    elif next_room >= gap:
                        # Move next.start back → close gap
                        scene["start"] = prev_end
                    elif prev_room + next_room >= gap:
                        # Split: prev absorb what it can, next absorb the rest
                        mid = prev_end + prev_room
                        prev["end"] = mid
                        scene["start"] = mid
                    else:
                        # Cả 2 đều full — fill bằng silence (hiếm, <1s)
                        prev_text = prev.get("text", "")
                        next_text = scene.get("text", "")
                        tag = smart_silence_tag(prev_text, next_text, gap, "[PAUSE]")
                        filled.append({
                            "start": round(prev_end, 2),
                            "end": round(scene["start"], 2),
                            "text": tag,
                            "type": "silence",
                        })
                else:
                    # Gap >= 1s → fill bằng silence scene (đủ dài cho B-ROLL)
                    prev_text = filled[-1].get("text", "")
                    next_text = scene.get("text", "")
                    tag = smart_silence_tag(prev_text, next_text, gap, "[PAUSE]")
                    filled.append({
                        "start": round(prev_end, 2),
                        "end": round(scene["start"], 2),
                        "text": tag,
                        "type": "silence",
                    })
        filled.append(scene)
    timeline = filled

    # Filter out degenerate segments
    timeline = [s for s in timeline if (s["end"] - s["start"]) >= 0.05]

    # ── Enforce [HARD_MIN, HARD_MAX] cho mọi scene ──
    timeline = _enforce_duration_limits(timeline)

    # Assign IDs
    for i, s in enumerate(timeline, start=1):
        s["scene_id"] = f"S{i:04d}"
        s["index"] = i

    # Round timestamps
    for s in timeline:
        s["start"] = round(s["start"], 2)
        s["end"] = round(s["end"], 2)

    return timeline


def _enforce_duration_limits(timeline: List[Dict]) -> List[Dict]:
    """Enforce [HARD_MIN, HARD_MAX] cho tất cả speech + silence.

    Lặp split→absorb cho đến khi không còn vi phạm hoặc hết iteration.
    """
    _TARGET_DUR = 4.0

    if not timeline:
        return timeline

    for iteration in range(5):  # Max 5 vòng lặp split→absorb
        changed = False

        # ── Split scenes > HARD_MAX ──
        split_result: List[Dict] = []
        for s in timeline:
            dur = s["end"] - s["start"]
            if dur > HARD_MAX + 0.01:
                chunks = _split_by_time(s, _TARGET_DUR, HARD_MIN, HARD_MAX)
                split_result.extend(chunks)
                changed = True
            else:
                split_result.append(s)
        timeline = split_result

        # ── Absorb scenes < HARD_MIN vào neighbor ──
        absorbed: List[Dict] = []
        for i, s in enumerate(timeline):
            dur = s["end"] - s["start"]
            if dur >= HARD_MIN - 0.01:
                absorbed.append(s)
                continue

            merged = False

            # Try merge vào TRƯỚC (ưu tiên nếu merged <= HARD_MAX)
            if absorbed:
                prev = absorbed[-1]
                merged_dur = s["end"] - prev["start"]
                if merged_dur <= HARD_MAX + 0.01:
                    prev["end"] = s["end"]
                    if s["type"] == "speech" and prev["type"] == "speech":
                        prev["text"] = prev["text"] + " " + s["text"]
                    merged = True
                    changed = True

            # Try merge vào SAU (nếu merge trước thất bại)
            if not merged and i + 1 < len(timeline):
                nxt = timeline[i + 1]
                merged_dur = nxt["end"] - s["start"]
                if merged_dur <= HARD_MAX + 0.01:
                    nxt["start"] = s["start"]
                    if s["type"] == "speech" and nxt["type"] == "speech":
                        nxt["text"] = s["text"] + " " + nxt["text"]
                    merged = True
                    changed = True

            # Fallback: Force merge vào TRƯỚC dù vượt HARD_MAX
            # → sẽ bị re-split ở iteration tiếp theo
            if not merged and absorbed:
                prev = absorbed[-1]
                prev["end"] = s["end"]
                if s["type"] == "speech" and prev["type"] == "speech":
                    prev["text"] = prev["text"] + " " + s["text"]
                merged = True
                changed = True

            if not merged:
                absorbed.append(s)

        timeline = absorbed

        if not changed:
            break

    # Convert speech scenes with very short text (<3 words) to silence
    # These are usually outro fragments, subscribe calls, or Whisper hallucinations
    for s in timeline:
        if s["type"] == "speech" and len(s["text"].split()) < 3:
            s["type"] = "silence"
            s["text"] = "[B-ROLL: PAUSE]"

    # Filter degenerate
    timeline = [s for s in timeline if (s["end"] - s["start"]) >= 0.05]

    return timeline


def _split_by_time(
    scene: Dict,
    target_dur: float,
    hard_min: float,
    hard_max: float,
) -> List[Dict]:
    """Split 1 scene dài thành chunks theo thời gian.

    Dùng khi scene không có words[] để split theo word boundary.
    Text được giữ nguyên cho chunk đầu, chunks sau dùng "..." (continuation).
    """
    start = scene["start"]
    end = scene["end"]
    total = end - start
    text = scene["text"]
    scene_type = scene["type"]

    # Tính số chunks cần thiết
    n_chunks = max(2, int(total / target_dur + 0.5))
    chunk_dur = total / n_chunks

    # Đảm bảo mỗi chunk >= hard_min
    if chunk_dur < hard_min:
        n_chunks = max(1, int(total / hard_min))
        chunk_dur = total / n_chunks

    # Nếu chỉ 1 chunk (total < hard_min * 2) → trả nguyên
    if n_chunks <= 1:
        return [scene]

    # Split text cho speech scenes
    if scene_type == "speech" and text:
        words_list = text.split()
        words_per_chunk = max(1, len(words_list) // n_chunks)
    else:
        words_list = []
        words_per_chunk = 0

    chunks: List[Dict] = []
    cur = start
    for ci in range(n_chunks):
        is_last = (ci == n_chunks - 1)
        chunk_end = end if is_last else round(cur + chunk_dur, 2)

        # Assign text + type — tránh consecutive duplicate (R9)
        chunk_type = scene_type
        if scene_type == "speech" and words_list:
            if len(words_list) >= n_chunks:
                # Đủ từ → chia đều
                w_start = ci * words_per_chunk
                w_end = len(words_list) if is_last else (ci + 1) * words_per_chunk
                chunk_text = " ".join(words_list[w_start:w_end]) or text
            else:
                # Ít từ hơn chunks → speech dài nhưng Whisper chỉ bắt vài từ
                # = outro/channel promotion → chuyển thành silence
                chunk_type = "silence"
                chunk_text = "[B-ROLL: OUTRO]"
        elif scene_type == "silence":
            chunk_text = scene.get("text", "[B-ROLL]")
        else:
            chunk_text = text

        chunks.append({
            "start": round(cur, 2),
            "end": round(chunk_end, 2),
            "text": chunk_text,
            "type": chunk_type,
        })
        cur = chunk_end

    return chunks
