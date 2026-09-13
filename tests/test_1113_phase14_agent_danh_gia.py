"""Phase 14 — đánh giá Agent bằng bốn Macro Tool THẬT.

Phase 14 hỏi Agent có: discover Tools từ registry · hiểu typed I/O · tôn trọng
visibility/lifecycle · báo giá đúng · dựng WorkflowDraft hợp lệ · **không biết
slug của App ngoài hợp đồng**.

Đo được **không cần model** — planner gọi LLM, nhưng bộ kiểm plan, bảng công cụ
và báo giá thì không.

## 🔴 Phát hiện: bảng công cụ của khách KHÔNG lọc theo `lifecycle`

`frontend/agent-canvas/src/presentationAdapter.ts:65` lọc đúng một điều kiện:
`tool.customer_visible !== false`. Không có bộ lọc `lifecycle` nào trong cả
đường Agent (`grep` toàn kho: 0 chỗ).

⇒ Bốn App vừa dựng — `lifecycle="development"`, `public=False`, **chưa nghiệm
  thu E2E**, `vram_min_mb` chưa đo thật — **đang hiện trong palette của khách**
  và bấm chạy được. `public=False` chỉ giấu **trang web** của App; nó không giấu
  **tool**.

## ⛔ Nhưng KHÔNG được ghim điều đó thành luật toàn kho

Đo trước khi khái quát: **7 tool ở 6 App khác** cũng `lifecycle="development"`
mà vẫn `customer_visible=True` — `thumbnail` · `taoanh` (×2) · `anhnoibo` ·
`autosubvideo` · `taoclipngan` · `ltt_llm`. Đó là những App **đang bán thật**.

⇒ Trên nền tảng này `lifecycle` **không phải** một cổng ẩn/hiện; nó là một nhãn
  trưởng thành dùng lỏng. Ghim *"development ⇒ ẩn"* sẽ làm đỏ 7 tool của người
  khác và áp một chính sách chưa ai duyệt.

⭐ Nên tệp này chốt **quyết định của riêng chương trình này** cho bốn App của nó,
   kèm lý do — không chốt một luật nền tảng.

## Kết luận Phase 14

`AGENT_CHANGE_REQUIRED: NO`. Bản sửa nằm ở **metadata của Tool**, đúng như
Phase 14 yêu cầu: *"ưu tiên sửa Tool metadata/description/examples trước
planner; không nhét luật App-specific vào Agent."*
"""
from __future__ import annotations

import pathlib

import pytest

from platform_core.agent.tools import discover_tools
from platform_core.agent.validator import validate_plan
from platform_core.registry import discover

BON = ("transcript", "audio_pause", "prompt_canh", "video_assembly")
TOOL = tuple(f"{s}.run" for s in BON)


def _manifest() -> dict:
    return {a.manifest.slug: a.manifest for a in discover() if not a.error}


# ── Agent thấy được bốn tool (điều kiện cần) ─────────────────────────────────

def test_Agent_DISCOVER_duoc_ca_bon_tool_tu_registry() -> None:
    t = discover_tools()
    for ten in TOOL:
        assert ten in t, f"{ten} khong den duoc executor Agent"
        assert t[ten].job_type == ten


# ── Cửa palette khách: đóng, và năng lực KHÔNG bị gỡ ─────────────────────────

@pytest.mark.parametrize("slug", BON)
def test_bon_App_nay_KHONG_o_palette_khach_khi_chua_nghiem_thu(slug) -> None:
    """Quyết định của **chương trình này**, không phải luật nền tảng.

    ⛔ Bốn App chưa nghiệm thu E2E qua worker, chưa kiểm trên URL công khai, và
       `video_assembly` còn chưa đo `vram_min_mb` thật. Mở cửa palette là mời
       khách bấm chạy một thứ chưa ai chạy hết một lượt.

    Mở lại khi parity đóng và E2E xong — mỗi lần một cổng, đúng như
    `00_STATUS.md` đã chốt.
    """
    m = _manifest()[slug]
    for t in m.tools:
        assert t.customer_visible is False, (
            f"{t.name} dang o palette khach khi App con development")


@pytest.mark.parametrize("slug", BON)
def test_dong_cua_palette_KHONG_go_nang_luc(slug) -> None:
    """`customer_visible=False` là soft-retire, không phải xoá.

    `discover_tools()` vẫn thấy (nên workflow/Agent executor vẫn chạy được), và
    `runtime_noi_bo.bao_gia()` vẫn tra được giá. Cùng khuôn `apps/chatltt`.
    """
    t = discover_tools()
    m = _manifest()[slug]
    for x in m.tools:
        assert x.name in t, "dong cua palette khong duoc lam mat tool"


# ── Vì sao không khái quát thành luật nền tảng ───────────────────────────────

def test_lifecycle_KHONG_phai_cong_an_hien_tren_nen_tang_nay() -> None:
    """Đo trước khi khái quát — và phép đo này **chặn** một luật sai.

    Nếu ai đó định ghim *"lifecycle=development ⇒ customer_visible=False"* thành
    bánh cóc toàn kho, bài này cho họ con số: có những App **đang bán thật** vi
    phạm nó. `lifecycle` ở đây là nhãn trưởng thành dùng lỏng, không phải cổng.

    ⚠️ Bài này **không** bảo tình trạng ấy là đúng. Nó chỉ nói: đó là quyết định
       của chủ những App kia, không phải của chương trình này.
    """
    khac = [(a.manifest.slug, t.name)
            for a in discover() if not a.error
            for t in a.manifest.tools
            if str(getattr(a.manifest, "lifecycle", "")) == "development"
            and t.customer_visible and a.manifest.slug not in BON]
    assert khac, ("khong con App nao cua nguoi khac o trang thai do — neu that "
                  "thi doc lai docstring: co the ghim luat toan kho duoc roi")


