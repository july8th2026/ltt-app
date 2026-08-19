"""Đọc manifest bản phát hành agent để trang tải hiển thị (Q95).

Trang tải phải công bố **SHA-256** của bản cài để khách đối chiếu, và nói trước
cảnh báo SmartScreen. Con số SHA-256 đó đến từ manifest mà `tools/nexus_sign_release.py`
sinh ra và người vận hành đặt vào `data/nexus/release_manifest.json` (dữ liệu vận
hành, **không** commit — cùng chỗ với các dữ liệu vận hành khác, Q28).

**Đọc để HIỂN THỊ, không để tin.** Bên tin manifest là agent, và nó xác minh chữ
ký Ed25519 trước khi chạy (`nexus_agent/updates.py`). Trang web chỉ khoe con số
cho người đọc; nên chỗ này **không** kiểm chữ ký, và cũng vì thế nó không được là
đường mà một manifest giả lọt vào máy khách — nó không chạm máy khách.

**Fail-safe, không fail-closed:** thiếu file hay file hỏng thì trả `None` để
trang nói "chưa có bản phát hành", **không** ném 500. Một trang tải sập vì thiếu
một file dữ liệu là một trang tải tệ hơn một trang nói thật rằng chưa có gì để
tải. (Khác với cờ `LTT_NEXUS` fail-*closed* — ở đó im lặng là đúng; ở đây rõ
ràng là đúng.)
"""
from __future__ import annotations

import json
import os

#: Các trường trang tải cần để hiển thị. Thiếu bất kỳ cái nào → coi như chưa có
#: bản phát hành, vì một dòng nửa vời (có version, thiếu sha256) tệ hơn không có.
TRUONG_HIEN_THI = ("version", "sha256", "url", "size")


def _duong_manifest(env: dict | None = None) -> str:
    e = os.environ if env is None else env
    thu_cong = str(e.get("LTT_NEXUS_RELEASE_MANIFEST", "")).strip()
    if thu_cong:
        return thu_cong
    from platform_core.runtime_paths import data_path

    return data_path("nexus", "release_manifest.json")


def ban_phat_hanh_hien_tai(env: dict | None = None) -> dict | None:
    """Manifest bản phát hành hiện tại, hoặc `None` nếu chưa có / không đọc được.

    Không bao giờ ném: mọi lỗi (thiếu file, JSON hỏng, thiếu trường) đều thành
    `None`. Xem docstring module vì sao fail-safe chứ không fail-closed ở đây.
    """
    duong = _duong_manifest(env)
    try:
        with open(duong, "r", encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(m, dict):
        return None
    if any(not str(m.get(t) or "").strip() for t in TRUONG_HIEN_THI):
        return None
    return m


__all__ = ["TRUONG_HIEN_THI", "ban_phat_hanh_hien_tai"]
