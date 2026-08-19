"""Nexus N3.3b — bản đóng gói agent giữ đúng ba lựa chọn chống Defender.

`N3_DONG_GOI_AGENT.md` §4b: one-dir (không one-file) và không UPX là hai thứ
làm giảm mạnh việc Defender xoá file, mà không tốn gì. Chúng dễ bị "sửa cho gọn"
thành one-file có UPX trong một lần dọn spec — nên khoá lại bằng test, vì hậu quả
(khách báo "phần mềm tự biến mất") chỉ hiện sau khi đã phát hành.

Test đọc **nội dung spec**, không chạy PyInstaller: build thật cần PyInstaller +
một máy Windows sạch, không có trong CI. Đây đúng là loại bất biến kiểm được
bằng cấu trúc.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "nexus_agent" / "packaging" / "nexus_agent.spec"


@pytest.fixture(scope="module")
def spec_src() -> str:
    assert SPEC.exists(), f"thieu spec {SPEC}"
    return SPEC.read_text(encoding="utf-8")


def test_khong_UPX(spec_src):
    """UPX = dau hieu gan co kinh dien. Moi cho co the UPX phai la False."""
    assert "upx=True" not in spec_src.replace(" ", "")
    # Phai co it nhat mot khai bao upx=False tuong minh (EXE va COLLECT).
    assert spec_src.replace(" ", "").count("upx=False") >= 2


def test_one_dir_khong_one_file(spec_src):
    """one-dir = co COLLECT + EXE dat exclude_binaries=True. one-file thi khong
    co COLLECT va EXE gom het binary."""
    assert "COLLECT(" in spec_src, "thieu COLLECT -> co the la one-file"
    compact = spec_src.replace(" ", "")
    assert "exclude_binaries=True" in compact, \
        "EXE phai exclude_binaries=True cho one-dir"


def test_khong_keo_GUI_hay_thu_vien_may_chu_vao_agent(spec_src):
    """Agent khach chi can danh tinh + HTTP + crypto. Keo tkinter/numpy vao la
    them be mat Defender soi va CVE phai va."""
    compact = spec_src.replace(" ", "").replace("'", "").replace('"', "")
    for cam in ("tkinter", "numpy", "pandas"):
        assert cam in compact.split("excludes=", 1)[1].split("]", 1)[0], \
            f"{cam} phai nam trong excludes"


def test_entry_point_la_main_cua_agent(spec_src):
    assert "__main__.py" in spec_src


def test_console_bat_de_doc_log_luc_chay(spec_src):
    """Agent chay `run` in log; an console thi loi luc chay bien mat khong dau."""
    assert "console=True" in spec_src.replace(" ", "")


# ── build script không kéo PyInstaller vào lúc import ────────────────────────

def test_build_script_import_duoc_khong_can_pyinstaller():
    """`tools/build_agent.py` phai import duoc tren may KHONG co PyInstaller —
    no la cong cu dung, khong phai phu thuoc may chu. Import-time keo PyInstaller
    vao se lam gate do tren may chu."""
    import importlib
    mod = importlib.import_module("tools.build_agent")
    assert hasattr(mod, "dung")


def test_thieu_pyinstaller_thi_bao_ro_chu_khong_stack_trace(monkeypatch):
    import builtins
    import tools.build_agent as ba

    that = builtins.__import__

    def gia(name, *a, **k):
        if name == "PyInstaller":
            raise ImportError("no module named PyInstaller")
        return that(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", gia)
    with pytest.raises(SystemExit) as ei:
        ba._kiem_pyinstaller()
    assert "pip install pyinstaller" in str(ei.value)
