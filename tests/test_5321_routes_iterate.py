"""Pha 3 -- routes iterate. Trong tam: bao gia truoc, va khong hoan khi rejected."""
from __future__ import annotations

import inspect


def test_generate_co_buoc_bao_gia_truoc_khi_thu_tien():
    """`confirmed=false` phai tra gia ma KHONG nop job -- khach thay tien truoc."""
    from apps.prompt_ai_ommi.routes import iterate as r
    nguon = inspect.getsource(r.generate)
    assert "confirmed" in nguon
    assert nguon.index("confirmed") < nguon.index("submit_with_credit")


def test_verdict_KHONG_he_goi_hoan_credit():
    """Banh coc: doc nguon, khong cho ai them `credit.hoan` vao day."""
    from apps.prompt_ai_ommi.routes import iterate as r
    nguon = inspect.getsource(r.verdict)
    assert "hoan" not in nguon, "verdict khong duoc hoan credit"


def test_moi_route_ghi_deu_kiem_csrf_va_rollout():
    from apps.prompt_ai_ommi.routes import iterate as r
    for ten in ("generate", "verdict"):
        nguon = inspect.getsource(getattr(r, ten))
        assert "_csrf(" in nguon and "_require_run_enabled" in nguon
