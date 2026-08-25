"""
P2 — ranh giới đường dẫn vận hành và hồ sơ môi trường.

Kiểm:
  - đường dẫn vận hành suy ra đúng kể cả khi chạy từ thư mục ngoài dự án
  - biến môi trường ghi đè được đường dẫn mặc định
  - `LTT_ENV` chọn đúng hồ sơ và **từ chối** giá trị lạ

## Vì sao tệp này ngắn đi một nửa (2026-08-25)

Nửa kia kiểm `load_settings()` — đọc `data/config.json`, kiểm phiên bản schema,
và soi `config.example.json` xem có giá trị giống khoá thật không. Cả ba đều đi
theo app socialbot khi app đó bị gỡ: `data/config.json` **là** cấu hình của nó
(Meta App ID, Sheet ID, tên cột, chống spam), và nền tảng nay không đọc tệp cấu
hình nào lúc khởi động.

⭐ Phần **còn lại** mới là phần đáng giữ nhất, và nó không liên quan gì tới
   socialbot: `resolve_runtime_paths` là thứ chặn lớp lỗi
   `os.path.join("data", ...)` — đường tương đối theo thư mục làm việc, mà trên
   máy chủ rơi vào `app\\data\\`, **thư mục bị xoá và thay toàn bộ mỗi lần cập
   nhật**. Mất phép kiểm này là mở lại một đường mất dữ liệu âm thầm.
   `AGENTS.md` mục 5.4 vẫn chốt quy tắc đó.
"""
from __future__ import annotations

import os

import pytest

from platform_core.runtime_paths import resolve_runtime_paths
from platform_core.settings import (
    Environment,
    UnknownEnvironmentError,
    resolve_environment,
)


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ─── runtime_paths ────────────────────────────────────────────────────────────

def test_default_paths_resolve_from_non_project_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # nothing project-related exists here
    paths = resolve_runtime_paths(env={})
    root = _project_root()
    assert paths.data_dir == os.path.join(root, "data")
    assert paths.secrets_dir == os.path.join(root, "secrets")


def test_env_vars_override_path_defaults(tmp_path):
    fake_env = {
        "LTT_DATA_DIR": str(tmp_path / "d"),
        "LTT_SECRETS_DIR": str(tmp_path / "s"),
        "LTT_LOGS_DIR": str(tmp_path / "l"),
        "LTT_TEMP_VIDEO_DIR": str(tmp_path / "t"),
    }
    paths = resolve_runtime_paths(env=fake_env)
    assert paths.data_dir == str(tmp_path / "d")
    assert paths.secrets_dir == str(tmp_path / "s")
    assert paths.logs_dir == str(tmp_path / "l")


def test_ensure_dirs_creates_data_logs_temp_but_not_secrets(tmp_path):
    fake_env = {
        "LTT_DATA_DIR": str(tmp_path / "d"),
        "LTT_SECRETS_DIR": str(tmp_path / "s"),
        "LTT_LOGS_DIR": str(tmp_path / "l"),
        "LTT_TEMP_VIDEO_DIR": str(tmp_path / "t"),
    }
    paths = resolve_runtime_paths(env=fake_env)
    paths.ensure_dirs()
    assert os.path.isdir(paths.data_dir)
    assert os.path.isdir(paths.logs_dir)
    assert os.path.isdir(paths.temp_video_dir)
    assert not os.path.exists(paths.secrets_dir)  # deployment/ACL concern, not ours


# ─── hồ sơ môi trường ─────────────────────────────────────────────────────────

def test_resolve_environment_defaults_to_development():
    assert resolve_environment(env={}) == Environment.DEVELOPMENT


@pytest.mark.parametrize("raw,expected", [
    ("development", Environment.DEVELOPMENT),
    ("local-server-test", Environment.LOCAL_SERVER_TEST),
    ("production", Environment.PRODUCTION),
    ("PRODUCTION", Environment.PRODUCTION),
])
def test_resolve_environment_known_values(raw, expected):
    assert resolve_environment(env={"LTT_ENV": raw}) == expected


def test_resolve_environment_rejects_unknown_value():
    """Giá trị lạ phải NÉM, không được lùi về `development`.

    Lùi về `development` là chỗ nguy hiểm nhất có thể lùi tới: nó bật tài liệu
    API tương tác, tắt cookie an toàn, và cho phép bịa khoá phiên tạm. Ba thứ
    đó không bao giờ được xảy ra vì một lỗi gõ phím trong biến môi trường.
    """
    with pytest.raises(UnknownEnvironmentError):
        resolve_environment(env={"LTT_ENV": "staging-typo"})


def test_khong_con_module_core(  ):
    """`core/` đã bị gỡ 2026-08-25 — và phải ở nguyên trạng thái đã gỡ.

    Đây là phép kiểm cùng loại với `test_52_desktop_removed`: xoá mã thì dễ,
    **giữ cho nó ở trạng thái đã xoá** mới khó. Một `core/` hồi sinh một nửa
    tệ hơn cả hai trạng thái, vì nó trông như dùng được rồi hỏng ở chỗ dùng.
    """
    import importlib

    for ten in ("core", "core.settings", "core.config_validator",
                "core.token_store", "core.sheet_runner", "utils.sheet_client"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(ten)
