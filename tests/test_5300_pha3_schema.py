"""Pha 3 -- schema: tach package khong lam vo import cu, va bang moi co du cot."""
from __future__ import annotations

import pytest

TEN_CU = (
    "OmmiResource", "OmmiResourceVariant", "OmmiTag", "OmmiResourceTag",
    "OmmiCollection", "OmmiCollectionItem", "OmmiResourceUsage",
    "OmmiMetaPrompt", "OmmiPromptSnippet", "OmmiStyle", "OmmiPromptVersion",
    "OmmiStoryboard", "OmmiScene", "OmmiSceneVersion",
)


@pytest.mark.parametrize("ten", TEN_CU)
def test_ten_lop_cu_van_import_duoc(ten):
    """Tach `tables.py` thanh package KHONG duoc lam vo mot import nao."""
    import apps.prompt_ai_ommi.tables as t
    assert hasattr(t, ten), f"mat {ten} sau khi tach package"
