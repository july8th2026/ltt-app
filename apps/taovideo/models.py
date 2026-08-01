"""
models.py — registry model seedance (di trú từ `app/models/video_model_registry.py`).

Mỗi model: nhãn hiển thị, `endpoint` (ep-... của tài khoản ModelArk — field `model`
gửi lên body), `provider_model_id` (dự phòng), độ phân giải / thời lượng / tỉ lệ
hỗ trợ. Endpoint ep-... đi kèm KEY byteplus (cùng tài khoản đã import từ BOT GEMINI).
"""
from __future__ import annotations

DEFAULT_MODEL = "seedance-2.0-mini"

MODELS = {
    "seedance-2.0-mini": {
        "label": "Seedance 2.0 Mini",
        "endpoint": "ep-20260721233903-fsrqt",
        "provider_model_id": "dreamina-seedance-2-0-mini-260615",
        "resolutions": ["480p", "720p"],
        "durations": [4, 5, 6, 8, 10, 12, 15],
        "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
        "active": True,
    },
    "seedance-2.0": {
        "label": "Seedance 2.0",
        "endpoint": "ep-20260725171301-kjhh8",
        "provider_model_id": "dreamina-seedance-2-0-260128",
        "resolutions": ["480p", "720p", "1080p", "4k"],
        "durations": [4, 5, 6, 8, 10, 12, 15],
        "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
        "active": True,
    },
    "seedance-2.0-fast": {
        "label": "Seedance 2.0 Fast",
        "endpoint": "ep-20260725171215-26j65",
        "provider_model_id": "dreamina-seedance-2-0-fast-260128",
        "resolutions": ["480p", "720p"],
        "durations": [4, 5, 6, 8, 10, 12, 15],
        "aspects": ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"],
        "active": True,
    },
}


def get(model_id: str) -> dict | None:
    return MODELS.get(model_id)


def provider_model(model_id: str) -> str:
    """id gửi trong body `model` = endpoint ep-... (dự phòng provider_model_id)."""
    m = MODELS.get(model_id) or {}
    return m.get("endpoint") or m.get("provider_model_id") or model_id


def options() -> list:
    """[(id, label)] cho UI, chỉ model active, mini trước."""
    return [(k, v["label"]) for k, v in MODELS.items() if v.get("active")]
