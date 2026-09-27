"""TARGET_KINDS du 10 loai (Task 14) - HAI hinh dang chu so huu song song.

Vi sao bai nay ton tai (canh bao cua dieu phoi, 27/09/2026): meta_prompt/
snippet/style dung co che catalog CU (`owner_id IS NULL`); 4 bang MOI cua Pha
4 (image_template/storyboard_framework/sample/profile) co `owner_id NOT
NULL` va dung `is_builtin=True` + `share_level="catalog"` thay the (cot
khong cho NULL - xem migration b64a39da941d va services/nhap_mau_goc.py). Mot
nhanh chi biet MOT hinh dang se lam viec ĐÚNG cho nua kia MOT CACH TINH CO
(vi so sanh owner_id don gian van dung), nhung neu ai do sau nay them mot
nhanh "la catalog thi X" chi kiem tra owner_id IS NULL, no se IM LANG bo qua
4 bang moi (dung lop loi `cho-noi-hai-module-vut-truong-im-lang`). Bai nay
khoa hanh vi quan sat duoc cho CA HAI hinh dang, va khoa viec "khoa la" luon
NO thay vi bi bo qua.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'tk10.db').as_posix()}")
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


ADMIN, USER_B = "admin-x", "user-b"


def test_target_kinds_co_dung_10_loai_tro_dung_lop():
    from apps.prompt_ai_ommi.services import chia_se as svc
    from apps.prompt_ai_ommi.tables import (
        OmmiMetaPrompt, OmmiPromptSnippet, OmmiStyle, OmmiImageTemplate,
        OmmiStoryboardFramework, OmmiSample, OmmiProfile)
    from apps.prompt_ai_ommi.tables.nhan_vat import (
        OmmiCharacter, OmmiBackground, OmmiPose)

    expected = {
        "meta_prompt": OmmiMetaPrompt, "style": OmmiStyle,
        "snippet": OmmiPromptSnippet, "character": OmmiCharacter,
        "background": OmmiBackground, "pose": OmmiPose,
        "image_template": OmmiImageTemplate,
        "storyboard_framework": OmmiStoryboardFramework,
        "sample": OmmiSample, "profile": OmmiProfile,
    }
    assert svc.TARGET_KINDS == expected


def test_unknown_kind_raises_instead_of_being_silently_skipped():
    """`_model()` phai NO tren khoa la, khong duoc tra None/rong roi bi goi
    boi qua o cho khac - day la doi chung cho "hinh dang la phai no"."""
    from apps.prompt_ai_ommi.services import chia_se as svc
    # "IMAGE_TEMPLATE" (hoa) KHONG nam trong danh sach - _model() ha thuong
    # co chu y (".strip().lower()"), nen no la mot khoa HOP LE, khong phai
    # khoa la. Danh sach duoi day la cac khoa THAT SU khong ton tai.
    for khoa_la in ("", "image-template", "khong-ton-tai", "image_templates"):
        with pytest.raises(svc.ShareError):
            svc._model(khoa_la)


def _builtin_image_template(db, owner=ADMIN, name="Mau he thong"):
    """Hinh dang MOI: owner_id NOT NULL, catalog qua is_builtin + share_level -
    khac han meta_prompt (owner_id NULL). Day la ca can bao ve."""
    from apps.prompt_ai_ommi.tables import OmmiImageTemplate
    row = OmmiImageTemplate(
        owner_id=owner, name=name, prompt_text="{SUBJECT} {STYLE}",
        asset_type="character", is_builtin=True, share_level="catalog")
    db.add(row); db.commit()
    return row


def _private_storyboard_framework(db, owner, name="Khung rieng"):
    from apps.prompt_ai_ommi.tables import OmmiStoryboardFramework
    row = OmmiStoryboardFramework(owner_id=owner, name=name)
    db.add(row); db.commit()
    return row


def test_stranger_cannot_share_a_builtin_catalog_item_of_the_new_shape(db):
    """Hinh dang MOI (owner_id NOT NULL, catalog qua is_builtin): nguoi
    thuong KHONG duoc sinh ma cho mot mau builtin thuoc ve admin - dung
    HANH VI da co voi hinh dang CU (owner_id NULL), khong phai mot nhanh
    rieng bi lo."""
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _builtin_image_template(db)
    with pytest.raises(svc.ShareNotFound):
        svc.sinh_ma(db, owner_id=USER_B, target_kind="image_template",
                   target_id=row.id)


def test_owner_can_share_and_receive_across_the_new_shape_tables(db):
    """Sinh ma + nhan + xem_truoc dung cho CA BON bang moi (dung field 'name'
    cua image_template, khong roi vao nhanh fallback 'title' cua sample)."""
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _private_storyboard_framework(db, owner=ADMIN)
    share = svc.sinh_ma(db, owner_id=ADMIN, target_kind="storyboard_framework",
                        target_id=row.id)
    db.commit()
    preview = svc.xem_truoc(db, code=share.code)
    assert preview["name"] == "Khung rieng"

    copy = svc.nhan(db, code=share.code, owner_id=USER_B)
    db.commit()
    assert copy.owner_id == USER_B
    assert copy.id != row.id
    assert copy.share_level == "private"
    assert copy.is_builtin is False


def test_only_admin_can_promote_the_new_shape_tables_to_catalog(db):
    """dat_muc_chia_se phai kiem "chi admin dat catalog" GIONG HET cho ca
    bon bang moi - khong co nhanh rieng nao khac di so voi meta_prompt/
    style/snippet da kiem o test_5403."""
    from apps.prompt_ai_ommi.services import chia_se as svc
    row = _private_storyboard_framework(db, owner=ADMIN)
    with pytest.raises(svc.ShareError):
        svc.dat_muc_chia_se(db, target_kind="storyboard_framework",
                            item_id=row.id, owner_id=ADMIN, is_admin=False,
                            level="catalog")
    updated = svc.dat_muc_chia_se(db, target_kind="storyboard_framework",
                                  item_id=row.id, owner_id=ADMIN,
                                  is_admin=True, level="catalog")
    db.commit()
    assert updated.share_level == "catalog"
