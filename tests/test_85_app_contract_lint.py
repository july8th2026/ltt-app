"""
Linter hop dong app (audit) — chot khong app nao vi pham hop dong CO HOC. Chay lai
moi lan them app: manifest/slug, job_types<->handle/credit_cost, CSRF+auth, guard co-lap.
"""
from __future__ import annotations


def test_khong_co_ERROR_hop_dong():
    from tools.lint_app_contract import lint
    errs = [f for f in lint() if f.level == "ERROR"]
    assert errs == [], "vi pham hop dong app: " + "; ".join(str(e) for e in errs)


def test_moi_app_co_job_types_deu_co_handle():
    """Khong app nao khai job_types ma thieu handle (chan job khong chay duoc)."""
    from tools.lint_app_contract import lint
    bad = [f for f in lint() if "job_types" in f.msg and f.level == "ERROR"]
    assert bad == [], str(bad)
