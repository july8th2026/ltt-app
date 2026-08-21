"""Bản kê phiên bản LTT Nexus — nguồn CHUNG cho trang tải và client tự-update.

Model B (Q101): web là nơi hướng dẫn + tải. Một manifest JSON mô tả bản mới nhất
cho từng nền tảng (URL tải, SHA-256, chữ ký phát hành). Trang tải render từ nó;
client tự-update đọc chính nó để biết có bản mới không.

Vận hành cập nhật bằng cách sửa `data/nexus_versions.json` (không cần deploy code).
Thiếu file → dùng mặc định dưới đây (mọi nền tảng "đang chuẩn bị", trừ khi có URL).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

#: Bốn nền tảng mục tiêu (Windows/macOS/iOS/Android). `available=False` → trang
#: hiện "đang chuẩn bị"; đặt `available` + `url` khi bản nền tảng đó sẵn sàng.
DEFAULT: dict = {
    "version": "1.0.0",
    "notes": "Bản phát hành đầu tiên của LTT Nexus.",
    "platforms": {
        "windows": {"label": "Windows 10/11 (64-bit)", "available": False,
                    "url": "", "sha256": "", "kind": "zip"},
        "macos": {"label": "macOS", "available": False, "url": "", "sha256": "",
                  "kind": "dmg"},
        "ios": {"label": "iOS (iPhone/iPad)", "available": False, "url": "",
                "kind": "appstore"},
        "android": {"label": "Android", "available": False, "url": "",
                    "sha256": "", "kind": "apk"},
    },
}

PLATFORM_ORDER = ["windows", "macos", "ios", "android"]


def _path() -> Path:
    data = os.environ.get("LTT_DATA_DIR", "data")
    return Path(data) / "nexus_versions.json"


def manifest() -> dict:
    """Manifest hiện hành: đọc `data/nexus_versions.json` nếu có, hợp nhất lên
    mặc định (thiếu khoá nào lấy mặc định). Hỏng file → mặc định, không ném."""
    base = json.loads(json.dumps(DEFAULT))  # bản sao sâu
    p = _path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return base
        if isinstance(data, dict):
            base["version"] = str(data.get("version") or base["version"])
            base["notes"] = str(data.get("notes") or base["notes"])
            plats = data.get("platforms")
            if isinstance(plats, dict):
                for key, val in plats.items():
                    if key in base["platforms"] and isinstance(val, dict):
                        base["platforms"][key].update(val)
    return base


def latest_version() -> str:
    return str(manifest().get("version") or "")


def platform_info(plat: str) -> dict:
    return manifest().get("platforms", {}).get(str(plat or ""), {})


__all__ = ["DEFAULT", "PLATFORM_ORDER", "latest_version", "manifest",
           "platform_info"]
