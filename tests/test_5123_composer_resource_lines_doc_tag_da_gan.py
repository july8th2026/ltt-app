"""composer.resource_lines() phai DOC tag da gan (ommi_binding), khong tu dem
lai, khi item cung cap san khoa "tag" (spec quyet dinh D-2, chua N-2).
"""
from __future__ import annotations

from apps.prompt_ai_ommi.services.composer import resource_lines


def test_dung_tag_co_san_thay_vi_tu_dem():
    items = [{"kind": "image", "tag": "@IMAGE_5", "name": "Nhân vật A",
             "description": "áo xanh"}]
    lines = resource_lines(items)
    assert lines == ["- @IMAGE_5 [image] Nhân vật A: áo xanh"], (
        "phai dung DUNG tag da gan (@IMAGE_5), khong tu dem thanh @IMAGE_1")


def test_khong_co_tag_van_tu_dem_nhu_cu_tuong_thich_nguoc():
    items = [{"kind": "image", "name": "A", "description": "x"},
             {"kind": "video", "name": "B", "description": "y"},
             {"kind": "image", "name": "C", "description": "z"}]
    lines = resource_lines(items)
    assert lines == [
        "- @IMAGE_1 [image] A: x",
        "- @VIDEO_1 [video] B: y",
        "- @IMAGE_2 [image] C: z",
    ]
