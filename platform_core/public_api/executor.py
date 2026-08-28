"""Resolve app-owned synchronous executors through the registry contract.

Protocol routes need a small app-specific surface for validation, model alias
resolution, token budgeting and execution.  Keeping the reference in the
tool manifest prevents ``server/api`` from importing a particular app and
lets another app expose the same protocols without editing the platform.
"""
from __future__ import annotations

import importlib


def _load(reference: str):
    module_name, separator, attribute = str(reference or "").partition(":")
    if not separator or not module_name or not attribute:
        raise RuntimeError("sync executor reference must be module:attribute")
    return getattr(importlib.import_module(module_name), attribute)


def for_tool(tool):
    """Load the executor declared by a ``ToolSpec`` or ``PublicTool``."""
    reference = getattr(tool, "sync_executor", "")
    if not reference:
        raise RuntimeError(f"tool {getattr(tool, 'name', '')!r} has no sync executor")
    return _load(reference)


def for_tool_name(name: str):
    """Find a tool by its declared name, without hardcoding any app."""
    from platform_core.registry import discover

    matches = [spec for loaded in discover() for spec in loaded.manifest.tools
               if spec.name == name]
    if len(matches) != 1:
        raise RuntimeError(f"expected one sync tool named {name!r}, found {len(matches)}")
    return for_tool(matches[0])
