"""
PATCHED VERSION: engine/assemble.py
Fix: WinError 206 - Batch xfade processing for large segment counts
Fix (NEW): xfade timebase mismatch (1/1000000 vs 1/30) by normalizing timebase ONLY at xfade boundaries (optimal, không bật transition 100%)

Changes from original:
1. Added _batch_xfade_concat() function (new)
2. Modified build_video_from_timeline() lines 10890-10940
3. Added import math
4. ✅ NEW: Patch _build_xfade_filter() to force consistent video timebase BEFORE every xfade using settb=1/30 (only at transition cuts)

✅ NEW (this patch request): Random transition type for 4 modes (fade/dissolve/zoom/whip_pan)
- ONLY touches transition-related area:
  - Adds helpers to pick transition type (random/weights/cooldown)
  - Updates _build_xfade_filter() to use chosen transition type instead of hard-coded fade
  - Updates _batch_xfade_concat() to pass cfg into _build_xfade_filter()
- DOES NOT change other pipeline logic or unrelated functions.

Installation:
1. Backup: copy engine\assemble.py engine\assemble.py.backup
2. Replace: copy this file to engine\assemble.py
3. Test: Run pipeline with transitions enabled
"""

import json
import os
import subprocess
import math
import random  # ✅ NEW: for random transition type selection
import numpy as np
from ..tuong_thich.log import info, error, warn
from ..tuong_thich.paths import ensure_dir
from ..tuong_thich.ffmpeg import probe_duration


def _resolve_clip_path(clip_path: str, workdir: str) -> str:
    """
    Resolve clip path to absolute path, handling both relative and absolute paths.

    This function fixes the path mismatch issue where timeline.json contains absolute paths
    but files are located relative to workdir.

    Args:
        clip_path: Path from timeline.json (can be absolute or relative)
        workdir: Current working directory (usually contains timeline.json)

    Returns:
        Absolute path to the video file

    Raises:
        FileNotFoundError: If video file cannot be found
    """
    # If already absolute and exists, use it
    if os.path.isabs(clip_path):
        if os.path.exists(clip_path):
            return clip_path

        # Absolute path doesn't exist - try to extract relative part
        # e.g., D:\AUTO-DUNGVIDEO\AUTO-TRUONG\workdir_bot\row11_xxx\_sanitized_videos\001-*.mp4
        #    -> _sanitized_videos/001-*.mp4
        parts = clip_path.replace('\\', '/').split('/')

        # Strategy 1: Find _sanitized_videos in path
        if '_sanitized_videos' in parts:
            idx = parts.index('_sanitized_videos')
            rel_path = '/'.join(parts[idx:])
            rel_path = rel_path.replace('/', os.sep)  # Convert to OS-specific separator

            # Try relative to workdir
            candidate = os.path.join(workdir, rel_path)
            if os.path.exists(candidate):
                info("path_resolved", original=clip_path, resolved=candidate, method="sanitized_videos_extraction")
                return candidate

        # Strategy 2: Just use filename and look in _sanitized_videos
        filename = os.path.basename(clip_path)
        candidate = os.path.join(workdir, '_sanitized_videos', filename)
        if os.path.exists(candidate):
            info("path_resolved", original=clip_path, resolved=candidate, method="filename_only")
            return candidate

        # Strategy 3: Try clips folder
        candidate = os.path.join(workdir, 'clips', filename)
        if os.path.exists(candidate):
            info("path_resolved", original=clip_path, resolved=candidate, method="clips_folder")
            return candidate

    # If relative path, resolve from workdir
    else:
        candidate = os.path.join(workdir, clip_path)
        if os.path.exists(candidate):
            return candidate

    # File not found - raise detailed error
    raise FileNotFoundError(
        f"Video clip not found: {clip_path}\n"
        f"Searched locations:\n"
        f"  1. Original path: {clip_path}\n"
        f"  2. Relative to workdir: {os.path.join(workdir, clip_path)}\n"
        f"  3. In _sanitized_videos: {os.path.join(workdir, '_sanitized_videos', os.path.basename(clip_path))}\n"
        f"  4. In clips: {os.path.join(workdir, 'clips', os.path.basename(clip_path))}\n"
        f"Workdir: {workdir}\n"
        f"Please check if video files exist in the expected location."
    )


def _run(cmd: list[str], show_output: bool = True, timeout: float = 1800):
    """
    Run a subprocess command.
    - show_output=True: print ffmpeg output if error happens
    [Phase 7] timeout=1800s (30 phút) — concat 87+ segments hoặc encode video dài
    có thể mất 10-25 phút thực. > 30 phút = chắc chắn hang.
    """
    try:
        if show_output:
            return subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=True, timeout=timeout,
            )
        else:
            return subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                check=True, timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        error("ffmpeg_timeout", cmd=" ".join(cmd[:6]) + "...",
              timeout_s=timeout)
        raise RuntimeError(
            f"FFmpeg timeout ({timeout:.0f}s) at assemble: {' '.join(cmd[:6])}..."
        )
    except subprocess.CalledProcessError as e:
        out = e.stdout if hasattr(e, "stdout") else None
        if out:
            error("ffmpeg_failed", cmd=" ".join(cmd), ffmpeg_output=out[-4000:])
        else:
            error("ffmpeg_failed", cmd=" ".join(cmd), ffmpeg_output="(no output captured)")
        raise


