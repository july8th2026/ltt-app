"""
Content vault export / inspection helpers (Phase 4.2).

Provides a thin layer over ContentHistoryStore for:
  • CSV export of all content records (audit + analysis outside the bot)
  • Top duplicate detection (videos uploaded to many targets — useful for
    spotting accidental cross-page spam from your own setup)
  • Per-target summary used by the dashboard

The bot UI consumes these via a "📦 Export Content History" action in the
Settings tab; the same functions are useful programmatically (cron tools,
backup scripts).
"""
from __future__ import annotations

import csv
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


@dataclass(frozen=True)
class DuplicateGroup:
    """A single video uploaded to >1 target — flagged for review."""
    video_hash:      str
    targets:         list             # list of target_id strings
    count:           int              # len(targets) — for sorting
    latest_uploaded_at: str


def export_to_csv(
    out_path:  str,
    *,
    store     = None,
    within_days: Optional[int] = None,
) -> int:
    """Dump all content_history rows to a CSV file. Returns rows written.

    Columns: video_hash, caption_hash, target_id, platform, publish_id, uploaded_at.
    Safe to call even when store is empty (writes only the header).
    """
    if store is None:
        from core.content_history import get_default_store
        store = get_default_store()

    # Build the WHERE clause for the date cutoff
    sql = (
        "SELECT video_hash, caption_hash, target_id, platform, publish_id, uploaded_at "
        "FROM content_history"
    )
    params: list = []
    if within_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=within_days)).isoformat()
        sql += " WHERE uploaded_at >= ?"
        params.append(cutoff)
    sql += " ORDER BY uploaded_at DESC"

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with store._connect() as conn:
        rows = conn.execute(sql, params).fetchall()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["video_hash", "caption_hash", "target_id",
                    "platform", "publish_id", "uploaded_at"])
        for r in rows:
            w.writerow(list(r))
    return len(rows)


def find_cross_target_duplicates(
    *,
    store      = None,
    min_targets: int = 2,
) -> list[DuplicateGroup]:
    """Return groups of (video_hash, [targets...]) where the same video was
    uploaded to ≥ min_targets distinct targets.

    Lots of duplicates here = user is intentionally cross-posting; this is
    legitimate but is exactly the pattern FB flags as page-farm spam. The
    UI shows the top groups so the user can decide whether to varying their
    content per page.
    """
    if store is None:
        from core.content_history import get_default_store
        store = get_default_store()

    with store._connect() as conn:
        rows = conn.execute(
            """SELECT video_hash, target_id, MAX(uploaded_at)
               FROM content_history
               WHERE video_hash != ''
               GROUP BY video_hash, target_id"""
        ).fetchall()

    by_hash: dict[str, dict] = defaultdict(lambda: {"targets": [], "latest": ""})
    for vh, tgt, latest in rows:
        d = by_hash[vh]
        d["targets"].append(tgt)
        if latest > d["latest"]:
            d["latest"] = latest

    groups = []
    for vh, d in by_hash.items():
        n = len(d["targets"])
        if n >= min_targets:
            groups.append(DuplicateGroup(
                video_hash=vh,
                targets=sorted(d["targets"]),
                count=n,
                latest_uploaded_at=d["latest"],
            ))
    # Sort: highest count first, then most recent
    groups.sort(key=lambda g: (-g.count, g.latest_uploaded_at), reverse=False)
    groups.sort(key=lambda g: g.count, reverse=True)
    return groups


def summary_by_target(*, store = None) -> list[dict]:
    """Per-target stats summary. List of dicts with target_id, total_posts,
    latest, distinct_videos."""
    if store is None:
        from core.content_history import get_default_store
        store = get_default_store()

    with store._connect() as conn:
        rows = conn.execute(
            """SELECT target_id, platform,
                      COUNT(*) AS total,
                      COUNT(DISTINCT video_hash) AS distinct_videos,
                      MAX(uploaded_at) AS latest,
                      MIN(uploaded_at) AS earliest
               FROM content_history
               GROUP BY target_id, platform
               ORDER BY total DESC"""
        ).fetchall()

    out = []
    for tgt, plat, total, distinct, latest, earliest in rows:
        out.append({
            "target_id":        tgt,
            "platform":         plat,
            "total_posts":      int(total),
            "distinct_videos":  int(distinct),
            "latest":           latest,
            "earliest":         earliest,
            "reuse_pct": round(
                (1.0 - (distinct / total)) * 100.0 if total else 0.0, 1
            ),
        })
    return out
