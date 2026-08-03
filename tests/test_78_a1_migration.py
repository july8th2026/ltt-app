"""
Đợt A1 — cổng parity cho 2 app di trú: `taoanh` (ảnh) + `kichban` (kịch bản text).

Khoá: catalog kịch bản đủ số lượng, prompt ghép từ fragment (giữ JSON braces),
parse kịch bản chịu được fence/JSON hỏng, manifest 2 app đúng hợp đồng.
"""
from __future__ import annotations

import pathlib

KB_PROMPTS = pathlib.Path(__file__).resolve().parent.parent / "apps" / "kichban" / "prompts"
KB_EXPECT = {"do_dai_video": 5, "giong_van": 6, "doi_tuong": 6, "ngon_ngu": 2}


# ── taoanh (ảnh) ───────────────────────────────────────────────────────────────
def test_taoanh_manifest():
    from apps.taoanh.manifest import MANIFEST
    assert MANIFEST.slug == "taoanh" and MANIFEST.route_prefix == "/taoanh"
    assert MANIFEST.job_types == ("taoanh.generate",)
    assert MANIFEST.credit_cost({"count": 3}) == 15
    assert MANIFEST.credit_cost({"count": 99}) == 20   # kẹp 4 ảnh
    assert MANIFEST.credit_cost({"model": "gemini-3.1-flash-image", "count": 2}) == 16
    assert MANIFEST.credit_cost({"model": "gemini-3-pro-image", "count": 1}) == 16


# ── kichban (kịch bản văn bản) ─────────────────────────────────────────────────
def test_kichban_catalog_du_so_luong():
    from platform_core import prompt_fragments as pf
    for g, n in KB_EXPECT.items():
        assert len(pf.options(KB_PROMPTS, g)) == n, f"{g} sai so luong"


def test_kichban_build_prompt_ghep_fragment_giu_json():
    from apps.kichban.jobs import build_prompt
    p = build_prompt("Cach hoc tieng Anh", duration="5-10_phut", tone="educational",
                     audience="beginner", language="vi")
    assert "Cach hoc tieng Anh" in p            # topic ghép vào
    assert '"title"' in p and "{" in p          # khối JSON mẫu GIỮ NGUYÊN (không vỡ .format)
    assert "{topic}" not in p and "{lang_directive}" not in p   # placeholder đã thay


def test_kichban_parse_script_fenced_json():
    from apps.kichban.jobs import _parse_script
    raw = '```json\n{"title":"T","hook":"h","sections":[{"title":"a","content":"b"}],' \
          '"outro":"o","description":"d","tags":["x","y"]}\n```'
    s = _parse_script(raw, "chu de")
    assert s["title"] == "T" and len(s["sections"]) == 1 and s["tags"] == ["x", "y"]
    assert s["parse_error"] is False


def test_kichban_parse_script_hong_khong_mat_du_lieu():
    from apps.kichban.jobs import _parse_script
    s = _parse_script("khong phai json", "chu de")
    assert s["parse_error"] is True and s["title"] == "chu de"
    assert s["sections"] and "khong phai json" in s["sections"][0]["content"]


def test_kichban_manifest():
    from apps.kichban.manifest import MANIFEST
    assert MANIFEST.slug == "kichban" and MANIFEST.route_prefix == "/kichban"
    assert MANIFEST.job_types == ("kichban.generate",)
    assert MANIFEST.credit_cost({}) == 3


# ── cả hai auto-discover được ──────────────────────────────────────────────────
def test_ca_hai_app_discover_khong_loi():
    from platform_core.registry import discover
    apps = {a.manifest.slug: a for a in discover()}
    for s in ("taoanh", "kichban"):
        assert s in apps and not apps[s].error, f"{s} loi discover"