def _ffmpeg_path(p: str) -> str:
    """
    FFmpeg concat demuxer on Windows behaves better with forward slashes.
    Also escape single quotes safely for concat list.
    """
    p = os.path.abspath(p)
    p = p.replace("\\", "/")
    p = p.replace("'", "\\'")
    return p


# ============================
# GPU / CODEC HELPERS
# ============================

def _is_nvenc(vcodec: str) -> bool:
    v = (vcodec or "").strip().lower()
    return v in ("h264_nvenc", "hevc_nvenc")


def _video_encode_args(vcodec: str) -> list[str]:
    """
    Return encoder args based on vcodec.
    - libx264: preset veryfast + CRF + bitrate target
    - NVENC: preset p5 + CQ + bitrate control (GPU encode)

    Target bitrate: 30-35Mbps for 1080p quality
    """
    v = (vcodec or "libx264").strip().lower()

    # NVIDIA NVENC (GPU)
    if _is_nvenc(v):
        # High quality settings for 1080p:
        # - CQ 18 (better quality than 19)
        # - Target bitrate 32M (30-35M range)
        # - Max bitrate 40M (allow peaks for complex scenes)
        # - Bufsize 64M (2x maxrate for smooth rate control)
        return [
            "-c:v", v,
            "-preset", "p7",      # [16GB] p5 -> p7: chat luong NVENC cao nhat
            "-rc", "vbr",
            "-cq", "16",          # [16GB] 18 -> 16: bitrate cao hon, net hon
            "-b:v", "32M",      # Target bitrate 32Mbps
            "-maxrate", "40M",  # Max bitrate 40Mbps
            "-bufsize", "64M",  # Buffer size
        ]

    # Default CPU encoder (libx264, libx265, etc.)
    # CRF 18 + bitrate target for consistent quality
    return [
        "-c:v", v,
        "-preset", "veryfast",
        "-crf", "18",           # Constant Rate Factor (18 = high quality)
        "-b:v", "32M",          # Target bitrate 32Mbps
        "-maxrate", "40M",      # Max bitrate 40Mbps
        "-bufsize", "64M",      # Buffer size
    ]


def _audio_encode_args() -> list[str]:
    return [
        "-c:a", "aac",
        "-ar", "48000",
        "-ac", "2",
    ]


def _common_mov_args() -> list[str]:
    return ["-movflags", "+faststart"]


# ============================
# TRANSITIONS (Stage 2 Rules)
# ============================

def _seg_type(seg: dict) -> str:
    return (seg.get("type") or "").strip().lower()


def _seg_text(seg: dict) -> str:
    return (seg.get("text") or "").strip()


def _seg_duration(seg: dict) -> float:
    e = float(seg.get("end", 0.0))
    s = float(seg.get("start", 0.0))
    return max(0.0, e - s)


def _is_speech(seg: dict) -> bool:
    return _seg_type(seg) == "speech"


def _is_silence(seg: dict) -> bool:
    return _seg_type(seg) == "silence"


def _broll_tag(seg: dict) -> str | None:
    txt = _seg_text(seg)
    if not txt:
        return None
    # [B-ROLL: TRANSITION] → extract TRANSITION
    # [B-ROLL / PAUSE] → extract PAUSE
    # [B-ROLL: ENVIRONMENT] → extract ENVIRONMENT
    lower = txt.lower()
    if "b-roll" in lower or "broll" in lower:
        # Remove prefix
        for prefix in ["[b-roll:", "[broll:", "[b-roll /", "[broll /"]:
            if prefix in lower:
                after = txt[lower.index(prefix) + len(prefix):]
                after = after.replace("]", "").strip().upper()
                if after:
                    return after
    return None


def _clamp(val: float, minv: float, maxv: float) -> float:
    return max(minv, min(maxv, val))


def _get_transition_cfg(cfg: dict) -> dict:
    """
    transitions:
      enable: true
      type: fade
      only_broll_boundaries: true
      min_scene_s: 3.0

      # Fade duration control
      dur_default_s: 0.22
      dur_min_s: 0.18
      dur_max_s: 0.28
      tag_overrides:
        TRANSITION: 0.20
        ENVIRONMENT: 0.24
        PAUSE: 0.28

      # Optional fallback: speech->speech selective (NOT 100%)
      enable_speech_to_speech: true
      speech_to_speech:
        enable: true
        min_scene_s: 5.0
        max_ratio: 0.20
        cooldown_cuts: 3

      # ✅ NEW (pipeline.yaml):
      # random_type: true
      # type_weights: {fade: 0.30, dissolve: 0.40, zoom: 0.20, whip_pan: 0.10}
      # cooldown_same_type: 2
    """
    return (cfg or {}).get("transitions", {}) or {}


def _get_s2s_cfg(cfg: dict) -> dict:
    tcfg = _get_transition_cfg(cfg)
    return (tcfg.get("speech_to_speech", {}) or {}) if tcfg else {}


# ============================
# ✅ NEW: Transition Type Picker (ONLY used at xfade boundaries)
# ============================

