"""Source video fingerprinting for cache invalidation.

Computes SHA-256 of first 64MB + file_size for fast identification.
Full-file hashing is too slow for large videos.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from cutclipshort.constants import SOURCE_HASH_CHUNK_SIZE

logger = logging.getLogger(__name__)


def compute_source_hash(video_path: Path) -> str:
    """Compute a fast fingerprint for a video file.

    Hashes the first SOURCE_HASH_CHUNK_SIZE bytes + file size.
    This is fast even for multi-GB files while being collision-resistant
    enough for cache invalidation purposes.

    Returns:
        String like "sha256:abcdef123456..."
    """
    file_size = video_path.stat().st_size
    h = hashlib.sha256()

    # Hash first chunk
    with open(video_path, "rb") as f:
        chunk = f.read(SOURCE_HASH_CHUNK_SIZE)
        h.update(chunk)

    # Include file size in hash to differentiate truncated files
    h.update(str(file_size).encode())

    digest = h.hexdigest()
    logger.debug(
        "Source hash for %s: sha256:%s (size=%d)",
        video_path.name, digest[:16], file_size,
    )
    return f"sha256:{digest}"


def verify_source_hash(video_path: Path, expected_hash: str) -> bool:
    """Verify that a video file matches an expected hash."""
    if not video_path.exists():
        return False
    actual = compute_source_hash(video_path)
    return actual == expected_hash
