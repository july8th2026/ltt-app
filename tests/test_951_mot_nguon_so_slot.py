"""Một nguồn cho số slot máy B và pool KV (multijob Task 2).

🔴 VÌ SAO: trước 11/09 có BỐN chỗ cùng khai "1 lượt đồng thời" — `DONG_THOI_MAY_B`,
`manifest.py` (`admission_slots=1`), gateway `LTT_LLM_MAX_DONG_THOI` và `--parallel 1`
trong yaml — và chỉ một cặp có phép kiểm đối chiếu. Đổi một chỗ mà quên chỗ kia thì
hai trần không biết nhau: máy A nhận 4 lượt, máy B trả 429 cho 3.
⭐ Nên phép kiểm này đọc CẢ BỐN và bắt chúng đồng ý với `ngan_sach.SO_SLOT_MAY_B`.
"""
from __future__ import annotations

import pathlib
import re

import yaml

from apps.ltt_llm import ngan_sach

GOC = pathlib.Path(__file__).resolve().parents[1]


def test_bi_danh_cu_la_cung_mot_so():
    assert ngan_sach.DONG_THOI_MAY_B == ngan_sach.SO_SLOT_MAY_B
    assert ngan_sach.POOL_KV_MAY_B == ngan_sach.CUA_SO_MODEL


def test_manifest_doc_tu_nguon():
    from apps.ltt_llm.manifest import MANIFEST

    tool = MANIFEST.tools[0]
    assert tool.admission_slots == ngan_sach.SO_SLOT_MAY_B
    assert tool.admission_token_pool == ngan_sach.POOL_KV_MAY_B


def test_manifest_khong_go_so_tay():
    """`admission_slots=1` gõ tay là đúng cái chồng chéo phép kiểm này sinh ra để dẹp."""
    van = (GOC / "apps" / "ltt_llm" / "manifest.py").read_text(encoding="utf-8")
    assert not re.search(r"admission_slots\s*=\s*\d", van)
    assert not re.search(r"admission_token_pool\s*=\s*\d", van)


def test_yaml_parallel_khop_so_slot():
    cfg = yaml.safe_load((GOC / "llm_gateway" / "deploy" / "llama-swap.yaml")
                         .read_text(encoding="utf-8"))
    chung = str(cfg["macros"]["CHUNG"]).split()
    i = chung.index("--parallel")
    assert int(chung[i + 1]) == ngan_sach.SO_SLOT_MAY_B, (
        f"llama-swap chay --parallel {chung[i + 1]} nhung ngan_sach khai "
        f"{ngan_sach.SO_SLOT_MAY_B}")


def test_gateway_mac_dinh_khop_so_slot():
    """`llm_gateway` deploy sang máy B nên không import được `ngan_sach` — đọc mã nguồn."""
    van = (GOC / "llm_gateway" / "config.py").read_text(encoding="utf-8")
    m = re.search(r'_int\("LTT_LLM_MAX_DONG_THOI",\s*(\d+)\)', van)
    assert m, "khong thay mac dinh LTT_LLM_MAX_DONG_THOI trong llm_gateway/config.py"
    assert int(m.group(1)) == ngan_sach.SO_SLOT_MAY_B


def test_chieu_catalog_mang_pool_nhung_khong_lo_ra_khach():
    from apps.ltt_llm.manifest import MANIFEST
    from platform_core.public_api.catalog import project_tool

    projected = project_tool(MANIFEST, MANIFEST.tools[0])
    assert projected.admission_token_pool == ngan_sach.POOL_KV_MAY_B
    assert "admission_token_pool" not in projected.to_public_dict()


def test_tool_khac_mac_dinh_khong_ap_ngan_sach_token():
    """Mặc định 0 ⇒ mọi tool khác (ảnh, tiếng, video…) không đổi hành vi admission."""
    import dataclasses

    from platform_core.registry import ToolSpec

    mac_dinh = {f.name: f.default for f in dataclasses.fields(ToolSpec)}
    assert mac_dinh["admission_token_pool"] == 0
