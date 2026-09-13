"""State machine and selection authority for VPS infrastructure profiles."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.vps.tables import (VpsInfrastructureProfile, VpsInstance,
                             VpsProfileHealth)

PROFILE_STATES = ("ACTIVE", "DRAINING", "STANDBY", "DISABLED")
HEALTH_STATES = ("UNKNOWN", "STALE", "HEALTHY", "DEGRADED", "CRITICAL")
REQUIRED_HEALTH_COMPONENTS = (
    "compute", "ip", "gateway", "network", "capacity", "runtime")

# Stable IDs make migration/backfill and operator tooling agree without looking
# profiles up by a mutable display name.
VULTR_PROFILE_ID = "00000000-0000-4000-8000-000000000401"
OVH_PROFILE_ID = "00000000-0000-4000-8000-000000000402"


class ProfileNotReady(RuntimeError):
    """Profile cannot safely accept a new external mutation."""


def pinned_profile(db: Session, instance: VpsInstance) -> VpsInfrastructureProfile:
    """Resolve only the durable pin; never fall back to default/global credentials."""
    db.refresh(instance)
    if instance.profile_resolution_state != "PINNED" or not instance.infrastructure_profile_id:
        raise ProfileNotReady("NEEDS_REVIEW: instance has no verified profile pin")
    row = db.get(VpsInfrastructureProfile, instance.infrastructure_profile_id)
    if row is None:
        raise ProfileNotReady("NEEDS_REVIEW: pinned profile is missing")
    db.refresh(row)
    if row.status == "DISABLED":
        raise ProfileNotReady("DISABLED: pinned profile blocks normal operations")
    if instance.vmid is not None and int(instance.vmid) in range(100, 108):
        raise ProfileNotReady("PROTECTED: VM100–107 cannot be operated by VPS")
    return row


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def health_prerequisites(
    db: Session,
    profile_id: str,
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> tuple[bool, str, datetime | None]:
    """Check latest independent component observations; missing/stale fails closed."""
    current = _utc(now or datetime.now(timezone.utc))
    newest: datetime | None = None
    for component in REQUIRED_HEALTH_COMPONENTS:
        row = db.execute(
            select(VpsProfileHealth)
            .where(
                VpsProfileHealth.infrastructure_profile_id == profile_id,
                VpsProfileHealth.component == component,
            )
            .order_by(VpsProfileHealth.observed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return False, f"missing health component: {component}", newest
        observed = _utc(row.observed_at)
        if newest is None or observed > newest:
            newest = observed
        timestamps = [observed]
        if row.generated_at is not None:
            timestamps.append(_utc(row.generated_at))
        for timestamp in timestamps:
            age = (current - timestamp).total_seconds()
            if age < -60:
                return False, f"future health component: {component}", newest
            if age > max_age_seconds:
                return False, f"stale health component: {component}", newest
        if row.status != "HEALTHY":
            return False, f"unhealthy component: {component}={row.status}", newest
    return True, "", newest


def activate_profile(
    db: Session,
    profile_id: str,
    *,
    make_default: bool = False,
    max_age_seconds: int = 300,
) -> VpsInfrastructureProfile:
    """Activate only after fresh health; serialize default changes in the DB."""
    profile = db.execute(
        select(VpsInfrastructureProfile)
        .where(VpsInfrastructureProfile.id == profile_id)
        .with_for_update()
    ).scalar_one_or_none()
    if profile is None:
        raise ProfileNotReady("profile not found")

    ready, reason, observed = health_prerequisites(
        db, profile.id, max_age_seconds=max_age_seconds)
    if not ready:
        raise ProfileNotReady(reason)

    if make_default:
        defaults = db.execute(
            select(VpsInfrastructureProfile)
            .where(VpsInfrastructureProfile.is_default.is_(True))
            .with_for_update()
        ).scalars().all()
        for old in defaults:
            old.is_default = False
        db.flush()

    profile.status = "ACTIVE"
    profile.accept_new = True
    profile.is_default = bool(make_default)
    profile.last_health_at = observed
    db.flush()
    return profile


def select_profile(db: Session, *, region: str) -> VpsInfrastructureProfile:
    """Select by customer-visible region only; provider/profile are not inputs."""
    rows = db.execute(
        select(VpsInfrastructureProfile)
        .where(
            VpsInfrastructureProfile.region == region,
            VpsInfrastructureProfile.status == "ACTIVE",
            VpsInfrastructureProfile.accept_new.is_(True),
        )
        .order_by(VpsInfrastructureProfile.is_default.desc())
        .with_for_update()
    ).scalars().all()
    rows = [row for row in rows if health_prerequisites(db, row.id)[0]]
    if not rows:
        raise ProfileNotReady(f"no healthy ACTIVE profile for region {region!r}")
    defaults = [row for row in rows if row.is_default]
    if len(defaults) == 1:
        return defaults[0]
    if len(rows) == 1:
        return rows[0]
    raise ProfileNotReady(f"ambiguous ACTIVE profiles for region {region!r}")


def pin_instance(
    instance: VpsInstance,
    profile: VpsInfrastructureProfile,
) -> None:
    """Pin once. An already-pinned instance can never follow a changed default."""
    if profile.status != "ACTIVE" or not profile.accept_new:
        raise ProfileNotReady("profile does not accept new VPS")
    existing = instance.infrastructure_profile_id
    if existing and existing != profile.id:
        raise ProfileNotReady("instance profile is immutable")
    instance.infrastructure_profile_id = profile.id
    instance.profile_resolution_state = "PINNED"
