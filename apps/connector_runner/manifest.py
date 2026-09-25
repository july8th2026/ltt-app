"""Chủ sở hữu job_type `workflow.piece` + `workflow.connector` +
`workflow.code` (plan wf-v2 P6, P-D mục 3).

⭐ VÌ SAO LÀ MỘT APP RIÊNG, KHÔNG PHẢI THÊM VÀO `apps/agent`

   `platform_core/jobs.py::resolve_handler` tra `registry.job_type_owners()`:
   một `job_type` **không app nào khai** thì worker không bao giờ nhận job đó,
   và node sẽ đứng QUEUED tới khi `TRAN_RUN` (20 giờ) hết hạn — im lặng, với
   tiền đã giữ. Nên hai job type này phải có chủ.

   Chủ đó ⛔ không được là `apps/agent`:
   `tests/test_190_public_api_coverage.py::
   test_the_agent_app_is_an_orchestrator_not_a_tool` chốt `job_types == ()`
   cho app ấy. Cùng lý do đã tách `apps/agent_dong_co` ngày 23/09 — và cùng
   khuôn: `catalog_parent` + `surface="runtime"`, không thẻ catalog, không mục
   nav, không ToolSpec riêng.

⚠️ BA job_type, MỘT app, và đó là có chủ ý: cả ba dùng **cùng một lane** và
   **cùng một tài nguyên admission** (`connector`, trần 2 suất — spec §11.2).
   Tách làm nhiều app sẽ cho nhiều lane và làm trần đó thành nhiều trần, tức
   nhân số tiến trình Node ~400 MB chạy đồng thời trên một máy production.
   `workflow.code` (P-D mục 3) KHÔNG chạy qua `connector.chay()`/vỏ
   `ltt-connector-runner` như `workflow.piece` — nó dùng
   `code_sandbox.chay()`, vỏ RIÊNG `ltt-code-runner`, không mở
   `proxy_egress`. Chung app vì chung admission, ⛔ không vì chung cách chạy.

⛔ `public=False`: đây là executor nội bộ, không phải sản phẩm bán cho khách.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest


def _gia(_params: dict) -> int:
    """Luôn 0 — `workflow_run` đã giữ chỗ từ trước (`hold_id`), và giá của
    node connector nằm ở `NodeDefinition.gia` (`Gia.co_dinh`), do
    `cau_noi._nop_job_connector` áp trần. ⛔ Không tính tiền hai nơi."""
    return 0


MANIFEST = AppManifest(
    slug="connector_runner",
    display_name=N_('LTT Workflow — connector runner'),
    route_prefix="/connector-runner",
    summary=N_('Executor nội bộ chạy node connector (piece Activepieces trong '
               'AppContainer, và connector native của LTT). Không phải sản '
               'phẩm riêng.'),
    icon="🔌",

    catalog_parent="agent",
    surface="runtime",
    public=False,
    enabled=True,
    lifecycle="internal",

    job_types=("workflow.piece", "workflow.connector", "workflow.code"),
    requires=("api",),
    credit_cost=_gia,
    notes=("Ranh gioi an ninh o platform_core/workflow/vo_boc.py "
           "(AppContainer, 0 capability mang). Egress hop le di qua "
           "proxy_egress.py, noi danh sach mien duoc ap NGOAI tien trinh "
           "piece — activepieces#11547."),
)
