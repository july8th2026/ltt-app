"""P4 crash/retry and disable-mid-step checks use independent external state."""
# ruff: noqa: F811 -- imported pytest fixture is intentionally requested below.
import pytest
from sqlalchemy import select

from tests.test_1013_vps_pinned_provisioning import db, _profile, _instance  # noqa: F401
from apps.vps.services import mutation_coordinator as coordinator
from apps.vps.tables import VpsExternalMutation


def _context(db):
    profile = _profile(db)
    instance = _instance(db, profile_id=profile.id)
    return profile, instance


def test_request_is_durable_before_external_call_and_retry_does_not_repeat(db):
    _, instance = _context(db)
    external, calls = [], []
    def mutate():
        row = db.execute(select(VpsExternalMutation)).scalar_one()
        assert row.state == "REQUESTED" and row.attempts == 1
        calls.append("mutate")
        external.append("done")
    kwargs = dict(operation_id="operation", instance=instance, step="VM_CREATE",
                  request={"vmid": 210}, mutate=mutate, readback=lambda: bool(external))
    assert coordinator.execute(db, **kwargs).state == "OBSERVED"
    assert coordinator.execute(db, **kwargs).state == "OBSERVED"
    assert calls == ["mutate"]


def test_lost_response_requires_review_and_never_repeats(db):
    _, instance = _context(db)
    external, calls = [], []
    def mutate():
        external.append("created")
        calls.append(1)
        raise TimeoutError("secret=fixture-do-not-store")
    kwargs = dict(operation_id="operation", instance=instance, step="VM_CREATE",
                  request={}, mutate=mutate, readback=lambda: bool(external))
    with pytest.raises(coordinator.MutationNeedsReview):
        coordinator.execute(db, **kwargs)
    row = db.execute(select(VpsExternalMutation)).scalar_one()
    assert row.state == "NEEDS_REVIEW" and "fixture" not in row.last_error_detail
    with pytest.raises(coordinator.MutationNeedsReview):
        coordinator.execute(db, **kwargs)
    assert calls == [1]


def test_disable_between_readback_and_mutation_prevents_call(db):
    profile, instance = _context(db)
    calls = []
    def readback():
        profile.status, profile.accept_new, profile.is_default = "DISABLED", False, False
        db.commit()
        return False
    with pytest.raises(coordinator.MutationBlocked):
        coordinator.execute(db, operation_id="operation", instance=instance,
                            step="VM_CREATE", request={}, readback=readback,
                            mutate=lambda: calls.append(1))
    assert calls == []


def test_mutation_without_confirming_readback_is_not_observed(db):
    _, instance = _context(db)
    calls = []
    with pytest.raises(coordinator.MutationNeedsReview):
        coordinator.execute(db, operation_id="operation", instance=instance,
                            step="VM_CREATE", request={}, readback=lambda: False,
                            mutate=lambda: calls.append(1))
    assert calls == [1]
    assert db.execute(select(VpsExternalMutation.state)).scalar_one() == "NEEDS_REVIEW"


def test_idempotency_key_cannot_silently_change_request(db):
    from apps.vps.services import mutation_journal
    from apps.vps.services.backends.contracts import BackendConflict
    _, instance = _context(db)
    mutation_journal.intent(db, operation_id="operation", instance=instance,
                            step="VM_CREATE", request={"vmid": 210})
    db.commit()
    with pytest.raises(BackendConflict):
        mutation_journal.intent(db, operation_id="operation", instance=instance,
                                step="VM_CREATE", request={"vmid": 211})


def test_retry_after_final_business_commit_failure_reuses_observed_mutation(
        db, monkeypatch):
    """External success must not be repeated when the final app commit fails.

    This injects the failure after the independent readback has already made
    the mutation OBSERVED. A new worker/session-shaped retry must adopt that
    durable evidence and may then finish the business state without another
    provider call.
    """
    _, instance = _context(db)
    external, calls = [], []

    def mutate():
        calls.append("provider-call")
        external.append("created")

    kwargs = dict(
        operation_id="operation-final-commit",
        instance=instance,
        step="VM_CREATE",
        request={"vmid": 210},
        mutate=mutate,
        readback=lambda: bool(external),
    )
    assert coordinator.execute(db, **kwargs).state == "OBSERVED"

    # Model a failed final application transaction. Its rollback must not undo
    # the journal commit that preceded it.
    real_commit = db.commit

    def fail_final_commit():
        db.rollback()
        raise RuntimeError("injected final business commit failure")

    monkeypatch.setattr(db, "commit", fail_final_commit)
    instance.trang_thai = "dang_chay"
    with pytest.raises(RuntimeError, match="injected final business commit failure"):
        db.commit()
    monkeypatch.setattr(db, "commit", real_commit)
    db.refresh(instance)
    assert instance.trang_thai != "dang_chay"

    assert coordinator.execute(db, **kwargs).state == "OBSERVED"
    instance.trang_thai = "dang_chay"
    db.commit()
    assert calls == ["provider-call"]
