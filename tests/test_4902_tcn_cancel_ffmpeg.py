"""Pha 0.3 — huỷ hợp tác render: giết cây tiến trình ffmpeg.

`BaseAdapter._run_command(cancel_check=...)` chạy lệnh qua Popen + poll 0.5s;
khi ``cancel_check()`` trả True → ``_giết_cay_tien_trinh`` (psutil →
``taskkill /T /F`` → ``proc.kill()``) rồi ném ``PipelineCancelledError``.
Test tự sinh tiến trình con (không đọc trạng thái máy), không cần ffmpeg.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psutil

from cutclipshort.adapters.base import BaseAdapter, _giết_cay_tien_trinh
from cutclipshort.errors import PipelineCancelledError

PY = sys.executable

# Lệnh "encode giả": sinh tiến trình con ngủ 60s, ghi pid ra file, đợi con.
# Dùng cho cả hai test — con-cháu phải chết khi cây bị giết.
_CMD_CODE = (
    "import subprocess, sys, time\n"
    "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
    "open({pidfile!r}, 'w').write(str(p.pid))\n"
    "p.wait()\n"
)


class _PythonAdapter(BaseAdapter):
    """Adapter giả dùng python.exe làm tool (không phụ thuộc ffmpeg)."""

    def __init__(self) -> None:
        super().__init__(PY)

    @property
    def tool_name(self) -> str:
        return "python"


def _cho_den_khi_mat_pid(pid: int, sau: float = 6.0) -> bool:
    han = time.monotonic() + sau
    while time.monotonic() < han:
        if not psutil.pid_exists(pid):
            return True
        time.sleep(0.2)
    return not psutil.pid_exists(pid)


def test_gieth_cay_gom_ca_con_chau(tmp_path):
    """Giết parent phải kéo theo cả tiến trình con (quan hệ cha-con)."""
    pidfile = tmp_path / "pid.txt"
    code = _CMD_CODE.format(pidfile=str(pidfile))
    proc = subprocess.Popen([PY, "-c", code])
    try:
        for _ in range(50):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            time.sleep(0.1)
        pid_con = int(pidfile.read_text().strip())
        assert psutil.pid_exists(pid_con), "chưa kịp sinh tiến trình con"
        _giết_cay_tien_trinh(proc)
    finally:
        proc.wait(timeout=10)
        pidfile.unlink(missing_ok=True)
    assert _cho_den_khi_mat_pid(pid_con), "con vẫn sống sau khi cây bị giết"


def test_run_command_huy_giet_con_va_nem_cancel(tmp_path):
    """cancel_check bật giữa chừng → PipelineCancelledError + tiến trình con chết."""
    ad = _PythonAdapter()
    pidfile = tmp_path / "pid.txt"
    code = _CMD_CODE.format(pidfile=str(pidfile))
    t0 = time.monotonic()
    try:
        ad._run_command([PY, "-c", code],
                        cancel_check=lambda: time.monotonic() - t0 > 1.5)
        raise AssertionError("phải ném PipelineCancelledError")
    except PipelineCancelledError:
        assert time.monotonic() - t0 < 15.0
    pid_con = int(pidfile.read_text().strip())
    assert _cho_den_khi_mat_pid(pid_con), "con vẫn sống sau khi huỷ"


def test_run_command_khong_huy_chay_den_khet():
    """cancel_check luôn False → lệnh chạy tới hết, trả CompletedProcess."""
    ad = _PythonAdapter()
    res = ad._run_command([PY, "-c", "import time; time.sleep(0.6); print('xong')"],
                          cancel_check=lambda: False)
    assert res.returncode == 0
    assert "xong" in (res.stdout or "")


def test_run_command_khong_cancel_check_giu_hanh_vi_cu():
    """Không có cancel_check → đường blocking y như trước (không đổi hành vi)."""
    ad = _PythonAdapter()
    res = ad._run_command([PY, "-c", "print('ok')"])
    assert res.returncode == 0
    assert "ok" in (res.stdout or "")


def test_encode_truyen_cancel_check_xuong_run_command(monkeypatch):
    """FFmpegAdapter.encode/encode_2pass truyền cancel_check tới _run_command."""
    from cutclipshort.adapters.ffmpeg import FFmpegAdapter

    ad = FFmpegAdapter(executable_path=PY)
    seen: dict = {}

    def _fake_run(self, args, **kw):
        seen.update(kw)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(FFmpegAdapter, "_run_command", _fake_run)
    ad.encode(input_path=Path("in.mp4"), output_path=Path("out.mp4"),
              cancel_check=lambda: True)
    assert callable(seen.get("cancel_check"))
    assert seen["cancel_check"]() is True

    seen.clear()
    ad.encode_2pass(input_path=Path("in.mp4"), output_path=Path("out.mp4"),
                    target_bitrate="2000k", cancel_check=lambda: True)
    assert callable(seen.get("cancel_check"))
    assert seen["cancel_check"]() is True
