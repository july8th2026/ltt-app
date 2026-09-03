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

    # ⛔ MOT dau — bat bien that, va la thu duy nhat o day khong duoc noi long.
    #    Hai dau nghia la alembic khong biet chay cai nao truoc.
    heads = scripts.get_heads()
    assert len(heads) == 1, heads

    # 🔴 **Hai phep chot cu da duoc go ngay 2026-09-03; ly do ghi lai o day.**
    #
    #    Ban dau cho nay chot rang migration `chatltt` vua la **dau chuoi** vua
    #    nam **ngay tren `c7b91e4a2f80`**:
    #
    #        assert "chatltt" in (rev.doc or "").lower() or rev.revision == "7d2c1e9f4a03"
    #        assert rev.down_revision == "c7b91e4a2f80"
    #
    #    Hai dieu do cung dung chi khi khong nhanh nao khac them migration. Khi
    #    `phien/asv-v4` gop vao, chuoi ASV cung tach ra tu chinh `c7b91e4a2f80`,
    #    va sau khi hop nhat mot trong hai chuoi buoc phai doi cho — luc do
    #    khong cach nao giu duoc ca hai phep chot.
    #
    # ⭐ Cai chung dinh chot la mot VI TRI, khong phai mot bat bien. Vi tri cua
    #    mot migration trong chuoi la ket qua cua thu tu gop, va no doi moi lan
    #    hai nhanh gap nhau. Thu dang chot: chuoi co dung MOT dau, migration cua
    #    chatltt CO trong chuoi va co moc, va len/xuong mot buoc thi sach — ba
    #    dieu do khong phu thuoc ai gop truoc.
    ma_chatltt = "7d2c1e9f4a03"
    trong_chuoi = {r.revision for r in scripts.walk_revisions()}
    assert ma_chatltt in trong_chuoi, "migration chatltt bien mat khoi chuoi"

    rev = scripts.get_revision(ma_chatltt)
    assert rev.down_revision, "migration chatltt khong moc vao dau ca"


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
