"""Fail-closed mutation execution with durable request and independent readback.

REQUESTED is committed before the external call. A retry never blindly repeats
an ambiguous mutation: it can only observe the intended state or ask for review.
This module owns its transaction boundary and is called only by worker jobs.
"""
from __future__ import annotations

from sqlalchemy import update

from apps.vps.services import mutation_journal as journal
from apps.vps.tables import VpsInfrastructureProfile, VpsExternalMutation


class MutationNeedsReview(RuntimeError):
    pass


class MutationBlocked(RuntimeError):
    pass


def execute(db, *, operation_id, instance, step, request, mutate, readback):
    """Return only after readback; never store raw exception/provider payloads."""
    row = journal.intent(db, operation_id=operation_id, instance=instance,
                         step=step, request=request)
    db.commit()

    def guard():
        db.refresh(instance)
        profile = db.get(VpsInfrastructureProfile, row.profile_id)
        if profile is not None:
            db.refresh(profile)
        if (profile is None or profile.status == "DISABLED"
                or instance.profile_resolution_state != "PINNED"
                or instance.infrastructure_profile_id != row.profile_id
                or instance.vmid in range(100, 108)):
            journal.failed(db, row, "BLOCKED_PROFILE_OR_SCOPE")
            db.commit()
            raise MutationBlocked("mutation blocked by pinned profile or protected scope")

    def review():
        journal.needs_review(db, row)
        db.commit()
        raise MutationNeedsReview("external outcome needs canonical readback review")

    guard()
    if row.state in ("NEEDS_REVIEW", "FAILED", "COMPENSATED"):
        raise MutationNeedsReview("mutation requires explicit operator recovery")
    try:
        matches = readback() is True
    except Exception:
        review()
    if matches:
        guard()
        journal.observed(db, row)
        db.commit()
        return row
    if row.state in ("REQUESTED", "OBSERVED"):
        review()
    guard()
    claimed = db.execute(update(VpsExternalMutation).where(
        VpsExternalMutation.id == row.id, VpsExternalMutation.state == "INTENT"
    ).values(state="REQUESTED", attempts=VpsExternalMutation.attempts + 1))
    if claimed.rowcount != 1:
        db.rollback()
        raise MutationNeedsReview("another worker owns the external request; retry readback")
    db.commit()
    try:
        mutate()
        guard()
        if readback() is not True:
            review()
    except MutationBlocked:
        raise
    except MutationNeedsReview:
        raise
    except Exception:
        review()
    journal.observed(db, row)
    db.commit()
    return row
