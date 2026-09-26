"""Ve giao bai: dung MOT lan, het han 30 phut (spec Pha 2 Sec 4.2)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture()
def bienh(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'hs-ticket.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    db = next(dbmod.get_session())
    yield db
    db.close()
    dbmod.reset_engine()


def _payload():
    return {"prompt": "xin chao", "params": {"model": "seedance-2.0-mini"},
            "refs": [], "tag_map": {}, "skipped": [], "skipped_over_limit": 0}


def test_doc_lan_hai_bi_tu_choi(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1",
                   payload=_payload())
    db.commit()

    row = hs.tim_ve(db, ve.id)
    lan_mot = hs.doc_va_tieu_ve(db, row)
    db.commit()
    assert lan_mot["prompt"] == "xin chao"

    row_lai = hs.tim_ve(db, ve.id)
    assert row_lai.used_at is not None
    with pytest.raises(hs.VeDaDung):
        hs.doc_va_tieu_ve(db, row_lai)


def test_ve_khong_ton_tai_tra_none(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    assert hs.tim_ve(db, "khong-ton-tai") is None
    with pytest.raises(hs.VeKhongHopLe):
        hs.doc_va_tieu_ve(db, None)


def test_ve_het_han_bi_tu_choi(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    from apps.prompt_ai_ommi.tables import OmmiHandoff
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1",
                   payload=_payload())
    db.commit()
    row = db.get(OmmiHandoff, ve.id)
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    row_lai = hs.tim_ve(db, ve.id)
    with pytest.raises(hs.VeHetHan):
        hs.doc_va_tieu_ve(db, row_lai)
    # Het han thi KHONG duoc tieu ve: neu tieu, mot lan tinh sai gio se bien
    # mot ve con song thanh ve chet vinh vien.
    assert hs.tim_ve(db, ve.id).used_at is None


def test_han_mac_dinh_dung_ba_muoi_phut(bienh):
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    truoc = datetime.now(timezone.utc)
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1",
                   payload=_payload())
    db.commit()
    assert hs.VE_HET_HAN_PHUT == 30
    con_lai = hs._co_mui_gio(ve.expires_at) - truoc
    assert timedelta(minutes=29) < con_lai <= timedelta(minutes=30, seconds=5)
    assert ve.target_app_slug == "taovideo"


def test_moc_gio_khong_mui_khong_lam_no_type_error(bienh):
    """SQLite tra `datetime` naive du cot khai `timezone=True`.

    So naive voi aware nem `TypeError` — mot 500 chi xuat hien tren SQLite,
    KHONG tren Postgres production. Day la doi chung cho `_co_mui_gio()`.
    """
    db = bienh
    from apps.prompt_ai_ommi.services import handoff_stage as hs
    ve = hs.tao_ve(db, project_id="proj_1", scene_id="scene_1",
                   payload=_payload())
    db.commit()
    ve.expires_at = datetime.now() + timedelta(minutes=10)  # naive, co y
    assert hs.doc_va_tieu_ve(db, ve)["prompt"] == "xin chao"
