"""Discover và resolve ToolSpec qua app registry hiện hữu."""
from __future__ import annotations

import copy
from typing import Callable, Iterable, Optional

from platform_core import prompt_fragments, providers
from platform_core.registry import APPS_DIR, LoadedApp, RegistryError, ToolSpec, discover


def discover_tools(*, apps: Optional[Iterable[LoadedApp]] = None,
                   allowed_slugs: Optional[set[str]] = None) -> dict[str, ToolSpec]:
    """Gom tool từ manifest hợp lệ, không import hay hardcode app cụ thể."""
    loaded = discover() if apps is None else list(apps)
    result: dict[str, ToolSpec] = {}
    for item in loaded:
        if item.error or not item.manifest.enabled:
            continue
        if allowed_slugs is not None and item.slug not in allowed_slugs:
            continue
        for tool in item.manifest.tools:
            if tool.name in result:
                raise RegistryError(f"tool name trùng: {tool.name!r}")
            result[tool.name] = tool
    return result


def _find_owner(tool_name: str, apps: Iterable[LoadedApp]) -> LoadedApp:
    for item in apps:
        if not item.error and any(t.name == tool_name for t in item.manifest.tools):
            return item
    raise RegistryError(f"không tìm thấy tool: {tool_name!r}")


def resolve_params_schema(
    tool_name: str,
    params: Optional[dict] = None,
    *,
    apps: Optional[Iterable[LoadedApp]] = None,
    model_lookup: Optional[Callable[[str], dict]] = None,
) -> dict:
    """Resolve enum động thành ``values`` mà không sửa ToolSpec gốc.

    ``model_lookup`` là seam kiểm thử/registry mở rộng; mặc định dùng capability
    tĩnh trong ``platform_core.providers``.
    """
    loaded = discover() if apps is None else list(apps)
    owner = _find_owner(tool_name, loaded)
    tool = next(t for t in owner.manifest.tools if t.name == tool_name)
    resolved = copy.deepcopy(tool.params_schema)
    params = params or {}
    lookup = model_lookup or providers.model_capabilities

    for schema in resolved.values():
        source = schema.get("source")
        if source:
            group = source.split("/", 1)[1]
            choices = prompt_fragments.options(APPS_DIR / owner.slug / "prompts", group)
            schema["values"] = [value for value, _label in choices]
            schema["options"] = [
                {"value": value, "label": label} for value, label in choices
            ]
        dependency = schema.get("depends_on")
        if dependency:
            selected = params.get(dependency)
            capabilities = lookup(str(selected)) if selected else {}
            schema["values"] = list(capabilities.get(schema["field"], ()))
    return resolved
