"""Who may call how much, and the switch that stops everything.

Two things live here, and they are separate on purpose.

**Policy** answers *how much*. It resolves one number — a rate, a concurrency
cap, a credit ceiling, an upload size — from a chain of overrides, and the answer
must be the same every time for the same inputs. A limit that varies with the
order the code happened to check things is a limit nobody can support.

**Kill switch** answers *not now*. It is not a limit set to zero. A limit is
steady-state policy; a kill switch is an incident tool with an author, a reason
and usually an expiry. Conflating them means the only record of "we turned this
off at 3am and why" is a number that looks like configuration.

The precedence chain
--------------------

::

    global  →  tier  →  user  →  project  →  credential  →  tool

* **global** — the deployment's environment (``PublicApiConfig``). It already
  existed, and it stays the floor;
* **tier** — the default policy row, if the operator defined one. A commercial
  plan lands here;
* **user → project → credential** — an override attached to a specific subject,
  narrowest last;
* **tool** — per-tool overrides carried inside whichever policy won.

Each step overrides **only the fields it actually sets**. A policy that sets a
concurrency cap and nothing else changes concurrency and leaves every other
number where the previous step left it. Without that rule, attaching a policy to
raise one limit would silently reset the four it says nothing about — and the
person who attached it would have no way to know.

That is also why every numeric column is nullable and ``NULL`` means "inherit"
rather than using ``0`` as the sentinel: zero is a real, meaningful limit (a rate
of zero refuses everything), and a scheme that spent it on "unset" could never
express it.

Anti-bypass
-----------

Before this module, the rate limits were bucketed per **key**. An account that
wanted five times the rate created five keys — no exploit required, just the
credential page. So a rate now costs the account as well as the key: the key
bucket protects the platform from one broken client, and the **account** bucket
is the one that means anything commercially.

Concurrency and the daily credit ceiling were already per account, so the hole
was specific to the two rate layers.

What is deliberately absent
---------------------------

**Paid priority classes.** ``jobs.claim()`` now provides fair-share by account,
stable FIFO inside an account and aging for old work. That is operational
fairness, not a commercial priority tier: there is still no priority column on
``Job`` and price/credit never appears in the ordering. Adding a policy field
would therefore promise a paid queue jump the product has not decided to sell.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from sqlalchemy import select

from platform_core.i18n import _ as _t
from platform_core.public_api.tables import (ApiKillSwitch, ApiPolicy,
                                             ApiPolicyAssignment,
                                             KILL_GLOBAL_SCOPES,
                                             KILL_GLOBAL_WRITES, KILL_KEY,
                                             KILL_MAINTENANCE, KILL_PROJECT,
                                             KILL_SCOPES, KILL_TOOL, KILL_USER,
                                             POLICY_SCOPE_KEY,
                                             POLICY_SCOPE_PROJECT,
                                             POLICY_SCOPE_USER, POLICY_SCOPES)

#: Fields a policy may override. Order is the order they are documented in.
LIMIT_FIELDS = ("rpm_read", "rpm_write", "rpm_create", "max_active_jobs",
                "daily_credit", "max_upload_bytes")

MIN_REASON = 8


class PolicyError(Exception):
    """A refusal an operator should read, not a bug."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Limits:
    """The resolved answer, and a record of how it was reached.

    ``sources`` names the step that last set each field. It exists because the
    first question about any limit is "why is it that number", and an engine
    that cannot answer it turns every support conversation into an
    investigation.
    """

    rpm_read: int
    rpm_write: int
    rpm_create: int
    max_active_jobs: int
    daily_credit: int
    max_upload_bytes: int
    class_concurrency: dict
    sources: dict

    def as_dict(self) -> dict:
        return {field: getattr(self, field) for field in LIMIT_FIELDS}


def _from_config(config) -> Limits:
    """The floor: whatever this deployment's environment already said.

    ``rpm_read`` and ``rpm_write`` both start from the single ``request_rpm``
    the config has always carried. Splitting reads from writes is new here, so
    the starting point has to be the number that was already in force —
    inventing a different default would change behaviour for a deployment that
    never opted into policies at all.
    """
    return Limits(
        rpm_read=int(config.request_rpm),
        rpm_write=int(config.request_rpm),
        rpm_create=int(config.create_rpm),
        max_active_jobs=int(config.max_active_jobs),
        daily_credit=int(config.daily_credit_limit),
        # The platform's own upload ceiling, not `max_body_bytes` — that one
        # caps a JSON control-plane body (256 KB) and has nothing to do with
        # media. Showing it here read as "uploads are capped at 256 KB", which
        # is wrong by four orders of magnitude.
        max_upload_bytes=_platform_upload_ceiling(),
        class_concurrency=dict(config.class_concurrency or {}),
        sources={field: "global" for field in LIMIT_FIELDS},
    )


