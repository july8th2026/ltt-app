"""Cụm v2 (assistant / snapshots / shares / clone / export) — **ĐÓNG CỬA**.

Nợ §5 của `docs/superpowers/plans/2026-09-24-wf-v2-MASTER.md`. Plan wf-v2 P8
Task 5. Quyết định và bằng chứng đầy đủ: `reports/p8-agent/task-5-report.md`.

## Vì sao ĐÓNG chứ không SỬA

1. **Hai không gian id, và giao diện chỉ cầm một.** Cửa v2 tra `AgentWorkflow`
   (`platform_core/agent/workflows.py::get_owned` → `db.get(AgentWorkflow,…)`);
   Canvas từ Task 6 của plan 01b mở workflow qua `/agent/api/v3/*`, tức cầm id
   của `Workflow`/`WorkflowDraft`. Hai bảng khác nhau, hai chuỗi uuid khác
   nhau ⇒ mọi lời gọi từ giao diện nhận **404 ngay lần bấm đầu**.
   `test_1728` đã ghim đúng sự việc ấy ở tầng giao diện.
2. **Đo 24/09 trên CSDL production**: `shares` **0 bản ghi mọi thời đại**,
   clone 0, restore 0 — **đối chứng** `save` = 78. Tức đường ghi thì sống, cả
   cụm chia sẻ thì chưa từng chạy một lần.
3. `CLAUDE.md`: *"Chưa có khách ở lớp Agent/Canvas/Workflow"* ⇒ không có
   tương thích ngược nào phải giữ. Sửa nghĩa là viết lại năm tính năng cho một
   tập người dùng **rỗng**, trong khi bản v3 của chúng thuộc phase 13.

⛔ Để cửa mở mà không ai đi qua là thứ tệ nhất trong ba lựa chọn: nó vẫn là
   **bề mặt tấn công** (`/shared/{token}` là cửa CÔNG KHAI, không đăng nhập),
   vẫn phải bảo trì, và mỗi lần ai đó đọc bảng định tuyến lại tưởng nó sống.
"""
from __future__ import annotations

import pathlib

import pytest

GOC = pathlib.Path(__file__).resolve().parent.parent

#: Cửa đã đóng. Mỗi dòng là một route từng tồn tại trên `router`.
DA_DONG = {
    # Trợ lý AI (Plan v1)
    ("POST", "/api/workflows/plan"),
    ("POST", "/api/workflows/{workflow_id}/assistant/preview"),
    ("POST", "/api/workflows/{workflow_id}/assistant/apply"),
    # Bản chụp
    ("GET", "/api/workflows/{workflow_id}/snapshots"),
    ("POST", "/api/workflows/{workflow_id}/snapshots/{revision}/restore"),
    # Chia sẻ qua link — ⚠️ `/shared/{token}` KHÔNG đòi đăng nhập
    ("GET", "/api/workflows/{workflow_id}/shares"),
    ("POST", "/api/workflows/{workflow_id}/shares"),
    ("GET", "/shared/{token}"),
    ("POST", "/shared/{token}/clone"),
    ("POST", "/api/workflows/{workflow_id}/shares/{share_id}/revoke"),
    # Thư viện
    ("GET", "/api/workflows/{workflow_id}/activity"),
    ("POST", "/api/workflows/{workflow_id}/clone"),
    ("POST", "/api/workflows/{workflow_id}/archive"),
    ("GET", "/api/workflows/{workflow_id}/export"),
    ("POST", "/api/workflows/import"),
    # ⭐ Cửa báo giá cũ (đóng 24/09, chủ dự án chốt). KHÁC bốn cụm trên ở một
    #    điểm nặng hơn: nó không chỉ còn sống — nó **tự xưng** `authoritative:
    #    True` về một con số SAI. `maximum = unit × fanout × (1 + max_retry)`,
    #    mà **hai thừa số ấy không tồn tại ở đâu trong runtime v2** (làn p10 đo).
    #    Tức khách đọc một con số, sổ tiền chạy theo một con số khác.
    #
    #    Thay bằng `POST /api/v3/workflows/{id}/bao-gia` — MỘT cửa cho cả đồ
    #    thị, gọi thẳng `_gia_node` (đúng hàm `bao_gia_do_thi` gọi). Đo: 24 → 2
    #    request mỗi phiên.
    ("POST", "/api/tools/{tool_name}/quote"),
}

#: 🔑 ĐỐI CHỨNG. Cửa v2 **còn sống** (kho lưu trữ Canvas v2, `tools/mobile_qa.py`
#: và `tools/agent_browser_server.py` còn dùng). Không có vế này thì một phép
#: kiểm "đã đóng" cũng xanh khi ai đó xoá nhầm cả app.
CON_SONG = {
    ("GET", "/api/workflows"),
    ("POST", "/api/workflows"),
    ("GET", "/api/workflows/{workflow_id}"),
    ("PUT", "/api/workflows/{workflow_id}"),
    ("POST", "/api/v3/workflows/{workflow_id}/soan"),
    # Cửa báo giá MỚI phải sống — nếu không, "đã đóng cửa cũ" chỉ nghĩa là
    # người soạn mất luôn báo giá.
    ("POST", "/api/v3/workflows/{workflow_id}/bao-gia"),
}


def _bang_dinh_tuyen() -> set:
    """`{(method, path)}` của app agent. ⚠️ Đường ở đây là đường TƯƠNG ĐỐI —
    nền tảng gắn router dưới tiền tố `/agent`."""
    from apps.agent.routes import router
    return {(m, r.path) for r in router.routes
            for m in (getattr(r, "methods", None) or ())}


def test_cum_v2_KHONG_con_route_nao():
    co = _bang_dinh_tuyen()
    con = sorted(DA_DONG & co)
    assert not con, f"cua v2 van con dang ky: {con}"


def test_doi_chung_cua_CON_SONG_van_dang_ky():
    thieu = sorted(CON_SONG - _bang_dinh_tuyen())
    assert not thieu, f"xoa qua tay: {thieu}"


def test_mo_dun_route_cua_cum_v2_da_bi_XOA():
    """⛔ Gỡ khỏi `__init__` mà để lại tệp là để một khẩu súng đã nạp đạn trong
    kho: một `import` vô tình đủ mở lại cả cụm."""
    thu_muc = GOC / "apps" / "agent" / "routes"
    con = [t for t in ("assistant.py", "sharing.py", "library.py")
           if (thu_muc / t).exists()]
    assert not con, con


def test_khong_con_ma_nao_GHI_bang_chia_se():
    """Đóng ở tầng MÃ, không chỉ ở bảng định tuyến.

    `AgentWorkflowShare` là bảng của cụm đã đóng. Bảng vẫn còn (xoá dữ liệu là
    thao tác không đảo được, và nó có 0 bản ghi nên không vội), nhưng **không
    được còn đường ghi**.
    """
    import ast

    xau = []
    for goc in ("apps", "platform_core", "server"):
        for p in sorted((GOC / goc).rglob("*.py")):
            if "__pycache__" in p.parts:
                continue
            for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                        and n.func.id == "AgentWorkflowShare":
                    xau.append(f"{p.relative_to(GOC)}:{n.lineno}")
    assert not xau, xau


@pytest.mark.parametrize("ten", ["snapshots", "restore_snapshot", "_snapshot"])
def test_ham_ban_chup_da_bi_go_khoi_kho_luu_tru(ten):
    from platform_core.agent import workflows
    assert not hasattr(workflows, ten), ten
