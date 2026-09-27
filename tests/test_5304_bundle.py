"""Pha 3 -- bundle: render meta-prompt KHONG goi LLM."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.prompt_ai_ommi.services.bundle import (
    dung_bundle, khai_bao_cua)


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'bundle.db').as_posix()}")
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


@pytest.fixture()
def brief_co_du_lieu(db):
    from apps.prompt_ai_ommi.tables import OmmiBrief
    brief = OmmiBrief(owner_id="u1", title="Phim thu", story_vi="x" * 40,
                      target_scenes=3, target_duration_sec=15)
    db.add(brief)
    db.flush()
    return brief


def _meta(body: str, **kw):
    return SimpleNamespace(id="m1", body=body, variables=kw.pop("variables", {}),
                           target_format="gemini_style", **kw)


def test_khai_bao_doc_duoc_o_pha_3_khi_CHUA_co_cot_placeholders():
    """Cot `placeholders` la cua pha 4. Pha 3 phai doc duoc tu `variables`."""
    meta = _meta("{TITLE}", variables={"placeholders": ["TITLE"]})
    assert khai_bao_cua(meta) == ["TITLE"]


def test_khai_bao_uu_tien_cot_thuc_khi_pha_4_da_them():
    meta = _meta("{TITLE}", variables={"placeholders": ["CU"]})
    meta.placeholders = ["TITLE"]
    assert khai_bao_cua(meta) == ["TITLE"]


def test_khai_bao_rong_thi_tra_list_rong_khong_nem_loi():
    assert khai_bao_cua(_meta("{TITLE}")) == []


def test_bundle_bao_thieu_thay_vi_gui_chuoi_hong(db, brief_co_du_lieu):
    """Thieu gia tri thi KHONG render im lang -- phai bao `missing`."""
    meta = _meta("{TITLE} {BIEN_KHONG_CO_NGUON}",
                 variables={"placeholders": ["TITLE", "BIEN_KHONG_CO_NGUON"]})
    ra = dung_bundle(db, brief_co_du_lieu, meta, None)
    assert "BIEN_KHONG_CO_NGUON" in ra["missing_placeholders"]


def test_bundle_du_gia_tri_thi_missing_rong_va_rendered_khong_con_the(
        db, brief_co_du_lieu):
    meta = _meta("Tieu de: {TITLE}. Noi dung: {BRIEF_VI}. {SCENES} canh.",
                 variables={"placeholders": ["TITLE", "BRIEF_VI", "SCENES"]})
    ra = dung_bundle(db, brief_co_du_lieu, meta, None)
    assert ra["missing_placeholders"] == []
    assert "{" not in ra["rendered"] or "{TITLE}" not in ra["rendered"]
    assert brief_co_du_lieu.title in ra["rendered"]


def test_bundle_KHONG_goi_LLM(monkeypatch, db, brief_co_du_lieu):
    """Doi chung cho viec 'mien phi': neu no goi provider thi no khong mien phi.

    Tiem mot provider no bom -- goi la test do.
    """
    from apps.prompt_ai_ommi import provider

    def _no(*a, **k):
        raise AssertionError("bundle KHONG duoc goi LLM")

    monkeypatch.setattr(provider, "generate_json", _no)
    meta = _meta("{TITLE}", variables={"placeholders": ["TITLE"]})
    dung_bundle(db, brief_co_du_lieu, meta, None)


def test_bundle_khong_he_import_provider():
    """Banh coc: doc AST, khong cho ai them `import provider` vao tep nay.

    Phep `test_bundle_KHONG_goi_LLM` chi bat duoc duong chay hien tai; phep
    nay bat ca duong chay TUONG LAI ma chua ai viet test cho.
    """
    import ast
    import pathlib

    nguon = pathlib.Path("apps/prompt_ai_ommi/services/bundle.py").read_text(
        encoding="utf-8")
    ten = set()
    for node in ast.walk(ast.parse(nguon)):
        if isinstance(node, ast.Import):
            ten |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            ten.add(node.module or "")
            ten |= {a.name for a in node.names}
    assert not any("provider" in t for t in ten), f"bundle import provider: {ten}"
