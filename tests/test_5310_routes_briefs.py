"""Pha 3 -- routes brief. Trong tam: cai gi MIEN PHI thi khong bi rollout chan.

`_run_mode()` mac dinh "off" tren production (do 26/09). Neu `preflight` va
`bundle` cung goi `_require_run_enabled` thi khach vao trang thay 503 ngay o
buoc mien phi -- va se ket luan app hong.
"""
from __future__ import annotations

import inspect


def test_preflight_va_bundle_KHONG_goi_require_run_enabled():
    from apps.prompt_ai_ommi.routes import briefs as r
    for ten in ("preflight", "bundle"):
        ham = getattr(r, ten)
        assert "_require_run_enabled" not in inspect.getsource(ham), (
            f"{ten} la buoc MIEN PHI, khong duoc chan boi rollout")


def test_quote_va_cac_buoc_ton_tien_CO_goi_require_run_enabled():
    from apps.prompt_ai_ommi.routes import briefs as r
    assert "_require_run_enabled" in inspect.getsource(r.quote)


def test_moi_endpoint_ghi_du_lieu_deu_kiem_csrf():
    """Banh coc: mot route POST/PUT/DELETE thieu `_csrf` la mot lo CSRF."""
    from apps.prompt_ai_ommi.routes import briefs as r
    for ten in ("tao", "sua", "xoa", "nhan_ban", "preflight", "bundle", "quote"):
        nguon = inspect.getsource(getattr(r, ten))
        assert "_csrf(" in nguon, f"{ten} thieu _csrf"


def test_quote_KHONG_go_tay_so_luot_mien_phi():
    """Bai hoc dieu phoi 26/09: `quote` gõ lai so 2 la mot cho khai TRUNG voi
    `LUOT_MIEN_PHI` cua services/iterate.py -- hai cho khai cung mot dieu.

    `quote` phai DUNG LAI `iterate.bao_gia`/`iterate.con_mien_phi`, khong tu
    tinh `2 - free_iterations_used` hay bat ky hang so gõ tay nao khac.
    """
    from apps.prompt_ai_ommi.routes import briefs as r
    nguon = inspect.getsource(r.quote)
    assert "2" not in nguon, f"quote go tay mot con so, phai doc hang so: {nguon}"
    assert "iterate" in nguon or "it.bao_gia" in nguon or "it.con_mien_phi" in nguon
