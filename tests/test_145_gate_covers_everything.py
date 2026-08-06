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


def test_banh_coc_nuot_loi_khong_cho_tang_them():
    """Không đòi 0 ngay (90 chỗ trong mã sống là một đợt sửa lớn, rủi ro cao,
    giá trị từng chỗ thấp) — nhưng tuyệt đối không được thêm chỗ mới."""
    import json
    import subprocess
    import sys

    moc = json.loads((ROOT / "tools" / "silent_except_baseline.json")
                     .read_text(encoding="utf-8"))["max"]
    r = subprocess.run([sys.executable, "tools/check_silent_except.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"số chỗ nuốt lỗi đã tăng quá mốc {moc}:\n{r.stdout}"


def test_phep_do_nuot_loi_khong_tinh_nham_cho_da_xu_ly_dung():
    """Handler biến ngoại lệ thành GIÁ TRỊ nhìn thấy được thì không phải nuốt.

    Thiếu điều kiện này, phép đo đếm thừa gấp đôi ở `platform_core` (18 thay vì
    8) và sẽ dẫn người đọc đi "sửa" những chỗ vốn đã đúng — như
    `registry.py` ghi lỗi vào `LoadedApp.error` để trang admin hiển thị.
    """
    import ast
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    from check_silent_except import _co_dung_ngoai_le

    def _handler(src):
        return next(n for n in ast.walk(ast.parse(src))
                    if isinstance(n, ast.ExceptHandler))

    nuot = _handler("try:\n    x()\nexcept Exception:\n    y = 1\n")
    xu_ly = _handler("try:\n    x()\nexcept Exception as exc:\n    ghi(str(exc))\n")
    bat_ten_khong_dung = _handler("try:\n    x()\nexcept Exception as exc:\n    y = 1\n")

    assert _co_dung_ngoai_le(nuot) is False
    assert _co_dung_ngoai_le(xu_ly) is True, "chỗ đã xử lý đúng bị tính là nuốt lỗi"
    assert _co_dung_ngoai_le(bat_ten_khong_dung) is False, (
        "đặt tên cho ngoại lệ rồi bỏ đó vẫn là nuốt")


def test_platform_core_khong_con_cho_nuot_loi_nao():
    """Tầng nền tảng là chỗ mọi app đi qua — lỗi biến mất ở đây là tệ nhất."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "tools/check_silent_except.py", "--list"],
                       cwd=ROOT, capture_output=True, text=True)
    con = [l.strip() for l in r.stdout.splitlines() if "platform_core/" in l]
    assert not con, f"platform_core còn nuốt lỗi lặng lẽ: {con}"
