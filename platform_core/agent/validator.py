"""Deterministic Plan v1 validator. No LLM, network, job or credit writes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from platform_core.agent.tools import (ToolParamsError, discover_tools,
                                       resolve_params_schema,
                                       validate_tool_params)
from platform_core.registry import credit_for, discover
from platform_core.agent.verifier import VERIFIER_CREDIT, verifier_cost

MAX_STEPS = 100
MAX_FANOUT = 4
MAX_RETRY = 2
_REF = re.compile(r"^\$(input|[a-z][a-z0-9_-]{0,31})\.([a-z][a-z0-9_]*)$")
_ON_FAIL = {"retry_same", "refine", "regenerate", "switch_model"}
_FORBIDDEN_KEYS = {"owner_id", "storage_key", "credential", "secret", "csrf_token",
                   "callback_url", "webhook_url", "command", "cmd", "shell", "path", "url"}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    step_id: str = ""
    field: str = ""


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]
    estimated_max_credit: int = 0
    step_costs: tuple[dict, ...] = ()


def _port_for_param(kind: str) -> str:
    if kind in ("string", "text", "enum"):
        return "text"
    if kind in ("int", "number", "bool"):
        return "json"
    return kind


def _placeholder(rule: dict):
    if "default" in rule:
        return rule["default"]
    values = rule.get("values") or []
    if values:
        return values[0]
    kind = rule["type"]
    if kind in ("string", "text", "image", "video", "audio", "model_ref"):
        return "resolved-reference"
    if kind == "int":
        return int(rule.get("min", 1))
    if kind == "number":
        return float(rule.get("min", 1))
    if kind == "bool":
        return False
    if kind.endswith("[]"):
        return ["resolved-reference"]
    return {}


def _has_cycle(deps: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(dep in deps and visit(dep) for dep in deps[node]):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in deps)


def _unsafe_payload(value) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _FORBIDDEN_KEYS or _unsafe_payload(item)
                   for key, item in value.items())
    if isinstance(value, list):
        return any(_unsafe_payload(item) for item in value)
    return isinstance(value, str) and value.lower().startswith(
        ("http://", "https://", "file://", "ftp://", "\\\\", "/"))


def validate_plan(plan: dict, *, input_types: Optional[dict[str, str]] = None,
                  allowed_slugs: Optional[set[str]] = None,
                  balance: Optional[int] = None, db=None, user=None) -> ValidationResult:
    issues: list[ValidationIssue] = []
    if not isinstance(plan, dict) or plan.get("version") != 1:
        return ValidationResult(False, (ValidationIssue("version", "Chỉ hỗ trợ Plan version 1."),))
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > MAX_STEPS:
        return ValidationResult(False, (ValidationIssue(
            "steps", f"Plan cần 1–{MAX_STEPS} steps."),))
    try:
        budget = int(plan.get("budget_max_credit", 0))
    except (TypeError, ValueError):
        budget = -1
    if budget < 0:
        issues.append(ValidationIssue("budget", "budget_max_credit không hợp lệ."))

    loaded = discover()
    if db is not None and user is not None:
        from platform_core import app_access
        allowed_slugs = {
            item.slug for item in loaded
            if app_access.muc_quyen(db, user, item.slug) == app_access.ENABLED
        }
    tools = discover_tools(apps=loaded, allowed_slugs=allowed_slugs)
    owners = {tool.name: item for item in loaded for tool in item.manifest.tools}
    ids: set[str] = set()
    by_id: dict[str, dict] = {}
    deps: dict[str, set[str]] = {}
    error_deps: dict[str, set[str]] = {}
    input_types = input_types or {}
    step_costs: list[dict] = []
    total = 0

    for step in steps:
        sid = str(step.get("id", "")) if isinstance(step, dict) else ""
        if not isinstance(step, dict) or not sid or sid in ids:
            issues.append(ValidationIssue("step_id", "Step id thiếu hoặc trùng.", sid))
            continue
        ids.add(sid); by_id[sid] = step
        after = step.get("after", [])
        if not isinstance(after, list) or any(not isinstance(x, str) for x in after):
            issues.append(ValidationIssue("after", "after phải là danh sách step id.", sid))
            after = []
        deps[sid] = set(after)
        after_error = step.get("after_error", [])
        if not isinstance(after_error, list) or any(not isinstance(x, str) for x in after_error):
            issues.append(ValidationIssue("after_error", "after_error phải là danh sách step id.", sid))
            after_error = []
        error_deps[sid] = set(after_error)
        if deps[sid].intersection(error_deps[sid]):
            issues.append(ValidationIssue("branch", "Một dependency không thể vừa success vừa error.", sid))

    for sid, after in deps.items():
        for dep in after:
            if dep not in ids:
                issues.append(ValidationIssue("dependency", f"Không có step phụ thuộc {dep}.", sid))
    for sid, after in error_deps.items():
        for dep in after:
            if dep not in ids:
                issues.append(ValidationIssue("dependency", f"Không có step lỗi phụ thuộc {dep}.", sid))
    combined = {sid: deps.get(sid,set()) | error_deps.get(sid,set()) for sid in ids}
    if _has_cycle(combined):
        issues.append(ValidationIssue("cycle", "Plan có chu trình."))

    for sid, step in by_id.items():
        tool_name = step.get("tool")
        spec = tools.get(tool_name)
        if spec is None:
            issues.append(ValidationIssue("tool", f"Tool không tồn tại/không có quyền: {tool_name}.", sid))
            continue
        params = step.get("params", {})
        if not isinstance(params, dict):
            issues.append(ValidationIssue("params", "params phải là object.", sid))
            continue
        if _unsafe_payload(params):
            issues.append(ValidationIssue(
                "unsafe_param", "Plan chứa storage/credential/callback URL không được phép.", sid))
            continue
        try:
            schema = resolve_params_schema(tool_name, params, apps=loaded)
        except Exception as exc:
            issues.append(ValidationIssue("schema", str(exc), sid)); continue
        checked = dict(params)
        for field, rule in schema.items():
            value = params.get(field)
            if (rule.get("type") in ("image", "video", "audio", "image[]", "video[]")
                    and value is not None
                    and not (isinstance(value, str) and value.startswith("$"))):
                issues.append(ValidationIssue(
                    "artifact_ref", "Artifact phải là tham chiếu $input/$step.", sid, field))
        for field, value in params.items():
            if not isinstance(value, str) or not value.startswith("$"):
                continue
            match = _REF.fullmatch(value)
            if not match:
                issues.append(ValidationIssue("reference", "Tham chiếu không hợp lệ.", sid, field)); continue
            source, output = match.groups()
            expected = _port_for_param(schema.get(field, {}).get("type", ""))
            if source == "input":
                actual = input_types.get(output)
            else:
                upstream = by_id.get(source)
                upstream_spec = tools.get(upstream.get("tool")) if upstream else None
                actual = upstream_spec.returns.get(output) if upstream_spec else None
                if source not in deps.get(sid, set()):
                    issues.append(ValidationIssue("reference_order", f"{source} phải có trong after.", sid, field))
            if actual is None:
                issues.append(ValidationIssue("reference", f"Không có output {value}.", sid, field))
            elif actual != expected:
                issues.append(ValidationIssue("port_type", f"{value} là {actual}, cần {expected}.", sid, field))
            if field in schema:
                checked[field] = _placeholder(schema[field])
        try:
            validated = validate_tool_params(tool_name, checked, apps=loaded)
        except ToolParamsError as exc:
            issues.append(ValidationIssue("params", str(exc), sid)); continue
        try:
            fanout = int(step.get("fanout", 1)); retry = int(step.get("max_retry", 0))
        except (TypeError, ValueError):
            fanout = retry = -1
        if not 1 <= fanout <= MAX_FANOUT:
            issues.append(ValidationIssue("fanout", "fanout phải trong 1–4.", sid)); continue
        if not 0 <= retry <= MAX_RETRY:
            issues.append(ValidationIssue("retry", "max_retry phải trong 0–2.", sid)); continue
        if step.get("on_fail", "retry_same") not in _ON_FAIL:
            issues.append(ValidationIssue("on_fail", "on_fail không hợp lệ.", sid)); continue
        verify = step.get("verify")
        requested = verify if isinstance(verify, list) else ([verify] if verify else [])
        if verify is not None and (not requested or any(not isinstance(v, dict) for v in requested)):
            issues.append(ValidationIssue("verify", "verify phải là object hoặc danh sách object.", sid)); continue
        bad_check = next((str(v.get("check", "")) for v in requested
                          if v.get("check") not in VERIFIER_CREDIT), "")
        if bad_check:
            issues.append(ValidationIssue("verify", f"Verifier không hỗ trợ: {bad_check}.", sid)); continue
        unavailable = next((str(v.get("check", "")) for v in requested
                            if v.get("check") not in spec.verifiable), "")
        if unavailable:
            issues.append(ValidationIssue(
                "verify", f"Tool không khai verifier {unavailable}.", sid)); continue
        try:
            unit = credit_for(spec.job_type, validated, apps=loaded)
        except Exception as exc:
            issues.append(ValidationIssue("price", str(exc), sid)); continue
        verify_unit = verifier_cost(verify)
        maximum = (unit + verify_unit) * fanout * (1 + retry)
        total += maximum
        step_costs.append({"step_id": sid, "unit": unit,
                           "verifier_unit": verify_unit, "fanout": fanout,
                           "max_retry": retry, "maximum": maximum,
                           "app_slug": owners[tool_name].slug})

    if budget >= 0 and total > budget:
        issues.append(ValidationIssue("budget", f"Cần tối đa {total}, vượt ngân sách {budget}."))
    if balance is not None and total > int(balance):
        issues.append(ValidationIssue("balance", f"Cần tối đa {total}, số dư {balance}."))
    return ValidationResult(not issues, tuple(issues), total, tuple(step_costs))
