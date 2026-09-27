"""nhap_mau_goc.nhap() - phai idempotent (R-3, spec S8.1: 'idempotent theo
(target_format, name)'; snippet/image_template/storyboard_framework dung khoa
rieng vi khong co target_format hoac khong dung co che owner_id NULL — xem
docstring services/nhap_mau_goc.py).

Dai so: 5420-5449 (Lan G).
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'nmg.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    session = next(dbmod.get_session())
    yield session
    session.close()
    dbmod.reset_engine()


def test_first_import_inserts_everything(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import (
        OmmiMetaPrompt, OmmiPromptSnippet, OmmiImageTemplate,
        OmmiStoryboardFramework)
    summary = nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    assert summary["meta_prompt"] == {"them": 12, "bo_qua": 0}
    assert summary["snippet"] == {"them": 13, "bo_qua": 0}
    assert summary["image_template"] == {"them": 21, "bo_qua": 0}
    assert summary["storyboard_framework"] == {"them": 5, "bo_qua": 0}

    assert db.query(OmmiMetaPrompt).count() == 12
    assert db.query(OmmiPromptSnippet).count() == 13
    assert db.query(OmmiImageTemplate).count() == 21
    assert db.query(OmmiStoryboardFramework).count() == 5


def test_second_import_is_a_no_op(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    summary = nsvc.nhap(db, admin_owner_id="admin-2")
    db.commit()
    assert summary["meta_prompt"] == {"them": 0, "bo_qua": 12}
    assert summary["snippet"] == {"them": 0, "bo_qua": 13}
    assert summary["image_template"] == {"them": 0, "bo_qua": 21}
    assert summary["storyboard_framework"] == {"them": 0, "bo_qua": 5}
    assert db.query(OmmiMetaPrompt).count() == 12


def test_imported_meta_prompts_are_catalog_owned_by_no_one(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    anh_thang = db.query(OmmiMetaPrompt).filter_by(name="Anh Thang").one()
    assert anh_thang.owner_id is None
    assert anh_thang.is_catalog is True
    assert anh_thang.share_level == "catalog"
    assert anh_thang.is_default is True
    assert anh_thang.target_format == "gemini_style"


def test_imported_image_templates_are_owned_by_the_importing_admin(db):
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    row = db.query(OmmiImageTemplate).filter_by(
        name="\U0001F464 Nhân vật — Chỉ nhân vật (8 góc)").one()
    assert row.owner_id == "admin-1"
    assert row.is_builtin is True
    assert row.share_level == "catalog"
    # placeholders duoc tu suy tu prompt_text luc nhap (khong phai "cot chet")
    assert "SUBJECT" in row.placeholders


def test_second_import_after_user_edit_keeps_user_edit(db):
    """Ca 'chay lan hai sau khi nguoi dung da sua mot muc' — ban sua cua ho
    phai con nguyen (khong bi ghi de bang gia tri goc, khong bi xoa di tao
    lai). Day la vi sao khoa idempotent la SELECT-roi-bo-qua, khong phai
    upsert/merge theo khoa tu nhien."""
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import OmmiMetaPrompt
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()

    row = db.query(OmmiMetaPrompt).filter_by(name="Anh Thang").one()
    row.body = "NOI DUNG DA BI NGUOI DUNG SUA TAY"
    db.commit()
    sua_id = row.id

    nsvc.nhap(db, admin_owner_id="admin-2")
    db.commit()

    lai = db.query(OmmiMetaPrompt).filter_by(name="Anh Thang").one()
    assert lai.id == sua_id, "khong duoc tao ban ghi thu hai cho cung ten"
    assert lai.body == "NOI DUNG DA BI NGUOI DUNG SUA TAY", (
        "ban sua cua nguoi dung phai con nguyen sau lan nhap thu hai")


def test_running_twice_in_a_row_does_not_duplicate_rows(db):
    """Idempotent doi hoi chinh xac: chay HAI LUOT LIEN TIEP roi so tong so
    hang khong tang them (khong chi so summary bao cao dung)."""
    from apps.prompt_ai_ommi.services import nhap_mau_goc as nsvc
    from apps.prompt_ai_ommi.tables import (
        OmmiMetaPrompt, OmmiPromptSnippet, OmmiImageTemplate,
        OmmiStoryboardFramework)
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    truoc = (db.query(OmmiMetaPrompt).count(), db.query(OmmiPromptSnippet).count(),
              db.query(OmmiImageTemplate).count(),
              db.query(OmmiStoryboardFramework).count())
    nsvc.nhap(db, admin_owner_id="admin-1")
    db.commit()
    sau = (db.query(OmmiMetaPrompt).count(), db.query(OmmiPromptSnippet).count(),
           db.query(OmmiImageTemplate).count(),
           db.query(OmmiStoryboardFramework).count())
    assert truoc == sau == (12, 13, 21, 5)
