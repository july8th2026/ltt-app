"""Turning a public tool call into a real job: validate → price → hold → queue.

This module is the adapter Q92 promised. It owns no engine of its own: pricing
is ``registry.credit_for()``, the queue is the ``jobs`` table, the money is the
credit ledger, and the atomicity comes from ``job_submit.submit_with_credit()``
— all of which the UI has been using in production.

**Order is the contract** (COMMON_RULES §5), and it is enforced here rather than
per route:

    validate input → resolve the quote → hold credit → insert the job
                                         └── one transaction, caller commits ──┘

Validation before money means a typo cannot cost anything. The hold and the job
row commit together, so "credit held but no job" cannot survive a crash: there
is no second store to fall out of sync with, and no queue signal outside the
database (Q26). Whatever the crash, either both rows are there or neither is.
"""
from __future__ import annotations

from platform_core.public_api.errors import invalid_request

# Media parameters take an upload/artifact id. Resolving one to a storage key is
# Prompt 07's job; until then a tool that needs media simply cannot be called,
# which is better than inventing a half-contract now.
_MEDIA_TYPES = {"image", "image[]", "video", "video[]", "audio"}

# Internal params the platform adds for its own bookkeeping. The prefix keeps
# them out of the public contract and makes them greppable.
API_META_KEY = "_api"


def _field_error(field: str, message: str):
    return invalid_request(f"{field}: {message}", field=field)


def validate_public_input(tool, payload: dict) -> dict:
    """Check a caller's input against the published contract. Returns it clean.

    Unknown fields are **rejected**, not ignored. The published schema says
    ``additionalProperties: false``; silently dropping a misspelled parameter
    would let a customer pay for a job that quietly ignored what they asked for.
    """
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise invalid_request("input must be an object.")

    schema = tool.input_schema
    properties = schema.get("properties", {})
    unknown = sorted(set(payload) - set(properties))
    if unknown:
        raise invalid_request(
            f"Unknown input field(s): {', '.join(unknown)}.", fields=unknown)

    missing = [name for name in schema.get("required", ())
               if payload.get(name) in (None, "")]
    if missing:
        raise invalid_request(
            f"Missing required field(s): {', '.join(missing)}.", fields=missing)

    clean: dict = {}
    for name, value in payload.items():
        if value is None:
            continue
        spec = properties[name]
        clean[name] = _validate_value(name, value, spec)
    return clean


def _validate_value(name: str, value, spec: dict):
    kind = spec.get("type")
    if kind == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise _field_error(name, "must be an integer.")
    elif kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise _field_error(name, "must be a number.")
    elif kind == "boolean":
        if not isinstance(value, bool):
            raise _field_error(name, "must be a boolean.")
    elif kind == "array":
        if not isinstance(value, list):
            raise _field_error(name, "must be an array.")
    elif kind == "object":
        if not isinstance(value, dict):
            raise _field_error(name, "must be an object.")
    else:
        if not isinstance(value, str):
            raise _field_error(name, "must be a string.")

    allowed = spec.get("enum")
    if allowed is not None and value not in allowed:
        raise _field_error(name, f"must be one of: {', '.join(map(str, allowed))}.")
    if "minimum" in spec and value < spec["minimum"]:
        raise _field_error(name, f"must be >= {spec['minimum']}.")
    if "maximum" in spec and value > spec["maximum"]:
        raise _field_error(name, f"must be <= {spec['maximum']}.")
    if "maxLength" in spec and isinstance(value, str) and len(value) > spec["maxLength"]:
        raise _field_error(name, f"must be at most {spec['maxLength']} characters.")
    return value


def tool_contract(tool) -> dict:
    """The app's public contract for this tool, as declared in its manifest."""
    from platform_core.registry import discover

    for item in discover():
        if item.manifest.slug != tool.app_slug:
            continue
        for spec in item.manifest.tools:
            if spec.job_type == tool.job_type and (
                    spec.name == tool.name
                    or (spec.api_contract or {}).get("public_name") == tool.name):
                return dict(spec.api_contract or {})
    return {}


def media_params(tool) -> dict:
    """``param -> internal media type`` for the tool's published inputs."""
    from platform_core.registry import discover

    internal_schema = _internal_schema(tool, discover())
    published = set((tool.input_schema or {}).get("properties", {}))
    return {name: str(spec.get("type"))
            for name, spec in internal_schema.items()
            if name in published and str(spec.get("type")) in _MEDIA_TYPES}


