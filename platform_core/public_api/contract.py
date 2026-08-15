"""The public surface, as one machine-readable fact, and what may change about it.

Why this exists
---------------

Every piece of the contract already existed somewhere: routes in
``server/api/inventory.py``, tool shapes behind ``contract_hash``, error codes in
the registry, event types in ``webhooks``. What did not exist was a way to ask
*"did any of that change, and was the change allowed?"* — so a breaking change
could ship because nobody diffed a thing nobody had assembled.

``snapshot()`` assembles it. ``compare()`` says what moved and, for each
difference, whether it is the kind a client survives.

What counts as breaking, and why
--------------------------------

The test is not "did bytes change" but **"would a working integration stop
working"**:

* a route or tool that disappears, or moves — the caller gets a 404 tomorrow;
* an operation that starts requiring authentication, or a scope it did not need;
* a tool whose ``contract_hash`` moves — that hash covers the input and output
  schema, so a caller's payload may no longer validate or their parser may no
  longer find a field;
* an execution mode change — a client written for a job id cannot read a
  synchronous answer;
* an error code that vanishes from the registry — somebody is branching on it;
* a webhook event type that disappears, or a payload version that moves — a
  receiver verifies and parses on both.

Additive changes are not breaking: a new route, a new tool, a new error code, a
new event type. A client that never asks for them cannot notice them.

The deliberate asymmetry
------------------------

Anything this module cannot classify is treated as **breaking**. An unknown
difference is exactly the case where somebody has changed something the checker
was not taught about, and defaulting to "probably fine" there would make the
whole gate decorative.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.public_api import protocol

#: Bumped only when the *shape of the snapshot itself* changes, so an old
#: baseline is refused loudly rather than compared against wrongly.
SNAPSHOT_VERSION = 1


def snapshot(config, *, routes=(), apps=None) -> dict:
    """Everything a client can depend on, in a stable, comparable shape.

    Sorted and keyed rather than positional: a diff of this file should show
    what changed about the API, not that two routes swapped places.

    ``routes`` is passed in rather than imported. The route inventory is an HTTP
    concern that lives in ``server/``, and ``platform_core`` sits underneath it —
    a lower layer that reaches upwards has quietly made the thing above it a
    dependency, and the first symptom is a module you cannot import without a
    web app. ``tools/check_api_compat.py`` knows both sides and supplies them.
    """
    from platform_core.public_api import errors, webhooks
    from platform_core.public_api.catalog import build_catalog
    from platform_core.public_api.error_registry import as_rows

    routes_map = {}
    for route in routes:
        routes_map[f"{route.method} {route.path}"] = {
            "authenticated": bool(route.authenticated),
            "in_schema": bool(route.in_schema),
            "execution_mode": route.execution_mode,
            "deprecated_on": route.deprecated_on,
            "sunset_on": route.sunset_on,
        }

    tools = {}
    for tool in build_catalog(config, apps=apps):
        body = tool.to_public_dict()
        tools[tool.name] = {
            "contract_hash": body["contract_hash"],
            "execution_mode": body["execution_mode"],
            "required_scopes": sorted(body.get("required_scopes") or ()),
            "aliases": sorted(body.get("aliases") or ()),
            "deprecated": body.get("deprecated", ""),
            "models": sorted((tool.model_aliases or {}).keys()),
        }

    codes = {}
    for row in as_rows():
        codes[row["code"]] = {"status": int(row["status"]),
                              "retry": row["retry"]}

    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "api_version": protocol.API_VERSION,
        "routes": dict(sorted(routes_map.items())),
        "tools": dict(sorted(tools.items())),
        "error_codes": dict(sorted(codes.items())),
        "webhook": {
            # The signature scheme and the payload shape a receiver parses.
            # Both are versioned, and both are immutable within a version —
            # a receiver that verifies today must verify tomorrow.
            "signature_version": webhooks.SIGNATURE_VERSION,
            "payload_version": webhooks.PAYLOAD_VERSION,
            "event_types": sorted(webhooks.TERMINAL_EVENTS),
            "payload_fields": sorted(webhooks.PAYLOAD_FIELDS),
        },
        "headers": sorted((protocol.HEADER_CORRELATION_ID,
                           protocol.HEADER_API_VERSION,
                           protocol.HEADER_IDEMPOTENCY_KEY,
                           protocol.HEADER_RETRY_AFTER)),
        "execution_modes_in_use": sorted(protocol.MODES_IN_USE),
        "problem_media_type": errors.PROBLEM_CONTENT_TYPE,
    }


@dataclass
class Difference:
    """One change, and whether a working integration survives it."""

    area: str
    subject: str
    kind: str            # "removed" | "changed" | "added"
    breaking: bool
    detail: str = ""

    def line(self) -> str:
        mark = "BREAKING" if self.breaking else "ok"
        return f"[{mark}] {self.area}: {self.subject} {self.kind} {self.detail}".strip()


@dataclass
class Comparison:
    differences: list = field(default_factory=list)

    @property
    def breaking(self) -> list:
        return [item for item in self.differences if item.breaking]

    @property
    def additive(self) -> list:
        return [item for item in self.differences if not item.breaking]

    @property
    def clean(self) -> bool:
        return not self.differences


#: Per-area, the fields whose change breaks a client. Anything not listed here
#: is metadata — and anything the checker does not recognise is breaking, which
#: is the safe direction for a rule about not breaking people.
BREAKING_ROUTE_FIELDS = ("authenticated", "execution_mode")
BREAKING_TOOL_FIELDS = ("contract_hash", "execution_mode", "required_scopes")
BREAKING_CODE_FIELDS = ("status",)


def compare(old: dict, new: dict) -> Comparison:
    """What changed between two snapshots, classified.

    ``old`` is the committed baseline; ``new`` is what the code serves now.
    """
    found = Comparison()
    if int(old.get("snapshot_version", 0)) != SNAPSHOT_VERSION:
        found.differences.append(Difference(
            "snapshot", "snapshot_version", "changed", True,
            "baseline was written by a different checker; regenerate it"))
        return found

    if old.get("api_version") != new.get("api_version"):
        found.differences.append(Difference(
            "version", "api_version", "changed", True,
            f'{old.get("api_version")} -> {new.get("api_version")}'))

    _compare_map(found, "route", old.get("routes", {}), new.get("routes", {}),
                 BREAKING_ROUTE_FIELDS)
    _compare_map(found, "tool", old.get("tools", {}), new.get("tools", {}),
                 BREAKING_TOOL_FIELDS)
    _compare_map(found, "error_code", old.get("error_codes", {}),
                 new.get("error_codes", {}), BREAKING_CODE_FIELDS)
    _compare_webhook(found, old.get("webhook", {}), new.get("webhook", {}))

    old_headers = set(old.get("headers") or ())
    for gone in sorted(old_headers - set(new.get("headers") or ())):
        found.differences.append(Difference(
            "header", gone, "removed", True, "clients read it"))
    return found


def _compare_map(found: Comparison, area: str, old: dict, new: dict,
                 breaking_fields) -> None:
    for subject in sorted(set(old) - set(new)):
        found.differences.append(Difference(area, subject, "removed", True))
    for subject in sorted(set(new) - set(old)):
        found.differences.append(Difference(area, subject, "added", False))
    for subject in sorted(set(old) & set(new)):
        before, after = old[subject], new[subject]
        for key in sorted(set(before) | set(after)):
            if before.get(key) == after.get(key):
                continue
            breaks = key in breaking_fields
            if area == "tool" and key == "required_scopes":
                # Only *adding* a required scope breaks a caller; dropping one
                # widens what an existing key may do.
                breaks = bool(set(after.get(key) or ())
                              - set(before.get(key) or ()))
            found.differences.append(Difference(
                area, subject, "changed", breaks,
                f'{key}: {before.get(key)!r} -> {after.get(key)!r}'))


def _compare_webhook(found: Comparison, old: dict, new: dict) -> None:
    for key in ("signature_version", "payload_version"):
        if old.get(key) != new.get(key):
            found.differences.append(Difference(
                "webhook", key, "changed", True,
                f'{old.get(key)} -> {new.get(key)} — receivers verify on this'))
    old_events = set(old.get("event_types") or ())
    new_events = set(new.get("event_types") or ())
    for gone in sorted(old_events - new_events):
        found.differences.append(Difference("webhook", gone, "removed", True,
                                            "a subscriber asked for it"))
    for extra in sorted(new_events - old_events):
        found.differences.append(Difference("webhook", extra, "added", False))
    old_fields = set(old.get("payload_fields") or ())
    for gone in sorted(old_fields - set(new.get("payload_fields") or ())):
        found.differences.append(Difference(
            "webhook", f"payload.{gone}", "removed", True, "receivers parse it"))


__all__ = ["BREAKING_CODE_FIELDS", "BREAKING_ROUTE_FIELDS",
           "BREAKING_TOOL_FIELDS", "Comparison", "Difference",
           "SNAPSHOT_VERSION", "compare", "snapshot"]
