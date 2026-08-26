"""Hồ sơ hệ thống phải đầy đủ, tái tạo được và không đọc dữ liệu runtime."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "ho_so_he_thong.txt"


def test_profile_is_current_and_utf8_without_bom():
    raw = PROFILE.read_bytes()
    assert raw and not raw.startswith(b"\xef\xbb\xbf")
    raw.decode("utf-8")
    done = subprocess.run(
        [sys.executable, "tools/build_system_profile.py", "--check"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stdout + done.stderr


def test_profile_covers_every_app_job_tool_migration_and_frontend():
    from platform_core.registry import discover
    from tools.system_profile.builder import migrations

    text = PROFILE.read_text(encoding="utf-8")
    for loaded in discover():
        assert f"[{loaded.slug}] {loaded.manifest.display_name}" in text
        for job_type in loaded.manifest.job_types:
            assert job_type in text
        for tool in loaded.manifest.tools:
            assert tool.name in text
    for migration in migrations():
        assert migration["revision"] in text
    for package in (ROOT / "frontend").glob("*/package.json"):
        assert package.parent.name in text
    assert "GET    /favicon.ico" in text
    assert "server/app.py:" in text


def test_profile_embeds_every_selected_source_once_without_size_limit():
    from tools.system_profile import source_files

    config = __import__("json").loads(
        (ROOT / "tools/system_profile_config.json").read_text(encoding="utf-8")
    )
    assert "max_bytes" not in config
    # ⛔ SUA 26/08 — bo `core`, `utils`, `scripts` khoi danh sach bat buoc.
    #    Ca ba thu muc do DA XOA cung app socialbot (Q108). `system_profile_config`
    #    da duoc cap nhat ngay luc do; phep kiem nay thi khong, nen no do o luot
    #    `pytest` day du dau tien chay sau dot xoa.
    #
    # ⭐ Them `sdk` — no CO trong config va la be mat khach lap trinh vien doc,
    #    nen no dang duoc nhung vao ho so va dang duoc chot o day.
    required_roots = {
        "alembic", "apps", "codex_sidecar", "cutclipshort", "deploy",
        "frontend", "platform_core", "sdk", "server", "setup", "tests",
        "tools",
    }
    assert required_roots.issubset(config["source_roots"])
    # `worker_main.py` DA XOA cung socialbot (Q108) — no la diem vao cua worker
    # dang bai FB/TikTok, khong phai worker job cua nen tang (`job_worker.py`).
    required_entrypoints = {
        "codex_sidecar_main.py", "job_worker.py", "requirements-whisperx.txt",
    }
    assert required_entrypoints.issubset(config["root_sources"])

    marker = "@@@LTT_PROFILE_FILE_BEGIN@@@ "
    text = PROFILE.read_text(encoding="utf-8")
    embedded = [line[len(marker):] for line in text.splitlines()
                if line.startswith(marker)]
    expected = [path.relative_to(ROOT).as_posix() for path in source_files()]
    assert embedded == expected
    assert len(embedded) == len(set(embedded))
    assert any(path.startswith("apps/") for path in embedded)
    assert any(path.startswith("platform_core/") for path in embedded)
    assert any(path.startswith("frontend/") for path in embedded)


def test_profile_source_blocks_have_original_byte_hashes():
    import hashlib

    from tools.system_profile import source_files

    marker = "@@@LTT_PROFILE_FILE_BEGIN@@@ "
    lines = PROFILE.read_text(encoding="utf-8").splitlines()
    metadata = {
        line[len(marker):]: lines[index + 1]
        for index, line in enumerate(lines[:-1])
        if line.startswith(marker)
    }
    for path in source_files():
        relative = path.relative_to(ROOT).as_posix()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert metadata[relative].startswith(f"SHA256={digest} ")


def test_profile_scope_excludes_runtime_and_secret_directories():
    from tools.system_profile import source_files

    forbidden = {"data", "secrets", "logs", "tmp", "test-results", "node_modules"}
    for path in source_files():
        relative = path.relative_to(ROOT)
        assert not forbidden.intersection(relative.parts), relative


def test_gate_checks_profile_freshness():
    from tools.gate import _steps

    names = {step.name for step in _steps(quick=True)}
    assert "system profile" in names
