"""tests/test_5541_composite_version_revert_retry.py.

Ngoài ba test gốc của plan (retry/revert/quyền), thêm hai bất biến CẤU TRÚC
theo yêu cầu điều phối 27/09 — áp dạng "mọi lớp được tham chiếu phải tồn tại,
mọi lớp được khai phải được dùng" vào chuỗi version/parent của
`OmmiImageJob`:

1. **Tham chiếu tồn tại**: một chuỗi retry 3 lượt phải có version 1,2,3 KHÔNG
   lỗ KHÔNG trùng, và `parent_id` của mỗi lượt sau phải trỏ tới một hàng THẬT
   đã tồn tại trong CSDL (không phải một id treo).
2. **Không cột chết**: mọi cột `OmmiImageJob` ghi ra (`owner_id`,
   `template_id`, `resource_id`, `params`, `job_id`, `version`, `parent_id`,
   `status`) đều được ĐỌC LẠI và kiểm giá trị — một cột không ai đọc là một
   cột khách trả tiền để có mà không ai dùng (đúng dạng lỗi nợ D-2 của
   `ommi_binding.scene_id`).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _template():
    return SimpleNamespace(id="tpl1", prompt_text="Ve {SUBJECT}", n_outputs=1,
                          aspect="1:1", asset_type="prop", requires_ref=False,
                          multi_ref_max=1, negative_lock="")


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'composite-retry.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="retry-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")
    db.commit()
    yield db, user.id
    db.close()
    dbmod.reset_engine()


def test_retry_creates_a_new_version_linked_to_its_parent(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    first = composite.generate(db, template=_template(), resource_id=resource.id,
                              owner_id=owner_id, reference_variant_ids=[],
                              confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()

    retried = composite.retry(db, image_job_id=first["image_job_id"],
                              owner_id=owner_id, app_slug="prompt_ai_ommi")
    db.commit()

    assert retried["version"] == 2
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    child = db.get(OmmiImageJob, retried["image_job_id"])
    assert child.parent_id == first["image_job_id"]


def test_retry_chain_has_no_gap_or_duplicate_version_and_every_parent_resolves(db_session):
    """Bat bien CAU TRUC thay cho khang dinh HINH THUC: khong chi kiem
    version cuoi cung == 3, ma kiem CA CHUOI 1,2,3 khong lo khong trung, va
    moi parent_id la mot THAM CHIEU THAT (row ton tai trong CSDL)."""
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()

    first = composite.generate(db, template=_template(), resource_id=resource.id,
                              owner_id=owner_id, reference_variant_ids=[],
                              confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    second = composite.retry(db, image_job_id=first["image_job_id"],
                             owner_id=owner_id, app_slug="prompt_ai_ommi")
    db.commit()
    third = composite.retry(db, image_job_id=second["image_job_id"],
                            owner_id=owner_id, app_slug="prompt_ai_ommi")
    db.commit()

    chain_ids = [first["image_job_id"], second["image_job_id"], third["image_job_id"]]
    rows = [db.get(OmmiImageJob, i) for i in chain_ids]
    assert all(r is not None for r in rows), "mot mat xich trong chuoi khong ton tai"
    assert sorted(r.version for r in rows) == [1, 2, 3]
    # parent_id (tru lượt đầu) phải trỏ tới một hàng THẬT đã tồn tại.
    assert rows[1].parent_id == rows[0].id
    assert rows[2].parent_id == rows[1].id
    assert rows[0].parent_id is None


def test_every_written_column_of_ommi_image_job_is_exercised(db_session):
    """Khong cot nao cua OmmiImageJob la cot CHET (khai ma khong ai dung)."""
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    from apps.prompt_ai_ommi.tables import OmmiImageJob
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    variant = rsvc.add_variant(db, resource_id=resource.id, owner_id=owner_id,
                               storage_key="k9")
    db.commit()

    made = composite.generate(db, template=_template(), resource_id=resource.id,
                             owner_id=owner_id, reference_variant_ids=[variant.id],
                             confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    row = db.get(OmmiImageJob, made["image_job_id"])

    assert row.owner_id == owner_id
    assert row.template_id == "tpl1"
    assert row.resource_id == resource.id
    assert row.params["image_keys"] == ["k9"]
    assert row.job_id == made["job_id"]
    assert row.version == 1
    assert row.parent_id is None
    assert row.status == "queued"

    composite.revert(db, image_job_id=row.id, owner_id=owner_id)
    db.commit()
    assert db.get(OmmiImageJob, row.id).status == "reverted"


def test_revert_marks_the_image_job_as_reverted(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    made = composite.generate(db, template=_template(), resource_id=resource.id,
                             owner_id=owner_id, reference_variant_ids=[],
                             confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    composite.revert(db, image_job_id=made["image_job_id"], owner_id=owner_id)
    db.commit()

    from apps.prompt_ai_ommi.tables import OmmiImageJob
    assert db.get(OmmiImageJob, made["image_job_id"]).status == "reverted"


def test_retry_of_someone_elses_image_job_is_rejected(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    made = composite.generate(db, template=_template(), resource_id=resource.id,
                             owner_id=owner_id, reference_variant_ids=[],
                             confirmed=True, app_slug="prompt_ai_ommi")
    db.commit()
    with pytest.raises(rsvc.ResourceNotFound):
        composite.retry(db, image_job_id=made["image_job_id"],
                        owner_id="mallory", app_slug="prompt_ai_ommi")
