"""`run` / `probe_duration` — chữ ký của `bot_dungvideo/utils/ffmpeg.py`.

⚠️ `probe_duration` **ném** khi không đọc được, **không** trả 0. Một thời lượng
   0 trôi xuống bộ dựng dòng thời gian cho ra một video rỗng mà không báo lỗi —
   tệp vẫn hợp lệ, vẫn mở được, chỉ là không có gì trong đó.
"""
from __future__ import annotations

import subprocess


class LoiFFmpeg(RuntimeError):
    """ffmpeg/ffprobe trả mã khác 0, hoặc trả thứ không đọc được."""


def run(cmd: list, show_output: bool = True, timeout: float = 1800):
    """Chạy một lệnh ffmpeg/ffprobe. Ném `LoiFFmpeg` khi mã trả về khác 0.

    ⛔ Giữ nguyên chữ ký ba tham số của bản legacy: 29 tệp engine gọi hàm này,
       và đổi chữ ký sẽ làm chúng hỏng **lúc chạy**, không phải lúc nạp.
    """
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise LoiFFmpeg(
            f"{cmd[0]} tra {r.returncode}: {(r.stderr or '')[-500:]}")
    return r


def probe_duration(duong: str) -> float:
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", duong],
            show_output=False, timeout=120)
    try:
        return float((r.stdout or "").splitlines()[0])
    except (ValueError, IndexError) as e:
        raise LoiFFmpeg(
            f"ffprobe tra ve khong phai so: {(r.stdout or '')[:80]!r}") from e
