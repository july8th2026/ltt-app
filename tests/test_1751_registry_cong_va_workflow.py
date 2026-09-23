"""Spec §4.5 — ToolSpec khai `cong` (ánh xạ cổng) và `workflow` (ẩn khỏi palette)."""
from __future__ import annotations

import pytest

from platform_core import registry
from platform_core.registry import AppManifest, RegistryError, ToolSpec


def _mf() -> AppManifest:
    return AppManifest(slug="t", display_name="T", route_prefix="/t",
                       job_types=("t.x",))


def _tool(**kw) -> ToolSpec:
    goc = dict(name="t.x", job_type="t.x", description="mo ta",
               params_schema={"prompt": {"type": "string"},
                              "anh": {"type": "image"}},
               returns={"out": "image"})
    goc.update(kw)
    return ToolSpec(**goc)


def test_mac_dinh_khong_app_nao_phai_sua():
    t = _tool()
    assert t.cong == {} and t.workflow is True
    registry._validate_hop_dong_v2(_mf(), t)


def test_khai_cong_hop_le_qua_duoc():
    t = _tool(cong={"vao": {"anh": "image"}, "ra": {"out": "image"}})
    registry._validate_hop_dong_v2(_mf(), t)


def test_cong_co_khoa_la_thi_tu_choi():
    with pytest.raises(RegistryError, match="cong"):
        registry._validate_hop_dong_v2(_mf(), _tool(cong={"giua": {}}))


def test_cong_vao_tro_toi_tham_so_khong_co_thi_tu_choi():
    with pytest.raises(RegistryError, match="khong co"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"vao": {"khong_ton_tai": "image"}}))


def test_cong_ra_tro_toi_khoa_returns_khong_co_thi_tu_choi():
    with pytest.raises(RegistryError, match="khong co"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"ra": {"khong_ton_tai": "image"}}))


def test_kieu_cong_la_thi_tu_choi():
    with pytest.raises(RegistryError, match="kieu cong"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"vao": {"anh": "hinh_anh"}}))


def test_workflow_phai_la_bool():
    with pytest.raises(RegistryError, match="workflow"):
        registry._validate_hop_dong_v2(_mf(), _tool(workflow="co"))


def test_moi_toolspec_that_van_nap_duoc():
    # Đối chứng: 19 tool thật vẫn qua bộ kiểm mới (mặc định không phá ai).
    for item in registry.discover():
        # LoadedApp.error dùng sentinel "" (không phải None) cho "không lỗi"
        # — cùng quy ước `not item.error` ở registry.py dòng ~1671.
        assert not item.error, (item.slug, item.error)
