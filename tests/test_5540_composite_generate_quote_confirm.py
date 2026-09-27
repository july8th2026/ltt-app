"""tests/test_5540_composite_generate_quote_confirm.py.

⚠️ Placeholder dùng ĐÚNG bộ thật của 21 image template (đo trên CSDL, spec
Sec 7.2): SUBJECT/STYLE/EXTRA/EQUIPMENT — ⛔ KHÔNG phải {NAME}/{ASSET_TYPE}
như bản nháp đầu của plan (đã báo cáo lại, xem báo cáo làm I).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _template(**over):
    base = dict(id="tpl1",
               prompt_text="Ve {SUBJECT} phong cach {STYLE} {EXTRA} {EQUIPMENT}",
               n_outputs=2, aspect="1:1", asset_type="character",
               requires_ref=True, multi_ref_max=2, negative_lock="khong mau")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'composite.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="composite-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")
    db.commit()
    yield db, user.id
    db.close()
    dbmod.reset_engine()


def test_quote_never_creates_a_job(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    db.commit()

    result = composite.quote(db, template=_template(), resource_id=resource.id,
                            owner_id=owner_id, reference_variant_ids=[])
    assert result["credit"] > 0

    from platform_core.models import Job
    assert db.query(Job).filter(Job.user_id == owner_id).count() == 0


def test_quote_substitutes_the_real_placeholder_set_not_dropping_extra_equipment(db_session):
    """SUBJECT lay tu resource, STYLE/EXTRA/EQUIPMENT la o nguoi dung go tay
    (dieu phoi da phan quyet: chi kiem cu phap, khong kiem nguon gia tri)."""
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="Ong gia",
                          prompt_text="mot ong gia toc bac")
    db.commit()

    result = composite.quote(
        db, template=_template(requires_ref=False), resource_id=resource.id,
        owner_id=owner_id, reference_variant_ids=[],
        extra="them mot chiec non", equipment="kiem go", style_body="tranh son dau")
    assert result["credit"] > 0


def test_requires_ref_template_rejects_generation_without_any_reference(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    db.commit()
    with pytest.raises(ValueError, match="anh tham chieu"):
        composite.generate(db, template=_template(requires_ref=True),
                           resource_id=resource.id, owner_id=owner_id,
                           reference_variant_ids=[], confirmed=True,
                           app_slug="prompt_ai_ommi")


def test_confirmed_generate_submits_taoanh_job_and_records_image_job(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="character", name="A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner_id,
                               storage_key="k1")
    db.commit()

    result = composite.generate(
        db, template=_template(), resource_id=resource.id, owner_id=owner_id,
        reference_variant_ids=[variant.id], confirmed=True,
        app_slug="prompt_ai_ommi")
    db.commit()

    from platform_core.models import Job
    job = db.query(Job).filter(Job.user_id == owner_id).one()
    assert job.job_type == "taoanh.generate"
    assert job.params["image_keys"] == ["k1"]

    from apps.prompt_ai_ommi.tables import OmmiImageJob
    image_job = db.get(OmmiImageJob, result["image_job_id"])
    assert image_job.version == 1
    assert image_job.parent_id is None
    assert image_job.template_id == "tpl1"
