"""Phase 12 — bốn workflow đại diện, chạy THẬT qua executor, có bằng chứng.

Câu hỏi Phase 12 đặt ra là *"4 App có thay được orchestration của bot cũ không"*.
Trả lời nó bằng cách **chạy**, không bằng cách đọc mã.

## 🔴 Phát hiện định hình cả phase: có HAI tầng workflow, chỉ MỘT tầng chạy

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

NGUOI = "phase12-owner"


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


@pytest.fixture()
def db():
    import platform_core.db as dbmod
    phien = next(dbmod.get_session())
    try:
        yield phien
    finally:
        phien.close()


def _plan(steps: list[dict], inputs: dict | None = None) -> dict:
    return {"version": 1, "budget_max_credit": 500,
            "inputs": inputs or {}, "steps": steps}


def _chay(db, plan: dict):
    """Đi ĐÚNG đường thật: cấp credit → báo giá → phê duyệt (giữ tiền) → tick.

    🔴 Bản đầu của phép kiểm này đặt thẳng `run.status = AGENT_RUNNING` và
       `budget_max`, rồi **không job con nào được tạo**. Lý do đọc ra từ chính
       checkpoint mà executor ghi: `fault: policy`, *"Không đủ phần ngân sách đã
       duyệt"*. Cổng là `run.estimated` — **khoản đã GIỮ** — chứ không phải
       `budget_max`; `budget.ensure_can_spend` nói thẳng: *"actual can never
       exceed the hold"*.

    ⭐ Và chi tiết đáng giữ: ở bản sai ấy, **`prompt_canh.run` vẫn qua** trong
       khi ba App kia trượt — vì `credit_cost` của nó là **0 có chủ đích** (tiền
       thu ở tầng `runtime_noi_bo` theo từng lượt gọi model). Tức một lỗi ở cổng
       ngân sách **không** biểu hiện đều trên bốn App, và nếu chỉ thử App ấy thì
       phép kiểm sẽ xanh trên một đường đang hỏng.
    """
    from tests.conftest import bao_dam_user
    from platform_core import credit
    from platform_core.agent import budget, executor, runs
    from platform_core.agent.validator import ValidationResult
    bao_dam_user(db, NGUOI)
    credit.cap_tay(db, NGUOI, 1000, by="phase12")
    r = runs.create_run(db, user_id=NGUOI, goal="phase12")
    budget.set_quote(db, r, plan=plan, validation=ValidationResult(True, (), 50, ()))
    budget.approve(db, run_id=r.id, user_id=NGUOI, approved_by=NGUOI,
                   expected_version=r.version)
    db.commit()
    r = executor.tick(db, run_id=r.id, user_id=NGUOI)
    db.commit()
    return r, runs.children(db, r)


# ── Đường có tồn tại không ───────────────────────────────────────────────────

def test_ca_BON_App_deu_duoc_executor_Agent_nhin_thay() -> None:
    """Điều kiện cần. Không có nó thì mọi workflow bên dưới là vô nghĩa."""
    from platform_core.agent.tools import discover_tools
    t = discover_tools()
    for ten in ("transcript.run", "audio_pause.run",
                "prompt_canh.run", "video_assembly.run"):
        assert ten in t, f"{ten} khong den duoc executor Agent"
        assert t[ten].job_type == ten


# ── Bốn workflow đại diện ────────────────────────────────────────────────────

@pytest.mark.parametrize("tool,tham_so", [
    ("transcript.run", {"audio": "artifact://a.wav"}),
    ("audio_pause.run", {"audio": "artifact://a.wav", "pause_plan": []}),
    ("prompt_canh.run", {"kich_ban": "mot kich ban", "so_canh": 3}),
    ("video_assembly.run", {"clips": "artifact://clips", "music": "artifact://nhac"}),
])
def test_moi_App_chay_duoc_nhu_MOT_NODE_va_sinh_dung_mot_Job(
        db, tool, tham_so) -> None:
    run, con = _chay(db, _plan([{"id": "s1", "tool": tool, "params": tham_so}]))
    assert len(con) == 1, f"{tool}: phai sinh dung MOT job"
    j = con[0]
    assert j.job_type == tool
    assert j.step_id == "s1" and j.plan_id == run.id
    # `submit_child` tiêm `owner_id` — đó là trường THUỘC MÁY CHỦ, và các
    # handler media dùng nó để chặn dùng hiện vật của tài khoản khác.
    assert j.params.get("owner_id") == NGUOI


def test_NOI_HAI_App_bang_tham_chieu_giua_cac_buoc(db) -> None:
    """Bằng chứng thật sự của Phase 12: dữ liệu **chảy** giữa hai App.

    Một App chạy được một mình chỉ chứng minh nó là một job. Thứ thay được
    orchestration của bot cũ là việc đầu ra bước trước thành đầu vào bước sau —
    ở bot cũ, đó là việc mà mã bot-local làm.
    """
    from platform_core.agent import runs
    # ⛔ Bản đầu của bài này nối `$s1.text` vào `prompt_canh.kich_ban`. HAI cái
    #    sai trong một dòng, và nó vẫn XANH:
    #      · `transcript.run` khai `returns={"transcript": "json"}` — **không có**
    #        cổng `text`;
    #      · và `json` nối vào `kich_ban` (`text`) là **lệch kiểu**.
    #
    #    Nó xanh vì `executor` **không** cưỡng chế `returns`: nó chỉ tra
    #    `outputs[port]` lúc chạy. Thứ cưỡng chế là **bộ kiểm**, và bài này gọi
    #    thẳng executor nên đi vòng qua nó — đúng cái bẫy "phép kiểm đi một đường
    #    production không đi" đã ghi ở `test_1112`.
    #
    # ⇒ Đổi sang một chuỗi **hợp kiểu thật**, đã đối chiếu với `validate_plan`:
    #   `audio_pause` trả `audio`, `transcript` nhận `audio`. Nghĩa nghiệp vụ
    #   cũng đúng: chèn khoảng lặng rồi phiên âm bản đã chèn.
    plan = _plan([
        {"id": "s1", "tool": "audio_pause.run", "after": [],
         "params": {"audio": "$input.audio", "pause_plan": []}},
        {"id": "s2", "tool": "transcript.run", "after": ["s1"],
         "params": {"audio": "$s1.audio"}},
    ], inputs={"audio": "artifact://a.wav"})
    run, con = _chay(db, plan)
    # Nhịp đầu: chỉ `s1` chạy — `s2` chờ `after`.
    assert [j.step_id for j in con] == ["s1"]
    assert con[0].params["audio"] == "artifact://a.wav", "input chua duoc giai"

    # Cho `s1` xong THẬT — đặt trên **Job**, không trên checkpoint.
    #
    # 🔴 Bản đầu của tôi ghi thẳng `run.checkpoint = {...}` và `s2` vẫn không
    #    chạy. Lý do: `_sync_children` **dựng lại** checkpoint từ các Job con ở
    #    đầu mỗi nhịp, nên trạng thái tôi tự ghi bị ghi đè bởi Job vẫn `queued`.
    #
    # ⭐ Đó là thiết kế đúng, và nó đáng ghi: trạng thái bước là **hàm của hàng
    #    đợi job**, không phải một bản sao ai cũng sửa được. Một phép kiểm ghi
    #    tắt vào checkpoint sẽ chứng minh một đường mà production không đi.
    from platform_core.agent import executor
    from platform_core.models import JOB_DONE
    con[0].status = JOB_DONE
    con[0].result = {"audio": "artifact://ra.wav"}
    db.commit()
    run = executor.tick(db, run_id=run.id, user_id=NGUOI)
    db.commit()
    s2 = [j for j in runs.children(db, run) if j.step_id == "s2"]
    assert len(s2) == 1, "s2 khong chay sau khi s1 xong"
    assert s2[0].params["audio"] == "artifact://ra.wav", "dau ra s1 khong chay sang s2"


def test_bang_chung_cho_moi_run__job_credit_va_trang_thai(db) -> None:
    """Phase 12 đòi: run id · Jobs · credit · trạng thái. Kiểm từng thứ tồn tại."""
    from platform_core.agent import executor
    run, con = _chay(db, _plan([
        {"id": "s1", "tool": "transcript.run", "params": {"audio": "x"}}]))
    assert run.id and run.status
    assert con and con[0].id and con[0].status
    # `actual_cost` là bút toán thật của run, đọc từ các Job con.
    assert isinstance(executor.actual_cost(run, con), int)
    assert isinstance(run.checkpoint, dict) and "s1" in run.checkpoint


def test_TOOL_khong_ton_tai_thi_NEM_LOI_chu_khong_bo_qua(db) -> None:
    """Một bước trỏ tới tool đã gỡ phải **nổ**, không được lặng lẽ nhảy qua.

    ⛔ Bỏ qua nghĩa là một workflow khách đã trả tiền chạy **thiếu một khâu** mà
       không ai được báo — và bên tiêu thụ nhận một đầu ra trông như hoàn chỉnh.
    """
    from platform_core.agent import executor
    with pytest.raises(executor.ExecutorError) as e:
        _chay(db, _plan([{"id": "s1", "tool": "khong_ton_tai.run", "params": {}}]))
    assert "khong_ton_tai.run" in str(e.value)
