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

import pytest
import yaml

from apps.ltt_llm import ngan_sach

GOC = pathlib.Path(__file__).resolve().parents[1]


def test_bi_danh_cu_la_cung_mot_so():
    assert ngan_sach.DONG_THOI_MAY_B == ngan_sach.SO_SLOT_MAY_B
    assert ngan_sach.POOL_KV_MAY_B == ngan_sach.CUA_SO_MODEL


def test_manifest_doc_tu_nguon():
    """🔴 HỎI BẰNG `admission_cho(model)`, KHÔNG BẰNG BỘ BA TĨNH (dual-model 2.3).

    Từ 2.3 `text.chat` khai `admission_theo_model`, nên `tool.admission_slots`
    là **0** và `tool.admission_token_pool` là **0** — bản cũ của phép kiểm này
    sẽ đỏ, và đỏ vì một lý do sai: nó đang đọc một trường không còn mang câu trả
    lời chứ không phải vì ai gõ số tay.

    Điều nó ĐO vẫn nguyên: bản khai đọc từ `ngan_sach.py`, không gõ số.
    """
    from apps.ltt_llm.manifest import MANIFEST

    tool = MANIFEST.tools[0]
    for model, pool in (("ltt-3.8", ngan_sach.POOL_38),
                        ("ltt-3.5", ngan_sach.POOL_35)):
        suc = tool.admission_cho(model)
        assert suc is not None, f"{model} khong co trong admission_theo_model"
        assert suc.slots == ngan_sach.SO_SLOT
        assert suc.token_pool == pool


def test_manifest_khong_go_so_tay():
    """`admission_slots=1` gõ tay là đúng cái chồng chéo phép kiểm này sinh ra để dẹp."""
    van = (GOC / "apps" / "ltt_llm" / "manifest.py").read_text(encoding="utf-8")
    assert not re.search(r"admission_slots\s*=\s*\d", van)
    assert not re.search(r"admission_token_pool\s*=\s*\d", van)


@pytest.mark.xfail(strict=True, reason="cho Task 3.3")
def test_yaml_parallel_khop_so_slot():
    """⛔ `xfail(strict=True)` CHO TASK 3.3 — không phải một phép kiểm bị tắt.

    Dual-model 2.6 đưa `SO_SLOT_MAY_B` lên **3** (L-14 §G1b: 4 slot ở ngữ cảnh
    đã chốt tràn ~400 MiB sang RAM chủ). `llama-swap.yaml` là **tệp của máy B**
    và Task 3.3 mới viết lại nó, nên trong đúng cửa sổ thời gian này hai bên
    lệch **có chủ ý**. `strict=True` ⇒ ngày yaml đúng thì XPASS ⇒ ĐỎ ⇒ người làm
    3.3 buộc phải gỡ dấu.

    ⚠️ HỆ QUẢ TRIỂN KHAI, và nó không nằm trong tệp này: máy A từ nay nhận **3**
       lượt đồng thời cho mỗi model trong khi llama-server bên B còn
       `--parallel 1`. Các commit Pha 2 **chưa deploy**; đừng deploy máy A trước
       khi Task 3.3 deploy yaml.
    """
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
    assert projected.admission_cho("ltt-3.8").token_pool == ngan_sach.POOL_38
    assert "admission_token_pool" not in projected.to_public_dict()
    assert "admission_theo_model" not in projected.to_public_dict(), (
        "ban chieu cong khai dang lo ten tai nguyen noi bo")


def test_tool_khac_mac_dinh_khong_ap_ngan_sach_token():
    """Mặc định 0 ⇒ mọi tool khác (ảnh, tiếng, video…) không đổi hành vi admission."""
    import dataclasses

    from platform_core.registry import ToolSpec

    mac_dinh = {f.name: f.default for f in dataclasses.fields(ToolSpec)}
    assert mac_dinh["admission_token_pool"] == 0
