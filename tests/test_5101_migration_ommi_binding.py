"""Migration ommi_binding — pha 1 (spec Sec 4.2).

Ba bai dau doc VAN BAN revision (tra loi "nguoi viet da viet gi"). Bai cuoi
CHAY THAT len/xuong/len tren mot CSDL SQLite tam (tra loi "thu da viet co
chay duoc khong") — cung khuon tests/test_1729_migration_go_agent_runs.py.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

GOC = pathlib.Path(__file__).resolve().parent.parent


def _scripts() -> ScriptDirectory:
    cfg = Config(str(GOC / "alembic.ini"))
    cfg.set_main_option("script_location", str(GOC / "alembic"))
    return ScriptDirectory.from_config(cfg)


@pytest.fixture(scope="module")
def rev():
    ds = [s for s in _scripts().walk_revisions() if "ommi_binding" in (s.path or "")]
    assert ds, "chua co migration ommi_binding"
    return ds[0]


@pytest.fixture(scope="module")
def nguon(rev) -> str:
    return pathlib.Path(rev.path).read_text(encoding="utf-8")


def test_la_mot_head_duy_nhat(rev):
    scripts = _scripts()
    heads = list(scripts.get_heads())
    assert len(heads) == 1, f"phai co dung mot dau, dang co {heads}"
    to_tien = {s.revision for s in scripts.iterate_revisions(heads[0], "base")}
    assert rev.revision in to_tien


def test_upgrade_tao_bang_du_cot(nguon):
    than = nguon.split("def upgrade()")[1].split("def downgrade()")[0]
    assert (re_search := __import__("re").search(r'create_table\(\s*"ommi_binding"', than))
    for cot in ("id", "owner_id", "project_id", "scene_id", "tag", "kind",
                "variant_id", "position", "role", "created_at"):
        assert f'"{cot}"' in than, f"upgrade thieu cot {cot}"
    assert "uq_ommi_binding_tag" in than


def test_downgrade_drop_bang(nguon):
    than = nguon.split("def downgrade()")[1]
    assert "drop_table" in than and "ommi_binding" in than


def test_LEN_XUONG_LEN_chay_that_tren_sqlite(tmp_path, rev):
    import os

    db = tmp_path / "ommi_binding.db"
    env = dict(os.environ)
    env["LTT_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    env["PYTHONPATH"] = str(GOC)

    def alembic(*args: str) -> None:
        ra = subprocess.run([sys.executable, "-m", "alembic", *args],
                            cwd=str(GOC), env=env, capture_output=True, text=True)
        assert ra.returncode == 0, f"alembic {' '.join(args)} -> {ra.returncode}\n{ra.stderr[-2000:]}"

    def co_bang() -> bool:
        import sqlalchemy as sa
        e = sa.create_engine(f"sqlite:///{db.as_posix()}")
        try:
            with e.connect() as c:
                return bool(c.execute(sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='ommi_binding'")).first())
        finally:
            e.dispose()

    alembic("upgrade", "head")
    assert co_bang(), "sau upgrade phai co bang ommi_binding"

    import sqlalchemy as sa
    e = sa.create_engine(f"sqlite:///{db.as_posix()}")
    try:
        with e.begin() as c:
            c.execute(sa.text(
                "INSERT INTO ommi_binding (id, owner_id, project_id, scene_id, "
                "tag, kind, variant_id, position, role, created_at) VALUES "
                "('b1','u1','p1','s1','@IMAGE_1','image','v1',1,"
                "'reference_image','2026-09-26 10:00:00')"))
            row = c.execute(sa.text(
                "SELECT tag, kind, position FROM ommi_binding")).first()
            assert row == ("@IMAGE_1", "image", 1)
    finally:
        e.dispose()

    alembic("downgrade", str(rev.down_revision))
    assert not co_bang(), "downgrade phai XOA bang ommi_binding"

    alembic("upgrade", "head")
    assert co_bang(), "len lai lan hai phai tao lai bang"