def _platform_upload_ceiling() -> int:
    """What an upload can be before the platform itself refuses it.

    Cloudflare rejects a body over 100 MB before it reaches the origin, so the
    multipart fallback is capped below that; a policy may lower the number for a
    tier but must not be able to raise it past what the edge will pass.
    """
    from platform_core.public_api.media import MULTIPART_LIMIT

    return int(MULTIPART_LIMIT)


def _apply(limits: Limits, policy: ApiPolicy, label: str) -> Limits:
    """Overlay one policy. Only the fields it sets; everything else survives."""
    changes: dict = {}
    sources = dict(limits.sources)
    for field in LIMIT_FIELDS:
        value = getattr(policy, field, None)
        if value is None:
            continue
        changes[field] = int(value)
        sources[field] = label
    classes = policy.class_concurrency or {}
    if classes:
        merged = dict(limits.class_concurrency)
        merged.update({str(key): int(value) for key, value in classes.items()})
        changes["class_concurrency"] = merged
        sources["class_concurrency"] = label
    if not changes:
        return limits
    return replace(limits, sources=sources, **changes)


def _apply_tool(limits: Limits, policy: ApiPolicy, tool_name: str) -> Limits:
    """The narrowest step: this policy's overrides for one named tool."""
    overrides = (policy.tool_overrides or {}).get(str(tool_name or ""))
    if not isinstance(overrides, dict) or not overrides:
        return limits
    changes: dict = {}
    sources = dict(limits.sources)
    for field in LIMIT_FIELDS:
        if field not in overrides or overrides[field] is None:
            continue
        try:
            changes[field] = int(overrides[field])
        except (TypeError, ValueError):
            continue
        sources[field] = f"tool:{tool_name}"
    if not changes:
        return limits
    return replace(limits, sources=sources, **changes)


def _assigned(db, scope: str, subject_id: str) -> ApiPolicy | None:
    if not subject_id:
        return None
    row = db.execute(
        select(ApiPolicy)
        .join(ApiPolicyAssignment,
              ApiPolicyAssignment.policy_id == ApiPolicy.id)
        .where(ApiPolicyAssignment.scope == scope,
               ApiPolicyAssignment.subject_id == str(subject_id))
    ).scalar_one_or_none()
    return row


def default_policy(db) -> ApiPolicy | None:
    return db.execute(select(ApiPolicy).where(
        ApiPolicy.is_default.is_(True))).scalar_one_or_none()


def resolve(db, *, config, principal=None, tool_name: str = "") -> Limits:
    """Walk the chain once and return the numbers that apply right now.

    Deterministic by construction: the steps are a fixed list, each one either
    sets a field or does not, and the last writer wins. No step can be skipped
    by data — a missing policy is simply a step that changes nothing.
    """
    limits = _from_config(config)

    tier = default_policy(db)
    if tier is not None:
        limits = _apply(limits, tier, f"tier:{tier.name}")

    winner = tier
    if principal is not None:
        for scope, subject in (
            (POLICY_SCOPE_USER, getattr(principal, "user_id", "")),
            (POLICY_SCOPE_PROJECT, getattr(principal, "project_id", "")),
            (POLICY_SCOPE_KEY, getattr(principal, "key_id", "")),
        ):
            policy = _assigned(db, scope, str(subject or ""))
            if policy is not None:
                limits = _apply(limits, policy, f"{scope}:{policy.name}")
                winner = policy

    # Tool overrides come from whichever policy won, not from every policy in
    # the chain: a tool rule inside a policy that was overridden wholesale is a
    # rule its author no longer intends to apply.
    if winner is not None and tool_name:
        limits = _apply_tool(limits, winner, tool_name)
    return limits


# ── Policies: writes ─────────────────────────────────────────────────────────

def create_policy(db, *, name: str, description: str = "", is_default=False,
                  class_concurrency=None, tool_overrides=None,
                  now: datetime | None = None, **fields) -> ApiPolicy:
    clean_name = str(name or "").strip()
    if not clean_name:
        raise PolicyError(_t("Chính sách phải có tên."))
    if db.execute(select(ApiPolicy).where(
            ApiPolicy.name == clean_name)).scalar_one_or_none() is not None:
        raise PolicyError(_t("Đã có chính sách trùng tên."))

    moment = now or _now()
    policy = ApiPolicy(
        id=str(uuid.uuid4()), name=clean_name,
        description=str(description or "")[:500],
        class_concurrency=_clean_classes(class_concurrency),
        tool_overrides=_clean_tool_overrides(tool_overrides),
        is_default=bool(is_default), created_at=moment, updated_at=moment,
        **_clean_fields(fields))
    db.add(policy)
    db.flush()
    if policy.is_default:
        _make_only_default(db, policy)
    return policy


