"""H26.8: hợp đồng public và catalog tích hợp của Prompt AI."""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_public_name_changes_but_runtime_contract_stays_stable():
    from apps.prompt_ai_ommi.manifest import MANIFEST

    assert MANIFEST.display_name == "Prompt AI"
    assert [item.label for item in MANIFEST.nav] == ["Prompt AI"]
    assert MANIFEST.slug == "prompt_ai_ommi"
    assert MANIFEST.route_prefix == "/prompt-ai-ommi"
    # ⭐ Ghim CHINH XAC, co y: `job_types` la HOP DONG RUNTIME. Doi mot ten o day
    #    lam mo coi moi job dang xep hang mang ten cu — `resolve_handler` tra
    #    "khong co handler" va job chet sau khi credit da giu.
    #
    # ⚠️ Nen bai nay DO khi ai them mot job type la DUNG Y, khong phai mot bai
    #    qua chat: them job type la viec CO CHU Y, va day la cho buoc nguoi them
    #    phai noi ra. Them vao tuple duoi, dung noi long thanh mot phep kiem
    #    "chua tap".
    #
    #    `import_zip` them 28/09 (pha 5, upload ZIP qua hang doi job).
    assert MANIFEST.job_types == ("prompt_ai_ommi.generate",
                                  "prompt_ai_ommi.import_zip")


def test_builtin_catalog_is_customer_safe_and_has_all_three_kinds():
    from apps.prompt_ai_ommi.services.builtin_catalog import list_builtins

    expected_minimum = {"style": 8, "meta": 4, "snippet": 4}
    for kind, minimum in expected_minimum.items():
        items = list_builtins(kind)
        assert len(items) >= minimum
        assert len({item.id for item in items}) == len(items)
        assert all(item.owner_id is None and item.is_catalog for item in items)
        assert all(item.name.strip() and item.body.strip() for item in items)


def test_builtin_catalog_does_not_import_the_read_only_bot_tree():
    source = (ROOT / "apps" / "prompt_ai_ommi" / "services" /
              "builtin_catalog.py").read_text(encoding="utf-8")
    assert "D:\\BOT GEMINI" not in source
    assert "app.modules.seedance" not in source


def test_browser_fixture_registers_app_tables_before_create_all():
    source = (ROOT / "tests" / "fixtures" /
              "prompt_ai_ommi_server.py").read_text(encoding="utf-8")
    imported = source.index("import apps.prompt_ai_ommi.tables")
    created = source.index("Base.metadata.create_all")
    assert imported < created


def test_workspace_uses_prompt_ai_public_copy_and_dashboard_layout():
    shell = (ROOT / "frontend" / "prompt-ai-ommi" / "src" /
             "OmmiShell.tsx").read_text(encoding="utf-8")
    overview = (ROOT / "frontend" / "prompt-ai-ommi" / "src" /
                "OverviewScreen.tsx").read_text(encoding="utf-8")
    assert "Điều hướng Prompt AI" in shell
    assert ">Prompt AI<" in shell
    assert "ommi-dashboard-grid" in overview
    assert "Chi tiêu hôm nay" in overview
