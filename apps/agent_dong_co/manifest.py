"""Chủ sở hữu job_type `workflow.dong_co` — tách khỏi `apps/agent` (23/09).

⭐ VÌ SAO LÀ MỘT APP MỚI, KHÔNG PHẢI THÊM VÀO `apps/agent`:

   `apps/agent` là UI Canvas + ToolSpec điều phối, và
   `tests/test_190_public_api_coverage.py::
   test_the_agent_app_is_an_orchestrator_not_a_tool` chốt bất biến: manifest
   của nó phải khai ĐÚNG `job_types == ("agent.advance",)` — "public nó là
   public cả một cơ chế chạy" (`docs/PUBLIC_API/APP_DISPOSITION_V1.md`), không
   phải bản thân một job_type động cơ. `workflow.dong_co` (spec
   `docs/superpowers/specs/2026-09-22-ltt-workflow-platform-v2-design.md`
   §5.1: MỘT job nền đơn chạy vòng cho cả hệ) vẫn phải được MỘT app nào đó
   khai trong `job_types` — nếu không, `platform_core/jobs.py::resolve_handler`
   không tra được `job_type_owners()` và worker không chạy được job này.

   ⇒ Tách CHỈ phần khai báo `job_types` sang app riêng này. Handler thật,
     `_dong_co`, vẫn sống nguyên trong `apps/agent/jobs.py` (dùng chung than
     thi hành với `agent.advance`, cùng lưới đỡ `bao_tri` ở
     `apps.agent.manifest._luoi_do_dong_co` — hàm đó chỉ gọi
     `tao_run.danh_thuc_dong_co`, không quan tâm job_type khai ở app nào, nên
     KHÔNG cần chuyển theo). `jobs.py` ở đây chỉ forward sang đó.

   Mẫu: `apps/asv_gpu` (executor nội bộ của `auto_scan_video`) —
   `catalog_parent` + `surface="runtime"`: không thẻ catalog, không mục nav,
   không `ToolSpec` riêng.

⚠️ `Job.app_slug` của các job `workflow.dong_co` VẪN ghi `"agent"` (xem
   `platform_core/workflow/tao_run.py`, `apps/agent/jobs.py::_dong_co`) — cố ý
   không đổi, để không phải sửa lại các test đã xanh
   (`tests/test_1717_wf_tao_run.py`, `tests/test_1719_wf_dong_co.py`) khẳng
   định giá trị đó. Điều này an toàn vì `platform_core/jobs.py::claim()` lọc
   worker theo NĂNG LỰC (`manifest.requires`), không theo `app_slug` cụ thể —
   và cả hai manifest đều khai `requires=("api",)`, nên một worker phục vụ
   được app này thì cũng phục vụ được app kia. Khác với `asv_gpu` (đòi
   `requires=("gpu",)` — một tập năng lực THẬT KHÁC `asv_media`), ở đây không
   có sự khác biệt năng lực nào để tách theo.
"""
from __future__ import annotations

from platform_core.i18n import N_
from platform_core.registry import AppManifest


def _gia(_params: dict) -> int:
    """Luôn 0 — động cơ không tự tính tiền, `workflow_run` đã giữ chỗ từ
    trước (`hold_id`); xem `platform_core/workflow/bao_gia.py`."""
    return 0


MANIFEST = AppManifest(
    slug="agent_dong_co",
    display_name=N_('LTT Agent AI — động cơ'),
    route_prefix="/agent-dong-co",
    summary=N_('Executor nội bộ của Agent/Workflow (job_type workflow.dong_co). '
               'Không phải sản phẩm riêng.'),
    icon="⚙",

    catalog_parent="agent",
    surface="runtime",
    public=False,
    enabled=True,
    lifecycle="internal",

    job_types=("workflow.dong_co",),
    requires=("api",),
    credit_cost=_gia,
    notes=("Tách 23/09 khỏi apps/agent để giữ bất biến "
          "orchestrator-không-phải-tool (test_190). Handler thật ở "
          "apps.agent.jobs — xem jobs.py cùng thư mục này."),
)