def update_policy(db, policy: ApiPolicy, *, description=None,
                  class_concurrency=None, tool_overrides=None,
                  is_default=None, now: datetime | None = None,
                  **fields) -> ApiPolicy:
    if description is not None:
        policy.description = str(description)[:500]
    if class_concurrency is not None:
        policy.class_concurrency = _clean_classes(class_concurrency)
    if tool_overrides is not None:
        policy.tool_overrides = _clean_tool_overrides(tool_overrides)
    for field, value in _clean_fields(fields, allow_none=True).items():
        setattr(policy, field, value)
    policy.updated_at = now or _now()
    if is_default is not None:
        policy.is_default = bool(is_default)
        if policy.is_default:
            _make_only_default(db, policy)
    db.flush()
    return policy


def delete_policy(db, policy: ApiPolicy) -> None:
    """Assignments go with it (``ON DELETE CASCADE``); limits fall back a step.

    Nothing is orphaned and nothing is silently kept: an account whose policy is
    deleted resolves to the tier, or to the global floor. That is a change an
    operator can predict, which is the only kind worth allowing.
    """
    db.execute(ApiPolicyAssignment.__table__.delete().where(
        ApiPolicyAssignment.policy_id == policy.id))
    db.delete(policy)
    db.flush()


def assign(db, *, policy: ApiPolicy, scope: str, subject_id: str,
           now: datetime | None = None) -> ApiPolicyAssignment:
    if scope not in POLICY_SCOPES:
        raise PolicyError(_t("Phạm vi gán không hợp lệ."))
    subject = str(subject_id or "").strip()
    if not subject:
        raise PolicyError(_t("Phải nêu đối tượng được gán."))

    existing = db.execute(select(ApiPolicyAssignment).where(
        ApiPolicyAssignment.scope == scope,
        ApiPolicyAssignment.subject_id == subject)).scalar_one_or_none()
    if existing is not None:
        # Reassignment rather than a second row: two policies on one subject
        # would make the answer depend on row order, which is exactly the
        # non-determinism this module exists to prevent.
        existing.policy_id = policy.id
        db.flush()
        return existing

    row = ApiPolicyAssignment(id=str(uuid.uuid4()), policy_id=policy.id,
                              scope=scope, subject_id=subject,
                              created_at=now or _now())
    db.add(row)
    db.flush()
    return row


def unassign(db, *, scope: str, subject_id: str) -> bool:
    row = db.execute(select(ApiPolicyAssignment).where(
        ApiPolicyAssignment.scope == scope,
        ApiPolicyAssignment.subject_id == str(subject_id))).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


def list_policies(db) -> list:
    return list(db.execute(select(ApiPolicy).order_by(
        ApiPolicy.is_default.desc(), ApiPolicy.name)).scalars())


def assignments_for(db, policy_id: str) -> list:
    return list(db.execute(select(ApiPolicyAssignment).where(
        ApiPolicyAssignment.policy_id == str(policy_id))).scalars())


def _make_only_default(db, policy: ApiPolicy) -> None:
    for row in db.execute(select(ApiPolicy).where(
            ApiPolicy.is_default.is_(True))).scalars():
        if row.id != policy.id:
            row.is_default = False
    db.flush()


def _clean_fields(fields: dict, *, allow_none: bool = False) -> dict:
    out: dict = {}
    for field, value in (fields or {}).items():
        if field not in LIMIT_FIELDS:
            raise PolicyError(_t("Trường hạn mức không hợp lệ: {field}"
                                 ).format(field=field))
        if value is None:
            if allow_none:
                out[field] = None
            continue
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise PolicyError(_t("Hạn mức phải là số nguyên: {field}"
                                 ).format(field=field)) from exc
        if number < 0:
            raise PolicyError(_t("Hạn mức không được âm: {field}"
                                 ).format(field=field))
        out[field] = number
    return out


def _clean_classes(values) -> dict:
    out: dict = {}
    for key, value in (values or {}).items():
        try:
            out[str(key)] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def _clean_tool_overrides(values) -> dict:
    out: dict = {}
    for tool, fields in (values or {}).items():
        if not isinstance(fields, dict):
            continue
        clean = {field: int(value) for field, value in fields.items()
                 if field in LIMIT_FIELDS and str(value).lstrip("-").isdigit()
                 and int(value) >= 0}
        if clean:
            out[str(tool)] = clean
    return out


