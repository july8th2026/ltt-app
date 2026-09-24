"""Projects: the ownership layer between an account and its API keys.

The hierarchy this locks in, and the reason each level exists:

    User            billing, credit, everything the platform already owns (Q92)
     └─ Project     one integration; the unit you revoke, budget and read logs by
         └─ Key     one credential; the unit you rotate

A **service account** would sit between project and key — a machine identity that
outlives any single credential. It is deliberately not built here (ADR D6 in
`docs/PUBLIC_API/EXTENSION_DECISIONS.md`): today a key *is* the machine identity,
and adding an entity with one row per key and no behaviour of its own would be a
join to maintain for nothing. What matters is that adding it later is additive —
a key already points at a project, so a service account slots in as an optional
owner inside that project without moving a single existing row.

Nothing here talks HTTP; the portal and any future admin console both call it.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from platform_core.public_api.tables import (ApiProject, DeveloperApiKey,
                                             PROJECT_ACTIVE, PROJECT_ARCHIVED)

#: Enough for real use, low enough that a runaway script cannot fill the table.
MAX_PROJECTS_PER_USER = 20

DEFAULT_PROJECT_NAME = "Default"
DEFAULT_PROJECT_SLUG = "default"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ProjectError(Exception):
    """Refusal a human caused and a human can fix."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def chuan_hoa_slug(name: str) -> str:
    """"Trang bán hàng" → "trang-ban-hang", not "trang-b-n-h-ng".

    Folding the diacritics first matters on a Vietnamese platform: dropping them
    turns most project names into a row of dashes, which is unreadable in the
    one place a slug exists to be readable — a log line and a support ticket.

    ⭐ This is the repository's ONLY slug normaliser, and it is deliberately
    *pure*: no length cap, no fallback value. Those two are policies of whoever
    is storing the slug, not properties of the transliteration — the `slug`
    column wants 64 characters and a non-empty default, while the workflow
    expression function `slugify()` (`platform_core/workflow/ham_bieu_thuc.py`)
    wants neither, because inventing a value the author never typed is a bug
    there. Splitting them the other way — two normalisers, one per caller — is
    how one string starts producing two different slugs.
    """
    import unicodedata

    text = str(name or "").strip().lower()
    # NFKD splits "á" into "a" + a combining mark; dropping the marks keeps the
    # letter. U+0111 (d with stroke) has no decomposition, so it is mapped by
    # hand — written as a codepoint rather than the character itself so the i18n
    # ratchet does not read a transliteration table as an untranslated message.
    text = text.replace(chr(0x0111), "d")
    decomposed = unicodedata.normalize("NFKD", text)
    folded = "".join(char for char in decomposed
                     if not unicodedata.combining(char))
    return _SLUG_RE.sub("-", folded).strip("-")


def slugify(name: str) -> str:
    """Slug for the `api_projects.slug` column: capped, never empty."""
    return chuan_hoa_slug(name)[:64] or DEFAULT_PROJECT_SLUG


def create(db, *, user_id: str, name: str, now: datetime | None = None) -> ApiProject:
    """Create a project for an account. Slug is unique per account, not global."""
    owner = str(user_id or "").strip()
    if not owner:
        raise ProjectError("A project must belong to an account.")
    label = str(name or "").strip()
    if not label:
        raise ProjectError("A project needs a name.")

    active = int(db.execute(
        select(func.count(ApiProject.id)).where(
            ApiProject.user_id == owner,
            ApiProject.status == PROJECT_ACTIVE)).scalar_one())
    if active >= MAX_PROJECTS_PER_USER:
        raise ProjectError(
            f"This account already has {MAX_PROJECTS_PER_USER} projects.")

    base = slugify(label)
    for attempt in range(50):
        # Suffix on collision rather than refusing: two integrations called
        # "Website" is a normal thing for a person to want, and failing on the
        # second one teaches nothing.
        slug = base if attempt == 0 else f"{base}-{attempt + 1}"
        project = ApiProject(id=str(uuid.uuid4()), user_id=owner,
                             name=label[:120], slug=slug,
                             status=PROJECT_ACTIVE, created_at=now or _now())
        db.add(project)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        return project
    raise ProjectError("Could not allocate a unique project slug.")


def default_for(db, *, user_id: str, now: datetime | None = None) -> ApiProject:
    """The account's default project, created on first use.

    Lazily, not at signup: an account that never touches the API should not have
    a project sitting in the table, and creating one on demand means the very
    first key already belongs somewhere.
    """
    owner = str(user_id or "").strip()
    existing = db.execute(select(ApiProject).where(
        ApiProject.user_id == owner,
        ApiProject.slug == DEFAULT_PROJECT_SLUG)).scalar_one_or_none()
    if existing is not None:
        if existing.status != PROJECT_ACTIVE:
            # An archived default is still the default: refusing here would
            # leave the account unable to make a key at all.
            existing.status = PROJECT_ACTIVE
            existing.archived_at = None
        return existing
    return create(db, user_id=owner, name=DEFAULT_PROJECT_NAME, now=now)


def list_for(db, *, user_id: str, include_archived: bool = False) -> list:
    statement = select(ApiProject).where(ApiProject.user_id == str(user_id or ""))
    if not include_archived:
        statement = statement.where(ApiProject.status == PROJECT_ACTIVE)
    return list(db.execute(
        statement.order_by(ApiProject.created_at)).scalars().all())


def get_owned(db, *, user_id: str, project_id: str) -> ApiProject | None:
    """Fetch a project **for this owner**. Ownership is in the query, not after."""
    return db.execute(select(ApiProject).where(
        ApiProject.id == str(project_id or ""),
        ApiProject.user_id == str(user_id or ""))).scalar_one_or_none()


def rename(db, project: ApiProject, name: str) -> ApiProject:
    label = str(name or "").strip()
    if not label:
        raise ProjectError("A project needs a name.")
    # The slug does not follow the name: it is what logs, tickets and any future
    # export already refer to, and renaming is a display decision.
    project.name = label[:120]
    return project


def archive(db, project: ApiProject, *, now: datetime | None = None) -> int:
    """Archive a project and revoke its keys. Returns how many keys were revoked.

    What archiving does **not** touch: jobs, credit ledger entries, usage rows,
    webhook deliveries. Those record money that moved and work that ran; a
    project going away cannot make them untrue. Archiving stops *future* use,
    which is the thing an owner actually wants when an integration is retired.
    """
    from platform_core.public_api import keys as devkeys

    current = now or _now()
    project.status = PROJECT_ARCHIVED
    project.archived_at = current

    revoked = 0
    for key in db.execute(select(DeveloperApiKey).where(
            DeveloperApiKey.project_id == project.id,
            DeveloperApiKey.revoked_at.is_(None))).scalars().all():
        if devkeys.revoke(db, key, now=current):
            revoked += 1
    return revoked


def unarchive(db, project: ApiProject) -> ApiProject:
    """Bring a project back. Its keys stay revoked — revocation is one-way."""
    project.status = PROJECT_ACTIVE
    project.archived_at = None
    return project


def keys_of(db, *, project_id: str) -> list:
    return list(db.execute(select(DeveloperApiKey).where(
        DeveloperApiKey.project_id == str(project_id or "")).order_by(
            DeveloperApiKey.created_at)).scalars().all())
