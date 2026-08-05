"""Vùng chạm tối thiểu 24px — WCAG 2.2 AA mục 2.5.8.

Đây là test tĩnh trên CSS, không thay cho đo bằng browser. Nó canh đúng một
điều: những luật đã sửa ngày 2026-08-06 không bị ai gỡ ra sau này. Đo thật vẫn
phải làm bằng Playwright ở 390px — audit control-plane ghi rõ cách làm.

Vì sao chọn đúng những selector này: đo trên Chrome thật ở 390×844 qua 15 trang
cho thấy chỉ còn bốn chỗ fail, và footer là chỗ duy nhất có mặt ở MỌI trang.
"""
from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSS = (ROOT / "server" / "static" / "ltt.css").read_text(encoding="utf-8")


def _blocks(selector: str) -> list[str]:
    """Mọi khối khai cho selector này.

    Một selector có thể xuất hiện nhiều lần và khối SAU thắng theo cascade, nên
    chỉ đọc khối đầu tiên là đọc nhầm luật. Bản đầu của test này mắc đúng lỗi đó
    và báo đỏ giả cho hai selector vốn đã đúng.
    """
    found = []
    for match in re.finditer(re.escape(selector) + r"\s*\{([^}]*)\}", CSS):
        found.append(match.group(1).replace(" ", ""))
    return found


@pytest.mark.parametrize("selector", [
    ".platform-footer a",   # 8 link, có ở mọi trang — chỗ tệ nhất trước khi sửa
    ".tv-audio",            # label chỉ cao 16px
    "#tv-files",            # ô chọn file 21px
    ".error-home-link",     # link trên trang lỗi
])
def test_selector_declares_a_minimum_touch_height(selector):
    blocks = _blocks(selector)
    assert blocks, f"mất selector {selector}"
    assert any("min-height:24px" in block for block in blocks), (
        f"{selector} không còn min-height:24px — vùng chạm sẽ fail WCAG 2.5.8")


def test_the_market_search_input_fills_its_box():
    """Khung tìm kiếm cao 40px nhưng `input` chỉ 21px: bấm vào phần còn lại của
    khung không focus được. Cho input kéo hết chiều cao mới là vùng chạm thật."""
    blocks = _blocks(".market-search input")
    assert blocks, "mất selector .market-search input"
    assert any("align-self:stretch" in b and "min-height:24px" in b for b in blocks)
