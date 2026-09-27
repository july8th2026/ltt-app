"""Banh coc: moi endpoint pha 3 deu co mot ham goi o frontend.

⭐ Do duoc 26/09: workspace React hien KHONG goi handoff, snapshot, import,
   reorder, usage, admin/catalog — tinh nang co o backend ma khach khong bam
   duoc. Phep kiem nay chan viec do lap lai o pha 3.
"""
from __future__ import annotations

import pathlib
import re

API = pathlib.Path("frontend/prompt-ai-ommi/src/ommiApi.ts")

DUONG_BAT_BUOC = (
    "/api/briefs", "/preflight", "/bundle", "/quote", "/generate",
    "/iterations", "/verdict", "/api/characters", "/lock", "/api/backgrounds",
)


def test_frontend_co_goi_moi_duong_pha_3():
    nguon = API.read_text(encoding="utf-8")
    thieu = [d for d in DUONG_BAT_BUOC if d not in nguon]
    assert thieu == [], f"frontend chua goi: {thieu}"


def test_khong_ham_nao_tu_tinh_lai_gia():
    """⛔ Gia la cua backend (`authoritative: true`). Tinh lai o frontend la hai
    cho khai cung mot dieu, va cho sai se la cho khach nhin thay.
    """
    nguon = API.read_text(encoding="utf-8")
    assert not re.search(r"credit\s*[*+]\s*\d", nguon)
