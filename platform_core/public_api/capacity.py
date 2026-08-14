"""Is the machinery behind a tool actually able to do the work right now.

A limit says "you have had enough". Capacity says "there is nothing to give" —
and they need different answers, because the second one is not the caller's
fault and retrying later really will work.

What is checked, and why only these
-----------------------------------

Each check maps to a resource whose absence makes a job **certain** to fail, and
each reads a signal the platform already maintains:

* **provider credentials** — ``api_pool`` already tracks health, cooldown and
  quota per key. Only meaningful when the pool is actually the source for that
  category: every app here falls back to an environment credential, so an empty
  pool says nothing, while a pool that holds keys and can serve none is a real
  signal that the next job will fail after paying;
* **GPU** — ``gpu.available()`` for tools whose app declares ``requires=("gpu",)``;
* **storage** — the object store must accept a write, because a tool that
  produces a file and cannot store it fails at the very end, after paying;

Nothing here polls, retries or scores. It reads what other modules already know.
A second health engine would be a second thing to keep correct, and the first
time the two disagreed the honest answer would be unknowable.

Where it is enforced, and where it is not
-----------------------------------------

Only at **job creation**. Reads keep working during an outage — a customer whose
provider is down still needs to list their jobs and fetch yesterday's artifacts,
and refusing that turns a degraded platform into a dark one.

It also refuses **before** the credit hold, never after: refusing a call costs
the caller nothing, while holding credit for work that cannot run means a refund
to reconcile and a support conversation to have.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

log = logging.getLogger("ltt.public_api.capacity")

#: Cached probe results, keyed by resource. Storage and GPU probes touch real
#: devices, and doing that on every job creation would make the guard the
#: slowest part of the call it is protecting.
_TTL_S = 15.0
_cache: dict = {}


@dataclass(frozen=True)
class Unavailable:
    """Which resource is missing, in words a caller can act on."""

    resource: str
    detail: str
    retry_after: int = 60


def reset() -> None:
    """Drop cached probes. For tests, and for a clean process start."""
    _cache.clear()


def _cached(resource: str, probe, *, now: float | None = None):
    import time

    moment = time.monotonic() if now is None else now
    hit = _cache.get(resource)
    if hit is not None and moment - hit[0] < _TTL_S:
        return hit[1]
    value = probe()
    _cache[resource] = (moment, value)
    return value


def _providers_healthy(db, category: str) -> bool:
    """Is the credential pool *in use for this category and exhausted*?

    Two states have to be told apart, and conflating them was a real bug caught
    by the existing suite:

    * the pool holds **no** keys for this category — apps fall back to an
      environment credential when the pool cannot serve them, so an empty pool
      says nothing about whether the work can run. Refusing here would ground a
      deployment that never opted into the pool at all;
    * the pool holds keys and **none are usable** — cooling down, out of quota,
      disabled. That is a genuine capacity signal: the app will try the pool,
      the pool will refuse, and the job fails after the hold.

    So: silent when the pool is not the source of truth for this category, and
    honest when it is.
    """
    from sqlalchemy import select

    from platform_core import api_pool
    from platform_core.models import ApiKey

    rows = db.execute(select(ApiKey).where(
        ApiKey.enabled.is_(True))).scalars().all()
    if not any(category in (key.categories or []) for key in rows):
        return True

    try:
        api_pool.chon_key(db, category=category)
        return True
    except Exception as exc:  # noqa: BLE001 - any refusal means "cannot serve"
        # Logged, not swallowed: the refusal is correct, but "which provider,
        # and why" is the whole question an operator has when jobs start being
        # turned away.
        log.warning("khong chon duoc key cho category %s: %s: %s",
                    category, type(exc).__name__, exc)
        return False


def _gpu_present() -> bool:
    from platform_core import gpu

    try:
        return bool(gpu.available())
    except Exception as exc:  # noqa: BLE001 - a probe that errors is not a yes
        log.warning("probe GPU that bai: %s: %s", type(exc).__name__, exc)
        return False


def _storage_writable() -> bool:
    """A real round trip, like `/health/ready` does for the database.

    A configuration check would pass while the bucket was unreachable, which is
    exactly the failure this is meant to catch.
    """
    import io
    import uuid

    from platform_core.storage import get_storage

    key = f"health/capacity-{uuid.uuid4().hex}.probe"
    storage = get_storage()
    try:
        storage.put(key, io.BytesIO(b"ok"), content_type="text/plain")
    except Exception as exc:  # noqa: BLE001 - unreachable storage is the point
        log.warning("storage khong nhan ghi: %s: %s", type(exc).__name__, exc)
        return False
    try:
        storage.delete(key)
    except Exception as exc:  # noqa: BLE001 - a leftover probe is not a failure
        # Deliberately not fatal: the write succeeded, which is what was being
        # asked. But a probe file that cannot be removed will accumulate, so it
        # is said out loud rather than dropped.
        log.info("khong xoa duoc file probe %s: %s", key, type(exc).__name__)
    return True


def check(db, *, tool, manifest=None) -> Unavailable | None:
    """The first missing resource for this tool, or ``None``.

    ``manifest`` is optional so a caller that already resolved it does not look
    it up twice; without it, only the resources every tool needs are checked.
    """
    if not _cached("storage", _storage_writable):
        return Unavailable(
            "storage", "Object storage is not accepting writes right now.", 120)

    requires = set(getattr(manifest, "requires", ()) or ())
    if "gpu" in requires and not _cached("gpu", _gpu_present):
        return Unavailable("gpu", "No GPU is available for this tool.", 300)

    category = _category_for(tool)
    if category and not _cached(f"provider:{category}",
                                lambda: _providers_healthy(db, category)):
        return Unavailable(
            "provider",
            "No provider credential is available for this capability.", 120)
    return None


def _category_for(tool) -> str:
    """Which provider category a tool's work draws on, from its public name.

    Derived from the capability the catalog already computes rather than from a
    new manifest field: the tool is called `image.generate` because it generates
    images, and a second declaration of that would be a second thing to keep in
    step (AGENTS.md 8.4 — the platform must not know app names).
    """
    capability = str(getattr(tool, "capability", "") or "")
    return {"image": "image", "video": "video", "chat": "chat",
            "text": "chat", "story": "chat"}.get(capability, "")


__all__ = ["Unavailable", "check", "reset"]
