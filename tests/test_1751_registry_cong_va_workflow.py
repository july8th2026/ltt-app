"""Spec §4.5 — ToolSpec khai `cong` (ánh xạ cổng) và `workflow` (ẩn khỏi palette)."""
from __future__ import annotations

import inspect
import sys

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
    with pytest.raises(RegistryError, match="khoá lạ"):
        registry._validate_hop_dong_v2(_mf(), _tool(cong={"giua": {}}))


def test_cong_vao_tro_toi_tham_so_khong_co_thi_tu_choi():
    with pytest.raises(RegistryError, match="không có trong params_schema"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"vao": {"khong_ton_tai": "image"}}))


def test_cong_ra_tro_toi_khoa_returns_khong_co_thi_tu_choi():
    with pytest.raises(RegistryError, match="không có trong returns"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"ra": {"khong_ton_tai": "image"}}))


def test_kieu_cong_la_thi_tu_choi():
    with pytest.raises(RegistryError, match="kiểu cổng không hợp lệ"):
        registry._validate_hop_dong_v2(
            _mf(), _tool(cong={"vao": {"anh": "hinh_anh"}}))


def test_workflow_phai_la_bool():
    with pytest.raises(RegistryError, match="workflow phải là bool"):
        registry._validate_hop_dong_v2(_mf(), _tool(workflow="co"))


# --- Fix round 1: cạnh vế `cong` không phải dict (chuỗi / list) ---------


def test_cong_vao_la_chuoi_thi_tu_choi_khong_phai_crash():
    # Trước fix: `.items()` trên chuỗi ném AttributeError, không phải
    # RegistryError đặt tên app + tool.
    with pytest.raises(RegistryError, match=r"cong\['vao'\] phải là dict, nhận"):
        registry._validate_hop_dong_v2(_mf(), _tool(cong={"vao": "image"}))


def test_cong_ra_la_list_thi_tu_choi_khong_phai_crash():
    with pytest.raises(RegistryError, match=r"cong\['ra'\] phải là dict, nhận"):
        registry._validate_hop_dong_v2(_mf(), _tool(cong={"ra": ["out"]}))


# --- Fix round 1: chứng minh kiểm tra dùng vốn từ he_kieu thật, không phải
#     một tập cứng cục bộ (Task 1 thêm `any`/`event`, và `image[]` là tập hợp)


def test_cong_dung_kieu_any_qua_duoc():
    registry._validate_hop_dong_v2(_mf(), _tool(cong={"vao": {"prompt": "any"}}))


def test_cong_dung_kieu_event_qua_duoc():
    registry._validate_hop_dong_v2(_mf(), _tool(cong={"vao": {"prompt": "event"}}))


def test_cong_dung_kieu_tap_hop_image_qua_duoc():
    registry._validate_hop_dong_v2(_mf(), _tool(cong={"vao": {"anh": "image[]"}}))


# --- Fix round 1: `cong={}` (mặc định) không kéo import platform_core.workflow ---


def test_cong_rong_khong_nap_he_kieu():
    for mod in ("platform_core.workflow.he_kieu", "platform_core.workflow"):
        sys.modules.pop(mod, None)
    registry._validate_hop_dong_v2(_mf(), _tool())  # cong rỗng (mặc định)
    assert "platform_core.workflow.he_kieu" not in sys.modules


# --- Fix round 1: chú thích "Sáu trường" đã lỗi thời (tám trường) ---------


def test_khong_con_soi_sau_truong_da_thanh_tam():
    src = inspect.getsource(registry)
    assert "Sáu trường" not in src
    assert src.count("Tám trường") >= 2


def test_moi_toolspec_that_van_nap_duoc():
    # Đối chứng: tool thật vẫn qua bộ kiểm mới (mặc định không phá ai). Chặn
    # đối chứng rỗng: nếu discover() từng trả về [] thì vòng lặp dưới không
    # kiểm gì cả — cùng luật với tests/test_964_wf_toolspec_v2.py:52.
    items = registry.discover()
    assert len(items) >= 19, "kho that phai co it nhat 19 app (chan doi chung rong)"
    for item in items:
        # LoadedApp.error dùng sentinel "" (không phải None) cho "không lỗi"
        # — cùng quy ước `not item.error` ở registry.py dòng ~1671.
        assert not item.error, (item.slug, item.error)
