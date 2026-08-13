"""The public tool catalog: what ``/api/v1`` is allowed to offer, and in what shape.

Three independent gates decide whether a tool appears, and **all** must say yes:

1. **App disposition.** An app whose lifecycle is retired/internal/maintenance,
   or whose surface is admin/runtime, is never public — no matter what its tools
   declare. That is the Prompt 01 disposition turned into code, so a manifest
   edit alone cannot publish an internal capability.
2. **Tool declaration.** ``ToolSpec.api_exposed`` plus a complete
   ``api_contract`` (the registry refuses to load an incomplete one).
3. **Operator switch.** ``LTT_PUBLIC_API_TOOLS`` names the tools this
   deployment serves.

Then the caller's own key narrows it further through ``allowed_tools``.

The second job of this module is **projection**: turning an internal
``params_schema`` into a public contract that leaks nothing. The internal schema
carries provider names, real model ids and references to the internal prompt
library; a public API that echoed them would tell every customer which vendor
runs behind which tool and hand them the vocabulary of internal prompt sets.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from platform_core.public_api.errors import not_found

# Apps that may ever appear on the public API. Everything else is closed by
# construction, including future lifecycles nobody has thought of yet.
PUBLIC_LIFECYCLES = frozenset({"released", "development"})
PUBLIC_SURFACES = frozenset({"customer"})

# Internal parameter type -> public JSON type. Media parameters become opaque
# reference strings: a customer passes an upload/artifact id, never a storage
# key or a path.
_PUBLIC_TYPES = {
    "string": "string",
    "text": "string",
    "int": "integer",
    "number": "number",
    "bool": "boolean",
    "enum": "string",
    "json": "object",
    "image": "string",
    "image[]": "array",
    "video": "string",
    "video[]": "array",
    "audio": "string",
    "model_ref": "string",
}

_PUBLIC_OUTPUT_TYPES = {
    "text": "string",
    "json": "object",
    "image": "artifact",
    "image[]": "artifact[]",
    "video": "artifact",
    "video[]": "artifact[]",
    "audio": "artifact",
    "model_ref": "string",
}


@dataclass(frozen=True)
class PublicTool:
    """One catalog entry, already projected for publication.

    ``job_type`` and ``app_slug`` are kept because the invocation path needs
    them — but :meth:`to_public_dict` never emits them. Which app or job type
    implements a tool is an implementation detail customers must not build on:
    the whole point of a stable public contract is that an app can be rewritten,
    renamed or split without breaking a single integration.
    """

    name: str
    description: str
    input_schema: dict
    output_schema: dict
    scopes: tuple
    app_slug: str
    job_type: str
    model_aliases: dict = field(default_factory=dict)
    deprecated: str = ""

    def to_public_dict(self) -> dict:
        body = {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_scopes": list(self.scopes),
        }
        if self.deprecated:
            body["deprecated"] = self.deprecated
        return body

    def resolve_model(self, alias: str) -> str:
        """Public alias -> internal model id. Empty when the alias is unknown."""
        return str(self.model_aliases.get(str(alias), ""))


def app_may_be_public(manifest, *, error: str = "") -> bool:
    """The Prompt 01 disposition, enforced in one place."""
    if error:
        return False
    return bool(
        manifest.enabled
        and manifest.lifecycle in PUBLIC_LIFECYCLES
        and manifest.surface in PUBLIC_SURFACES
    )


def project_tool(manifest, tool) -> PublicTool:
    """Build the public contract for one tool. Assumes the registry validated it."""
    contract = tool.api_contract or {}
    hidden = {str(name) for name in (contract.get("hidden") or ())}
    enums = contract.get("enums") or {}
    models = {str(alias): str(target)
              for alias, target in (contract.get("models") or {}).items()}

    properties: dict = {}
    required: list = []
    for param, schema in tool.params_schema.items():
        if param in hidden:
            continue
        kind = str(schema.get("type"))
        public: dict = {"type": _PUBLIC_TYPES.get(kind, "string")}

        if kind == "model_ref":
            # Only aliases ever leave the building.
            public["enum"] = sorted(models)
            public["description"] = "Model alias."
        elif kind == "enum":
            values = list(schema.get("values") or enums.get(param) or ())
            # Keep the declared type: a height of 1080 published as "1080" would
            # make every client quote a number as a string and then wonder why
            # validation rejects it.
            numeric = values and all(isinstance(value, int) and
                                     not isinstance(value, bool)
                                     for value in values)
            public["type"] = "integer" if numeric else public["type"]
            public["enum"] = values if numeric else [str(value) for value in values]
        elif kind in {"image", "video", "audio"}:
            public["description"] = "Upload or artifact id."
        elif kind in {"image[]", "video[]"}:
            public["items"] = {"type": "string"}
            public["description"] = "Upload or artifact ids."

        for source, target in (("min", "minimum"), ("max", "maximum"),
                               ("max_length", "maxLength"),
                               ("default", "default")):
            if source in schema:
                public[target] = schema[source]
        properties[param] = public
        if schema.get("required"):
            required.append(param)

    input_schema = {"type": "object", "properties": properties,
                    # Unknown fields are rejected rather than ignored: silently
                    # dropping a misspelled parameter is how a caller ends up
                    # paying for a job that did not do what they asked.
                    "additionalProperties": False}
    if required:
        input_schema["required"] = sorted(required)

    output_schema = {"type": "object", "properties": {
        str(key): {"type": _PUBLIC_OUTPUT_TYPES.get(str(value), "string")}
        for key, value in tool.returns.items()}}

    return PublicTool(
        name=str(contract.get("public_name") or tool.name),
        # The internal description is written for whoever maintains the app and
        # routinely names the provider behind it; the public one is written for
        # a customer and must not.
        description=str(contract.get("description") or tool.description or ""),
        input_schema=input_schema,
        output_schema=output_schema,
        scopes=tuple(str(scope) for scope in (contract.get("scopes") or ())),
        app_slug=manifest.slug,
        job_type=tool.job_type,
        model_aliases=models,
        deprecated=str(contract.get("deprecated") or ""),
    )


def build_catalog(config, apps=None) -> list:
    """Every tool this deployment publishes, sorted by public name."""
    if apps is None:
        from platform_core.registry import discover
        apps = discover()

    tools: list = []
    for item in apps:
        manifest = item.manifest
        if not app_may_be_public(manifest, error=item.error):
            continue
        for tool in manifest.tools:
            if not tool.api_exposed:
                continue
            public = project_tool(manifest, tool)
            if not config.tool_exposed(public.name):
                continue
            tools.append(public)
    return sorted(tools, key=lambda entry: entry.name)


def visible_to(catalog: list, principal) -> list:
    """Narrow a catalog by the calling key's own allowlist."""
    if principal is None:
        return list(catalog)
    return [tool for tool in catalog if principal.may_use_tool(tool.name)]


def require_tool(catalog: list, name: str, principal=None) -> PublicTool:
    """Look one tool up, or raise the same 404 a missing tool would.

    A tool the deployment does not publish must be indistinguishable from one
    that never existed; otherwise the catalog doubles as a directory of what LTT
    runs internally.
    """
    from platform_core.public_api.principal import ensure_tool_allowed

    wanted = str(name or "")
    for tool in catalog:
        if tool.name == wanted:
            if principal is not None:
                ensure_tool_allowed(principal, tool.name, publicly_exposed=True)
            return tool
    raise not_found("No such tool.")
