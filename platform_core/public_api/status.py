"""What a customer is allowed to know about how we are doing.

Two audiences, two pages
------------------------

``/status`` already exists and is operator-only: it is the doctor report, and it
names the database, the disk, the tunnel and the provider pool. That is exactly
right for the person fixing things and exactly wrong for the public — an outage
page that lists your internal topology tells an attacker which door is currently
unlocked.

So this module maps **internal health onto public capability**. A customer learns
whether image generation is working; they do not learn that the answer came from
a GPU lease table, a credential pool or a disk check.

The mapping rule
----------------

Every public capability is derived from the tool catalog — the same names a
customer already calls (`image.generate` → capability `image`). Nothing declares
a separate list of "services", because a second list is one that drifts, and the
first time it drifts the status page is confidently wrong.

A capability is degraded when the machinery it *actually needs* is unavailable,
which is the same question `capacity.py` answers at job creation. Reusing it
means the status page cannot disagree with what the API is doing — the failure
mode where a page says "operational" while every call is refused.

What is deliberately withheld
-----------------------------

No host names, no queue depths, no provider names, no error text from upstream,
no counts that reveal customer volume. The public page says which capability is
affected, since when, and what is being done — and nothing that would only be
useful to somebody planning to make it worse.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from platform_core.i18n import N_, _ as _t

OPERATIONAL = "operational"
DEGRADED = "degraded"
MAINTENANCE = "maintenance"
OUTAGE = "outage"

#: Worst-first, so a page can sort by severity without a second table.
SEVERITY = {OUTAGE: 3, MAINTENANCE: 2, DEGRADED: 1, OPERATIONAL: 0}

#: What a customer is told for each state. Written for somebody deciding whether
#: to retry, not for somebody debugging us.
#: Marked for translation at import and resolved at render, because a status
#: page is read by whoever is affected — and during an incident that is the
#: worst possible moment to serve somebody a language they do not read.
PUBLIC_WORDING = {
    OPERATIONAL: N_("Hoạt động bình thường."),
    DEGRADED: N_("Đang trục trặc — lời gọi mới có thể bị từ chối tạm thời."),
    MAINTENANCE: N_("Đang bảo trì theo kế hoạch."),
    OUTAGE: N_("Đang gián đoạn."),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CapabilityStatus:
    """One line on the public page."""

    capability: str
    state: str
    tools: tuple
    note: str = ""
    since: datetime | None = None

    @property
    def wording(self) -> str:
        return _t(PUBLIC_WORDING.get(self.state,
                                     PUBLIC_WORDING[OPERATIONAL]))


def public_status(db, config, *, now: datetime | None = None) -> dict:
    """The whole public page, as data.

    Assembled from three sources the platform already maintains: the catalog
    (what exists), the kill switches (what an operator turned off deliberately)
    and the capacity probes (what is broken without anybody deciding).
    """
    from platform_core.public_api import policy
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.tables import (KILL_MAINTENANCE, KILL_TOOL)

    moment = now or _now()
    tools = build_catalog(config)

    switches = {}
    for row in policy.active_switches(db, now=moment):
        switches[(row.scope, row.subject)] = row
    global_maintenance = switches.get((KILL_MAINTENANCE, ""))

    grouped: dict = {}
    for tool in tools:
        grouped.setdefault(tool.capability, []).append(tool)

    lines = []
    for capability, members in sorted(grouped.items()):
        state, note, since = OPERATIONAL, "", None

        if global_maintenance is not None:
            # An operator said so, and said why. The reason is written by an
            # operator for a customer, so it is shown as written.
            state = MAINTENANCE
            note = global_maintenance.reason
            since = global_maintenance.created_at
        else:
            off = [switches.get((KILL_TOOL, tool.name)) for tool in members]
            off = [row for row in off if row is not None]
            if off and len(off) == len(members):
                state, note, since = MAINTENANCE, off[0].reason, off[0].created_at
            elif off:
                state, note, since = DEGRADED, off[0].reason, off[0].created_at
            else:
                missing = _capacity_gap(db, members)
                if missing is not None:
                    state = DEGRADED
                    # `capacity` messages are already written for a caller —
                    # "no GPU is available", not "gpu_leases row missing".
                    note = missing

        lines.append(CapabilityStatus(
            capability=capability, state=state,
            tools=tuple(tool.name for tool in members), note=note, since=since))

    overall = OPERATIONAL
    for line in lines:
        if SEVERITY[line.state] > SEVERITY[overall]:
            overall = line.state

    return {
        "checked_at": moment,
        "overall": overall,
        "overall_wording": _t(PUBLIC_WORDING[overall]),
        "capabilities": sorted(lines,
                               key=lambda row: (-SEVERITY[row.state],
                                                row.capability)),
    }


def _capacity_gap(db, tools) -> str | None:
    """The first missing resource across a capability's tools, in public words."""
    from platform_core.public_api import capacity
    from platform_core.registry import discover

    manifests = {item.manifest.slug: item.manifest
                 for item in discover() if not item.error and item.manifest}
    for tool in tools:
        missing = capacity.check(db, tool=tool,
                                 manifest=manifests.get(tool.app_slug))
        if missing is not None:
            return missing.detail
    return None


__all__ = ["CapabilityStatus", "DEGRADED", "MAINTENANCE", "OPERATIONAL",
           "OUTAGE", "PUBLIC_WORDING", "SEVERITY", "public_status"]
