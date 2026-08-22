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
#:
#: `note` (tuỳ chọn) thay dòng "Sẵn sàng để tải". Cần cho iOS: file `.ipa` chưa
#: ký **không cài được bằng Safari** — iOS chỉ cho cài thẳng từ web khi có chữ
#: ký phân phối + manifest `itms-services`. Nói rõ ngay trên nút, đừng để người
#: dùng tải về rồi mới phát hiện không mở được.
DEFAULT: dict = {
    "version": "1.0.0",
    "notes": "Bản phát hành đầu tiên của LTT Nexus.",
    "platforms": {
        # `setup_url`/`setup_sha256` là file cài MỘT-FILE (tự giải nén), dùng cho
        # **tự cập nhật**: client tải nó, kiểm hash, rồi chạy `--silent-install`.
        # `url` (zip) vẫn giữ cho người muốn bản chạy-không-cài. Thiếu `setup_url`
        # thì client **không** rơi về zip — chạy zip thẳng không được, đoán bừa
        # là hỏng ngầm.
        "windows": {"label": "Windows 10/11 (64-bit)", "available": False,
                    "url": "", "sha256": "", "kind": "zip",
                    "setup_url": "", "setup_sha256": ""},
        # macOS cung co `setup_url`, va o day no tro chinh file `.dmg`: duong tu
        # cap nhat ban macOS gan `.dmg`, `ditto` goi `.app` de len ban cu roi mo
        # lai (`nexus_client::tai_va_cai_ban_moi`). Khac Windows o cho `url` va
        # `setup_url` co the tro CUNG mot file — macOS khong co khai niem "ban
        # chay-khong-cai" tach roi.
        "macos": {"label": "macOS", "available": False, "url": "", "sha256": "",
                  "kind": "dmg", "setup_url": "", "setup_sha256": ""},
        # `signed=True` chỉ đặt khi IPA đã ký Ad Hoc/Enterprise — lúc đó trang
        # hiện nút "Cài lên iPhone" (itms-services) và Safari cài thẳng được.
        # Ký bằng Apple ID miễn phí (hồ sơ development) KHÔNG tính: iOS từ chối.
        "ios": {"label": "iOS (iPhone/iPad)", "available": False, "url": "",
                "sha256": "", "kind": "ipa", "note": "", "signed": False},
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
