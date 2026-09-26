"""R-4: tach tables.py thanh package khong duoc lam vo import cu.

Vi sao doc nay la RED truoc khi sua: `OmmiBinding` chua ton tai o dau ca, va
`apps.prompt_ai_ommi.tables` van la MOT MODULE PHANG (khong co __path__) —
ca hai assertion duoi day that bai tren cay hien tai.
"""
from __future__ import annotations


def test_import_cu_van_chay_dung_moi_ten_lop():
    from apps.prompt_ai_ommi.tables import (  # noqa: F401 (muc dich la CHUNG MINH import khong vo)
        RESOURCE_KINDS, OmmiResource, OmmiResourceVariant, OmmiTag,
        OmmiResourceTag, OmmiCollection, OmmiCollectionItem,
        OmmiResourceUsage, OmmiMetaPrompt, OmmiPromptSnippet,
        OmmiPromptVersion, OmmiStyle, OmmiStoryboard, OmmiScene,
        OmmiSceneVersion, OmmiBinding)
    assert OmmiResource.__tablename__ == "ommi_resource"
    assert OmmiScene.__tablename__ == "ommi_scene"
    assert OmmiBinding.__tablename__ == "ommi_binding"


def test_tables_la_mot_package_va_binding_import_thang_duoc():
    import apps.prompt_ai_ommi.tables as tables_pkg
    assert hasattr(tables_pkg, "__path__"), (
        "tables phai la PACKAGE (co __init__.py), khong con la mot module phang")
    from apps.prompt_ai_ommi.tables.binding import OmmiBinding as TrucTiep
    assert TrucTiep is tables_pkg.OmmiBinding


def test_ommi_binding_co_dung_cot_theo_spec_4_2():
    from apps.prompt_ai_ommi.tables.binding import OmmiBinding
    cols = {c.name for c in OmmiBinding.__table__.columns}
    assert cols == {"id", "owner_id", "project_id", "scene_id", "tag",
                    "kind", "variant_id", "position", "role", "created_at"}
