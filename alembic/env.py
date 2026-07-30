"""
Alembic environment.

Khác bản mẫu do `alembic init` sinh ra ở hai chỗ, cả hai đều có lý do:

1. **Chuỗi kết nối lấy từ `LTT_DATABASE_URL`, không từ `alembic.ini`.** Chuỗi
   đó chứa mật khẩu, mà `alembic.ini` nằm trong git.
2. **Thông báo lỗi được che mật khẩu.** Khi migration hỏng vì không kết nối
   được, thông báo của driver thường nhúng nguyên chuỗi kết nối — và người ta
   hay dán nguyên thông báo lỗi đó vào chat để hỏi.
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Cho phep `alembic` chay tu bat ky thu muc nao ma van import duoc goi cua du an.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from platform_core.db import Base, che_mat_khau, database_url  # noqa: E402
import platform_core.models  # noqa: E402,F401  — nap model de Base.metadata day du

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    try:
        return database_url()
    except Exception as exc:
        raise SystemExit(
            f"Khong chay duoc migration: {exc}\n"
            "Dat LTT_DATABASE_URL roi chay lai."
        ) from None


def run_migrations_offline() -> None:
    """Sinh SQL ra man hinh, khong ket noi CSDL.

    Dung khi nguoi quan tri CSDL muon xem truoc cau lenh se chay tren mot he
    thong that truoc khi cho phep.
    """
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chay migration truc tiep tren CSDL."""
    url = _url()
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = url

    try:
        connectable = engine_from_config(
            section, prefix="sqlalchemy.", poolclass=pool.NullPool)
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # Bat de autogenerate nhan ra ca viec doi KIEU cot, khong chi
                # them/bot cot. Thieu no, mot lan doi String(32) -> String(64)
                # se bi bo qua am tham.
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    except SystemExit:
        raise
    except Exception as exc:
        raise SystemExit(
            "Migration that bai: " + che_mat_khau(f"{type(exc).__name__}: {exc}")
        ) from None


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
