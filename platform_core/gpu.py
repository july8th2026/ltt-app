"""
gpu.py — máy có mấy GPU, cái nào còn chỗ. Dùng chung cho mọi app.

Vì sao nằm ở `platform_core`: từ 2026-08-06 máy chủ có **hai** RTX 5060 Ti.
Trước đó mỗi app tự hỏi `nvidia-smi` một kiểu, và cả hai chỗ đang có đều **chỉ
đọc dòng đầu** (`splitlines()[0]`) — đúng với một GPU, sai lặng lẽ với hai:
GPU thứ hai không bao giờ được nhìn thấy, mà cũng chẳng có lỗi nào báo ra.

⚠️ Module này CHỈ ĐỌC trạng thái. Nó **không** đủ để chia GPU giữa các worker.
Đọc "còn 16 GB trống" rồi quyết định là một cuộc đua kinh điển: hai worker cùng
đọc thấy trống, cùng chọn GPU 0, cùng nạp model, cùng OOM. Việc giành chỗ phải
đi qua `platform_core.gpu_lease` (khoá nguyên tử trong CSDL).

Neo GPU bằng **UUID** chứ không bằng index: index do driver đánh theo thứ tự bus
và **đổi khi cắm thêm/bớt card**. Một lease ghi "GPU 1" sẽ trỏ sang card khác
sau khi lắp thêm card; ghi UUID thì không.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)

# nvidia-smi treo được (driver lỗi, card kẹt). Worker không được đứng chờ vô hạn.
QUERY_TIMEOUT_S = 8

_FIELDS = ("index", "name", "uuid", "memory.total", "memory.free", "utilization.gpu")


@dataclass(frozen=True)
class GpuInfo:
    index: int
    name: str
    uuid: str
    total_mb: int
    free_mb: int
    util_pct: int

    @property
    def used_mb(self) -> int:
        return max(0, self.total_mb - self.free_mb)


def available() -> bool:
    """Máy này có `nvidia-smi` không. Máy không GPU là hợp lệ, không phải lỗi."""
    return shutil.which("nvidia-smi") is not None


def list_gpus() -> list[GpuInfo]:
    """Mọi GPU NVIDIA thấy được. Trả [] nếu máy không có GPU hoặc không hỏi được.

    Trả rỗng chứ không ném: máy phát triển không có GPU vẫn phải chạy được, và
    một sự cố `nvidia-smi` không được phép làm chết vòng lặp worker.
    """
    if not available():
        return []
    try:
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={','.join(_FIELDS)}",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=QUERY_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("nvidia-smi không chạy được (%s) — coi như máy không có GPU", exc)
        return []
    if out.returncode != 0:
        log.warning("nvidia-smi trả mã %s: %s", out.returncode, out.stderr.strip()[:200])
        return []

    gpus: list[GpuInfo] = []
    # Duyệt MỌI dòng. Đây chính là chỗ hai bản cũ đọc `[0]` và bỏ sót GPU thứ hai.
    for line in out.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(_FIELDS):
            log.warning("nvidia-smi trả dòng lạ, bỏ qua: %r", line[:120])
            continue
        try:
            gpus.append(GpuInfo(index=int(parts[0]), name=parts[1], uuid=parts[2],
                                total_mb=int(parts[3]), free_mb=int(parts[4]),
                                util_pct=int(parts[5])))
        except ValueError:
            log.warning("nvidia-smi trả số không đọc được, bỏ qua: %r", line[:120])
    return gpus


def by_uuid(uuid: str) -> GpuInfo | None:
    return next((g for g in list_gpus() if g.uuid == uuid), None)


def visible_devices_value(uuid: str) -> str:
    """Giá trị cho `CUDA_VISIBLE_DEVICES` để tiến trình con CHỈ thấy GPU này.

    Dùng UUID chứ không dùng số: nếu truyền "1" mà lúc đó driver đánh lại thứ
    tự thì tiến trình con chạy nhầm card đang bận. CUDA nhận thẳng chuỗi UUID.
    """
    return uuid


def env_for(uuid: str, base: dict | None = None) -> dict:
    """Bản sao môi trường đã ghim tiến trình con vào đúng một GPU.

    Ghim bằng biến môi trường chứ không bằng `torch.cuda.set_device`: phần lớn
    việc nặng của nền tảng chạy trong **tiến trình con** (whisperx, ffmpeg,
    engine vendor) mà ta không sửa được mã nguồn bên trong.
    """
    env = dict(os.environ if base is None else base)
    env["CUDA_VISIBLE_DEVICES"] = visible_devices_value(uuid)
    return env
