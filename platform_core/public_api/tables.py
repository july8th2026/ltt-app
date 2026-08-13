"""Developer API key — the customer-facing machine credential (Q92, Prompt 03).

This is a **different domain** from ``platform_core.models.ApiKey``, and the two
must never be merged. They have opposite requirements:

* ``api_keys`` holds *provider* credentials the platform uses to call Gemini,
  BytePlus and friends. The worker has to recover the original secret, so it is
  encrypted at rest and ``api_keys.lay_credential()`` decrypts it;
* this table holds *customer* credentials. Nothing ever needs the original
  secret again — only the ability to check one. So only a one-way digest is
  stored, and a database leak yields nothing an attacker can present.

Storage layout of one key::

    ltt_sk_<key_id>_<secret>
            └─ public ─┘ └ 256-bit CSPRNG, never stored ┘

``key_id`` is public and indexed: a lookup is one primary-key hit rather than a
scan comparing digests. ``verifier_digest`` is ``HMAC-SHA256(pepper, secret)``,
with the pepper kept **outside** the database (see ``keys.py``) so that reading
the table alone still does not let an attacker verify guesses offline.

Why not bcrypt/argon2: this digest is checked on *every* API request. A KDF
priced to resist offline cracking of a human password would hand any anonymous
caller a CPU amplifier — the DoS is the bigger risk, and the input here is 256
bits of CSPRNG output, which has no dictionary to attack.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, JSON,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base

# Human-recognisable prefix. "sk" = secret key: if one of these ever appears in
# a paste, a log or a public repository, it is greppable and revocable.
KEY_PREFIX = "ltt_sk"

DEVKEY_ACTIVE = "active"
DEVKEY_REVOKED = "revoked"
DEVKEY_EXPIRED = "expired"
DEVKEY_DISABLED = "disabled"


def _now() -> datetime:
    return datetime.now(timezone.utc)


PROJECT_ACTIVE = "active"
PROJECT_ARCHIVED = "archived"


class ApiProject(Base):
    """One integration belonging to one account: the unit keys are grouped by.

    Why this exists at all, given that ``User`` already owns everything: an
    account that runs two integrations — say a website and an internal batch
    job — has no way to revoke one without disturbing the other, no way to give
    each its own spend ceiling, and no way to tell from a log line which of them
    is misbehaving. A project is the smallest thing that fixes all three, and it
    is deliberately *not* an organisation: billing still belongs to the user
    (Q92), so no second source of truth about money appears here.

    Archiving, never deleting. Keys, jobs and ledger entries are evidence about
    money that moved; a project that could be deleted would take the meaning of
    those rows with it while the rows themselves stayed.
    """

    __tablename__ = "api_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Stable, human-readable, unique per account — what a log line and a support
    # ticket refer to, and what stays put when the display name is edited.
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=PROJECT_ACTIVE,
                                        nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "slug", name="uq_api_project_owner_slug"),
        Index("ix_api_projects_owner_status", "user_id", "status"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"<ApiProject {self.slug} user={self.user_id[:8]}>"

    def is_active(self) -> bool:
        return self.status == PROJECT_ACTIVE


class DeveloperApiKey(Base):
    """One credential belonging to one platform ``User`` (Q92: principal = user)."""

    __tablename__ = "developer_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # RESTRICT, like the credit ledger: a key is evidence about who spent what,
    # and an account is deactivated rather than deleted.
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    # Nullable on purpose. Keys issued before projects existed keep working
    # exactly as they did; the migration gives each of them a project, and this
    # column stays nullable so that a future key-issuing path which forgets to
    # pass one fails visibly in review rather than at 3am on an upgrade.
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("api_projects.id", ondelete="RESTRICT"),
        nullable=True, index=True)
    # CIDR blocks this key may be presented from. Empty = anywhere, which is the
    # honest default: most integrations run from a host whose address changes.
    allowed_ips: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # Public half of the token: safe to show in a UI, in a log line and in an
    # audit record. This is what a support conversation refers to.
    key_id: Mapped[str] = mapped_column(String(48), nullable=False, unique=True,
                                        index=True)
    # HMAC-SHA256 hex of the secret half. Never the secret itself.
    verifier_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    # Which pepper produced the digest, so a pepper can be rotated without
    # invalidating every key at once.
    pepper_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Coarse permissions (Prompt 04 enforces them; stored here so a key issued
    # today already carries its policy).
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    # Optional narrowing of the public tool catalog. Empty list = "whatever the
    # catalog exposes"; the catalog itself is already an explicit allowlist, so
    # this is a second, per-key restriction rather than the only one.
    allowed_tools: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    # Written at most once per bucket (see ``keys.touch_last_used``): a column
    # updated on every authenticated request would turn a read-only endpoint
    # into a write and put every request behind a row lock.
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_developer_api_keys_owner_created", "user_id", "created_at"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        # key_id only: the secret is not in memory here, and the digest has no
        # business appearing in a log line either.
        return f"<DeveloperApiKey {self.key_id} user={self.user_id[:8]}>"

    def status(self, *, now: datetime | None = None) -> str:
        """Derived lifecycle state; the columns stay independent and auditable."""
        current = now or _now()
        if self.revoked_at is not None:
            return DEVKEY_REVOKED
        if not self.enabled:
            return DEVKEY_DISABLED
        if self.expires_at is not None and _aware(self.expires_at) <= current:
            return DEVKEY_EXPIRED
        return DEVKEY_ACTIVE

    def is_usable(self, *, now: datetime | None = None) -> bool:
        return self.status(now=now) == DEVKEY_ACTIVE


def _aware(value: datetime) -> datetime:
    """SQLite hands back naive datetimes; PostgreSQL does not."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


