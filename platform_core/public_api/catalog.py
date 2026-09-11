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

import hashlib
import json
from dataclasses import dataclass, field

from platform_core.public_api.errors import not_found
from platform_core.public_api.protocol import ASYNC_JOB, mode_of_tool

# How stable a published model alias is. Stability is a *promise about change*,
# not a quality rating: `beta` may be withdrawn, `stable` will be deprecated
# before it disappears, `deprecated` already has a replacement.
STABILITY_STABLE = "stable"
STABILITY_BETA = "beta"
STABILITY_DEPRECATED = "deprecated"
STABILITIES = (STABILITY_STABLE, STABILITY_BETA, STABILITY_DEPRECATED)

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
    "json[]": "array",
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
    "json[]": "array",
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
    #: ``{output_field: input_param}`` — which input decides how many entries an
    #: ``artifact[]`` output holds. Internal: it never reaches
    #: ``to_public_dict``, so declaring it moves no contract hash. Read by test
    #: mode so a canned answer has the same cardinality as a live one (EXT-12).
    output_counts: dict = field(default_factory=dict)
    deprecated: str = ""
    #: Former public names that still resolve to this tool. Renaming a tool
    #: without one of these breaks every integration that used the old name.
    aliases: tuple = ()
    #: How a call to this tool executes. Published so a client knows whether to
    #: expect a job id or an answer *before* it writes the integration, rather
    #: than discovering it from the shape of the first response.
    execution_mode: str = ASYNC_JOB
    #: Operational only; deliberately absent from `to_public_dict`. Routes and
    #: workers use it to compete for one pool without exposing topology/model.
    admission_resource: str = ""
    admission_slots: int = 0
    admission_token_pool: int = 0
    #: `{model_id | "*": AdmissionModel}` (multijob 2.1). Cùng khuôn với
    #: `admission_token_pool` ngay trên: vận hành nội bộ, deliberately absent
    #: từ `to_public_dict` — ánh xạ theo model có thể phơi ra id model nội bộ.
    admission_theo_model: dict = field(default_factory=dict)
    sync_executor: str = ""

    def to_public_dict(self) -> dict:
        body = {
            "name": self.name,
            "capability": self.capability,
            "description": self.description,
            "execution_mode": self.execution_mode,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "required_scopes": list(self.scopes),
        }
        if self.aliases:
            body["aliases"] = list(self.aliases)
        if self.deprecated:
            body["deprecated"] = self.deprecated
        # Last, and computed over everything above it: a caller can store this
        # and detect that a contract moved without diffing schemas by hand, and
        # `--check` can prove the docs describe this exact contract.
        body["contract_hash"] = contract_hash(body)
        return body

    @property
    def capability(self) -> str:
        """The domain this tool belongs to, taken from its own public name.

        Derived rather than declared: a separate `capability` field in the
        manifest is one more thing to keep in sync with the name, and the first
        time they disagree the catalog is lying. `image.generate` is an image
        capability because it is called `image.generate`.
        """
        return self.name.split(".")[0]

    def resolve_model(self, alias: str) -> str:
        """Public alias -> internal model id. Empty when the alias is unknown."""
        target = self.model_aliases.get(str(alias))
        if isinstance(target, dict):
            return str(target.get("id") or "")
        return str(target or "")

    def model_names(self) -> list:
        return sorted(self.model_aliases)


@dataclass(frozen=True)
class PublicModel:
    """One publishable model alias, aggregated across the tools that accept it.

    A model is a *public* concept here — the alias, what it can do, how stable
    it is and which tools take it. The provider, the real model id, the pool it
    is served from and its live health are all internal and stay that way; a
    customer who learns which vendor sits behind `pro` has learned something
    they can only use to route around LTT.
    """

    name: str
    capability: str
    stability: str = STABILITY_STABLE
    description: str = ""
    tools: tuple = ()
    constraints: dict = field(default_factory=dict)
    replaced_by: str = ""

    def to_public_dict(self) -> dict:
        body = {
            "name": self.name,
            "capability": self.capability,
            "stability": self.stability,
            "description": self.description,
            "tools": list(self.tools),
            # Deliberately absent: price. What a call costs depends on the whole
            # input (how many images, how many scenes), so a per-model number
            # would be right often enough to be trusted and wrong often enough
            # to matter. `POST /quotes` is the one place that prices a *call*.
            "constraints": dict(self.constraints),
        }
        if self.replaced_by:
            body["replaced_by"] = self.replaced_by
        return body


