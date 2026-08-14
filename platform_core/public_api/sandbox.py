"""Test mode: the whole API, with the provider replaced and no money moved.

What a sandbox is for, and what it therefore must be
----------------------------------------------------

An integrator needs to prove the *wiring*: that their key works, that their
payload matches the schema, that a retry does not double-charge, that their
webhook receiver is reachable and verifies a signature. None of that needs a
provider call. What a sandbox can never prove is output quality — and pretending
otherwise is how a mock becomes a lie, so quality is checked with one live call
on the cheapest tool instead.

So test mode changes exactly one link in the chain: the handler. Authentication,
scopes, the tool catalog, input validation, quoting, the idempotency record, the
job row, the worker, the webhook and its signature are the same code as live. A
sandbox that skipped any of those would let an integration pass here and fail in
production, which is worse than having no sandbox at all (decision D4).

The two hard rules
------------------

**A test key cannot spend.** Not "spends little" — cannot. It never reaches
``credit.giu_cho``, so a leaked test key costs nothing, which is the property a
live key can never have.

**Live and test never mix.** A test key sees only test jobs; a live key sees only
live ones. Same tables, same worker, one flag — a second ledger or a second queue
would be a second thing to keep correct (COMMON_RULES §3).
"""
from __future__ import annotations

MODE_LIVE = "live"
MODE_TEST = "test"
MODES = (MODE_LIVE, MODE_TEST)

#: What a canned artifact contains. A real PNG header so a client that inspects
#: the bytes sees an image rather than something that only claims to be one.
SAMPLE_PNG = (b"\x89PNG\r\n\x1a\n"
              b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
              b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
              b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
              b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")

SAMPLE_TEXT = ("This is sandbox output. No provider was called and no credit "
               "moved. Switch to a live key to get real results.")


def is_test(mode: str) -> bool:
    return str(mode or MODE_LIVE) == MODE_TEST


def mode_of_job(job) -> str:
    """The mode a job was created in, from the meta block the API attached."""
    from platform_core.public_api.invocation import api_meta

    return str(api_meta(job).get("mode") or MODE_LIVE)


def ensure_same_mode(job, principal):
    """Return ``job``, or raise the same 404 a stranger's job would.

    A test key must not be able to read, cancel or download a live job — and a
    live key must not see test traffic mixed into its history. Same 404 as
    ownership uses: a caller cannot tell "not yours" from "wrong world" from
    "never existed".
    """
    from platform_core.public_api.errors import not_found

    if mode_of_job(job) != str(getattr(principal, "mode", MODE_LIVE)
                               or MODE_LIVE):
        raise not_found("Not found.")
    return job


def restrict_to_mode(statement, model, principal):
    """Narrow a job query to the caller's own world.

    Filtered in SQL rather than after the fetch, because filtering a page after
    it is read gives short pages and a wrong "has more" — the caller would page
    through gaps.

    Jobs created before this column existed, and every job created from the web
    UI, carry no mode at all. Those are live work, so a live key sees them and a
    test key does not.
    """
    from sqlalchemy import or_

    from platform_core.public_api.invocation import API_META_KEY

    column = model.params[(API_META_KEY, "mode")].as_string()
    if is_test(getattr(principal, "mode", MODE_LIVE)):
        return statement.where(column == MODE_TEST)
    return statement.where(or_(column.is_(None), column != MODE_TEST))


#: Ceiling on canned files per output field. The count comes from validated
#: input, so it is already bounded by the tool's own schema; this is the belt
#: that keeps a contract mistake from turning one call into a disk full.
MAX_SANDBOX_FILES = 8


def _how_many(tool, field: str, params: dict) -> int:
    """How many entries an ``artifact[]`` field should hold.

    A live ``count=2`` call returns two files; a sandbox that always returned
    one would have the right *shape* and the wrong *cardinality*, which is
    enough to break an integration that reads the second entry.
    """
    param = (getattr(tool, "output_counts", None) or {}).get(field)
    if not param:
        return 1
    try:
        wanted = int((params or {}).get(param, 1))
    except (TypeError, ValueError):
        wanted = 1
    return max(1, min(wanted, MAX_SANDBOX_FILES))


def canned_result(tool, params: dict, storage) -> dict:
    """A result shaped exactly like the tool's published output schema.

    Driven by the contract rather than hand-written per tool: a sandbox whose
    response shape drifts from the real one teaches an integrator to parse
    something that will not arrive.
    """
    from platform_core.public_api.media import store_sandbox_artifact

    outputs = (tool.output_schema or {}).get("properties", {})
    result: dict = {}
    for field, spec in outputs.items():
        kind = str(spec.get("type") or "")
        if kind == "artifact":
            result[field] = store_sandbox_artifact(storage, params, field, 0)
        elif kind == "artifact[]":
            count = _how_many(tool, field, params)
            result[field] = [store_sandbox_artifact(storage, params, field, i)
                             for i in range(count)]
        elif kind == "object":
            result[field] = {"sandbox": True, "note": SAMPLE_TEXT}
        else:
            result[field] = SAMPLE_TEXT
    return result
