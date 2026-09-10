"""Discover và resolve ToolSpec qua app registry hiện hữu."""
from __future__ import annotations

import copy
from typing import Callable, Iterable, Optional

from platform_core import prompt_fragments, providers
from platform_core import registry as _reg
from platform_core.registry import (APPS_DIR, LoadedApp, RegistryError, ToolSpec,
                                    tai_tham_chieu)


class ToolParamsError(ValueError):
    """Tham số do planner/canvas sinh không tuân ToolSpec."""


def discover_tools(*, apps: Optional[Iterable[LoadedApp]] = None,
                   allowed_slugs: Optional[set[str]] = None) -> dict[str, ToolSpec]:
    """Gom tool từ manifest hợp lệ, không import hay hardcode app cụ thể."""
    loaded = _reg.discover() if apps is None else list(apps)
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
    db=None,
    user_id: str = "",
) -> dict:
    """Resolve enum động thành ``values`` mà không sửa ToolSpec gốc.

    ``model_lookup`` là seam kiểm thử/registry mở rộng; mặc định dùng capability
    tĩnh trong ``platform_core.providers``.

    ``db`` + ``user_id`` (H43 Phase 02): có thì resolve thêm `ToolSpec.tuy_chon_dong`
    — tuỳ chọn **theo người dùng** (vd giọng nhân bản của chính họ). Không có
    thì bỏ qua, các caller cũ chạy nguyên.
    """
    loaded = _reg.discover() if apps is None else list(apps)
    owner = _find_owner(tool_name, loaded)
    tool = next(t for t in owner.manifest.tools if t.name == tool_name)
    resolved = copy.deepcopy(tool.params_schema)
    params = params or {}
    lookup = model_lookup or providers.model_capabilities
    dong = getattr(tool, "tuy_chon_dong", None) or {}

    for ten, schema in resolved.items():
        ref = dong.get(ten)
        if ref and db is not None:
            chon = tai_tham_chieu(ref)(db, user_id) or ()
            schema["options"] = [
                {"value": str(c["value"]), "label": str(c.get("label", c["value"]))}
                for c in chon if isinstance(c, dict) and "value" in c]
            schema["values"] = [o["value"] for o in schema["options"]]
        if schema.get("type") == "model_ref":
            options = providers.model_options(
                str(schema.get("category", "")), tuple(schema.get("providers", ())))
            schema["values"] = [option["value"] for option in options]
            schema["options"] = options
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


def validate_tool_params(
    tool_name: str,
    params: dict,
    *,
    apps: Optional[Iterable[LoadedApp]] = None,
    model_lookup: Optional[Callable[[str], dict]] = None,
    db=None,
    user_id: str = "",
) -> dict:
    """Validate nghiêm tham số Agent trước submit; trả bản sao nếu hợp lệ."""
    if not isinstance(params, dict):
        raise ToolParamsError("params phải là object")
    loaded = _reg.discover() if apps is None else list(apps)
    owner = _find_owner(tool_name, loaded)
    tool = next(t for t in owner.manifest.tools if t.name == tool_name)
    schema = resolve_params_schema(
        tool_name, params, apps=loaded, model_lookup=model_lookup,
        db=db, user_id=user_id)
    unknown = sorted(set(params) - set(schema))
    if unknown:
        raise ToolParamsError(f"tham số không được phép: {', '.join(unknown)}")

    out = copy.deepcopy(params)
    for name, rule in schema.items():
        if name not in params:
            if rule.get("required"):
                raise ToolParamsError(f"thiếu tham số bắt buộc: {name}")
            if "default" in rule:
                out[name] = copy.deepcopy(rule["default"])
            continue
        value = params[name]
        kind = rule["type"]
        valid = True
        if kind in ("string", "text", "image", "video", "audio", "model_ref"):
            valid = isinstance(value, str) and bool(value.strip())
        elif kind == "int":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif kind == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        elif kind == "bool":
            valid = isinstance(value, bool)
        elif kind in ("image[]", "video[]"):
            valid = isinstance(value, list) and all(isinstance(v, str) and v for v in value)
        elif kind == "json":
            valid = isinstance(value, (dict, list))
        elif kind == "enum":
            valid = value in rule.get("values", ())
        if not valid:
            raise ToolParamsError(f"tham số {name} sai kiểu/giá trị")
        if kind in ("int", "number"):
            if "min" in rule and value < rule["min"]:
                raise ToolParamsError(f"tham số {name} nhỏ hơn min")
            if "max" in rule and value > rule["max"]:
                raise ToolParamsError(f"tham số {name} lớn hơn max")
        if kind in ("string", "text"):
            if "max_length" in rule and len(value) > rule["max_length"]:
                raise ToolParamsError(f"tham số {name} quá dài")
        if kind == "model_ref":
            # 🔴 FAIL-CLOSED. Bản trước viết `and rule.get("values") and ...`, tức
            #    danh sách **rỗng** làm phép kiểm **tự tắt** — mọi chuỗi đều lọt.
            #
            #    Lỗ đó có sẵn nhưng chưa ai chạm vì enum chưa bao giờ rỗng. Pha 04
            #    (AI CLEAN REBUILD V2) retire `gemini`, mà `taoanh/manifest.py:64,149`
            #    và `thumbnail/manifest.py:85` đều khai `"providers": ["gemini"]`
            #    ⇒ enum thành rỗng ⇒ lỗ **được kích hoạt**: `image.generate` nhận
            #    bất kỳ tên model nào, kể cả `"model-khong-co"`.
            #
            # ⭐ Danh sách rỗng nghĩa là **không model nào hợp lệ**, không phải
            #    "không có ràng buộc nào". Hai câu ấy ngược nhau, và cách viết cũ
            #    chọn đúng câu nguy hiểm.
            if value not in (rule.get("values") or ()):
                raise ToolParamsError(f"model không hợp lệ cho {name}")
    return out