def canonical(payload) -> str:
    """Stable JSON for hashing: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def contract_hash(payload: dict) -> str:
    body = {key: value for key, value in payload.items()
            if key != "contract_hash"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()[:16]


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
    # An alias maps either to a bare internal id (the original form) or to a
    # dict that also carries what a caller needs to choose between aliases.
    # Both are kept: a tool with one obvious model should not have to write a
    # dictionary to say so.
    models = {str(alias): (dict(target) if isinstance(target, dict)
                           else {"id": str(target)})
              for alias, target in (contract.get("models") or {}).items()}
    param_docs = dict(contract.get("params") or {})

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

        # Public prose, if the app wrote any. It overrides the generic line the
        # projection puts on media/model parameters, because "the id of the
        # image to enlarge" beats "Upload or artifact id." every time.
        docs = param_docs.get(param) or {}
        if docs.get("description"):
            public["description"] = str(docs["description"])
        if "example" in docs:
            # JSON Schema 2020-12 spells this `examples`, as a list.
            public["examples"] = [docs["example"]]
        # 🔴 KHI NÀO MỘT THAM SỐ MỚI DÙNG ĐƯỢC — khai bằng DỮ LIỆU, không bằng văn.
        #
        #    `image.ltt` có `mode` ba giá trị, và `image_key` chỉ dùng cho hai
        #    trong ba. Trước 25/08 điều đó chỉ nằm trong một câu tiếng Anh giữa
        #    `description`, nên trang tài liệu không có cách nào lọc theo — và
        #    bộ sinh ví dụ đã dựng ra một thân **tự mâu thuẫn** vì không biết.
        #
        # ⛔ ĐỪNG để giao diện đọc `description` rồi đoán. Một template phân tích
        #    văn xuôi tiếng Anh là một template sẽ sai vào ngày ai đó sửa câu chữ.
        #
        # ⚠️ Tiền tố `x-` là quy ước mở rộng của JSON Schema/OpenAPI: bộ kiểm tra
        #    schema **bỏ qua** khoá lạ, nên khai thêm không làm hỏng client nào.
        #    Nó là chú thích cho người và cho trang tài liệu, không phải luật kiểm.
        if docs.get("only_when"):
            public["x-ltt-only-when"] = {
                str(khoa): [str(v) for v in gia_tri]
                for khoa, gia_tri in dict(docs["only_when"]).items()}
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

    # 🔴 KEEP THE MEDIA KIND. Do not flatten everything into `artifact`.
    #
    #    `image`, `video` and `audio` all map to `"artifact"`, and at that point
    #    *what kind of file this is* leaves the system. Two real consequences:
    #
    #      · The sandbox returns **a PNG for everything** - `media
    #        .store_sandbox_artifact` had `SAMPLE_PNG` hard-wired. Accidentally
    #        right for image tools; `speech.ltt` is the first audio tool on the
    #        API, and an integrator would download a `.png` served as
    #        `image/png` from a field the schema calls audio.
    #      · A caller reading `{"type": "artifact"}` cannot tell whether to
    #        expect a WAV or a PNG.
    #
    #    `media` is ADDITIVE - nothing reading `type` is affected. It still
    #    changes every artifact tool's `contract_hash`, so it went through
    #    `check_api_compat --accept` with a CHANGELOG entry, on purpose.
    output_schema = {"type": "object", "properties": {
        str(key): ({"type": _PUBLIC_OUTPUT_TYPES.get(str(value), "string"),
                    "media": str(value).rstrip("[]")}
                   if _PUBLIC_OUTPUT_TYPES.get(str(value), "").startswith(
                       "artifact")
                   else {"type": _PUBLIC_OUTPUT_TYPES.get(str(value), "string")})
        for key, value in tool.returns.items()}}

    from platform_core.public_api.limits import resource_class

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
        output_counts={str(key): str(value) for key, value
                       in (contract.get("output_counts") or {}).items()},
        deprecated=str(contract.get("deprecated") or ""),
        aliases=tuple(str(name) for name in (contract.get("aliases") or ())),
        execution_mode=mode_of_tool(contract),
        admission_resource=str(
            getattr(tool, "admission_resource", "") or resource_class(manifest)),
        admission_slots=max(0, int(getattr(tool, "admission_slots", 0) or 0)),
        admission_token_pool=max(
            0, int(getattr(tool, "admission_token_pool", 0) or 0)),
        sync_executor=str(getattr(tool, "sync_executor", "") or ""),
        admission_theo_model=dict(getattr(tool, "admission_theo_model", {}) or {}),
    )


def build_models(catalog: list) -> list:
    """The model aliases the published catalog exposes, one entry per alias.

    Aggregated across tools rather than declared centrally, for the same reason
    the capability is derived: a central list is a second place to update, and
    the day it disagrees with the tools it is the catalog that is wrong.
    """
    merged: dict = {}
    for tool in catalog:
        for alias, spec in tool.model_aliases.items():
            entry = merged.setdefault(alias, {
                "capability": tool.capability, "tools": [],
                "stability": str(spec.get("stability") or STABILITY_STABLE),
                "description": str(spec.get("description") or ""),
                "constraints": dict(spec.get("constraints") or {}),
                "replaced_by": str(spec.get("replaced_by") or ""),
            })
            entry["tools"].append(tool.name)
            # A tool that says nothing keeps whatever the first describing tool
            # said; a tool that *does* describe the alias wins, so metadata can
            # live next to the richest use of the model.
            if spec.get("description") and not entry["description"]:
                entry["description"] = str(spec["description"])
            if spec.get("stability"):
                entry["stability"] = str(spec["stability"])
    return sorted(
        (PublicModel(name=alias, capability=data["capability"],
                     stability=data["stability"],
                     description=data["description"],
                     tools=tuple(sorted(set(data["tools"]))),
                     constraints=data["constraints"],
                     replaced_by=data["replaced_by"])
         for alias, data in merged.items()),
        key=lambda model: model.name)


def require_model(models: list, name: str) -> PublicModel:
    wanted = str(name or "")
    for model in models:
        if model.name == wanted:
            return model
    raise not_found("No such model.")


def capabilities_of(catalog: list) -> list:
    """Distinct capability domains this deployment publishes."""
    return sorted({tool.capability for tool in catalog})


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
        # A former name resolves to the same tool. The key's allowlist is still
        # checked against the *current* name, so renaming a tool cannot widen
        # what an existing key may call.
        if tool.name == wanted or wanted in tool.aliases:
            if principal is not None:
                ensure_tool_allowed(principal, tool.name, publicly_exposed=True)
            return tool
    raise not_found("No such tool.")
