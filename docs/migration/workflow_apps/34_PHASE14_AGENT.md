# 34 — Phase 14: đánh giá Agent bằng bốn Macro Tool thật

**Ngày:** 2026-09-11 · **Bằng chứng:** `tests/test_1113_phase14_agent_danh_gia.py`

## Kết luận

```
AGENT_CHANGE_REQUIRED: NO
```

Bản sửa duy nhất nằm ở **metadata của Tool**, đúng như Phase 14 yêu cầu:
*"ưu tiên sửa Tool metadata/description/examples trước planner; không nhét luật
App-specific vào Agent."*

---

## 1. Agent làm đúng những gì Phase 14 hỏi

| Câu hỏi | Đo | Kết quả |
|---|---|---|
| discover Tools từ registry | `discover_tools()` | ✅ 4/4, đúng `job_type` |
| hiểu typed I/O | `validate_plan` | ✅ bắt **lệch kiểu** (`json` vào cổng `text`) |
| " | " | ✅ bắt **cổng không khai** (`$s1.text`) |
| báo giá | `estimated_max_credit`, `step_costs` | ✅ mỗi bước một dòng giá |
| tool không tồn tại | `validate_plan` | ✅ từ chối |
| không biết slug ngoài hợp đồng | `test_60` | ✅ (đã có từ trước) |
| cổng fail-closed | `_prepare_run` · `legacy_runs` | ✅ **cả hai** đường validate server-side rồi `raise` |

---

## 2. 🔴 Phát hiện: palette khách KHÔNG lọc theo `lifecycle`

`frontend/agent-canvas/src/presentationAdapter.ts:65` lọc đúng một điều kiện:
`tool.customer_visible !== false`. `grep` toàn kho: **không** bộ lọc `lifecycle`
nào trong cả đường Agent.

⇒ Bốn App vừa dựng — `lifecycle="development"`, `public=False`, **chưa nghiệm thu
  E2E** — **đang hiện trong palette của khách** và bấm chạy được. `public=False`
  chỉ giấu **trang web** của App; nó không giấu **tool**.

**Đã sửa:** `customer_visible=False` trên cả bốn ToolSpec. Đó là *soft-retire*,
không phải xoá: `discover_tools()` vẫn thấy, `runtime_noi_bo.bao_gia()` vẫn tra
được giá, workflow đã dựng vẫn chạy. Cùng khuôn `apps/chatltt`.

Mở lại khi parity đóng và E2E xong — mỗi lần một cổng.

### ⛔ Nhưng KHÔNG ghim thành luật toàn kho

Đo trước khi khái quát: **7 tool ở 6 App khác** cũng `lifecycle="development"`
mà vẫn `customer_visible=True` — `thumbnail` · `taoanh` (×2) · `anhnoibo` ·
`autosubvideo` · `taoclipngan` · `ltt_llm`. Đó là những App **đang bán thật**.

⇒ Trên nền tảng này `lifecycle` **không phải** một cổng ẩn/hiện; nó là nhãn
  trưởng thành dùng lỏng. Ghim *"development ⇒ ẩn"* sẽ làm đỏ 7 tool của người
  khác và áp một chính sách chưa ai duyệt. Tệp kiểm chốt **quyết định của riêng
  chương trình này**, kèm một bài đo giữ chính ranh giới ấy.

---

## 3. ⛔ Hai lỗi trong phép kiểm của tôi, cả hai do Phase 14 lộ ra

### 3.1 `test_1111` nối một cổng KHÔNG TỒN TẠI, và vẫn xanh

Phase 12 của tôi nối `$s1.text` vào `prompt_canh.kich_ban`. Hai cái sai trong
một dòng:

* `transcript.run` khai `returns={"transcript": "json"}` — **không có** cổng `text`;
* và `json` nối vào `kich_ban` (`text`) là **lệch kiểu**.

Nó xanh vì **`executor` không cưỡng chế `returns`** — nó chỉ tra `outputs[port]`
lúc chạy. Thứ cưỡng chế là **bộ kiểm**, và bài ấy gọi thẳng executor nên đi vòng
qua nó. Đúng cái bẫy đã ghi ở `test_1112`: *phép kiểm đi một đường production
không đi.*

**Đã sửa** sang chuỗi hợp kiểu thật, đối chiếu với `validate_plan`:
`audio_pause` trả `audio` → `transcript` nhận `audio`. Nghĩa nghiệp vụ cũng đúng:
chèn khoảng lặng rồi phiên âm bản đã chèn.

### 3.2 Quên `input_types` thì bộ kiểm từ chối một plan hợp lệ

`validate_plan(plan)` không có `input_types` ⇒ `$input.audio` bị coi là không tồn
tại. Suýt đọc thành *"bộ kiểm từ chối plan hợp lệ"*.

---

## 4. Còn lại

Chưa đo được **valid graph rate / wrong-tool rate** của planner — chúng cần gọi
LLM thật, tức cần suất máy B. Ghi ra chứ không nhận là đã đo.