def _normalize_xfade_transition_name(name: str) -> str:
    """
    Map friendly names (pipeline.yaml) -> FFmpeg xfade transition names.

    Supported (requested):
      fade      -> fade
      dissolve  -> dissolve
      zoom      -> zoomin
      whip_pan  -> hrwind

    Also accept:
      zoomin, hrwind, hlwind directly.
    """
    t = (name or "").strip().lower()
    if not t:
        return "fade"

    alias = {
        "fade": "fade",
        "dissolve": "dissolve",
        "cross_dissolve": "dissolve",
        "crossdissolve": "dissolve",
        "zoom": "zoomin",
        "zoom_transition": "zoomin",
        "zoomin": "zoomin",
        "whip": "hrwind",
        "whip_pan": "hrwind",
        "whippan": "hrwind",
        "hrwind": "hrwind",
        "hlwind": "hlwind",
        # legacy config values:
        "wipe": "hrwind",   # treat wipe as whip-like wind (keeps legacy harmless)
    }
    return alias.get(t, t)


def _pick_weighted_transition(weights: dict, banned: set[str]) -> str | None:
    """
    Weighted random pick from weights dict excluding banned keys.
    Returns None if nothing eligible.
    """
    items = []
    total = 0.0
    for k, v in (weights or {}).items():
        if not k:
            continue
        kk = str(k).strip().lower()
        if kk in banned:
            continue
        try:
            w = float(v)
        except Exception:
            continue
        if w <= 0.0:
            continue
        items.append((kk, w))
        total += w

    if not items or total <= 0.0:
        return None

    r = random.random() * total
    acc = 0.0
    for kk, w in items:
        acc += w
        if r <= acc:
            return kk
    return items[-1][0]


def _choose_transition_type_for_cut(cfg: dict, recent_types: list[str]) -> str:
    """
    Choose transition type for ONE cut (only when a transition is applied).
    Respects:
      - transitions.type (fallback)
      - transitions.random_type
      - transitions.type_weights
      - transitions.cooldown_same_type
    """
    tcfg = _get_transition_cfg(cfg)

    fallback = _normalize_xfade_transition_name(str(tcfg.get("type", "fade")))

    random_on = bool(tcfg.get("random_type", False))
    if not random_on:
        return fallback

    weights_raw = tcfg.get("type_weights", {}) or {}
    if not isinstance(weights_raw, dict) or not weights_raw:
        return fallback

    cooldown_same = int(tcfg.get("cooldown_same_type", 0) or 0)
    banned: set[str] = set()
    if cooldown_same > 0 and recent_types:
        # ban last N chosen types
        for t in recent_types[-cooldown_same:]:
            if t:
                banned.add(str(t).strip().lower())

    picked = _pick_weighted_transition(weights_raw, banned)
    if not picked:
        # if everything is banned, try again without bans
        picked = _pick_weighted_transition(weights_raw, set())
    if not picked:
        return fallback

    return _normalize_xfade_transition_name(picked)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    if a is None or b is None:
        return 0.0
    try:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    except (ValueError, ZeroDivisionError):
        return 0.0


def _has_discourse_marker(text: str, markers: list[str]) -> bool:
    """
    Check if text contains discourse marker (Vietnamese or English).

    Supports both:
    - Start of sentence: "However, the wind changed..."
    - Mid-sentence after punctuation: "The wind died. But suddenly..."
    - Word boundaries: Detects whole words only (not substrings)
    """
    if not text or not markers:
        return False
    text_lower = text.strip().lower()

    # Check each marker
    for marker in markers:
        marker_lower = marker.lower()

        # Method 1: Starts with marker (original behavior)
        if text_lower.startswith(marker_lower):
            return True

        # Method 2: Marker after punctuation with space (e.g., ". but", "! however")
        # Common punctuation: period, exclamation, question mark
        for punct in ['. ', '! ', '? ', '; ', ', ']:
            pattern = punct + marker_lower
            if pattern in text_lower:
                # Check if it's a whole word (not substring)
                idx = text_lower.find(pattern)
                after_idx = idx + len(pattern)
                # Check character after marker is space or end of string
                if after_idx >= len(text_lower) or text_lower[after_idx] in [' ', '.', ',', '!', '?', ';']:
                    return True

    return False


