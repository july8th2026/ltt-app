"""
vulkan_device.py — dịch card vật lý (nvidia-smi) sang chỉ số thiết bị **Vulkan** cho `-g`.

VÌ SAO CẦN: Vulkan đánh số thiết bị RIÊNG, do loader liệt kê, **không** trùng thứ tự
nvidia-smi và **không** chịu ảnh hưởng của CUDA_VISIBLE_DEVICES. Trước đây
`jobs._gpu_runtime()` lấy `GpuInfo.index` (chỉ số nvidia-smi) rồi truyền thẳng làm `-g`;
điều đó chỉ đúng khi máy có duy nhất một GPU và nó cũng là thiết bị Vulkan số 0.

SỰ CỐ THẬT 11/09/2026 trên chính máy chủ này: sau khi việc vẽ desktop được chuyển sang
iGPU Intel UHD 630, thứ tự Vulkan ĐẢO NGƯỢC. Engine liệt kê:

    [0 Intel(R) UHD Graphics 630]
    [1 NVIDIA GeForce RTX 5060 Ti]
    [2 Intel(R) UHD Graphics 630]

Lease vẫn cấp card NVIDIA (nvidia-smi index 0), nên `-g 0` lúc này trỏ vào **iGPU Intel**:
job upscale hoặc chạy cực chậm trên card onboard, hoặc chết — mà không có lỗi nào nói ra
điều đó. Cùng ngày, cấu hình 2 card cũng từng khiến một ánh xạ tĩnh ghim `-g 2` vào một
thiết bị không tồn tại, engine thoát mã 127 và không ghi ra tệp nào.

CÁCH LÀM: hỏi CHÍNH engine liệt kê thiết bị (nó in "[i Tên]  queueC=..." ở mọi lần chạy),
rồi so TÊN với card mà lease đã cấp.
  - đúng một thiết bị trùng tên  → dùng nó;
  - nhiều thiết bị trùng tên (máy nhiều card cùng model) → chỉ nhận khi có chỉ định tường
    minh qua biến môi trường LTT_VULKAN_INDEX, còn lại **FAIL CLOSED**;
  - không thấy tên đó           → FAIL CLOSED.
Thà job báo lỗi rõ còn hơn lặng lẽ chạy trên iGPU rồi giao kết quả chậm/hỏng cho khách.

Kết quả được nhớ theo tên card trong vòng đời tiến trình: đổi phần cứng hay đổi cấu hình
màn hình đều đòi khởi động lại dịch vụ, nên không có chuyện cache cũ còn sống.
"""
from __future__ import annotations

import logging
import os
import re
import struct
import subprocess
import tempfile
import zlib

from apps.upscalevideo import engine
from platform_core.i18n import _ as _t

log = logging.getLogger(__name__)

_DEV_LINE = re.compile(r"^\[(\d+) (.+?)\]\s+queueC=")
_ENV_OVERRIDE = "LTT_VULKAN_INDEX"
_PROBE_TIMEOUT_S = 60
_cache: dict[str, int] = {}


class VulkanDeviceError(RuntimeError):
    """Không xác định được thiết bị Vulkan ứng với card đã được cấp."""


def parse_devices(text: str) -> dict[int, str]:
    """{chỉ số Vulkan: tên thiết bị} đọc từ output của realesrgan-ncnn-vulkan."""
    out: dict[int, str] = {}
    for line in text.splitlines():
        found = _DEV_LINE.match(line.strip())
        if found:
            out.setdefault(int(found.group(1)), found.group(2).strip())
    return out


def pick_index(devices: dict[int, str], gpu_name: str, override: int | None = None) -> int:
    """Chỉ số Vulkan của card tên `gpu_name`. Mơ hồ hoặc không thấy → VulkanDeviceError."""
    ung_vien = sorted(i for i, ten in devices.items() if ten == gpu_name)
    if len(ung_vien) == 1:
        return ung_vien[0]
    if len(ung_vien) > 1:
        if override in ung_vien:
            return int(override)
        raise VulkanDeviceError(
            _t('Có {n} thiết bị Vulkan cùng tên "{ten}" ({ds}); đặt {bien} để chỉ rõ dùng cái nào.')
            .format(n=len(ung_vien), ten=gpu_name, ds=ung_vien, bien=_ENV_OVERRIDE))
    raise VulkanDeviceError(
        _t('Không thấy card "{ten}" trong danh sách thiết bị Vulkan của engine: {ds}')
        .format(ten=gpu_name, ds=devices))


def _tiny_png(path: str) -> None:
    """Ảnh xám 16x16 — đủ để engine khởi tạo Vulkan và in danh sách thiết bị."""
    rong = cao = 16
    tho = b"".join(b"\x00" + b"\x80\x80\x80" * rong for _ in range(cao))

    def khoi(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + khoi(b"IHDR", struct.pack(">IIBBBBB", rong, cao, 8, 2, 0, 0, 0))
           + khoi(b"IDAT", zlib.compress(tho))
           + khoi(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def probe_listing() -> str:
    """Chạy engine một lần trên ảnh 16x16 (không truyền -g) để lấy danh sách thiết bị."""
    with tempfile.TemporaryDirectory(prefix="ltt_vkprobe_") as thu_muc:
        vao = os.path.join(thu_muc, "in.png")
        ra = os.path.join(thu_muc, "out.png")
        _tiny_png(vao)
        ket_qua = subprocess.run(
            [str(engine._EXE), "-i", vao, "-o", ra, "-n", "realesr-general-x4v3", "-m", "models"],
            cwd=str(engine.engine_dir()), capture_output=True, text=True,
            errors="replace", timeout=_PROBE_TIMEOUT_S)
        return (ket_qua.stderr or "") + (ket_qua.stdout or "")


def _override() -> int | None:
    gia_tri = os.environ.get(_ENV_OVERRIDE, "").strip()
    if not gia_tri:
        return None
    try:
        return int(gia_tri)
    except ValueError:
        log.warning("[vulkan] %s=%r is not a number - ignored", _ENV_OVERRIDE, gia_tri)
        return None


def reset_cache() -> None:
    _cache.clear()


def vulkan_index_for(gpu_name: str) -> int:
    """Chỉ số Vulkan (`-g`) của card tên `gpu_name`, ví dụ "NVIDIA GeForce RTX 5060 Ti"."""
    if gpu_name not in _cache:
        thiet_bi = parse_devices(probe_listing())
        chi_so = pick_index(thiet_bi, gpu_name, _override())
        log.info("[vulkan] %r -> Vulkan device %d (engine listed: %s)",
                 gpu_name, chi_so, thiet_bi)
        _cache[gpu_name] = chi_so
    return _cache[gpu_name]
