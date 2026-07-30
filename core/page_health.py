"""
Page health tracker (Phase 2.3).

Detects FB-side reach throttling — Facebook's silent "shadow ban" where
your posts still publish but reach drops 50-90 % without warning. The
mechanic: FB compares recent post performance to the account's own
baseline; if reach is consistently below baseline, it's the strongest
signal that the page is on a soft watchlist.

Strategy:
  • For each page, fetch insights for the last N posts (default 5).
  • Compute current_avg_reach.
  • Compare to baseline_avg_reach (7-day rolling average kept in a tiny
    SQLite table).
  • If current < baseline × THROTTLE_THRESHOLD → flag "SUSPECTED_THROTTLE".

The bot uses this flag to:
  • Cut the page's daily quota in half temporarily (P3.x integration).
  • Surface in the Anti-Spam dashboard.
  • Notify the user via Telegram.

Implementation note:
  This module is READ-only against FB API. Writing reduced quotas is the
  caller's job; this module just produces PageHealthReport snapshots.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ─── Configuration ───────────────────────────────────────────────────────────

# None = tu dong giai qua LTT_DATA_DIR. Cung khuon voi core/content_history.py.
_DEFAULT_DB_PATH: Optional[str] = None


def _default_db_path() -> str:
    """Nơi lưu CSDL sức khoẻ Page, giải qua ranh giới đường dẫn của P2."""
    if _DEFAULT_DB_PATH:
        return _DEFAULT_DB_PATH
    try:
        from core.runtime_paths import data_path
        return data_path("page_health.db")
    except Exception:
        return os.path.join("data", "page_health.db")
_THROTTLE_THRESHOLD    = 0.60   # current/baseline < 0.6 → flagged
_SAMPLES_FOR_BASELINE  = 10     # need 10+ recent samples for confident baseline


class PageHealthLevel(Enum):
    UNKNOWN     = "unknown"        # not enough samples yet
    HEALTHY     = "healthy"        # current ≥ baseline
    SUSPECTED   = "suspected"      # current 60-90 % of baseline
    THROTTLED   = "throttled"      # current < 60 % of baseline
    DEAD        = "dead"           # 3+ consecutive zero-reach posts


@dataclass(frozen=True)
class PageHealthReport:
    page_id:        str
    page_name:      str
    samples:        int
    current_avg:    float
    baseline_avg:   float
    drop_pct:       float          # how much reach dropped from baseline (positive = bad)
    level:          PageHealthLevel
    message:        str


# ─── Store: per-post reach history ───────────────────────────────────────────

_DB_LOCK = threading.Lock()


class PageHealthStore:
    """Tiny SQLite-backed store of per-post reach numbers. Used to compute
    rolling baselines without re-querying FB on every dashboard refresh.
    """

    def __init__(self, db_path: Optional[str] = None):
        db_path = db_path or _default_db_path()
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False, timeout=10)

    def _init_schema(self):
        with _DB_LOCK, self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS page_reach (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    page_id     TEXT NOT NULL,
                    video_id    TEXT NOT NULL,
                    reach       INTEGER NOT NULL,
                    sampled_at  TEXT NOT NULL,
                    UNIQUE(page_id, video_id)
                );
                CREATE INDEX IF NOT EXISTS idx_page_sampled
                    ON page_reach(page_id, sampled_at);
            """)
            conn.commit()

    def record_reach(self, page_id: str, video_id: str, reach: int):
        """Insert (or replace) one (page, video) reach sample.
        UPSERT semantics so re-sampling the same video updates the number."""
        if not page_id or not video_id:
            return
        ts = datetime.now(timezone.utc).isoformat()
        try:
            with _DB_LOCK, self._connect() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO page_reach
                       (page_id, video_id, reach, sampled_at)
                       VALUES (?, ?, ?, ?)""",
                    (page_id, video_id, int(reach or 0), ts),
                )
                conn.commit()
        except Exception as exc:
            import sys
            print(f"[PageHealthStore] record_reach failed: {exc}", file=sys.stderr)

    def recent_samples(self, page_id: str, limit: int = 20) -> list[int]:
        """Most recent N reach numbers for *page_id*, newest first."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT reach FROM page_reach
                   WHERE page_id = ?
                   ORDER BY sampled_at DESC LIMIT ?""",
                (page_id, int(limit)),
            ).fetchall()
        return [int(r[0]) for r in rows]

    def baseline_and_current(
        self,
        page_id: str,
        current_window: int = 3,
        baseline_window: int = 10,
    ) -> tuple[float, float, int]:
        """Return (current_avg, baseline_avg, total_samples).

        current_window  = newest N posts → "what is happening now"
        baseline_window = next M posts (older) → "what is normal"

        Returns (0, 0, 0) if not enough samples for a baseline.
        """
        samples = self.recent_samples(page_id, limit=current_window + baseline_window)
        n = len(samples)
        if n < current_window:
            return 0.0, 0.0, n
        current = samples[:current_window]
        baseline = samples[current_window:current_window + baseline_window]
        if not baseline:
            # Not enough baseline samples — return current only
            return sum(current) / len(current), 0.0, n
        return (
            sum(current) / len(current),
            sum(baseline) / len(baseline),
            n,
        )


# ─── Public: assessment ─────────────────────────────────────────────────────

def assess_page_health(
    page_id:   str,
    page_name: str,
    *,
    store: Optional[PageHealthStore] = None,
) -> PageHealthReport:
    """Build a PageHealthReport from the local reach store.

    Does NOT call FB API. Use update_page_reach_from_insights() to refresh
    the store first (periodic background task).
    """
    s = store or _default_store()
    current_avg, baseline_avg, samples = s.baseline_and_current(page_id)

    if samples < 3:
        return PageHealthReport(
            page_id=page_id, page_name=page_name, samples=samples,
            current_avg=current_avg, baseline_avg=baseline_avg, drop_pct=0.0,
            level=PageHealthLevel.UNKNOWN,
            message=f"📊 '{page_name}': chưa đủ data ({samples} sample) — cần ≥3 post để đánh giá",
        )

    if baseline_avg <= 0:
        # Have current data but no baseline → can't compare
        return PageHealthReport(
            page_id=page_id, page_name=page_name, samples=samples,
            current_avg=current_avg, baseline_avg=baseline_avg, drop_pct=0.0,
            level=PageHealthLevel.UNKNOWN,
            message=f"📊 '{page_name}': chưa có baseline (cần ≥{_SAMPLES_FOR_BASELINE+3} post)",
        )

    ratio = current_avg / baseline_avg if baseline_avg else 1.0
    drop_pct = (1.0 - ratio) * 100.0

    if current_avg == 0 and samples >= 3:
        level = PageHealthLevel.DEAD
        msg = f"☠️ '{page_name}': 3 post gần nhất 0 reach — page có thể đã bị ban hoặc disabled"
    elif ratio < _THROTTLE_THRESHOLD:
        level = PageHealthLevel.THROTTLED
        msg = (
            f"🔴 '{page_name}': reach giảm {drop_pct:.0f}% so với baseline "
            f"({current_avg:.0f} vs {baseline_avg:.0f}) — nghi throttle"
        )
    elif ratio < 0.90:
        level = PageHealthLevel.SUSPECTED
        msg = (
            f"🟠 '{page_name}': reach giảm {drop_pct:.0f}% — theo dõi thêm"
        )
    else:
        level = PageHealthLevel.HEALTHY
        msg = f"✅ '{page_name}': reach ổn định ({current_avg:.0f}/{baseline_avg:.0f})"

    return PageHealthReport(
        page_id=page_id, page_name=page_name, samples=samples,
        current_avg=round(current_avg, 1), baseline_avg=round(baseline_avg, 1),
        drop_pct=round(drop_pct, 1), level=level, message=msg,
    )


def update_page_reach_from_insights(
    graph_client,
    page_id:           str,
    page_access_token: str,
    video_ids:         list,
    *,
    store: Optional[PageHealthStore] = None,
) -> int:
    """Fetch insights for each video_id and persist the reach number.

    Returns the count of videos successfully sampled. Wrapped in broad
    try/except so a transient API failure doesn't break the periodic task.
    """
    if not video_ids:
        return 0
    s = store or _default_store()
    n = 0
    for vid in video_ids:
        try:
            ins = graph_client.get_video_insights(vid, page_access_token)
            reach = int(ins.get("reach", 0) or 0)
            s.record_reach(page_id, str(vid), reach)
            n += 1
        except Exception:
            continue
    return n


# ─── Singleton accessor ──────────────────────────────────────────────────────

_default: Optional[PageHealthStore] = None
_default_lock = threading.Lock()


def _default_store() -> PageHealthStore:
    global _default
    with _default_lock:
        if _default is None:
            _default = PageHealthStore()
        return _default


def all_page_reports(token_store=None) -> list[PageHealthReport]:
    """Build a report for every page known to the FB token store.

    Falls back to empty list if no accounts connected.
    """
    if token_store is None:
        try:
            from core.token_store import get_default_store
            token_store = get_default_store()
        except Exception:
            return []
    out = []
    for acc in token_store.all_accounts():
        for p in acc.get_selected_pages():
            out.append(assess_page_health(p.id, p.name))
    return out
