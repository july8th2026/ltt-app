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


def cuda_dung_duoc() -> tuple[bool, str]:
    """Tiến trình NÀY có dùng được CUDA không, và nếu không thì vì sao.

    ⚠️ **`available()` và hàm này trả lời hai câu khác nhau**, và lẫn chúng đã
       tốn một buổi chẩn đoán (26/09/2026). `nvidia-smi` thấy card ⛔ KHÔNG có
       nghĩa tiến trình dùng được card:

           torch 2.11.0+cpu  ->  cuda.is_available() = False, device_count = 0

       Đo được ngày đó: `gpu_lease.acquire` VẪN cấp lease (vì `nvidia-smi` thấy
       card) ⇒ `ctx.has_gpu = True` ⇒ handler bật đường `--buoc-gpu` ⇒
       `demucs_runner` trả `{"thieu_card": true}` ⇒ giai đoạn hỏng trong ~0 giây
       ⇒ hoãn ⇒ **hoãn ⛔ không tính là một lần thử** ⇒ quay vòng vô hạn với CPU
       ≈ 0. Triệu chứng là *"treo"*, y hệt một lease bị rò — nên hai lỗi khác
       loại trông giống nhau và ai chẩn đoán cũng lẫn.

    ⭐ Fail-OPEN khi ⛔ không thấy `torch`: câu trả lời lúc đó là *"không biết"*,
       ⛔ không phải *"không dùng được"*. Một stack GPU không qua torch (ffmpeg
       NVENC, một sidecar có venv riêng) vẫn phải giành được card như trước.
       Hàm này chỉ ngăn ca ta ĐÃ ĐO được là hỏng chắc.

    ⚠️ Lần gọi đầu trong một tiến trình chưa nạp torch phải trả giá `import
       torch` (vài giây). ⛔ Không đệm kết quả: một tiến trình worker sống nhiều
       giờ có thể bị mất driver giữa đường, và một câu trả lời đệm từ lúc khởi
       động sẽ nói dối đúng lúc cần đúng.
    """
    import importlib.util
    try:
        if importlib.util.find_spec("torch") is None:
            return True, ""
    except Exception as e:                  # noqa: BLE001 - find_spec cũng ném được
        log.debug("gpu/cuda_dung_duoc: khong tra duoc torch: %s", e)
        return True, ""
    try:
        import torch
    except Exception as e:                  # noqa: BLE001
        # Cài dở dang (thiếu DLL) — ⛔ không kết luận được là card hỏng.
        log.debug("gpu/cuda_dung_duoc: khong import duoc torch: %s", e)
        return True, ""
    ban = str(getattr(torch, "__version__", "?"))
    try:
        if not torch.cuda.is_available():
            return False, f"torch {ban}: cuda.is_available() = False"
        so = int(torch.cuda.device_count())
    except Exception as e:                  # noqa: BLE001
        return False, f"torch {ban}: torch.cuda loi: {type(e).__name__}: {e}"
    if so <= 0:
        return False, f"torch {ban}: cuda.device_count() = 0"
    return True, ""


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


#: Giá trị `CUDA_VISIBLE_DEVICES` mà CUDA hiểu là "không card nào".
#:
#: 🔴 **Không dùng chuỗi rỗng.** Đo 24/09 (làn `gpu-may-a`): `""` truyền qua
#:    `subprocess` trên Windows bị **xoá hẳn** khỏi môi trường tiến trình con,
#:    nên tiến trình con thấy ĐỦ MỌI card và `torch.cuda.is_available()` trả
#:    True. Một nhánh "CPU" như thế **không có triệu chứng nào**: nó chạy trên
#:    card và báo `thiet_bi: cuda`. Cả một bảng so CPU↔GPU dựng trên `""` sẽ là
#:    GPU so với GPU, mọi tăng tốc ~1,0×, và kết luận sẽ là "card không giúp gì".
KHONG_CARD = "-1"


def env_khong_card(base: dict | None = None) -> dict:
    """Bản sao môi trường đã **che mọi GPU** khỏi tiến trình con.

    Dùng khi nền tảng **không** cấp card: che card đi thì một bộ đo không thể
    lặng lẽ lấy card ngoài sổ sách, và `gpu_lease` giữ được nghĩa của nó. Đối
    xứng với `env_for` — hai chiều của cùng một quyết định, nên nằm cùng một chỗ.
    """
    env = dict(os.environ if base is None else base)
    env["CUDA_VISIBLE_DEVICES"] = KHONG_CARD
    return env


def env_for(uuid: str, base: dict | None = None) -> dict:
    """Bản sao môi trường đã ghim tiến trình con vào đúng một GPU.

    Ghim bằng biến môi trường chứ không bằng `torch.cuda.set_device`: phần lớn
    việc nặng của nền tảng chạy trong **tiến trình con** (whisperx, ffmpeg,
    engine vendor) mà ta không sửa được mã nguồn bên trong.
    """
    env = dict(os.environ if base is None else base)
    env["CUDA_VISIBLE_DEVICES"] = visible_devices_value(uuid)
    return env
