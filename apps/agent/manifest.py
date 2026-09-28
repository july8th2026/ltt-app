"""Manifest for the orchestration UI; execution uses existing app ToolSpecs.

⚠️ `job_types` PHẢI là `()` — không thêm `workflow.dong_co` vào đây dù handler
   thật của nó (`_dong_co`) vẫn sống trong `jobs.py` cùng thư mục này.
   `test_190_public_api_coverage.py::test_the_agent_app_is_an_orchestrator_not_a_tool`
   chốt bất biến "`agent` là runtime điều phối, không phải bản thân một
   job_type động cơ" — `apps/agent_dong_co/manifest.py` mới là nơi khai
   job_type đó (chỉ đăng ký, gọi thẳng sang `apps.agent.jobs.handle`). Xem
   docstring ở đó.

⏭️ `agent.advance` (vòng tick của Plan v1) ĐÃ GỠ 23/09/2026 cùng
   `platform_core/agent/executor.py` — spec §17.5. Từ đó app này không còn khai
   job_type nào: nó là UI thuần.
"""
from platform_core.i18n import N_
from platform_core.registry import AppManifest, NavEntry


def _orchestration_cost(_params: dict) -> int:
    return 0


def _luoi_do_dong_co() -> None:
    """Mỗi 60 s: có wakeup tới hạn mà không có job động cơ chờ/chạy ⇒ nộp lại.
    KHÔNG ném (luật `bao_tri`).

    ⭐ Review chốt (final-review.md F1): bản cũ gọi `tao_run.danh_thuc_dong_co`
       VÔ ĐIỀU KIỆN mỗi 60 s — kể cả khi hệ thống không có run nào — nên ổn
       định ở ~1440 job `workflow.dong_co` rỗng/ngày mãi mãi. Docstring luôn
       nói "có wakeup tới hạn MÀ không có job động cơ chờ/chạy", nhưng code
       chỉ kiểm vế sau. Sửa: tự hỏi vế TRƯỚC (có `Wakeup` nào tới hạn, chưa ai
       nhặt) trước khi gọi `danh_thuc_dong_co` — hàm đó tự kiểm vế sau (job
       động cơ chưa kết thúc) như cũ. Lưới đỡ vẫn nguyên vẹn: nó chỉ bớt nộp
       khi THẬT SỰ không có việc gì tới hạn.
    """
    try:
        from datetime import datetime, timezone
        from sqlalchemy import select
        from platform_core.db import get_session
        from platform_core.models import Wakeup
        from platform_core.workflow import tao_run
        gen = get_session(); db = next(gen)
        try:
            bay_gio = datetime.now(timezone.utc).replace(tzinfo=None)
            ke = db.execute(select(Wakeup.id).where(
                Wakeup.claimed_at.is_(None), Wakeup.due_at <= bay_gio)
                .limit(1)).scalar()
            if ke is not None:
                tao_run.danh_thuc_dong_co(db)   # khử trùng job chưa kết thúc
            db.commit()
        finally:
            db.close()
    except Exception:                        # noqa: BLE001
        import logging
        logging.getLogger(__name__).exception("luoi do dong co")


MANIFEST = AppManifest(
    slug="agent",
    display_name="LTT Agent AI",
    route_prefix="/agent",
    summary=N_('Biến mục tiêu thành kế hoạch nhiều bước, báo giá trước và chạy có kiểm soát.'),
    icon="✦",
    accent="#8B5CF6",
    # ⭐ IA dich (`docs/architecture/agent_ui_v2/09_TARGET_DESIGN.md` §1, Q1=B):
    #    SAU muc cap cao nhat. `built=False` la co san cua nen tang — `base.html`
    #    tu dan huy hieu "Dang xay" canh nhan, nen mot muc chua lam KHONG phai
    #    mot trang gia vo hoat dong.
    #
    # ⛔ KHONG con muc "Canvas" o day: trinh soan la mot muc CON cua mot
    #    workflow (`/agent/workflows/{id}`), khong phai mot muc cap cao nhat —
    #    do la chinh cho IA cu sai (`01_CURRENT_UI_AUDIT.md` §1.1: giao dien
    #    khong co cua nao toi workflow thu hai). `/agent/canvas` van song nhu
    #    mot loi vao khong-id (`test_1726`), no chi khong con nam tren nav.
    nav=(NavEntry("LTT Agent AI", "/agent", "✦", "agent"),
         NavEntry(N_("Workflows"), "/agent/workflows", "◇", "agent_workflows"),
         NavEntry(N_("Lượt chạy"), "/agent/runs", "🕘", "agent_runs",
                  built=False),
         # UI-9 (28/09): trang thật (danh mục mẫu), không còn "đang xây" —
         # xem `apps/agent/routes/trang.py::trang_templates`.
         NavEntry(N_("Mẫu"), "/agent/templates", "📚", "agent_templates"),
         NavEntry(N_("Các kết nối"), "/agent/connections", "🔌",
                  "agent_connections", built=False),
         NavEntry(N_("Agent"), "/agent/agents", "✦", "agent_agents",
                  built=False),
         NavEntry(N_("Cài đặt Agent"), "/agent/settings", "⚙",
                  "agent_settings", built=False)),
    job_types=(),
    requires=("api",),
    credit_cost=_orchestration_cost,
    enabled=True,
    public=True,
    lifecycle="development",
    capabilities=("Automation",),
    group="AI Studio",
    badge="MỚI",
    notes="Canvas V2 chay tren platform_core/workflow (spec ADR-WF-002). Khong con Plan v1.",
    bao_tri=_luoi_do_dong_co,
    bao_tri_moi_giay=60,
)
