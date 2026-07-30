"""
Content history & deduplication store.

Why this exists:
  Facebook's spam detection hashes video content. Uploading the same .mp4 to
  many pages — or to the same page twice — produces a strong "page-farm /
  spam" signal. This module gives the bot a memory of what it has already
  posted so it can refuse duplicates BEFORE they hit the Graph API.

Design:
  • SQLite single-file DB at data/content_history.db
  • Index on (video_hash, target_id) for fast lookup
  • Thread-safe (sqlite3.connect with check_same_thread=False + module lock)
  • Hashing: SHA-256 of the first 4 MB of file bytes (full hash is overkill
    for large videos; first 4 MB is unique enough for duplicate detection
    while staying fast for a 500 MB file).

Usage:
    store = ContentHistoryStore()
    fp    = store.fingerprint_video(video_path)
    if store.has_been_posted(fp.video_hash, target_id="page_123"):
        # skip / warn
    ...
    store.record_posted(
        video_hash=fp.video_hash,
        caption_hash=fp.caption_hash,
        target_id="page_123",
        platform="facebook",
        publish_id="vid_456",
    )
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ─── Configuration ───────────────────────────────────────────────────────────

# None = tu dong giai qua LTT_DATA_DIR. Dat duong dan cu the de ep buoc —
# tests/conftest.py dung cach nay de cach ly khoi CSDL that.
_DEFAULT_DB_PATH: Optional[str] = None


def _default_db_path() -> str:
    """Nơi lưu CSDL lịch sử nội dung, giải qua ranh giới đường dẫn của P2.

    Trước đây là hằng số tương đối theo thư mục làm việc. Hai hệ quả:

    1. Trên máy chủ nó rơi vào `app\\data\\` — thư mục bị thay mỗi lần cập nhật,
       nên lịch sử chống trùng nội dung mất sạch sau mỗi lần deploy.
    2. `tests/conftest.py` gán đè `_DEFAULT_DB_PATH` để cách ly test, nhưng vì
       hằng số này được dùng làm **giá trị mặc định của tham số** (gán một lần
       lúc import) nên việc gán đè đó không bao giờ có tác dụng — bộ test vẫn
       ghi vào CSDL thật. Giải lười ở đây vá luôn cả điều đó.
    """
    if _DEFAULT_DB_PATH:
        return _DEFAULT_DB_PATH
    try:
        from core.runtime_paths import data_path
        return data_path("content_history.db")
    except Exception:
        return os.path.join("data", "content_history.db")
_VIDEO_SAMPLE_BYTES = 4 * 1024 * 1024        # 4 MB — enough for SHA collision-resistance
_DB_LOCK            = threading.Lock()        # serialises writes across threads


# ─── Public API: fingerprint ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ContentFingerprint:
    """Snapshot of a piece of content's identifying hashes."""
    video_hash:   str   # SHA-256 hex of first 4 MB of the video file
    caption_hash: str   # SHA-256 hex of (title + description), lowercased
    p_hash:       str = ""   # Sprint A2: perceptual hash for fuzzy match


def hash_video_bytes(file_path: str) -> str:
    """Read the first 4 MB of *file_path* and return its SHA-256 hex digest.
    For files smaller than the sample size, the whole file is hashed."""
    if not file_path or not os.path.exists(file_path):
        return ""
    h = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            data = f.read(_VIDEO_SAMPLE_BYTES)
        h.update(data)
        return h.hexdigest()
    except OSError:
        return ""


def hash_caption(title: str, description: str) -> str:
    """Hash the normalised concatenation of title + description.
    Whitespace is collapsed and case-folded so trivial edits still match."""
    title       = (title       or "").strip().lower()
    description = (description or "").strip().lower()
    blob = (title + "\n" + description).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ─── Store ───────────────────────────────────────────────────────────────────

