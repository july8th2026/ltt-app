"""`tools/gate.py` phải phủ MỌI thứ cần chạy trước khi báo xong.

Vì sao có file này: trước 2026-08-06, `python -m pytest` không chạy test
frontend, nên "full regression xanh" bỏ sót 77 test vitest và người chạy gate
phải nhớ gõ thêm ba lệnh. Thêm một frontend thứ tư mà quên khai ở đây là lặp lại
đúng lỗ hổng đó — nên để test canh, đừng để trí nhớ canh.
"""
from __future__ import annotations

import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _frontends_on_disk() -> set[str]:
    folder = ROOT / "frontend"
    return {item.name for item in folder.iterdir()
            if item.is_dir() and (item / "package.json").exists()}


def test_gate_lists_every_frontend_that_exists():
    from tools.gate import FRONTENDS

    on_disk = _frontends_on_disk()
    missing = on_disk - set(FRONTENDS)
    assert missing == set(), (
        f"frontend chưa khai trong tools/gate.py: {sorted(missing)}")
    stale = set(FRONTENDS) - on_disk
    assert stale == set(), f"gate khai frontend không còn tồn tại: {sorted(stale)}"


def test_gate_runs_the_scanners_and_pytest():
    """Bốn thứ này là cổng tối thiểu; thiếu bất kỳ cái nào thì gate nói dối."""
    from tools.gate import _steps

    names = {step.name for step in _steps(quick=False)}
    assert "secret scan" in names
    assert "app contract lint" in names
    # Buoc nay bat loai loi test khong bat duoc: route khong co test ma thieu
    # import. Da tim thay mot cai that o POST /upscalevideo/queue (2026-08-06).
    assert "ten chua dinh nghia" in names
    assert "pytest" in names
    for frontend in _frontends_on_disk():
        assert f"frontend {frontend}" in names


def test_quick_mode_only_drops_pytest():
    """`--quick` để lặp nhanh, nhưng không được lặng lẽ bỏ luôn scanner."""
    from tools.gate import _steps

    full = {step.name for step in _steps(quick=False)}
    quick = {step.name for step in _steps(quick=True)}
    assert full - quick == {"pytest"}


def test_gate_reports_every_step_instead_of_stopping_at_the_first_failure():
    """Dừng ở lỗi đầu buộc người sửa chạy lại cả bộ để thấy lỗi thứ hai — với
    pytest 20 phút thì mỗi vòng mất nửa giờ."""
    source = (ROOT / "tools" / "gate.py").read_text(encoding="utf-8")
    assert "for step in steps:" in source
    # Không được thoát sớm giữa vòng chạy.
    run_loop = source.split("for step in steps:", 1)[1].split("print(\"\\n\"", 1)[0]
    assert "break" not in run_loop and "return" not in run_loop


@pytest.mark.parametrize("doc", ["CLAUDE.md", "AGENTS.md"])
def test_the_gate_command_is_documented(doc):
    """Một lệnh gate mà không ai biết là không tồn tại."""
    text = (ROOT / doc).read_text(encoding="utf-8")
    assert "tools/gate.py" in text or "tools\\gate.py" in text, (
        f"{doc} chưa nhắc tới tools/gate.py")
