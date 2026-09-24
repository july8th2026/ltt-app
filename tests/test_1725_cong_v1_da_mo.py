"""Cổng 501 của `/api/v1/workflows` đã mở — và mã cổng đã bị XOÁ.

## Vì sao đo sự VẮNG MẶT của mã, không chỉ đo mã trả về

`_chay_workflow_da_mo()` là một hàm trả hằng `False`. Một bản "mở cổng" lười
chỉ đổi `return False` thành `return True` và để hàm đó nằm lại. Hàm nằm lại là
một công tắc **không ai sở hữu**: sáu tháng nữa một người đọc nó sẽ tưởng đây là
cờ rollout đang bật, và tắt nó để "thử".

Bánh cóc này chốt: mở cổng = **gỡ** cổng.
"""
from __future__ import annotations

import pathlib

GOC = pathlib.Path(__file__).resolve().parent.parent
NGUON = GOC / "server" / "api" / "workflows.py"


def test_khong_con_cong_tac_chay_workflow_da_mo():
    nguon = NGUON.read_text(encoding="utf-8")
    for ten in ("_chay_workflow_da_mo", "_LOI_CHUA_MO",
                "workflow_runs_unavailable"):
        assert ten not in nguon, (
            f"{ten} van con trong {NGUON.name} — mo cong nghia la GO cong, "
            "khong phai doi `return False` thanh `return True`")


def test_hai_route_van_con_o_do():
    """🔑 Vế đối chứng: xoá luôn hai route cũng làm bài trên xanh."""
    nguon = NGUON.read_text(encoding="utf-8")
    assert '"/workflows/{workflow_id}/quotes"' in nguon
    assert '"/workflows/{workflow_id}/runs"' in nguon
