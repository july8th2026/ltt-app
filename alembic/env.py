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
from platform_core.registry import load_app_tables  # noqa: E402

# App co bang rieng khai model o apps/<slug>/tables.py. Khong nap o day thi
# autogenerate coi chung la bang la va sinh migration XOA chung.
load_app_tables()

config = context.config

if config.config_file_name is not None:
    # ⛔ `disable_existing_loggers=False` LA BAT BUOC, khong phai tuy chon.
    #
    #    `fileConfig` mac dinh la True, va True o day nghia la: moi logger DA
    #    duoc tao truoc luc nay bi dat `disabled = True` — **vinh vien**, khong
    #    khoi phuc, khong mot dong canh bao.
    #
    # 🔴 Do 03/09. `alembic upgrade` chay trong tien trinh (test_616) tat
    #    `platform_core.job_runner`, va phep kiem chong ro bi mat cua worker
    #    (`test_67`) do vi `caplog.text` RONG — no khong bat duoc mot canh bao
    #    ma logger da bi tat khong bao gio phat ra. Phep kiem do XANH khi chay
    #    mot minh; no chi do khi mot tep khac tao logger truoc, roi migration
    #    chay sau. Ba tep, ba thu muc, khong lien quan gi nhau.
    #
    # ⭐ Nhung cai gia thuc su khong nam o bo test. Bat ky ai nhung alembic vao
    #    mot tien trinh dang song — mot script bao tri, mot lenh quan tri, mot
    #    worker tu migrate — deu lam CA tien trinh do cam tieng tu do tro di.
    #    Migration khong duoc quyen tat log cua ung dung chu nha.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

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
