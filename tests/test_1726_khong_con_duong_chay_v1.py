"""Sau cắt chuyển §17: không còn đường HTTP nào chạy Plan v1.

## Vì sao đo bằng BẢNG ĐỊNH TUYẾN, không bằng `grep` tệp

Xoá một tệp mà quên gỡ nó khỏi `__init__.py` ⇒ `ImportError` lúc khởi động —
cái đó tự lộ. Ngược lại mới nguy: **giữ** tệp nhưng tưởng đã xoá. Bảng định
tuyến của app đã dựng là thứ duy nhất nói được "đường này còn sống hay không",
vì nó là thứ người dùng thật gặp.

## Vế đối chứng bắt buộc

Hai trang HTML (`/agent`, `/agent/canvas`) **phải còn**. Không có vế này thì
một bản vá xoá cả `apps/agent/routes/` cũng làm bài trên xanh — và Canvas sẽ
404 cho mọi người, trong khi bộ test báo màu xanh.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def duong_dan() -> set[str]:
    from apps.agent.routes import router
    return {f"{getattr(r, 'path', '')}" for r in router.routes}


CHET = [
    "/api/workflows/{workflow_id}/validate",
    "/api/workflows/{workflow_id}/runs",
    "/api/workflows/{workflow_id}/frames/{frame_id}/export",
    "/api/runs/{run_id}/tick",
    "/api/runs/{run_id}/approve",
    "/api/runs/{run_id}/again",
    "/api/runs/{run_id}/bundle",
    "/api/runs/{run_id}/restore-workflow",
    "/api/runs",
    "/plan",
    "/runs/{run_id}",
    "/runs/{run_id}/tick",
]


@pytest.mark.parametrize("p", CHET)
def test_duong_chay_v1_da_bien_mat(duong_dan, p):
    assert p not in duong_dan, f"{p} van con — spec §17.4/17.5"


@pytest.mark.parametrize("p", ["", "/canvas"])
def test_hai_trang_html_VAN_CON(duong_dan, p):
    """🔑 Vế đối chứng — `/agent/canvas` là nơi bundle Canvas được phục vụ."""
    assert p in duong_dan


@pytest.mark.parametrize("p", ["/api/v3/workflows/{workflow_id}/runs",
                               "/api/v3/runs/{run_id}",
                               "/api/v3/runs/{run_id}/cancel"])
def test_duong_chay_v3_CO_MAT(duong_dan, p):
    assert p in duong_dan


def test_khong_con_cong_503_tam():
    import apps.agent.routes._shared as shared
    assert not hasattr(shared, "_chan_neu_dang_nang_cap_v3"), (
        "cong chan tam cua `phien/wf-chan` phai di cung route no canh")
    for ten in ("_enqueue_advance", "_cancel_advance_jobs", "_prepare_run",
                "_require_new_runs_enabled"):
        assert not hasattr(shared, ten), f"{ten} khong con ai goi"
