"""tests/test_5542_composite_placeholder_invariants.py.

Bất biến điều phối yêu cầu 27/09 cho Task 9: "mọi `{TEN}` trong `prompt_text`
phải nằm trong tập placeholder đã khai" — DÙNG LẠI
`services/placeholders.py::kiem_placeholder` của pha 3 (⛔ không viết bộ kiểm
thứ hai), kèm tiêm lỗi: thêm một `{TEN_KHONG_CO_THAT}` phải làm quote() ĐỎ.

Không cần OmmiImageJob (Task 2) — `quote()` không bao giờ chạm bảng đó, nên
cả ba test dưới đây chạy được kể cả khi Task 2 chưa xong.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _template(prompt_text, **over):
    base = dict(id="tpl-syntax", prompt_text=prompt_text, n_outputs=1,
               aspect="1:1", asset_type="prop", requires_ref=False,
               multi_ref_max=1, negative_lock="")
    base.update(over)
    return SimpleNamespace(**base)


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'composite-ph.db').as_posix()}")
    import platform_core.db as dbmod
    import platform_core.models  # noqa: F401
    from platform_core.registry import load_app_tables
    load_app_tables()
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    from platform_core import credit
    db = next(dbmod.get_session())
    from platform_core.users import tao_nguoi_dung
    user = tao_nguoi_dung(db, email="ph-a@example.com",
                          password="Strong-pass-123", is_verified=True)
    credit.cap_tay(db, user.id, 200, by="test")
    db.commit()
    yield db, user.id
    db.close()
    dbmod.reset_engine()


def test_known_placeholder_names_pass_syntax_check(db_session):
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    result = composite.quote(
        db, template=_template("Ve {SUBJECT} {STYLE} {EXTRA} {EQUIPMENT}"),
        resource_id=resource.id, owner_id=owner_id, reference_variant_ids=[])
    assert result["credit"] > 0


def test_unknown_placeholder_name_is_rejected_injected_error(db_session):
    """TIÊM LỖI bắt buộc: một tên KHÔNG có thật trong tập đã khai phải làm
    `quote()` ĐỎ ngay — đây chính là phép do điều phối yêu cầu thêm."""
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    with pytest.raises(ValueError, match="TEN_KHONG_CO_THAT"):
        composite.quote(
            db, template=_template("Ve {SUBJECT} o {TEN_KHONG_CO_THAT}"),
            resource_id=resource.id, owner_id=owner_id,
            reference_variant_ids=[])


def test_prompt_without_any_placeholder_is_not_flagged_as_invalid(db_session):
    """Đối chứng: một `prompt_text` KHÔNG dùng placeholder nào vẫn phải hợp
    lệ — nếu không, phép kiểm trên đang bắt nhầm "không dùng" thành "sai"."""
    from apps.prompt_ai_ommi.services import composite, resources as rsvc
    db, owner_id = db_session
    resource = rsvc.create(db, owner_id=owner_id, kind="prop", name="A")
    db.commit()
    result = composite.quote(
        db, template=_template("Mot cau khong co placeholder nao het"),
        resource_id=resource.id, owner_id=owner_id, reference_variant_ids=[])
    assert result["credit"] > 0