class ContentHistoryStore:
    """SQLite-backed log of every successful publish, keyed by content hash.

    Used by the publisher pipeline to (a) refuse duplicate uploads and
    (b) feed the anti-spam dashboard with per-page history.
    """

    def __init__(self, db_path: Optional[str] = None):
        db_path = db_path or _default_db_path()
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    # ── Schema ────────────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with _DB_LOCK, self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS content_history (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_hash    TEXT    NOT NULL,
                    caption_hash  TEXT    NOT NULL,
                    target_id     TEXT    NOT NULL,
                    platform      TEXT    NOT NULL,
                    publish_id    TEXT    NOT NULL,
                    uploaded_at   TEXT    NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_video_target
                    ON content_history(video_hash, target_id);
                CREATE INDEX IF NOT EXISTS idx_caption_target
                    ON content_history(caption_hash, target_id);
                CREATE INDEX IF NOT EXISTS idx_uploaded_at
                    ON content_history(uploaded_at);
            """)
            # Sprint A2: lazy-add p_hash column. ALTER TABLE IF NOT EXISTS
            # isn't valid SQLite; check pragma instead.
            cols = [r[1] for r in conn.execute("PRAGMA table_info(content_history)").fetchall()]
            if "p_hash" not in cols:
                conn.execute("ALTER TABLE content_history ADD COLUMN p_hash TEXT DEFAULT ''")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_phash ON content_history(p_hash)")
            conn.commit()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)

    # ── Public: fingerprint helper ────────────────────────────────────────────

    def fingerprint(
        self,
        video_path: str = "",
        title: str = "",
        description: str = "",
    ) -> ContentFingerprint:
        """Build a ContentFingerprint for the given file + caption text."""
        return ContentFingerprint(
            video_hash   = hash_video_bytes(video_path) if video_path else "",
            caption_hash = hash_caption(title, description),
        )

    # ── Public: duplicate check ───────────────────────────────────────────────

    def has_perceptual_match(
        self,
        p_hash:      str,
        *,
        target_id:   str,
        within_days: int = 30,
        threshold:   Optional[int] = None,
    ) -> str:
        """Sprint A2: fuzzy duplicate check via perceptual hash.

        Returns the matching p_hash from history (within Hamming threshold)
        or "" if no match. Different from has_been_posted() which is exact
        SHA-256 match. Use BOTH: SHA for strict identical, pHash for
        re-encoded variants.
        """
        if not p_hash:
            return ""
        # Defensive guard: never trust a degenerate input hash either —
        # mirrors the rejection logic inside perceptual_video_hash().
        if p_hash in ("0000000000000000", "ffffffffffffffff"):
            return ""
        from datetime import timedelta
        from core.perceptual_hash import find_perceptual_match, MATCH_THRESHOLD
        th = threshold if threshold is not None else MATCH_THRESHOLD
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        # Exclude legacy degenerate hashes ('0000...', 'ffff...') from the
        # comparison set. These were stored by older bot builds before the
        # perceptual_video_hash sanity check, and would cause every new
        # video that ALSO hits the degenerate case to falsely match.
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT p_hash FROM content_history
                   WHERE target_id = ? AND uploaded_at >= ?
                     AND p_hash NOT IN ('', '0000000000000000', 'ffffffffffffffff')""",
                (target_id, cutoff),
            ).fetchall()
        known = [r[0] for r in rows if r[0]]
        return find_perceptual_match(p_hash, known, threshold=th)

    def has_been_posted(
        self,
        *,
        video_hash:   str = "",
        caption_hash: str = "",
        target_id:    str,
        platform:     str = "",
        within_days:  Optional[int] = None,
    ) -> bool:
        """Return True if a row matches video_hash on target_id (optionally
        recent only).

        Match policy: video_hash is REQUIRED. Caption-only matches are
        intentionally NOT flagged here — different videos legitimately
        share captions (templates, batch posts) so caption-only flag would
        be too aggressive and break legitimate workflows. caption_hash is
        kept as a parameter for symmetry with record_posted() and for
        possible future "soft warn" lookups, but it's ignored in the SQL.

        An empty video_hash returns False (no false positives on rows that
        haven't been fingerprinted yet — e.g. when the file is mocked in
        a test or not yet downloaded).
        """
        if not video_hash:
            return False
        clauses = ["target_id = ?", "video_hash = ?"]
        params:  list = [target_id, video_hash]
        if platform:
            clauses.append("platform = ?"); params.append(platform)
        if within_days is not None:
            # SQLite stores ISO strings; comparison works lexicographically
            from datetime import timedelta
            cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
            clauses.append("uploaded_at >= ?"); params.append(cutoff)
        sql = (
            "SELECT 1 FROM content_history WHERE "
            + " AND ".join(clauses)
            + " LIMIT 1"
        )
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return row is not None

    # ── Public: record a successful publish ───────────────────────────────────

    def record_posted(
        self,
        *,
        video_hash:   str,
        caption_hash: str,
        target_id:    str,
        platform:     str,
        publish_id:   str,
        p_hash:       str = "",
    ) -> None:
        """Append a row to content_history. Never raises — failures land in stderr.

        video_hash must be non-empty: caption-only records are filtered out
        because they generate noise (test mocks, drives without a downloaded
        file) without contributing to spam detection — see has_been_posted().

        p_hash (Sprint A2) is optional — stored to enable fuzzy match later.
        """
        if not target_id or not video_hash:
            return
        ts = datetime.now(timezone.utc).isoformat()
        try:
            with _DB_LOCK, self._connect() as conn:
                conn.execute(
                    """INSERT INTO content_history
                       (video_hash, caption_hash, target_id, platform,
                        publish_id, uploaded_at, p_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (video_hash, caption_hash, target_id,
                     platform, publish_id, ts, p_hash),
                )
                conn.commit()
        except Exception as exc:
            import sys
            print(f"[ContentHistoryStore] record_posted failed: {exc}", file=sys.stderr)

    # ── Public: history queries (for dashboards) ──────────────────────────────

    def recent_for_target(self, target_id: str, limit: int = 50) -> list[dict]:
        """Return the most recent N posts for *target_id*."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT video_hash, caption_hash, platform, publish_id, uploaded_at
                   FROM content_history WHERE target_id = ?
                   ORDER BY uploaded_at DESC LIMIT ?""",
                (target_id, int(limit)),
            ).fetchall()
        return [
            {
                "video_hash":   r[0],
                "caption_hash": r[1],
                "platform":     r[2],
                "publish_id":   r[3],
                "uploaded_at":  r[4],
            }
            for r in rows
        ]

    def count_for_target(self, target_id: str, within_days: int = 7) -> int:
        """How many posts to *target_id* in the last *within_days* days?"""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        with self._connect() as conn:
            (n,) = conn.execute(
                """SELECT COUNT(*) FROM content_history
                   WHERE target_id = ? AND uploaded_at >= ?""",
                (target_id, cutoff),
            ).fetchone()
        return int(n)

    def all_targets(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT target_id FROM content_history ORDER BY target_id"
            ).fetchall()
        return [r[0] for r in rows]

    def total_count(self) -> int:
        with self._connect() as conn:
            (n,) = conn.execute("SELECT COUNT(*) FROM content_history").fetchone()
        return int(n)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def purge_older_than(self, days: int) -> int:
        """Delete rows older than *days* days. Returns rows removed."""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with _DB_LOCK, self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM content_history WHERE uploaded_at < ?",
                (cutoff,),
            )
            conn.commit()
            return cur.rowcount


# ─── Singleton accessor ──────────────────────────────────────────────────────

_default_store: Optional[ContentHistoryStore] = None
_default_lock = threading.Lock()


def get_default_store(db_path: Optional[str] = None) -> ContentHistoryStore:
    """Process-wide singleton. Pass a custom path to override (tests use this)."""
    global _default_store
    db_path = db_path or _default_db_path()
    with _default_lock:
        if _default_store is None or _default_store.db_path != db_path:
            _default_store = ContentHistoryStore(db_path)
        return _default_store


class DuplicateContentError(RuntimeError):
    """Raised when an upload would create a content duplicate that risks
    triggering Facebook's page-farm / spam detection."""
