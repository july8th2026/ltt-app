# P8 Task 2 — node `ai.agent` chạy trên **run con** (spec §12.3)

## Nguồn (⛔ không tự suy)

- **Activepieces** `packages/core/shared/src/lib/ee/agent/agent.ts`:
  `maxSteps: z.number().int().positive().max(MAX_AGENT_STEP_BUDGET)…`,
  `tools: z.array(AgentTool).max(MAX_AGENT_TOOLS)…` ⇒ **trần sống trong lược
  đồ**, nên cấu hình vượt trần không bao giờ được LƯU. Ta đặt `maximum` /
  `maxItems` vào `NodeDefinition.tham_so` và cưỡng chế ở **cổng publish**.
- **LangGraph** `libs/langgraph/langgraph/pregel/main.py` — hết bước thì
  `raise GraphRecursionError` (`ErrorCode.GRAPH_RECURSION_LIMIT`), ⛔ không im
  lặng trả kết quả dở. Ở đây: FAILED `vuot_so_buoc`.

## Hình dạng đã dựng

`ai.agent` = `thi_hanh="run_con"`, vòng lặp hai pha, **cả hai pha là run con
một-node**: `NGHI` (`app.text.chat` → một QUYẾT ĐỊNH JSON) → `CONG_CU` (node
khách chọn) → `NGHI` → … → `{"xong": true, "ket_qua": …}`.

⭐ Pha NGHI cũng đi qua hàng đợi job, không gọi thẳng máy B trong transaction
động cơ. Gọi thẳng sẽ là **đúng cái lỗ** `planner.py` từng là (P08 F-06:
*"đường DUY NHẤT tới máy B không đi qua admission"*).

| Tệp | Việc |
|---|---|
| `platform_core/workflow/tac_tu.py` (mới) | vòng lặp, ngân sách, danh sách trắng, `tiep_buoc` |
| `platform_core/workflow/nut_loi/ai_agent.py` (mới) | `NodeDefinition` + trần trong `tham_so` |
| `bien_dich.py` | `TIEN_TO_LOI` **"core."** → tuple 4 không gian (`core./trigger./ai./connector.`) · `_kiem_tham_so_loi` thêm `maximum`/`minimum`/`maxItems` ⇒ mã `tham_so_vuot_tran` |
| `bao_gia.py` | `_gia_node`: `ai.agent` ⇒ `params.ngan_sach_credit` (§12.3) |
| `dong_co.py` | `tac_tu.tiep_buoc(...)` trong `xu_ly_run` (WAITING không tự về READY) |
| `su_kien.py` | thêm loại `AgentStep` (spec §12.3 khai nó cùng hàng `SupervisorDecision`; chỉ nửa kia có sẵn) |

🔴 **`TIEN_TO_LOI = "core."` là một lỗi im lặng có sẵn**: `nut_loi/__init__.py`
khai **bốn** không gian, compiler chỉ nhận một, nên một node `ai.*` đầy đủ bị
từ chối bằng `loai_node_chua_ho_tro` — *"chưa hỗ trợ"* về thứ đã hỗ trợ.

## Đỏ trước / xanh sau

```
E   ImportError: cannot import name 'ai_agent' from 'platform_core.workflow.nut_loi'
1 error in 0.96s
... rồi 15 failed  ->  10 failed, 5 passed  ->  3 failed, 12 passed
```
```
tests/test_2921_wf_ai_agent.py ...............   15 passed in 4.50s
core:wf_soan  (63 tệp)  1264 passed, 32 skipped in 75,04 s
core:wf_dong_co (39 tệp) 454 passed, 32 skipped in 55,73 s
```

Hai đỏ lan toả, **cả hai là bánh cóc đúng**, đã sửa: `test_1789` (mô-đun đăng
ký không ai import) và `test_969` (số route v3: 11 → 12).

## Phép kiểm nói **KHÔNG** phủ cái gì

- Chưa chạy trên PostgreSQL (SQLite in-memory) và chưa gọi máy B thật — quyết
  định của model là dữ liệu **tiêm vào** qua `jobs.complete`.
- `timeout_s` đã khai trong `tham_so` nhưng **chưa cưỡng chế lúc chạy**: không
  có phép kiểm nào cho nó, nên đừng đọc bộ này là "agent có hạn giờ".
- Chưa đo huỷ run cha khi một bước agent đang chạy.
- `ai.llm`/`ai.extract` vẫn `publish_duoc=False` (nợ P7: compiler chưa dịch
  `prompt` → `messages`). `ai.agent` **không** dùng chúng; pha NGHI đi qua
  `app.text.chat`.

## 🔴 Chưa làm được — cần điều phối

`nut_loi/__init__.py` (làn **p5c** sở hữu) chưa import `ai_agent`, nên node
**không tồn tại lúc chạy** — đúng bệnh mà làn p7 mắc. Đã khai vào
`test_1789::CHUA_BAT` để sự vắng mặt **đọc được** thay vì im lặng. Một dòng:

```python
from platform_core.workflow.nut_loi import ai_agent as _ai_agent  # noqa: E402,F401
```

và xoá mục `"ai_agent"` khỏi `CHUA_BAT`.