def _calculate_hybrid_transition_score(
    cfg: dict,
    prev_seg: dict,
    cur_seg: dict,
    prev_embed: np.ndarray | None,
    cur_embed: np.ndarray | None,
    time_since_last_s: float
) -> tuple[bool, float, dict]:
    """
    Calculate hybrid transition score using multiple signals.

    Returns:
        (should_apply, duration, debug_info)
    """
    s2s_cfg = _get_s2s_cfg(cfg)
    hybrid_cfg = s2s_cfg.get("hybrid", {})

    if not hybrid_cfg.get("enable", False):
        return False, 0.0, {"reason": "hybrid_disabled"}

    # Config (OPTIMIZED for speech-to-speech transitions - Version 2.3.0)
    # Threshold lowered from 0.6 to 0.3 to increase transition detection
    threshold = float(hybrid_cfg.get("threshold", 0.3))
    weights = hybrid_cfg.get("weights", {})
    w_semantic = float(weights.get("semantic", 0.35))
    w_text = float(weights.get("text_marker", 0.35))
    w_gap = float(weights.get("temporal_gap", 0.25))  # Increased from 0.20 to 0.25
    w_duration = float(weights.get("duration_bonus", 0.10))

    semantic_threshold = float(hybrid_cfg.get("semantic_threshold", 0.65))
    gap_threshold_s = float(hybrid_cfg.get("gap_threshold_s", 0.2))  # Lowered from 0.5 to 0.2
    min_interval_s = float(hybrid_cfg.get("min_interval_s", 10.0))  # Lowered from 20.0 to 10.0
    discourse_markers = hybrid_cfg.get("discourse_markers", [])

    score = 0.0
    debug = {}

    # Signal 1: Semantic similarity (CLIP embeddings)
    if prev_embed is not None and cur_embed is not None:
        similarity = _cosine_similarity(prev_embed, cur_embed)
        # Lower similarity = topic change = higher score
        semantic_score = max(0.0, 1.0 - similarity) * w_semantic
        score += semantic_score
        debug["semantic"] = {"similarity": round(similarity, 3), "score": round(semantic_score, 3)}
    else:
        debug["semantic"] = {"similarity": None, "score": 0.0, "reason": "no_embeddings"}

    # Signal 2: Text markers (discourse markers)
    cur_text = cur_seg.get("text", "")
    has_marker = _has_discourse_marker(cur_text, discourse_markers)
    text_score = w_text if has_marker else 0.0
    score += text_score
    debug["text_marker"] = {"found": has_marker, "score": round(text_score, 3)}
    if has_marker:
        # Find which marker
        for marker in discourse_markers:
            if cur_text.strip().lower().startswith(marker.lower()):
                debug["text_marker"]["marker"] = marker
                break

    # Signal 3: Temporal gap (pause duration)
    gap_s = float(cur_seg.get("start", 0.0)) - float(prev_seg.get("end", 0.0))
    gap_score = 0.0
    if gap_s >= gap_threshold_s:
        gap_score = min(w_gap, gap_s * 0.1)
    score += gap_score
    debug["temporal_gap"] = {"gap_s": round(gap_s, 2), "score": round(gap_score, 3)}

    # Signal 4: Duration bonus (longer scenes = more confident)
    # Threshold lowered from 7.0 to 5.0 for more flexibility (Version 2.3.0)
    prev_dur = _seg_duration(prev_seg)
    cur_dur = _seg_duration(cur_seg)
    min_dur = min(prev_dur, cur_dur)
    duration_score = w_duration if min_dur >= 5.0 else 0.0
    score += duration_score
    debug["duration"] = {"min_dur": round(min_dur, 2), "score": round(duration_score, 3)}

    # Penalty: Too frequent (time since last transition)
    # Penalty reduced from 0.5 to 0.7 (less harsh) - Version 2.3.0
    if time_since_last_s < min_interval_s:
        penalty_factor = 0.7
        score *= penalty_factor
        debug["penalty"] = {"reason": "too_frequent", "interval_s": round(time_since_last_s, 2), "factor": penalty_factor}

    # Final decision
    debug["total_score"] = round(score, 3)
    debug["threshold"] = threshold
    debug["decision"] = score >= threshold

    should_apply = score >= threshold
    duration = _transition_duration(cfg, None) if should_apply else 0.0

    return should_apply, duration, debug


def _transition_duration(cfg: dict, tag: str | None) -> float:
    tcfg = _get_transition_cfg(cfg)
    dur_default = float(tcfg.get("dur_default_s", 0.22))
    dur_min = float(tcfg.get("dur_min_s", 0.18))
    dur_max = float(tcfg.get("dur_max_s", 0.28))

    if tag:
        overrides = tcfg.get("tag_overrides", {}) or {}
        if tag in overrides:
            try:
                dur_default = float(overrides[tag])
            except Exception:
                pass

    return _clamp(dur_default, dur_min, dur_max)


def _broll_boundary_transition(cfg: dict, prev_seg: dict, cur_seg: dict) -> tuple[bool, float]:
    """
    Primary rule:
    - Only at B-ROLL cluster boundaries: speech<->silence
    - NOT inside silence->silence clusters
    - Only if both sides >= min_scene_s
    """
    tcfg = _get_transition_cfg(cfg)
    if not bool(tcfg.get("enable", False)):
        return (False, 0.0)

    min_scene_s = float(tcfg.get("min_scene_s", 3.0))
    only_broll_boundaries = bool(tcfg.get("only_broll_boundaries", True))

    prev_d = _seg_duration(prev_seg)
    cur_d = _seg_duration(cur_seg)
    if prev_d < min_scene_s or cur_d < min_scene_s:
        return (False, 0.0)

    prev_is_speech = _is_speech(prev_seg)
    prev_is_silence = _is_silence(prev_seg)
    cur_is_speech = _is_speech(cur_seg)
    cur_is_silence = _is_silence(cur_seg)

    # If you want boundary-only: only speech<->silence
    if only_broll_boundaries:
        if prev_is_speech and cur_is_silence:
            tag = _broll_tag(cur_seg)
            return (True, _transition_duration(cfg, tag))
        if prev_is_silence and cur_is_speech:
            tag = _broll_tag(prev_seg)
            return (True, _transition_duration(cfg, tag))
        return (False, 0.0)

    # Otherwise apply everywhere (but you said you DON'T want 100%)
    # We'll still keep this conservative:
    if prev_is_silence and cur_is_silence:
        return (False, 0.0)

    return (True, _transition_duration(cfg, None))


