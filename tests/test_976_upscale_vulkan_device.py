"""Chỉ số `-g` của NCNN là chỉ số VULKAN, không phải chỉ số nvidia-smi của lease.

Sự cố thật 11/09/2026 trên máy chủ: sau khi việc vẽ desktop chuyển sang iGPU Intel, engine
liệt kê [0]=Intel, [1]=RTX 5060 Ti, [2]=Intel (trước đó [0]=RTX, [1]=Intel). Lease vẫn cấp
card NVIDIA ở nvidia-smi index 0, nên `-g 0` trỏ vào iGPU → job upscale chạy nhầm card
onboard, hỏng ÂM THẦM (vẫn "chạy", chỉ chậm thảm hoặc chết giữa chừng).

Các danh sách thiết bị dưới đây là output THẬT của realesrgan-ncnn-vulkan trên máy đó.
"""
from __future__ import annotations

import pytest

from apps.upscalevideo import vulkan_device as vd

RTX = "NVIDIA GeForce RTX 5060 Ti"
INTEL = "Intel(R) UHD Graphics 630"

# Sau khi desktop sang iGPU (11/09/2026 21:09) — thứ tự ĐẢO so với trước đó.
LIET_KE_SAU_KHI_DOI = """\
[0 Intel(R) UHD Graphics 630]  queueC=0[1]  queueG=0[1]  queueT=0[1]
[0 Intel(R) UHD Graphics 630]  bugsbn1=0  bugbilz=92  bugcopc=0  bugihfa=0
[1 NVIDIA GeForce RTX 5060 Ti]  queueC=2[8]  queueG=0[16]  queueT=1[2]
[1 NVIDIA GeForce RTX 5060 Ti]  fp16-p/s/a=1/1/1  int8-p/s/a=1/1/1
[2 Intel(R) UHD Graphics 630]  queueC=0[1]  queueG=0[1]  queueT=0[1]
"""

# Trước khi đổi: RTX đứng trước.
LIET_KE_TRUOC_KHI_DOI = """\
[0 NVIDIA GeForce RTX 5060 Ti]  queueC=2[8]  queueG=0[16]  queueT=1[2]
[1 Intel(R) UHD Graphics 630]  queueC=0[1]  queueG=0[1]  queueT=0[1]
"""


def test_parse_lay_dung_mot_ten_cho_moi_thiet_bi():
    assert vd.parse_devices(LIET_KE_SAU_KHI_DOI) == {0: INTEL, 1: RTX, 2: INTEL}
    assert vd.parse_devices(LIET_KE_TRUOC_KHI_DOI) == {0: RTX, 1: INTEL}


def test_parse_bo_qua_dong_khong_phai_thiet_bi():
    assert vd.parse_devices("realesrgan-ncnn-vulkan\n12.50%\nvkAllocateMemory failed\n") == {}


def test_chon_dung_card_nvidia_sau_khi_thu_tu_dao():
    # Đây là ca đã làm hỏng production: chỉ số nvidia-smi 0, nhưng Vulkan phải là 1.
    assert vd.pick_index(vd.parse_devices(LIET_KE_SAU_KHI_DOI), RTX) == 1


def test_chon_dung_card_truoc_khi_doi():
    assert vd.pick_index(vd.parse_devices(LIET_KE_TRUOC_KHI_DOI), RTX) == 0


def test_khong_thay_card_thi_fail_closed():
    with pytest.raises(vd.VulkanDeviceError, match="RTX 4090"):
        vd.pick_index(vd.parse_devices(LIET_KE_SAU_KHI_DOI), "NVIDIA GeForce RTX 4090")


def test_nhieu_card_cung_ten_khong_co_chi_dinh_thi_fail_closed():
    devices = {0: INTEL, 1: RTX, 2: RTX}
    with pytest.raises(vd.VulkanDeviceError, match="2 thiết bị"):
        vd.pick_index(devices, RTX)


def test_nhieu_card_cung_ten_nhan_chi_dinh_hop_le():
    devices = {0: INTEL, 1: RTX, 2: RTX}
    assert vd.pick_index(devices, RTX, override=2) == 2
    # Chỉ định trỏ vào thiết bị KHÔNG phải card đó (0 = Intel) thì vẫn phải từ chối.
    with pytest.raises(vd.VulkanDeviceError):
        vd.pick_index(devices, RTX, override=0)


def test_cache_chi_do_engine_mot_lan(monkeypatch):
    so_lan = []

    def gia_lap_probe():
        so_lan.append(1)
        return LIET_KE_SAU_KHI_DOI

    monkeypatch.setattr(vd, "probe_listing", gia_lap_probe)
    vd.reset_cache()
    try:
        assert vd.vulkan_index_for(RTX) == 1
        assert vd.vulkan_index_for(RTX) == 1
        assert len(so_lan) == 1
    finally:
        vd.reset_cache()


def test_bien_moi_truong_chi_dinh_duoc_doc(monkeypatch):
    monkeypatch.setenv("LTT_VULKAN_INDEX", "2")
    assert vd._override() == 2
    monkeypatch.setenv("LTT_VULKAN_INDEX", "khong-phai-so")
    assert vd._override() is None
    monkeypatch.delenv("LTT_VULKAN_INDEX", raising=False)
    assert vd._override() is None


def test_tiny_png_hop_le(tmp_path):
    p = tmp_path / "t.png"
    vd._tiny_png(str(p))
    data = p.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert b"IHDR" in data and data.endswith(b"IEND\xaeB`\x82")
