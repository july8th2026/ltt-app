"""
Đợt A1 — cổng parity cho app di trú `taoanh` (ảnh).

Khoá: manifest đúng hợp đồng, bảng giá theo model và số ảnh, và app tự
discover được không lỗi.

## Vì sao tệp này ngắn đi một nửa (2026-08-25)

Đợt A1 gốc di trú **hai** app: `taoanh` (ảnh) và `kichban` (kịch bản văn bản).
Nửa `kichban` — catalog prompt, ghép fragment giữ nguyên khối JSON, parse kịch
bản chịu được fence hỏng — đi cùng app đó khi nó bị gỡ (Q109).

⭐ Nhưng một bài học ở đó **không** thuộc về `kichban` và đáng nhớ: prompt của
   nó nhúng một khối JSON mẫu, nên `str.format()` vỡ ở dấu `{`. Cách sửa là
   ghép fragment chứ không format. App nào sau này nhúng JSON vào prompt sẽ gặp
   lại đúng chỗ đó — `platform_core/prompt_fragments.py` vẫn còn và vẫn là câu
   trả lời.
"""
from __future__ import annotations


# ── taoanh (ảnh) ───────────────────────────────────────────────────────────────
def test_taoanh_manifest():
    from apps.taoanh.manifest import MANIFEST
    assert MANIFEST.slug == "taoanh" and MANIFEST.route_prefix == "/taoanh"
    assert MANIFEST.job_types == ("taoanh.generate",)
    assert MANIFEST.credit_cost({"count": 3}) == 15
    assert MANIFEST.credit_cost({"count": 99}) == 20   # kẹp 4 ảnh
    assert MANIFEST.credit_cost({"model": "gemini-3.1-flash-image", "count": 2}) == 16
    assert MANIFEST.credit_cost({"model": "gemini-3-pro-image", "count": 1}) == 16


def test_taoanh_discover_khong_loi():
    from platform_core.registry import discover
    apps = {a.manifest.slug: a for a in discover()}
    assert "taoanh" in apps and not apps["taoanh"].error
