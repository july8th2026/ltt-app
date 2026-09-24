# P8 Task 1 — Planner ra **draft v3** (phase gốc 11, spec §12.2)

## Nguồn (⛔ không tự suy)

- **n8n** `packages/@n8n/ai-workflow-builder.ee/src/tools/add-node.tool.ts`
  (`n8n-io/n8n`). Hai điều lấy nguyên văn:
  1. Model **không dựng node**, nó chỉ nêu ý định qua một lược đồ zod
     (`nodeCreationSchema`); mã tất định mới dựng — `findNodeType(...)` trả
     `null` ⇒ `NODE_TYPE_NOT_FOUND`. ⇒ ta để `bien_dich` phán quyết, **không**
     viết bảng tra thứ hai.
  2. **Vị trí do mã tính** (`calculateNodePosition`), không do model bịa. Toạ độ
     model gửi bị bỏ — `test_vi_tri_do_ma_tinh_khong_lay_cua_model`.
- Spec §4.1 (hình dạng draft v3) · §12.2 (Agent không publish).

## Việc đã làm

| Tệp | Nội dung |
|---|---|
| `platform_core/agent/ke_hoach_v3.py` (mới) | `danh_muc()` (chỉ node `publish_duoc`) · `build_prompt()` · `chuan_hoa()` (đầu ra model → draft v3, chỉ kiểm **hình dạng**) · `kiem()`/`soan_draft()` (đi qua `bien_dich.bien_dich`, tức **đúng cổng publish**) |
| `platform_core/agent/planner.py` | thêm bí danh công khai `goi_model` (`_goi_model` giữ nguyên vì `test_389`/`test_1208` đã ghim) |
| `apps/agent/routes/agent_v3.py` (mới) | `POST /api/v3/workflows/{id}/soan` — **ghi draft** + trả báo giá. ⛔ không publish |
| `apps/agent/routes/__init__.py` | đăng ký module route |

## Đỏ trước / xanh sau

```
ERROR tests/test_2920_planner_draft_v3.py
E   ImportError: cannot import name 'ke_hoach_v3' from 'platform_core.agent'
1 error in 0.97s
```

```
tests/test_2920_planner_draft_v3.py ...............   [100%]
15 passed in 0.86s          (chạy lại SAU khi gộp `main` 054a67c8: 15 passed)
```

## Phép kiểm nói **KHÔNG** phủ cái gì

- Chưa gọi model **thật**: mọi phép ở đây tiêm `llm_call`. Chất lượng đồ thị do
  `ltt-3.5` sinh ra là việc của FLOW G (Task 6), không phải của Task 1.
- `soan_draft` khi `llm_call=None` đi qua `planner.goi_model` — đường đó đã có
  `test_389`/`test_1208` phủ (giành suất admission, không có đường lui ra
  provider ngoài); Task 1 **không** đo lại.
- Cửa `/soan` chưa có phép kiểm HTTP (CSRF, 404 chủ sở hữu, 409 revision) —
  Task 6 phủ bằng FLOW G trên PostgreSQL.

## Chưa làm được

- `plan_once()` (Plan v1) **vẫn còn**: người dùng duy nhất của nó là
  `apps/agent/routes/assistant.py`, và việc gỡ cụm v2 là **Task 5**. Gỡ ở đây
  sẽ làm hỏng một cửa còn đăng ký, nên nó đi cùng quyết định của Task 5.
