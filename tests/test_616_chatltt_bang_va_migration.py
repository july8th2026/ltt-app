"""
test_616 — Phase 07: bảng `chatltt_*` + migration Alembic lên/xuống sạch, một head.
"""
from __future__ import annotations

import pytest


def test_ba_bang_mang_dung_tien_to_va_registry_nap_duoc():
    from platform_core.db import Base
    from platform_core.registry import load_app_tables

    da_nap = load_app_tables()
    assert "chatltt" in da_nap
    ten = {t for t in Base.metadata.tables if t.startswith("chatltt_")}
    assert ten == {"chatltt_conversation", "chatltt_message", "chatltt_execution"}


def test_alembic_mot_head_va_migration_chatltt_noi_dung_chuoi():
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = scripts.get_heads()
    assert len(heads) == 1, heads
    rev = scripts.get_revision(heads[0])
    assert "chatltt" in (rev.doc or "").lower() or rev.revision == "7d2c1e9f4a03"
    assert rev.down_revision == "c7b91e4a2f80"


@pytest.mark.timeout(240)
def test_upgrade_head_roi_downgrade_mot_buoc_sach(tmp_path, monkeypatch):
    """Lên head tạo đủ ba bảng; xuống một bước xoá đúng ba bảng, không sót index."""
    from sqlalchemy import create_engine, inspect

    url = "sqlite:///" + (tmp_path / "mig.db").as_posix()
    monkeypatch.setenv("LTT_DATABASE_URL", url)
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    insp = inspect(create_engine(url))
    bang = set(insp.get_table_names())
    assert {"chatltt_conversation", "chatltt_message", "chatltt_execution"} <= bang
    idx = {i["name"] for i in insp.get_indexes("chatltt_message")}
    assert {"ix_chatltt_msg_conv_parent", "ix_chatltt_msg_conv_created"} <= idx

    command.downgrade(cfg, "-1")
    insp = inspect(create_engine(url))
    bang2 = set(insp.get_table_names())
    assert not {t for t in bang2 if t.startswith("chatltt_")}
    assert (bang - bang2) == {"chatltt_conversation", "chatltt_message", "chatltt_execution"}
