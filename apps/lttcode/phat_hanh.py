"""Quyết định bản cập nhật nào tới máy nào (spec updater LTTCODEAPP §2).

`quyet_dinh` là hàm thuần: nhận manifest đã đọc + tham số của request, trả
`(mã HTTP, thân JSON | None)`. Thứ tự luật:

1. tham số sai ⇒ 400; kênh lạ ⇒ 404; manifest thiếu/hỏng ⇒ 204 (client không
   bao giờ thấy 500 — một tệp JSON gõ sai không được làm app người dùng báo lỗi);
2. `kill_switch` ⇒ 204 cho mọi người, kể cả bản bắt buộc;
3. ứng viên = bản chưa `revoked`, mới hơn bản đang chạy, và **không có
   `session_format` thấp hơn** bản đang chạy: định dạng session của DSH chỉ tiến,
   bản cũ hơn từ chối mở session mới ⇒ người dùng mất quyền vào session của mình;
4. dưới `min_version` ⇒ bắt buộc, bỏ qua rollout;
5. rollout: `sha256(install_id:version)` lấy 8 hex đầu, mod 100, so với %.
   Thiếu install_id chỉ nhận bản 100% — không đoán nhóm từ IP.

Không ghi log IP hay install_id.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from platform_core.runtime_paths import data_path

log = logging.getLogger(__name__)

KENH = ("stable", "beta", "dev")
TARGET = "windows"
ARCH = "x86_64"
TEP_MANIFEST = "lttcode_releases.json"
THU_MUC_DIST = "lttcode_dist"

_SEMVER = re.compile(r"^(\d{1,6})\.(\d{1,6})\.(\d{1,6})$")
#: Tên tệp "hiền" — cùng luật với `/nexus/dl/`: chặn '/', '\\', '..' tận gốc.
TEN_TEP = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def phien_ban(chuoi: Any) -> tuple[int, int, int] | None:
    m = _SEMVER.match(chuoi) if isinstance(chuoi, str) else None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def doc_manifest() -> dict | None:
    path = Path(data_path(TEP_MANIFEST))
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.warning("lttcode: cannot read %s: %s", TEP_MANIFEST, e)
        return None
    return data if isinstance(data, dict) else None


def trong_nhom(install_id: str | None, version: str, percent: int) -> bool:
    if percent >= 100:
        return True
    if percent <= 0 or not install_id:
        return False
    so = int(hashlib.sha256(f"{install_id}:{version}".encode()).hexdigest()[:8], 16)
    return so % 100 < percent


def _khoa(r: dict) -> tuple[int, int, int]:
    """Khoá so sánh của một bản ĐÃ qua `_ban_hop_le` (version chắc chắn là semver)."""
    return phien_ban(r["version"]) or (0, 0, 0)


def _so_nguyen(v: Any, mac_dinh: int) -> int:
    if isinstance(v, bool):
        return mac_dinh
    try:
        return int(v)
    except (TypeError, ValueError):
        return mac_dinh


def _ban_hop_le(r: Any) -> bool:
    return (
        isinstance(r, dict)
        and phien_ban(r.get("version")) is not None
        and isinstance(r.get("file"), str)
        and bool(TEN_TEP.match(r["file"]))
        and isinstance(r.get("signature"), str)
        and bool(r["signature"])
    )


def ban_moi_nhat(manifest: dict | None, channel: str) -> dict | None:
    """Bản chưa thu hồi cao nhất của kênh — cho trang tải."""
    kenh = (manifest or {}).get("channels") if isinstance(manifest, dict) else None
    kenh = kenh.get(channel) if isinstance(kenh, dict) else None
    ds = [r for r in (kenh.get("releases") or []) if _ban_hop_le(r) and r.get("revoked") is not True] \
        if isinstance(kenh, dict) and isinstance(kenh.get("releases"), list) else []
    return max(ds, key=_khoa) if ds else None


def quyet_dinh(
    manifest: dict | None,
    channel: str,
    target: str,
    arch: str,
    current: str,
    install_id: str | None,
    base_url: str,
) -> tuple[int, dict | None]:
    cur = phien_ban(current)
    if target != TARGET or arch != ARCH or cur is None:
        return 400, None
    if channel not in KENH:
        return 404, None
    kenh = manifest.get("channels") if isinstance(manifest, dict) else None
    kenh = kenh.get(channel) if isinstance(kenh, dict) else None
    if not isinstance(kenh, dict) or kenh.get("kill_switch") is True:
        return 204, None
    releases = [r for r in kenh.get("releases") or [] if _ban_hop_le(r)] \
        if isinstance(kenh.get("releases"), list) else []

    format_hien_tai = next(
        (_so_nguyen(r.get("session_format"), 0) for r in releases if _khoa(r) == cur), None)
    ung_vien = [
        r for r in releases
        if r.get("revoked") is not True
        and _khoa(r) > cur
        and (format_hien_tai is None or _so_nguyen(r.get("session_format"), 0) >= format_hien_tai)
    ]
    if not ung_vien:
        return 204, None
    chon = max(ung_vien, key=_khoa)

    bat_buoc = cur < (phien_ban(kenh.get("min_version")) or (0, 0, 0))
    if not bat_buoc and not trong_nhom(install_id, chon["version"], _so_nguyen(chon.get("rollout_percent"), 0)):
        return 204, None

    return 200, {
        "version": chon["version"],
        "notes": chon.get("notes") or "",
        "pub_date": chon.get("pub_date"),
        "url": f"{base_url.rstrip('/')}/lttcode/dl/{chon['file']}",
        "signature": chon["signature"],
        "mandatory": bat_buoc,
    }
