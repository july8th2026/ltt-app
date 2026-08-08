"""Catalog tích hợp của Prompt AI, phát hành cùng code và chỉ đọc.

Các mục là bản chắt lọc từ năng lực Prompt Seedance; không đọc database, file
người dùng hay import runtime từ cây nguồn. Người dùng clone một mục thành bản
riêng trước khi sửa.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
import json

from platform_core.i18n import _ as _t


_PUBLISHED_AT = datetime(2026, 8, 9, tzinfo=timezone.utc)
_KINDS = {"meta", "snippet", "style"}


@dataclass(frozen=True)
class BuiltinLibraryItem:
    id: str
    kind: str
    name: str
    body: str
    owner_id: None = None
    is_catalog: bool = True
    cloned_from_id: None = None
    archived_at: None = None
    deprecated_at: None = None
    deprecated_note: str = ""
    updated_at: datetime = _PUBLISHED_AT
    purpose: str = "director"
    variables: dict = field(default_factory=dict)
    category: str = ""
    negative: str = ""
    attributes: dict = field(default_factory=dict)
    version: int = 1


@lru_cache(maxsize=1)
def _all() -> tuple[BuiltinLibraryItem, ...]:
    resource = files("apps.prompt_ai_ommi.prompts").joinpath(
        "library_catalog.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    rows = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError(_t("Catalog tích hợp Prompt AI không hợp lệ."))
    made = []
    seen = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError(_t("Mục catalog Prompt AI phải là object."))
        kind = str(raw.get("kind") or "")
        item_id = str(raw.get("id") or "")
        name = str(raw.get("name") or "").strip()
        body = str(raw.get("body") or "").strip()
        if kind not in _KINDS or not item_id or item_id in seen or not name or not body:
            raise ValueError(_t("Mục catalog Prompt AI thiếu hoặc trùng định danh."))
        if len(item_id) > 36:
            raise ValueError(_t("Định danh catalog Prompt AI vượt 36 ký tự."))
        seen.add(item_id)
        made.append(BuiltinLibraryItem(
            id=item_id, kind=kind, name=name, body=body,
            purpose=str(raw.get("purpose") or "director")[:64],
            variables=(dict(raw.get("variables") or {})
                       if isinstance(raw.get("variables"), dict) else {}),
            category=str(raw.get("category") or "")[:64],
            negative=str(raw.get("negative") or ""),
            attributes=(dict(raw.get("attributes") or {})
                        if isinstance(raw.get("attributes"), dict) else {}),
        ))
    return tuple(made)


def list_builtins(kind: str, query: str = "") -> list[BuiltinLibraryItem]:
    wanted = (kind or "").strip().lower()
    if wanted not in _KINDS:
        return []
    needle = (query or "").strip().casefold()
    rows = [item for item in _all() if item.kind == wanted]
    if needle:
        rows = [item for item in rows
                if needle in item.name.casefold() or needle in item.body.casefold()]
    return sorted(rows, key=lambda item: item.name.casefold())


def find_builtin(kind: str, item_id: str) -> BuiltinLibraryItem | None:
    return next((item for item in list_builtins(kind) if item.id == item_id), None)