# ── Kill switches ────────────────────────────────────────────────────────────

def active_switches(db, *, now: datetime | None = None) -> list:
    """Every switch still in force. Expired rows are simply not returned.

    No sweeper: a switch whose expiry has passed stops applying the moment it
    passes, and the row stays as evidence of what was done and why.
    """
    moment = now or _now()
    return [row for row in db.execute(select(ApiKillSwitch)).scalars()
            if row.is_active(now=moment)]


def engage(db, *, scope: str, subject: str = "", reason: str,
           created_by: str = "", expires_at: datetime | None = None,
           now: datetime | None = None) -> ApiKillSwitch:
    """Turn something off, on the record.

    ``reason`` is required and checked here rather than in the UI: a switch
    reached from a script with no reason is exactly the outage nobody can
    explain afterwards.
    """
    if scope not in KILL_SCOPES:
        raise PolicyError(_t("Phạm vi kill switch không hợp lệ."))
    clean_subject = "" if scope in KILL_GLOBAL_SCOPES else str(subject or "").strip()
    if scope not in KILL_GLOBAL_SCOPES and not clean_subject:
        raise PolicyError(_t("Phải nêu đối tượng cho phạm vi này."))
    if len(str(reason or "").strip()) < MIN_REASON:
        raise PolicyError(_t(
            "Phải ghi lý do (ít nhất {n} ký tự) cho thao tác này."
        ).format(n=MIN_REASON))

    moment = now or _now()
    if expires_at is not None and expires_at <= moment:
        raise PolicyError(_t("Thời điểm hết hiệu lực phải ở tương lai."))

    existing = db.execute(select(ApiKillSwitch).where(
        ApiKillSwitch.scope == scope,
        ApiKillSwitch.subject == clean_subject)).scalar_one_or_none()
    if existing is not None:
        existing.reason = str(reason).strip()[:500]
        existing.created_by = str(created_by or "")[:255]
        existing.created_at = moment
        existing.expires_at = expires_at
        db.flush()
        return existing

    row = ApiKillSwitch(id=str(uuid.uuid4()), scope=scope,
                        subject=clean_subject, reason=str(reason).strip()[:500],
                        created_by=str(created_by or "")[:255],
                        created_at=moment, expires_at=expires_at)
    db.add(row)
    db.flush()
    return row


def release(db, switch: ApiKillSwitch) -> None:
    db.delete(switch)
    db.flush()


def switch_by_id(db, switch_id: str):
    return db.get(ApiKillSwitch, str(switch_id))


@dataclass(frozen=True)
class Refusal:
    """Why a call is being refused, in terms the caller can act on."""

    scope: str
    reason: str
    retry_after: int = 60


def check(db, *, principal=None, tool_name: str = "", is_write: bool = False,
          now: datetime | None = None) -> Refusal | None:
    """The first refusal that applies, or ``None``.

    Ordered widest first — maintenance, then global writes, then the subject,
    then the tool. When several switches apply, the caller is told about the
    broadest one, because that is the one whose lifting unblocks them.
    """
    moment = now or _now()
    switches = active_switches(db, now=moment)
    if not switches:
        return None

    by_key = {(row.scope, row.subject): row for row in switches}

    row = by_key.get((KILL_MAINTENANCE, ""))
    if row is not None:
        return Refusal(KILL_MAINTENANCE, row.reason, 300)

    if is_write:
        row = by_key.get((KILL_GLOBAL_WRITES, ""))
        if row is not None:
            return Refusal(KILL_GLOBAL_WRITES, row.reason, 300)

    if principal is not None:
        for scope, subject in ((KILL_USER, getattr(principal, "user_id", "")),
                               (KILL_PROJECT, getattr(principal, "project_id", "")),
                               (KILL_KEY, getattr(principal, "key_id", ""))):
            row = by_key.get((scope, str(subject or "")))
            if row is not None:
                return Refusal(scope, row.reason, 0)

    if tool_name:
        row = by_key.get((KILL_TOOL, str(tool_name)))
        if row is not None:
            return Refusal(KILL_TOOL, row.reason, 300)
    return None


__all__ = [
    "LIMIT_FIELDS", "Limits", "MIN_REASON", "PolicyError", "Refusal",
    "active_switches", "assign", "assignments_for", "check", "create_policy",
    "default_policy", "delete_policy", "engage", "list_policies", "release",
    "resolve", "switch_by_id", "unassign", "update_policy",
]