def test_palette_khach_loc_DUNG_MOT_dieu_kien() -> None:
    """Chốt sợi dây: bộ lọc palette là `customer_visible`, không phải `lifecycle`.

    Nếu ai đó thêm một bộ lọc `lifecycle` ở frontend, bài này đỏ và họ đọc được
    rằng bốn App trên đang dựa vào `customer_visible` chứ không vào `lifecycle`.

    ⛔ **Không `pytest.skip`.** Bản đầu bỏ qua khi không thấy tệp frontend, và
       `check_bo_qua` bắt đúng: *"một test bị bỏ qua là một test không canh gì
       cả"*. Tệp ấy **được git theo dõi** (`git ls-files` xác nhận), nên vắng mặt
       không phải một điều kiện môi trường hợp lệ — đó là một cây hỏng, và bài
       này phải nói ra chứ không im lặng xanh.
    """
    f = (pathlib.Path(__file__).resolve().parent.parent / "frontend"
         / "agent-canvas" / "src" / "presentationAdapter.ts")
    assert f.is_file(), (
        "khong thay `presentationAdapter.ts` — tep nay duoc git theo doi, nen "
        "vang mat nghia la cay hong chu khong phai mot moi truong khac")
    van = f.read_text(encoding="utf-8", errors="ignore")
    assert "customer_visible" in van
    assert "lifecycle" not in van, (
        "frontend da them bo loc lifecycle — doc lai docstring tep nay")


# ── Bộ kiểm plan hiểu typed I/O của bốn tool ─────────────────────────────────

def _plan(steps: list[dict], inputs: dict | None = None) -> dict:
    return {"version": 1, "budget_max_credit": 500,
            "inputs": inputs or {}, "steps": steps}


def test_plan_HOP_LE_dung_tool_that_thi_qua_duoc_bo_kiem() -> None:
    """⚠️ `input_types` là BẮT BUỘC: thiếu nó, `$input.audio` bị coi là không tồn tại.

    Bản đầu của bài này quên nó và tôi suýt đọc kết quả thành "bộ kiểm từ chối
    một plan hợp lệ".
    """
    kq = validate_plan(_plan(
        [{"id": "s1", "tool": "transcript.run", "after": [],
          "params": {"audio": "$input.audio"}}],
        inputs={"audio": "artifact://a.wav"}),
        input_types={"audio": "audio"})
    assert kq.valid, [i for i in kq.issues][:3]
    assert kq.estimated_max_credit >= 0


def test_TOOL_khong_ton_tai_thi_bo_kiem_TU_CHOI() -> None:
    kq = validate_plan(_plan(
        [{"id": "s1", "tool": "khong_co_that.run", "after": [], "params": {}}]))
    assert not kq.valid, "bo kiem cho qua mot tool khong ton tai"


def test_bao_gia_ra_MOT_SO_cho_moi_buoc() -> None:
    """Phase 14 đòi *quote correctness*. Chốt hình dạng: mỗi bước một dòng giá.

    Chuỗi dùng ở đây là chuỗi **hợp kiểu thật**: `audio_pause` trả `audio`, và
    `transcript` nhận `audio`. Nghĩa nghiệp vụ cũng đúng — chèn khoảng lặng rồi
    phiên âm bản đã chèn.
    """
    kq = validate_plan(_plan(
        [{"id": "s1", "tool": "audio_pause.run", "after": [],
          "params": {"audio": "$input.audio", "pause_plan": "$input.ke_hoach"}},
         {"id": "s2", "tool": "transcript.run", "after": ["s1"],
          "params": {"audio": "$s1.audio"}}],
        inputs={"audio": "artifact://a.wav", "ke_hoach": []}),
        input_types={"audio": "audio", "ke_hoach": "json"})
    assert kq.valid, [i for i in kq.issues][:3]
    assert len(kq.step_costs) == 2, "moi buoc phai co mot dong gia"


def test_bo_kiem_BAT_duoc_lech_kieu_VA_cong_khong_khai() -> None:
    """Hai lớp bảo vệ khác nhau, và cả hai đều thật.

    ⛔ `executor` **không** cưỡng chế `returns` — nó chỉ tra `outputs[port]` lúc
       chạy. Thứ cưỡng chế là **bộ kiểm**, và cả hai đường thật đều gọi nó rồi
       `raise` (`_prepare_run` · `legacy_runs`). Nên một plan chỉ tới được
       executor sau khi đã qua bộ kiểm.
    """
    lech = validate_plan(_plan(
        [{"id": "s1", "tool": "transcript.run", "after": [],
          "params": {"audio": "$input.audio"}},
         {"id": "s2", "tool": "prompt_canh.run", "after": ["s1"],
          "params": {"kich_ban": "$s1.transcript", "so_canh": 3}}],
        inputs={"audio": "x"}), input_types={"audio": "audio"})
    assert not lech.valid
    assert any(i.code == "port_type" for i in lech.issues),         "noi json vao mot cong text ma khong bao lech kieu"

    thieu = validate_plan(_plan(
        [{"id": "s1", "tool": "transcript.run", "after": [],
          "params": {"audio": "$input.audio"}},
         {"id": "s2", "tool": "prompt_canh.run", "after": ["s1"],
          "params": {"kich_ban": "$s1.text", "so_canh": 3}}],
        inputs={"audio": "x"}), input_types={"audio": "audio"})
    assert not thieu.valid
    assert any(i.code == "reference" for i in thieu.issues),         "tham chieu mot cong KHONG khai ma khong bao"
