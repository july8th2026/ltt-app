"""The caller of a ``/api/v1`` request, and the authorization rules about it.

Framework-free on purpose: these are the rules that decide whether a request may
proceed, and they should be testable without booting an HTTP app.

Two decisions are encoded here, and both are about *what an attacker learns from
a refusal*:

**401 vs 403 vs 404.**

* no credential, or one that does not verify → **401**. Nothing is revealed:
  the caller has not proved anything yet;
* a valid key that lacks the scope, or is not allowed to use a tool that exists
  publicly → **403**. This is function-level authorization. Saying so is safe
  and it is the only answer that lets a developer fix their key;
* a valid key asking for an object owned by somebody else → **404**, byte for
  byte identical to an object that never existed. Answering 403 here would turn
  every id into an oracle: iterate ids, collect the ones that answer 403, and
  you have mapped another customer's jobs without reading a single one.

**Ownership is checked against the key's owner, never against a parameter.**
The user id comes from the verified credential; a request cannot pass one in.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.public_api.errors import forbidden, not_found


@dataclass(frozen=True)
class Principal:
    """Who is calling, resolved from a verified developer API key.

    ``user_id`` is the billing owner (Q92: the principal is always a platform
    ``User``). ``allowed_tools`` empty means "whatever the public catalog
    exposes" — the catalog is itself an explicit allowlist, so this is a second
    narrowing rather than the only one.
    """

    key_id: str
    user_id: str
    scopes: frozenset = field(default_factory=frozenset)
    allowed_tools: frozenset = field(default_factory=frozenset)
    request_id: str = ""

    def has_scope(self, scope: str) -> bool:
        return str(scope) in self.scopes

    def may_use_tool(self, tool_name: str) -> bool:
        """Per-key narrowing only; the catalog decides public exposure."""
        if not self.allowed_tools:
            return True
        return str(tool_name) in self.allowed_tools


def ensure_scope(principal: Principal, scope: str) -> None:
    """Function-level authorization. Raises 403 with the scope named.

    Naming the missing scope is deliberate: it is information about the
    *caller's own key*, not about the platform's data, and withholding it just
    makes an integration take a support ticket to finish.
    """
    if not principal.has_scope(scope):
        raise forbidden(f"This API key is missing the required scope: {scope}.")


def ensure_any_scope(principal: Principal, scopes) -> None:
    wanted = [str(scope) for scope in scopes]
    if not any(principal.has_scope(scope) for scope in wanted):
        raise forbidden(
            "This API key is missing one of the required scopes: "
            f"{', '.join(sorted(wanted))}.")


def ensure_tool_allowed(principal: Principal, tool_name: str, *,
                        publicly_exposed: bool) -> None:
    """Catalog exposure first, then the key's own allowlist.

    Order matters. A tool the platform does not expose publicly must look like
    it does not exist (404) no matter who asks — otherwise the API becomes a
    directory of internal capability. Only for a tool that *is* public does a
    per-key restriction make sense to admit (403).
    """
    if not publicly_exposed:
        raise not_found("No such tool.")
    if not principal.may_use_tool(tool_name):
        raise forbidden("This API key is not allowed to use this tool.")


def ensure_owner(obj, principal: Principal, *, owner_attr: str = "user_id"):
    """Object-level authorization: return ``obj``, or raise 404.

    Pass the row you fetched. A missing row and a row owned by somebody else
    produce the same 404 — the caller cannot tell them apart, which is the
    point. Prefer also filtering by owner in the query; this is the backstop for
    the paths where that is inconvenient, not a licence to skip it.
    """
    if obj is None:
        raise not_found("Not found.")
    owner = str(getattr(obj, owner_attr, "") or "")
    if not owner or owner != principal.user_id:
        raise not_found("Not found.")
    return obj