def _apply_speech_to_speech_fallback(
    cfg: dict,
    seg_meta: list[dict],
    apply: list[tuple[bool, float]],
    embeddings: list[np.ndarray] | None = None
) -> tuple[list[tuple[bool, float]], int]:
    """
    Fallback rule for speech->speech cuts (selective).

    Supports TWO modes:
    1. HYBRID (new): Multi-signal scoring (semantic + text markers + temporal + duration)
    2. SIMPLE_RATIO (current): Deterministic ratio-based selection

    Args:
        cfg: Config dict
        seg_meta: Segment metadata with text, start, end, type
        apply: Current transition decisions [(bool, duration), ...]
        embeddings: Optional list of CLIP embeddings for each segment

    Returns:
        (updated_apply, added_count)
    """
    tcfg = _get_transition_cfg(cfg)
    if not bool(tcfg.get("enable", False)):
        return apply, 0

    if not bool(tcfg.get("enable_speech_to_speech", False)):
        return apply, 0

    s2s = _get_s2s_cfg(cfg)
    if not bool(s2s.get("enable", True)):
        return apply, 0

    n = len(seg_meta)
    if n < 2:
        return apply, 0

    # Get mode: hybrid / simple_ratio
    mode = s2s.get("mode", "simple_ratio")

    # ========================================
    # MODE: HYBRID (Multi-Signal Scoring)
    # ========================================
    if mode == "hybrid":
        hybrid_cfg = s2s.get("hybrid", {})
        min_scene_s = float(hybrid_cfg.get("min_scene_s", 5.0))

        total_cuts = n - 1
        time_accumulator = 0.0
        last_transition_time = 0.0
        added = 0

        for cut_i in range(total_cuts):
            # Skip if already has transition (B-ROLL)
            ok0, d0 = apply[cut_i]
            if ok0 and d0 > 0.0:
                time_accumulator += _seg_duration(seg_meta[cut_i])
                last_transition_time = time_accumulator
                continue

            prev_seg = seg_meta[cut_i]
            cur_seg = seg_meta[cut_i + 1]

            # Only speech->speech
            if not (_is_speech(prev_seg) and _is_speech(cur_seg)):
                time_accumulator += _seg_duration(prev_seg)
                continue

            # Duration check
            if _seg_duration(prev_seg) < min_scene_s or _seg_duration(cur_seg) < min_scene_s:
                time_accumulator += _seg_duration(prev_seg)
                continue

            # Get embeddings for scoring
            prev_embed = embeddings[cut_i] if embeddings and cut_i < len(embeddings) else None
            cur_embed = embeddings[cut_i + 1] if embeddings and cut_i + 1 < len(embeddings) else None

            # Calculate hybrid score
            time_since_last = time_accumulator - last_transition_time
            should_apply, dur, debug_info = _calculate_hybrid_transition_score(
                cfg, prev_seg, cur_seg, prev_embed, cur_embed, time_since_last
            )

            if should_apply:
                apply[cut_i] = (True, dur)
                added += 1
                last_transition_time = time_accumulator

                # Log decision (first 5 + every 10th)
                if added <= 5 or added % 10 == 0:
                    info("s2s_hybrid_transition_added",
                         cut_index=cut_i,
                         scene_prev=cut_i,
                         scene_cur=cut_i + 1,
                         score=debug_info.get("total_score"),
                         threshold=debug_info.get("threshold"),
                         details=debug_info)

            time_accumulator += _seg_duration(prev_seg)

        info("s2s_hybrid_done", mode="hybrid", added=added, total_cuts=total_cuts)
        return apply, added

    # ========================================
    # MODE: SIMPLE_RATIO (Current Logic)
    # ========================================
    elif mode == "simple_ratio":
        simple_cfg = s2s.get("simple_ratio", {})
        s2s_min_scene_s = float(simple_cfg.get("min_scene_s", 5.0))
        max_ratio = float(simple_cfg.get("max_ratio", 0.20))
        cooldown_cuts = int(simple_cfg.get("cooldown_cuts", 3))

        # Clamp ratio sane
        if max_ratio <= 0.0:
            return apply, 0
        if max_ratio > 0.60:
            max_ratio = 0.60

        total_cuts = n - 1
        max_total_transitions = int(total_cuts * max_ratio)

        # Already used transitions from B-ROLL
        already = sum(1 for ok, d in apply if ok and d > 0.0)
        remaining_budget = max(0, max_total_transitions - already)
        if remaining_budget <= 0:
            return apply, 0

        # Deterministic selection
        step = max(1, int(round(1.0 / max_ratio)))
        cooldown = 0
        added = 0

        for cut_i in range(total_cuts):
            if added >= remaining_budget:
                break

            ok0, d0 = apply[cut_i]
            if ok0 and d0 > 0.0:
                cooldown = cooldown_cuts
                continue

            if cooldown > 0:
                cooldown -= 1
                continue

            prev_seg = seg_meta[cut_i]
            cur_seg = seg_meta[cut_i + 1]

            if not (_is_speech(prev_seg) and _is_speech(cur_seg)):
                continue

            if _seg_duration(prev_seg) < s2s_min_scene_s or _seg_duration(cur_seg) < s2s_min_scene_s:
                continue

            if cut_i % step == 0:
                dur = _transition_duration(cfg, None)
                apply[cut_i] = (True, dur)
                added += 1
                cooldown = cooldown_cuts

        info("s2s_simple_done", mode="simple_ratio", added=added, total_cuts=total_cuts)
        return apply, added

    # Unknown mode - return unchanged
    warn("s2s_unknown_mode", mode=mode)
    return apply, 0


