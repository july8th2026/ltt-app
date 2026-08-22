"""
catalog.py — model nào, chế độ nào, dùng template nào.

Toàn bộ nằm trong `workflows/catalog.json` để **thêm model không phải sửa mã**.
Máy A gọi `GET /v1/models` để biết cổng này đang phục vụ gì; `providers_live.py`
của nền tảng đọc đúng đường đó (`list_models_path`).

Hình dạng một mục:

    {"id": "hidream-o1",
     "label": "HiDream-O1 (may nha)",
     "license": "MIT",
     "modes": {
        "t2i":       {"template": "hidream_o1_t2i.json", "ref_slots": []},
        "edit":      {"template": "hidream_o1_edit.json", "ref_slots": ["ref1"]},
        "subject":   {"template": "hidream_o1_subject.json", "ref_slots": ["ref1", "ref2"]}
     },
     "defaults": {"width": 2560, "height": 1440, "steps": 50, "cfg": 5.0},
     "buckets": [[2560,1440],[2048,2048],[1440,2560]],
     "max_refs": 2}

⛔ `max_refs` mặc định **2**, không phải 5. `ref_max_size()` của HiDream-O1 thu nhỏ
   mỗi ảnh tham chiếu theo số lượng: 1 ảnh giữ nguyên · 2 ảnh ×0,75 · 3 ảnh ÷2 ·
   4 ảnh ×0,375 · ≥5 ảnh ÷4. Nhồi 5 ảnh là tự bỏ đi ¾ độ phân giải tham chiếu —
   ngược hẳn mục tiêu chất lượng-trên-hết (D-010).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .workflows import THU_MUC_MAC_DINH

TEN_FILE = "catalog.json"


class CatalogError(ValueError):
    pass


@dataclass(frozen=True)
class ModeSpec:
    template: str
    ref_slots: tuple[str, ...]


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    license: str
    modes: dict[str, ModeSpec]
    defaults: dict
    buckets: tuple[tuple[int, int], ...]
    max_refs: int

    def public(self) -> dict:
        """Cái máy A được thấy. **Không lộ tên file template** — đó là chi tiết thi
        hành của máy B, và lộ ra là mời người khác phụ thuộc vào nó."""
        return {
            "id": self.id, "label": self.label, "license": self.license,
            "modes": sorted(self.modes), "defaults": dict(self.defaults),
            "buckets": [list(b) for b in self.buckets], "max_refs": self.max_refs,
        }


def nap_catalog(thu_muc: Optional[Path] = None) -> dict[str, ModelSpec]:
    duong = (thu_muc or THU_MUC_MAC_DINH) / TEN_FILE
    if not duong.is_file():
        return {}
    try:
        data = json.loads(duong.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CatalogError(f"{TEN_FILE} khong phai JSON hop le: {e}") from None
    ra: dict[str, ModelSpec] = {}
    for muc in (data.get("models") or []):
        mid = str(muc.get("id") or "").strip()
        if not mid:
            raise CatalogError("mot muc model thieu 'id'")
        modes = {}
        for ten, m in (muc.get("modes") or {}).items():
            tpl = str((m or {}).get("template") or "").strip()
            if not tpl:
                raise CatalogError(f"model {mid} che do {ten} thieu 'template'")
            modes[str(ten)] = ModeSpec(tpl, tuple((m or {}).get("ref_slots") or ()))
        if not modes:
            raise CatalogError(f"model {mid} khong khai che do nao")
        ra[mid] = ModelSpec(
            id=mid,
            label=str(muc.get("label") or mid),
            license=str(muc.get("license") or "unknown"),
            modes=modes,
            defaults=dict(muc.get("defaults") or {}),
            buckets=tuple(tuple(b) for b in (muc.get("buckets") or ())),
            max_refs=int(muc.get("max_refs") or 2),
        )
    return ra
