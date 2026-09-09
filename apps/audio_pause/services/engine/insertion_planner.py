from __future__ import annotations

import json
from typing import Optional
from .nhat_ky import info, debug


def generate_insertion_plan(
    anchor_map: dict,
    min_gap_s: float = 0.8,
    min_pause_ms: int = 120,
    max_pause_ms: int = 2500,
) -> list[dict]:
    """
    Generate insertion plan from matched anchors.
    - Clamp pause_ms to [min_pause_ms, max_pause_ms]
    - Remove overlapping pauses (keep higher priority)
    - Enforce min_gap_s between consecutive pauses
    """

    matched = anchor_map.get("matched", [])
    if not matched:
        info("insertion_plan_empty")
        return []

    # sort by time, then by priority asc (lower number = higher priority = first)
    matched = sorted(
        matched,
        key=lambda x: (x["start_time"], x.get("priority", 3))
    )

    plan = []
    last_end_sec = -999.0  # timestamp where last pause ends

    skipped = 0
    for m in matched:
        at_sec = float(m["start_time"])
        pause_ms = int(m["pause_ms"])

        # Clamp pause duration to configured range
        pause_ms = max(min_pause_ms, min(max_pause_ms, pause_ms))

        pause_dur_s = pause_ms / 1000.0

        # Overlap / min_gap check: skip if too close to previous pause end
        if at_sec < last_end_sec + min_gap_s:
            debug("insertion_skip_overlap",
                  id=m.get("id"), at_sec=round(at_sec, 2),
                  last_end=round(last_end_sec, 2), min_gap=min_gap_s)
            skipped += 1
            continue

        plan.append({
            "at_sec": at_sec,
            "pause_ms": pause_ms,
            "id": m.get("id"),
        })
        last_end_sec = at_sec + pause_dur_s

    if skipped:
        info("insertion_plan_skipped_overlaps", skipped=skipped)

    info("insertion_plan_ready", count=len(plan))

    # Log detailed per-pause info for debugging placement
    if plan:
        details = []
        for p in plan:
            entry = {
                "id": p.get("id"),
                "at_sec": round(p["at_sec"], 3),
                "pause_ms": p["pause_ms"],
            }
            # Carry forward debug context from anchor match if available
            m_item = _find_matched_item(matched, p.get("id"))
            if m_item:
                wb = m_item.get("word_before")
                wa = m_item.get("word_after")
                entry["word_before"] = f"{wb['word']}({wb['end']})" if wb else "—"
                entry["word_after"] = f"{wa['word']}({wa['start']})" if wa else "—"
                mt = m_item.get("matched_text") or m_item.get("matched_before_text") or ""
                entry["matched_text"] = mt[:60]
                entry["score"] = round(m_item.get("similarity", 0), 4)
            details.append(entry)
        debug("insertion_plan_details", pauses=details)

    return plan


def _find_matched_item(matched_list: list, item_id) -> Optional[dict]:
    """Find matched anchor by id for debug context lookup."""
    for m in matched_list:
        if m.get("id") == item_id:
            return m
    return None


def save_insertion_plan(plan: list[dict], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    debug("insertion_plan_saved", path=path, count=len(plan))


def load_insertion_plan(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