def _has_audio_stream(video_path: str) -> bool:
    """
    Check if video file has audio stream.
    Returns True if audio stream exists, False otherwise.
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return bool(result.stdout.strip())
    except Exception:
        # If ffprobe fails, assume video has audio (safer default)
        return True


def _build_xfade_filter(
    seg_files: list[str],
    seg_durs: list[float],
    apply: list[tuple[bool, float]],
    n: int,
    cfg: dict | None = None  # ✅ NEW: pass cfg to choose transition type (default None keeps old behavior)
) -> tuple[str, float, int]:
    """
    Build filter_complex chain:
    - Normalize PTS
    - Generate silent audio for videos without audio
    - If transition => xfade + acrossfade
    - Else => concat

    ✅ Patch (optimal):
    - Only normalize timebase at xfade boundaries (settb=1/30), to avoid mismatch
      where v_prev may come from concat output with timebase 1/1000000.

    ✅ NEW:
    - Transition type can be randomized per-cut (fade/dissolve/zoomin/hrwind)
      controlled by cfg["transitions"] keys:
        random_type, type_weights, cooldown_same_type, type (fallback)

    Args:
        seg_files: List of video file paths (needed to check audio streams)
        seg_durs: List of segment durations
        apply: List of (use_transition, duration) tuples
        n: Number of segments
        cfg: Pipeline cfg dict (optional)

    Returns:
        (filter_complex_string, total_duration, transitions_count)
    """
    parts = []

    # Check which videos have audio
    has_audio = [_has_audio_stream(seg_files[i]) for i in range(n)]

    # Normalize PTS and fps for each input
    for i in range(n):
        # Keep per-input normalization (helps consistency)
        parts.append(f"[{i}:v]fps=30,setsar=1,setpts=PTS-STARTPTS[v{i}]")

        if has_audio[i]:
            parts.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}]")
        else:
            # Generate silent audio (do not touch existing structure beyond needed)
            dur = seg_durs[i]
            parts.append(f"anullsrc=channel_layout=stereo:sample_rate=48000:duration={dur:.3f}[a{i}]")

    v_prev = "v0"
    a_prev = "a0"
    total = float(seg_durs[0]) if seg_durs else 0.0
    transitions_count = 0

    # ✅ NEW: remember chosen transition types to apply cooldown_same_type
    recent_tr_types: list[str] = []

    for i in range(1, n):
        use_tr, d = apply[i - 1]
        d = float(d)

        if use_tr and d > 0.0:
            transitions_count += 1
            offset = max(0.0, total - d)

            # ✅ CRITICAL FIX:
            # v_prev might be output of concat => timebase can become 1/1000000
            # Normalize BOTH sides timebase right before xfade, without changing structure elsewhere.
            vprev_tb = f"vprev_tb{i}"
            vi_tb = f"v{i}tb"
            parts.append(f"[{v_prev}]settb=1/30[{vprev_tb}]")
            parts.append(f"[v{i}]settb=1/30[{vi_tb}]")

            # ✅ NEW: pick transition type (random/weights/cooldown) ONLY for this xfade
            if cfg is not None:
                tr_name = _choose_transition_type_for_cut(cfg, recent_tr_types)
            else:
                tr_name = "fade"  # safe default if cfg not provided

            recent_tr_types.append(tr_name)

            parts.append(
                f"[{vprev_tb}][{vi_tb}]"
                f"xfade=transition={tr_name}:duration={d:.3f}:offset={offset:.3f}"
                f"[v{i}m]"
            )
            parts.append(f"[{a_prev}][a{i}]acrossfade=d={d:.3f}:c1=tri:c2=tri[a{i}m]")

            v_prev = f"v{i}m"
            a_prev = f"a{i}m"
            total = total + float(seg_durs[i]) - d
        else:
            parts.append(f"[{v_prev}][v{i}]concat=n=2:v=1:a=0[v{i}m]")
            parts.append(f"[{a_prev}][a{i}]concat=n=2:v=0:a=1[a{i}m]")
            v_prev = f"v{i}m"
            a_prev = f"a{i}m"
            total = total + float(seg_durs[i])

    # Final output normalize (kept)
    parts.append(f"[{v_prev}]fps=30,format=yuv420p[vout]")
    parts.append(f"[{a_prev}]anull[aout]")

    return ";".join(parts), total, transitions_count


# ============================================================================
# NEW: Batch xfade processing to avoid command line length limit
# ============================================================================

def _batch_xfade_concat(
    seg_files: list[str],
    seg_durs: list[float],
    seg_meta: list[dict],
    apply: list[tuple[bool, float]],
    cfg: dict,
    out_video_abs: str,
    tmp_dir: str,
    vcodec: str,
    fps: int,
    width: int,
    height: int
) -> tuple[int, int]:
    """
    Process xfade transitions in batches to avoid Windows command line limit.

    Strategy:
    1. Divide segments into batches of MAX_BATCH_SIZE
    2. Apply xfade within each batch (small command)
    3. Concat all batches using demuxer (safe for any number)

    Returns:
        (total_transitions, num_batches)
    """
    MAX_BATCH_SIZE = 8  # Xfade filter stable limit

    n_total = len(seg_files)
    n_batches = math.ceil(n_total / MAX_BATCH_SIZE)

    info("xfade_batch_start",
         total_segments=n_total,
         batch_size=MAX_BATCH_SIZE,
         num_batches=n_batches)

    batch_outputs = []
    total_transitions = 0

    # ========================================
    # Phase 1: Process each batch with xfade
    # ========================================
    for batch_idx in range(n_batches):
        start_idx = batch_idx * MAX_BATCH_SIZE
        end_idx = min(start_idx + MAX_BATCH_SIZE, n_total)
        batch_size = end_idx - start_idx

        batch_segs = seg_files[start_idx:end_idx]
        batch_durs = seg_durs[start_idx:end_idx]

        batch_apply = []
        for i in range(start_idx, end_idx - 1):
            if i < len(apply):
                batch_apply.append(apply[i])
            else:
                batch_apply.append((False, 0.0))

        # ✅ ONLY CHANGE HERE: pass cfg into _build_xfade_filter (transition-only)
        fc, est_dur, tr_count = _build_xfade_filter(batch_segs, batch_durs, batch_apply, batch_size, cfg=cfg)
        total_transitions += tr_count

        batch_out = os.path.join(tmp_dir, f"xfade_batch_{batch_idx:03d}.mp4")

        inputs = []
        for p in batch_segs:
            inputs += ["-i", p]

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", "[aout]",
            *_video_encode_args(vcodec),
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-s", f"{width}x{height}",
            *_audio_encode_args(),
            *_common_mov_args(),
            batch_out
        ]

        info("xfade_batch_processing",
             batch=f"{batch_idx+1}/{n_batches}",
             segments=f"{start_idx+1}-{end_idx}",
             transitions=tr_count,
             output=batch_out)

        _run(cmd, show_output=True)
        batch_outputs.append(batch_out)

    # ========================================
    # Phase 2: Concat all batches
    # ========================================
    if len(batch_outputs) == 1:
        import shutil
        shutil.move(batch_outputs[0], out_video_abs)
        info("xfade_batch_done_single",
             output=out_video_abs,
             transitions=total_transitions)
    else:
        final_concat_list = os.path.join(tmp_dir, "xfade_batches_concat.txt")
        with open(final_concat_list, "w", encoding="utf-8", newline="\n") as f:
            for p in batch_outputs:
                f.write(f"file '{_ffmpeg_path(p)}'\n")

        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", _ffmpeg_path(final_concat_list),
            "-c:v", "copy",
            "-c:a", "copy",
            *_common_mov_args(),
            out_video_abs
        ]

        info("xfade_batch_concat_start",
             batches=len(batch_outputs),
             method="demuxer_copy")

        _run(concat_cmd, show_output=True)

        info("xfade_batch_done_multi",
             output=out_video_abs,
             batches=len(batch_outputs),
             transitions=total_transitions)

    return total_transitions, n_batches


# ============================================================================
# Main function - build_video_from_timeline (MODIFIED)
# ============================================================================

def build_video_from_timeline(cfg: dict, timeline: list[dict], out_video: str):
    """
    Build base video from timeline:
    - Create trimmed/re-encoded segment mp4 (uniform params)
    - If transitions enabled: xfade_batched (batch processing to avoid command line limit)
    - Else: concat demuxer -> COPY streams (NO re-encode, super fast, low CPU)
    """
    out_dir = os.path.dirname(os.path.abspath(out_video))
    tmp_dir = ensure_dir(os.path.join(out_dir, "tmp_segments"))

    width = int(cfg["output"]["width"])
    height = int(cfg["output"]["height"])
    fps = int(cfg["output"]["fps"])
    vcodec = str(cfg["output"]["video_codec"])

    seg_files: list[str] = []
    seg_durs: list[float] = []
    seg_meta: list[dict] = []

    info("build_video_start",
         timeline_entries=len(timeline),
         output=out_video,
         workdir=out_dir)

    # 1) Create uniform segments
    for i, t in enumerate(timeline):
        seg = t["segment"]
        src_original = t["clip"]["file"]

        try:
            src = _resolve_clip_path(src_original, out_dir)
        except FileNotFoundError as e:
            error("clip_not_found",
                  segment_index=i,
                  scene_id=t.get("scene_id", "unknown"),
                  original_path=src_original,
                  error_detail=str(e))
            raise

        if i % 10 == 0 or i < 3:
            info("processing_segment",
                 index=i,
                 total=len(timeline),
                 scene_id=t.get("scene_id", "unknown"),
                 original_path=src_original if src_original != src else None,
                 resolved_path=src if src_original != src else None)

        dur = max(0.05, float(seg["end"] - seg["start"]))
        out_seg = os.path.join(tmp_dir, f"seg_{i:04d}.mp4")

        try:
            src_dur = probe_duration(src)
        except Exception as e:
            error("probe_duration_failed",
                  segment_index=i,
                  scene_id=t.get("scene_id", "unknown"),
                  video_path=src,
                  error=str(e))
            raise

        start = 0.0
        if src_dur > dur + 0.2:
            start = max(0.0, min(src_dur - dur - 0.05, (src_dur - dur) / 2.0))

        vf = f"scale={width}:{height},fps={fps},format=yuv420p"

        cmd = [
            "ffmpeg", "-y",
            "-r", "30",  # keep as-is
            "-ss", f"{start:.3f}",
            "-i", src,
            "-t", f"{dur:.3f}",
            "-vf", vf,
            *_video_encode_args(vcodec),
            "-pix_fmt", "yuv420p",
            "-vsync", "cfr",
            "-video_track_timescale", "15360",
            *_audio_encode_args(),
            *_common_mov_args(),
            out_seg
        ]

        try:
            _run(cmd, show_output=True)
        except Exception as e:
            error("ffmpeg_segment_failed",
                  segment_index=i,
                  scene_id=t.get("scene_id", "unknown"),
                  input_video=src,
                  output_segment=out_seg,
                  error=str(e))
            raise

        seg_files.append(out_seg)
        seg_durs.append(float(dur))
        seg_meta.append(seg)

    if not seg_files:
        raise RuntimeError("No segments were created. timeline is empty.")

    # Save segment timing map for subtitle alignment
    # Maps each segment to its ACTUAL video position (cumulative),
    # so subtitles can be remapped from voice timestamps to video timeline.
    cumulative_pos = 0.0
    segment_timing = []
    for i, (dur_val, meta) in enumerate(zip(seg_durs, seg_meta)):
        segment_timing.append({
            "index": i,
            "scene_id": meta.get("scene_id", ""),
            "original_start": round(meta.get("start", 0), 3),
            "original_end": round(meta.get("end", 0), 3),
            "video_start": round(cumulative_pos, 3),
            "video_end": round(cumulative_pos + dur_val, 3),
        })
        cumulative_pos += dur_val

    timing_path = os.path.join(out_dir, "segment_timing.json")
    try:
        with open(timing_path, "w", encoding="utf-8") as f:
            json.dump(segment_timing, f, ensure_ascii=False, indent=2)
        info("segment_timing_saved", path=timing_path, segments=len(segment_timing))
    except OSError as e:
        warn("segment_timing_save_failed", error=str(e))

    info("segments_created", total=len(seg_files), tmp_dir=tmp_dir)

    # Extract embeddings from timeline (if available)
    embeddings = None
    if timeline and "segment" in timeline[0]:
        embeddings = []
        has_embeddings = False
        for t in timeline:
            seg_embed = t.get("segment", {}).get("embedding")
            if seg_embed:
                embeddings.append(np.array(seg_embed, dtype=np.float32))
                has_embeddings = True
            else:
                embeddings.append(None)

        if has_embeddings:
            info("embeddings_loaded_from_timeline",
                 total_segments=len(timeline),
                 embeddings_found=sum(1 for e in embeddings if e is not None))
        else:
            embeddings = None
            info("no_embeddings_in_timeline", note="Hybrid mode will use text markers only")

    out_video_abs = os.path.abspath(out_video)

    # =========================
    # Stage 2 transitions path (batched)
    # =========================
    tcfg = _get_transition_cfg(cfg)
    if bool(tcfg.get("enable", False)) and len(seg_files) >= 2:
        apply: list[tuple[bool, float]] = []
        for i in range(1, len(seg_meta)):
            prev_seg = seg_meta[i - 1]
            cur_seg = seg_meta[i]
            ok, d = _broll_boundary_transition(cfg, prev_seg, cur_seg)
            apply.append((ok, d))

        apply, added_s2s = _apply_speech_to_speech_fallback(cfg, seg_meta, apply, embeddings)

        total_tr, n_batches = _batch_xfade_concat(
            seg_files=seg_files,
            seg_durs=seg_durs,
            seg_meta=seg_meta,
            apply=apply,
            cfg=cfg,
            out_video_abs=out_video_abs,
            tmp_dir=tmp_dir,
            vcodec=vcodec,
            fps=fps,
            width=width,
            height=height
        )

        info(
            "assemble_base_video_done",
            out=out_video_abs,
            segments=len(seg_files),
            method="xfade_batched",
            batches=n_batches,
            transitions=total_tr,
            transitions_s2s_added=added_s2s,
            vcodec=vcodec,
            rule="fade_light_broll_boundary_primary + speech2speech_selective_optional + batch_processing"
        )
        return

    # =========================
    # NO transitions: concat demuxer (SAFE + FAST)
    # =========================

    list_path = os.path.join(tmp_dir, "concat.txt")
    with open(list_path, "w", encoding="utf-8", newline="\n") as f:
        for p in seg_files:
            f.write(f"file '{_ffmpeg_path(p)}'\n")

    demux_cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-f", "concat", "-safe", "0",
        "-i", _ffmpeg_path(list_path),
        "-c:v", "copy",
        "-c:a", "copy",
        *_common_mov_args(),
        out_video_abs
    ]

    try:
        _run(demux_cmd, show_output=True)
        info(
            "assemble_base_video_done",
            out=out_video_abs,
            segments=len(seg_files),
            method="concat_demuxer_copy",
            vcodec=vcodec
        )
        return
    except Exception as e:
        warn("concat_demuxer_copy_failed_try_reencode", error=str(e), list_path=list_path)

    demux_reencode_cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts",
        "-f", "concat", "-safe", "0",
        "-i", _ffmpeg_path(list_path),
        *_video_encode_args(vcodec),
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-s", f"{width}x{height}",
        *_audio_encode_args(),
        *_common_mov_args(),
        out_video_abs
    ]

    _run(demux_reencode_cmd, show_output=True)

    info(
        "assemble_base_video_done",
        out=out_video_abs,
        segments=len(seg_files),
        method="concat_demuxer_reencode",
        vcodec=vcodec
    )
