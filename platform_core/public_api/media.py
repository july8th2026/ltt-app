"""Public media: upload tickets in, artifacts out.

Both directions exist to keep one promise: **a customer never handles a storage
key**. Keys encode the bucket layout, the owner id and sometimes the app; handing
them out would let a caller guess at other people's objects and would freeze the
storage layout into the public contract.

So the API speaks in two opaque ids:

* an **upload id** — a row in the existing ``upload_sessions`` table (Q85), which
  already implements staging → verify → promote-after-hold → sweep;
* an **artifact id** — ``<job_id>.<field>.<index>``, resolvable only by the
  account that owns the job, and only into a short-lived signed URL.

Nothing here invents storage lifecycle. The upload rules, quotas, magic-byte
checks, compensation and sweeper are the platform's; this module maps the public
vocabulary onto them.
"""
from __future__ import annotations

import re

from platform_core.public_api.errors import invalid_request, not_found

# Per media kind: what a caller may upload and how big. Images are capped where
# the image apps already cap them; video is generous because it is meant to go
# straight to object storage rather than through this process.
MEDIA_RULES = {
    "image": (("image/png", "image/jpeg", "image/webp"), 16 * 1024 * 1024),
    "video": (("video/mp4", "video/quicktime", "video/webm", "video/x-matroska"),
              2 * 1024 * 1024 * 1024),
    "audio": (("audio/mpeg", "audio/mp4", "audio/wav", "audio/x-m4a"),
              64 * 1024 * 1024),
}

# Multipart through this process is the fallback for deployments without
# presigned uploads. Cloudflare rejects a larger body before it reaches the
# origin, so promising more would be a lie (see `platform_core/storage.py`).
MULTIPART_LIMIT = 90 * 1024 * 1024

_ARTIFACT_ID = re.compile(r"^([0-9a-fA-F-]{36})\.([a-z][a-z0-9_]{0,40})\.(\d{1,3})$")


def media_kind(public_type: str, internal_type: str) -> str:
    """Which upload rules apply to a tool parameter."""
    base = str(internal_type or "").replace("[]", "")
    return base if base in MEDIA_RULES else ""


def rules_for(kind: str):
    try:
        return MEDIA_RULES[kind]
    except KeyError as exc:
        raise invalid_request("Unsupported media kind.") from exc


# ── Artifact ids ──────────────────────────────────────────────────────────────

def artifact_id(job_id: str, field: str, index: int = 0) -> str:
    return f"{job_id}.{field}.{int(index)}"


def parse_artifact_id(value: str) -> tuple[str, str, int]:
    """Split an artifact id, or raise the same 404 an unknown one gets.

    A malformed id must not be distinguishable from a well-formed id belonging
    to somebody else — both are simply "not found".
    """
    match = _ARTIFACT_ID.fullmatch(str(value or ""))
    if match is None:
        raise not_found("Not found.")
    return match.group(1), match.group(2), int(match.group(3))


def artifacts_of(job, tool) -> list:
    """Public artifact descriptors for a finished job.

    Driven by the tool's *published* output schema, so a result field that was
    never part of the contract cannot become downloadable by accident.
    """
    result = job.result if isinstance(job.result, dict) else {}
    outputs = (tool.output_schema or {}).get("properties", {}) if tool else {}
    found = []
    for field, spec in outputs.items():
        kind = str(spec.get("type") or "")
        if not kind.startswith("artifact"):
            continue
        value = result.get(field)
        if kind.endswith("[]"):
            for index, item in enumerate(value or []):
                if item:
                    found.append({"id": artifact_id(job.id, field, index),
                                  "field": field, "index": index})
        elif value:
            found.append({"id": artifact_id(job.id, field, 0),
                          "field": field, "index": 0})
    return found


def storage_key_for(job, field: str, index: int, tool=None) -> str:
    """The internal key behind an artifact id. Never returned to a caller.

    ``tool`` is required in practice: without it any key a handler happened to
    put in ``result`` — a debug dump, an intermediate file — would become
    downloadable through a guessable id. The published output schema is the
    allowlist.
    """
    if tool is not None:
        allowed = {entry["id"] for entry in artifacts_of(job, tool)}
        if artifact_id(job.id, field, index) not in allowed:
            raise not_found("Not found.")
    result = job.result if isinstance(job.result, dict) else {}
    value = result.get(field)
    if isinstance(value, list):
        if index >= len(value):
            raise not_found("Not found.")
        value = value[index]
    elif index != 0:
        raise not_found("Not found.")
    key = str(value or "")
    if not key:
        raise not_found("Not found.")
    return key


def results_of(job, tool) -> dict:
    """Non-artifact outputs of a finished job, filtered by the contract.

    Wave 1 and 2 tools returned files, so the public job view only ever needed
    artifact ids. The wave 3 tools return **data** — a prompt package, a
    storyboard — and that data is the product. It still cannot be handed over
    wholesale: a handler is free to put anything in ``result``, so only fields
    the published output schema declares (and that are not artifacts) are
    returned. Same allowlist rule as artifacts, different shape.
    """
    result = job.result if isinstance(job.result, dict) else {}
    outputs = (tool.output_schema or {}).get("properties", {}) if tool else {}
    public: dict = {}
    for field, spec in outputs.items():
        kind = str(spec.get("type") or "")
        if kind.startswith("artifact") or field not in result:
            continue
        public[field] = result[field]
    return public
