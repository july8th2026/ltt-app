"""Phase 12 — bốn App đại diện có đến được tầng điều phối không.

⏭️ 23/09/2026 — BỐN bài *chạy thật* của tệp này ĐÃ GỠ cùng runtime v1
   (`platform_core/agent/executor.py`, spec §17.5): `moi_App_chay_duoc_nhu_
   MOT_NODE`, `NOI_HAI_App_bang_tham_chieu`, `bang_chung_cho_moi_run` và
   `TOOL_khong_ton_tai_thi_NEM_LOI`. Cả bốn lái `executor.tick()` — thứ không
   còn tồn tại.

⚠️ Đây là một LỖ HỔNG ĐỘ PHỦ có thật, không phải một dọn dẹp trung tính. Bằng
   chứng Phase 12 (*"4 App thay được orchestration của bot cũ"*) giờ chỉ còn
   vế **nhìn thấy**, mất vế **chạy**. Vế chạy phải dựng lại trên động cơ
   Workflow V2 (`platform_core/workflow/dong_co`) — nó có hàng đợi job riêng,
   nên đó là một bộ bài mới chứ không phải một lần đổi tên hàm.

Bản ghi lịch sử bên dưới giữ nguyên: nó giải thích vì sao có HAI tầng workflow
và vì sao tầng V2 từng không chạy — bối cảnh của chính lần cắt chuyển này.

## 🔴 Phát hiện định hình cả phase (ghi 2026, tầng V2 nay ĐÃ có bộ thi hành)

Câu hỏi Phase 12 đặt ra là *"4 App có thay được orchestration của bot cũ không"*.
Trả lời nó bằng cách **chạy**, không bằng cách đọc mã.

| tầng | có gì | ai lái |
|---|---|---|
| `platform_core/workflow/` (V2) | `dinh_nghia` · `thi_hanh` · `dieu_khien` · `bao_gia` | **không ai** |
| `platform_core/agent/` (M1) | `executor.tick` → `submit_child` → hàng đợi Job | `agent.advance` |

Đo được, không suy:

* `sinh_job()` (`dieu_khien.py:28`) — thứ quyết định một node có sinh Job không —
  **chỉ** được gọi bởi `bao_gia.py:51`, tức đường **báo giá**. Không lời gọi nào
  ở đường thi hành.
* `thi_hanh.py` chỉ có `tao_run` · `ghi_chuyen` · `anh_chup_hien_tai`. Nó **ghi**
  trạng thái, không **đẩy** nó.
* Không tệp nào trong `platform_core/workflow/` tạo một `Job`.
* `job_runner.py` và `server/` không nhắc tới `workflow`.

⇒ Tầng V2 **định nghĩa · phiên bản hoá · báo giá · ghi trạng thái** được, nhưng
  không có bộ thi hành. Đường sống là **executor Agent (M1)**, và nó nhìn thấy
  cả bốn App qua `discover_tools()`.

⚠️ Nên "dựng lại hành vi bot bằng Nodes" ở thời điểm này nghĩa là **plan của
   AgentRun**, không phải `graph` của `WorkflowVersion`. Ghi ra đây vì đọc mã
   không nói được điều đó — cả hai tầng đều trông như đang sống.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("moi_truong")

@pytest.fixture()
def moi_truong(tmp_path, monkeypatch):
    import platform_core.db as dbmod
    monkeypatch.setenv("LTT_DATABASE_URL",
                       f"sqlite:///{(tmp_path / 'wf12.db').as_posix()}")
    monkeypatch.setenv("LTT_ENV", "development")
    monkeypatch.setenv("LTT_SESSION_SECRET", "phase12-workflow")
    import platform_core.models  # noqa: F401
    dbmod.reset_engine()
    dbmod.Base.metadata.create_all(dbmod.get_engine())
    yield
    dbmod.reset_engine()


# ── Đường có tồn tại không ───────────────────────────────────────────────────

def test_ca_BON_App_deu_duoc_tang_dieu_phoi_nhin_thay() -> None:
    """Điều kiện cần. Không có nó thì mọi workflow bên dưới là vô nghĩa."""
    from platform_core.agent.tools import discover_tools
    t = discover_tools()
    for ten in ("transcript.run", "audio_pause.run",
                "prompt_canh.run", "video_assembly.run"):
        assert ten in t, f"{ten} khong den duoc tang dieu phoi"
        assert t[ten].job_type == ten


# ── Bốn workflow đại diện ────────────────────────────────────────────────────
