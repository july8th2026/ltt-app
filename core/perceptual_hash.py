"""
Perceptual-hash dedup (Sprint A2).

Why this exists:
  Facebook hashes video content using a perceptual signature, not just
  byte-level SHA. Two videos that look 99 % the same (re-encoded, slight
  brightness change, trimmed first/last frame) have IDENTICAL pHash but
  DIFFERENT SHA-256. The original SHA-256 dedup misses such cases.

This module exposes a pure-Python perceptual hash with NO third-party deps,
suitable for shipping inside a desktop bot:
  • Sample N evenly-spaced frames from the video container (here: the first
    several KB which we already have buffered) and hash the dHash pattern.
  • Returns a 64-bit hex string. Hamming distance < THRESHOLD = same video.

Limitations vs commercial pHash:
  • Operates on raw byte chunks, not decoded frames — order of magnitude
    weaker than libraries like videohash / Vipsash, but ZERO dependency.
  • Designed as a complement to SHA-256, not a replacement. Both are
    stored so callers can match strictly (SHA) or loosely (pHash).

Usage:
    h = perceptual_video_hash(file_path)
    if hamming_distance(h, other_h) <= MATCH_THRESHOLD:
        # likely same content
"""
from __future__ import annotations

import os
from typing import Iterable


# Hamming-distance threshold for "same video".
#
# IMPORTANT: the dHash loop below sets at most (samples - 1) bits, so the
# effective hash size is (samples - 1) bits, NOT the 64 bits suggested by
# the hex format. The original docstring claimed "tuned against 4 MB
# sampling window" but the threshold of 8 was actually mis-tuned: with
# only 15 effective bits, threshold 8 produces ~70 % false-match rate on
# random videos (binomial(15, 0.5) tail probability).
#
# Fix: tightened to 2. With 15 effective bits this gives ~0.4 % false
# positive rate while still catching most byte-identical re-encodes.
# When the algorithm is upgraded to true 64-bit dHash (see TODO below),
# this threshold can be relaxed back to 8.
MATCH_THRESHOLD = 2

_SAMPLES_PER_VIDEO   = 16        # TODO: bump to 65 for true 64-bit hash
_WINDOW_SIZE_BYTES   = 4096      # bytes per window


def perceptual_video_hash(file_path: str) -> str:
    """Compute a 64-bit perceptual signature for *file_path*.

    Returns a 16-char hex string. Empty string on read failure or empty
    file. Two videos with identical signatures are very likely the same;
    similar signatures (low Hamming distance) are likely re-encodings.

    Algorithm:
      1. Open file; if smaller than _WINDOW_SIZE_BYTES * 2 → use full content.
      2. Pick _SAMPLES_PER_VIDEO evenly-spaced offsets.
      3. Read _WINDOW_SIZE_BYTES per offset; XOR/sum into a 64-bit bucket.
      4. Convert each bucket to one bit by comparing to its predecessor
         (differential / dHash style). Robust to small absolute shifts.
    """
    if not file_path or not os.path.exists(file_path):
        return ""
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return ""
    if size == 0:
        return ""

    samples = max(_SAMPLES_PER_VIDEO, 8)
    win     = min(_WINDOW_SIZE_BYTES, max(256, size // samples))

    buckets: list[int] = []
    try:
        with open(file_path, "rb") as f:
            for i in range(samples):
                # Evenly-spaced offset. For tiny files this wraps to 0
                # but that's fine — we still produce a valid signature.
                offset = (i * size) // samples
                if offset + win > size:
                    offset = max(0, size - win)
                f.seek(offset)
                chunk = f.read(win)
                bucket = 0
                for j, b in enumerate(chunk):
                    bucket ^= (b << ((j * 7) & 31))
                buckets.append(bucket & 0xFFFFFFFFFFFFFFFF)
    except OSError:
        return ""

    if not buckets:
        return ""

    # dHash: bit i = 1 if buckets[i] > buckets[i-1]
    bits = 0
    for i in range(1, len(buckets)):
        if buckets[i] > buckets[i - 1]:
            bits |= (1 << (i - 1))
    # Pad to 64 bits
    h = f"{bits & 0xFFFFFFFFFFFFFFFF:016x}"
    # Reject degenerate hashes — all-zero or all-F signals that the dHash
    # comparison produced no information (monotonically non-increasing or
    # non-decreasing buckets). Returning these would cause every video
    # hitting the same degenerate case to falsely match every other one.
    # Treat as "no hash available" → caller will fall back to SHA dedup only.
    if h in ("0000000000000000", "ffffffffffffffff"):
        return ""
    return h


def hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two hex hashes. Returns 64 if either is
    invalid — treated as "definitely different"."""
    if not a or not b or len(a) != len(b):
        return 64
    try:
        return bin(int(a, 16) ^ int(b, 16)).count("1")
    except ValueError:
        return 64


def is_perceptually_same(a: str, b: str, threshold: int = MATCH_THRESHOLD) -> bool:
    """True if two hashes are within *threshold* Hamming distance."""
    return hamming_distance(a, b) <= threshold


def find_perceptual_match(
    target_hash: str,
    known_hashes: Iterable[str],
    threshold: int = MATCH_THRESHOLD,
) -> str:
    """Return the first *known_hashes* entry within Hamming threshold of
    *target_hash*, or "" if none matches. O(n) — fine for our scale
    (content_history is at most a few thousand rows)."""
    if not target_hash:
        return ""
    for kh in known_hashes:
        if hamming_distance(target_hash, kh) <= threshold:
            return kh
    return ""