IDEMPOTENCY_IN_PROGRESS = "in_progress"
IDEMPOTENCY_COMPLETED = "completed"


class ApiIdempotencyRecord(Base):
    """One remembered chargeable operation, keyed by the caller's own key.

    Why a table and not the existing ``jobs.dedupe_key``: that one only matches
    a job that is still ``queued``/``running`` (``platform_core/jobs.py``), so a
    client retrying after its first request already finished would create a
    *second* job and a *second* hold. For a network client — which retries by
    design, on timeouts it cannot distinguish from failures — that is a
    double-charge waiting to happen.

    The unique constraint is the guarantee, not the code around it: two requests
    racing with the same key both try to insert, the database lets exactly one
    win, and the loser reads the winner's row.

    ``request_hash`` is what makes "same key, different payload" detectable —
    that combination is a client bug, and answering 409 is the only honest reply.
    """

    __tablename__ = "public_api_idempotency"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key_id: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    # Denormalised from the key so ownership questions never need a join, and so
    # a rotated/revoked key does not orphan its records.
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(48), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=IDEMPOTENCY_IN_PROGRESS, nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False)
    response: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("key_id", "operation", "idempotency_key",
                         name="uq_public_api_idempotency"),
        Index("ix_public_api_idempotency_owner", "user_id", "created_at"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return (f"<ApiIdempotencyRecord {self.operation} {self.status} "
                f"job={self.job_id[:8]}>")


class ApiRequestLog(Base):
    """One public API request, reduced to what makes it explainable.

    The columns are chosen by what a developer asks when something goes wrong —
    *which key, which tool, how did it end, how long, what did it cost, and
    where is the job* — and stop there. There is no body column and no `detail`
    column, because a debugging table that quietly accumulates payloads becomes
    a copy of customer content with a friendlier name.

    ``request_id`` is the same correlation id the response carries, so the
    string a customer pastes into a support ticket is the primary way in.
    """

    __tablename__ = "public_api_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False,
                                            index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(48), default="", nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), default="",
                                            nullable=False)
    method: Mapped[str] = mapped_column(String(8), default="", nullable=False)
    #: The templated route, not the filled-in path: an id in a URL is noise,
    #: and grouping by route is what makes the list readable.
    route: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    code: Mapped[str] = mapped_column(String(48), default="", nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                        index=True)
    credit_delta: Mapped[int] = mapped_column(Integer, default=0,
                                              nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        # The two questions the page asks: "my recent calls" and "my failures".
        Index("ix_public_api_requests_owner_time", "user_id", "created_at"),
        Index("ix_public_api_requests_owner_status", "user_id", "status"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return (f"<ApiRequestLog {self.method} {self.route} {self.status} "
                f"{self.request_id[:8]}>")


class ApiBudget(Base):
    """A spending limit a customer set for themselves.

    Note what is **not** here: any column that could change what the ledger
    says. A budget observes spending and, if hard-capped, refuses the next call;
    it never writes, adjusts or hides a credit entry. That separation is the
    only reason a self-service field is allowed near money at all.
    """

    __tablename__ = "api_budgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    #: "account" or "project" — a project is the unit EXT-04 made revocable and
    #: budgetable on its own.
    scope: Mapped[str] = mapped_column(String(16), default="account",
                                       nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), default="",
                                            nullable=False)
    period: Mapped[str] = mapped_column(String(8), default="month",
                                        nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    #: Percentages at which to warn. Bounded on the way in: an alert at 3% is
    #: noise, and noise is how people learn to ignore the one at 100%.
    thresholds: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    #: False warns, True refuses. A customer who asked to be *told* at 80% must
    #: not discover that being told also meant being stopped.
    hard_cap: Mapped[bool] = mapped_column(Boolean, default=False,
                                           nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        Index("ix_api_budgets_owner", "user_id", "scope"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return (f"<ApiBudget {self.scope} {self.period} {self.amount} "
                f"hard={self.hard_cap}>")


class ApiNotification(Base):
    """One alert raised for one account.

    ``kind`` + ``subject`` is what deduplication keys on: "budget X crossed 80%"
    is a different subject from "budget X crossed 100%", and both are different
    from the same threshold on another budget.
    """

    __tablename__ = "api_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), default="",
                                         nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    body: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # The cooldown lookup: same account, same kind, same subject, recent.
        Index("ix_api_notifications_dedupe", "user_id", "kind", "subject",
              "created_at"),
        Index("ix_api_notifications_unread", "user_id", "read_at"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"<ApiNotification {self.kind} {self.subject}>"


WEBHOOK_PENDING = "pending"
WEBHOOK_DELIVERED = "delivered"
WEBHOOK_FAILED = "failed"
WEBHOOK_DEAD = "dead"


class WebhookSubscription(Base):
    """Where an account wants job events delivered.

    ``secret_enc`` is **encrypted**, not hashed, and that difference is the whole
    reason this is not the developer-key table: the server has to reproduce the
    secret to sign outbound requests, while a developer key must never be
    recoverable. Same word, opposite requirement.
    """

    __tablename__ = "public_api_webhooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(String(48), default="", nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    # Kept for a grace window after a rotation, and signed with alongside the
    # new one. A rotation that took effect instantly would fail every delivery
    # already in flight at a receiver that had switched — which is exactly the
    # moment a customer is watching (EXT-10).
    previous_secret_enc: Mapped[str] = mapped_column(Text, default="",
                                                     nullable=False)
    previous_secret_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)
    events: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    disabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_public_api_webhooks_owner", "user_id", "enabled"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return f"<WebhookSubscription {self.id[:8]} user={self.user_id[:8]}>"


class WebhookDelivery(Base):
    """One event queued for one subscription — the transactional outbox row.

    Written in the same transaction as the job's terminal state, so an event
    cannot be lost by a crash between "job finished" and "webhook sent", and a
    receiver being down cannot hold up the job or its settlement.

    ``(subscription_id, event_id)`` is unique: a retry of the enqueue, or two
    workers reclaiming the same job, still produce exactly one delivery.
    """

    __tablename__ = "public_api_webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False,
                                                 index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), default="", nullable=False,
                                        index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=WEBHOOK_PENDING,
                                        nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    last_status_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("subscription_id", "event_id",
                         name="uq_public_api_webhook_event"),
        Index("ix_public_api_webhook_due", "status", "next_attempt_at"),
    )

    def __repr__(self) -> str:      # pragma: no cover - debugging aid
        return (f"<WebhookDelivery {self.event_type} {self.status} "
                f"attempts={self.attempts}>")