def build_job_params(tool, clean_input: dict, *, media_values=None) -> dict:
    """Map validated public input onto the internal job parameters.

    Two translations happen here and nowhere else: a public model alias becomes
    the real model id, and a media reference becomes a storage key. Both exist
    so the public contract can stay stable while the implementation changes.

    ``media_values`` carries what a media parameter should become. At quote time
    it is a placeholder (nothing has been promoted yet — Q85 forbids persisting
    an input before its job holds credit); at submit time it is the promoted
    key. A media parameter with no value at all is refused rather than silently
    dropped.
    """
    from platform_core.registry import discover

    internal_schema = _internal_schema(tool, discover())
    supplied = dict(media_values or {})
    params: dict = {}

    # A hidden parameter means "the server decides", and the server's decision is
    # the default the app declared. Leaving it out entirely is not the same
    # thing: the handler then falls back to *its* default, which is a different
    # value in at least one real case — hiding `operation` on the storyboard tool
    # made it run (and price) as the prompt-package generator instead.
    hidden = {str(name) for name in ((tool_contract(tool).get("hidden")) or ())}
    for name in hidden:
        spec = internal_schema.get(name) or {}
        if "default" in spec and name not in clean_input:
            params[name] = spec["default"]

    for name, value in clean_input.items():
        kind = str((internal_schema.get(name) or {}).get("type") or "string")
        if kind == "model_ref":
            resolved = tool.resolve_model(value)
            if not resolved:
                raise _field_error(name, "unknown model alias.")
            params[name] = resolved
        elif kind in _MEDIA_TYPES:
            if name not in supplied:
                raise _field_error(name, "this input requires an upload id.")
            params[name] = supplied[name]
        else:
            params[name] = value
    return params


def promote_media(db, storage, *, job, sessions: dict) -> list:
    """Move confirmed uploads to their durable keys, after the hold exists.

    Order is Q85's, not a preference: the credit hold proves the job is real
    before anything becomes permanent in storage. Returns the promotions so the
    caller can compensate them if its transaction later fails — object storage
    does not roll back with the database.
    """
    from sqlalchemy.orm.attributes import flag_modified
    from platform_core import upload_sessions

    promotions: list = []
    params = dict(job.params or {})
    for param, session in sessions.items():
        suffix = _suffix(session.filename)
        final_key = f"{job.app_slug}/{job.user_id}/{job.id}/{param}{suffix}"
        key = upload_sessions.promote(db, storage, session, job=job,
                                      final_key=final_key)
        promotions.append((session.staging_key, final_key, session.content_type))
        params[param] = key
    job.params = params
    flag_modified(job, "params")
    db.flush()
    return promotions


def _suffix(filename: str) -> str:
    from pathlib import PurePath

    return PurePath(str(filename or "")).suffix.lower()[:12]


def _internal_schema(tool, apps) -> dict:
    for item in apps:
        if item.manifest.slug != tool.app_slug:
            continue
        for spec in item.manifest.tools:
            if spec.job_type == tool.job_type and (
                    spec.name == tool.name
                    or (spec.api_contract or {}).get("public_name") == tool.name):
                return dict(spec.params_schema)
    raise invalid_request("This tool is no longer available.")


def price(tool, params: dict) -> int:
    """What this call costs, from the platform's single pricing source."""
    from platform_core.registry import RegistryError, credit_for

    try:
        return int(credit_for(tool.job_type, params))
    except RegistryError as exc:
        # A tool whose price cannot be resolved must never run: free execution
        # is money leaving the building silently (Q5, and the invariant in
        # `docs/QUYET_DINH_NEN_TANG.md` §2.4).
        raise invalid_request("This tool cannot be priced right now.") from exc


def submit(db, *, principal, tool, params: dict, quote: dict,
           idempotency_key: str):
    """Hold credit and queue the job in one transaction. Caller commits.

    Raises ``credit.ThieuCreditError`` when the balance is short — and because
    the hold and the job insert share this transaction, the caller's rollback
    leaves neither behind.
    """
    from platform_core.job_submit import submit_with_credit

    meta = {
        "tool": tool.name,
        "key_id": principal.key_id,
        "quote_intent": str(quote.get("intent") or ""),
        "idempotency_key": str(idempotency_key or ""),
    }
    job_params = dict(params)
    # Every app handler in this platform reads `owner_id` from its parameters to
    # scope storage keys and to check that a referenced file belongs to the
    # caller. The UI routes pass it; the API must too, and it must come from the
    # verified principal rather than from anything the request said.
    job_params["owner_id"] = principal.user_id
    job_params[API_META_KEY] = meta

    # The quote's intent is also the dedupe key: a retry that somehow reaches
    # `jobs.submit` directly still cannot open a second job for one quote.
    from platform_core.job_submit import dedupe_key_for

    dedupe = dedupe_key_for(tool.job_type, {
        "intent": meta["quote_intent"], "key_id": principal.key_id})

    return submit_with_credit(
        db, user_id=principal.user_id, app_slug=tool.app_slug,
        job_type=tool.job_type, params=job_params, dedupe_key=dedupe,
    )


def api_meta(job) -> dict:
    """The bookkeeping block this module attached, or an empty dict."""
    meta = (job.params or {}).get(API_META_KEY)
    return dict(meta) if isinstance(meta, dict) else {}
