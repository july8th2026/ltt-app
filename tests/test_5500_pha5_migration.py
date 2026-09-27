"""tests/test_5500_pha5_migration.py — schema pha 5 dung hinh dang da khai.

Pha 5 (kho tai nguyen sau) them dung MOT migration cho ca pha (spec S9.1):
file_hash/favorite/rating tren ommi_resource_variant + bang ommi_trash +
bang ommi_image_job. Test nay chi kiem TRA SCHEMA chay that qua alembic
upgrade/downgrade tren mot SQLite tam - khong cham CSDL that.
"""
from __future__ import annotations

import subprocess
import sys

import pytest
from sqlalchemy import inspect, text


@pytest.fixture()
def db_url(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'pha5-migration.db').as_posix()}"
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    return url


def _run_alembic(*args, cwd=None):
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        capture_output=True, text=True, cwd=cwd)
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_upgrade_creates_pha5_shape(db_url):
    _run_alembic("upgrade", "head")
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    insp = inspect(engine)

    variant_cols = {c["name"] for c in insp.get_columns("ommi_resource_variant")}
    assert {"file_hash", "favorite", "rating"} <= variant_cols

    trash_cols = {c["name"] for c in insp.get_columns("ommi_trash")}
    assert {"id", "owner_id", "target_kind", "target_id", "payload",
            "deleted_at", "purge_after", "created_at"} <= trash_cols

    job_cols = {c["name"] for c in insp.get_columns("ommi_image_job")}
    assert {"id", "owner_id", "template_id", "resource_id", "params",
            "job_id", "version", "parent_id", "status",
            "created_at"} <= job_cols

    with engine.connect() as conn:
        conn.execute(text(
            "INSERT INTO ommi_resource_variant "
            "(id, resource_id, owner_id, label, storage_key, thumb_key, "
            " width, height, bytes_size, position, created_at) "
            "VALUES ('v1', 'r1', 'o1', '', 'k', '', 0, 0, 0, 0, "
            " CURRENT_TIMESTAMP)"))
        row = conn.execute(text(
            "SELECT favorite, rating, file_hash FROM ommi_resource_variant "
            "WHERE id = 'v1'")).one()
        assert row.favorite in (0, False)   # server_default=false
        assert row.rating is None
        assert row.file_hash is None


def test_downgrade_reverses_cleanly(db_url):
    _run_alembic("upgrade", "head")
    _run_alembic("downgrade", "-1")
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    insp = inspect(engine)
    assert "ommi_trash" not in insp.get_table_names()
    assert "ommi_image_job" not in insp.get_table_names()
    variant_cols = {c["name"] for c in insp.get_columns("ommi_resource_variant")}
    assert "file_hash" not in variant_cols


def test_upgrade_downgrade_upgrade_is_idempotent(db_url):
    """Chu ky upgrade -> downgrade -1 -> upgrade lai phai chay sach, khong
    con rang buoc/index mo coi tu lan upgrade truoc lam lan sau vo."""
    _run_alembic("upgrade", "head")
    _run_alembic("downgrade", "-1")
    _run_alembic("upgrade", "head")
    from sqlalchemy import create_engine
    engine = create_engine(db_url)
    insp = inspect(engine)
    variant_cols = {c["name"] for c in insp.get_columns("ommi_resource_variant")}
    assert {"file_hash", "favorite", "rating"} <= variant_cols
    assert "ommi_trash" in insp.get_table_names()
    assert "ommi_image_job" in insp.get_table_names()
