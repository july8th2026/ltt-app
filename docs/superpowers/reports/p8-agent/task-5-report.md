# P8 Task 5 — nợ §5: cụm v2 (assistant/snapshots/shares/clone/export)

## Quyết định: **ĐÓNG CỬA**, không sửa

### Bằng chứng

1. **Cơ chế — hai không gian id.** Cửa v2 tra `AgentWorkflow`
   (`platform_core/agent/workflows.py::get_owned` → `db.get(AgentWorkflow, id)`).
   Canvas từ plan 01b Task 6 mở workflow qua `/agent/api/v3/*`, tức cầm id của
   `Workflow`/`WorkflowDraft`. Hai bảng, hai chuỗi uuid ⇒ **404 ngay lần bấm
   đầu**. `test_1728` đã ghim sự việc ở tầng giao diện từ 23/09.
2. **Số — production 24/09**: `shares` **0 bản ghi mọi thời đại**, clone 0,
   restore 0. **Đối chứng** `save` = 78 ⇒ đường ghi sống, cả cụm chia sẻ chưa
   từng chạy một lần. (Số của lượt đo 24/09 ghi trong plan MASTER §5; làn này
   ⛔ không đọc CSDL production.)
3. `CLAUDE.md`: *"Chưa có khách ở lớp Agent/Canvas/Workflow"* ⇒ không có tương
   thích ngược phải giữ. Sửa = viết lại **năm** tính năng cho một tập người
   dùng **rỗng**, trong khi bản v3 của chúng thuộc phase gốc 13.

⛔ **Để cửa mở mà không ai đi qua là lựa chọn tệ nhất trong ba**: `/shared/{token}`
là cửa **CÔNG KHAI, không đăng nhập**, tức một bề mặt tấn công cho một tính
năng chưa từng được dùng; nó vẫn phải bảo trì; và ai đọc bảng định tuyến cũng
tưởng nó sống.

## Đã xoá

| | |
|---|---|
| Route (15) | `POST /api/workflows/plan` · `assistant/preview` · `assistant/apply` · `snapshots` · `snapshots/{rev}/restore` · `shares` (GET/POST) · `/shared/{token}` · `/shared/{token}/clone` · `shares/{id}/revoke` · `activity` · `clone` · `archive` · `export` · `import` |
| Tệp | `apps/agent/routes/assistant.py` · `sharing.py` · `library.py` |
| Hàm | `workflows._snapshot` / `snapshots` / `restore_snapshot` · tham số `save(reason=…)` · `_shared._active_share` / `_assistant_serializer` / `_ASSISTANT_SALT` |

**CÒN SỐNG** (đối chứng trong `test_2924`): `/api/workflows` GET/POST,
`/api/workflows/{id}` GET/PUT — kho lưu trữ Canvas v2 mà `tools/mobile_qa.py`
và `tools/agent_browser_server.py` còn dùng — và cửa mới
`POST /api/v3/workflows/{id}/soan`.

⛔ **Không xoá bảng, không xoá dữ liệu.** `agent_workflow_shares` /
`agent_workflow_snapshots` ở lại: xoá bảng là thao tác **không đảo được** và
cần migration (ngoài ranh giới làn). `test_2924` chốt rằng **không còn đường
ghi** nào vào `AgentWorkflowShare` trong `apps/`+`platform_core/`+`server/`.

## Đỏ trước / xanh sau

```
tests/test_2924_dong_cua_cum_v2.py   7 failed in 3.08s      (trước khi xoá)
tests/test_2924_dong_cua_cum_v2.py   7 passed in 3.03s
lan toả: 1352 passed, 32 skipped in 68,33 s
   (core:wf_soan 63 tệp + test_292x + test_96/97/101/131/86/211)
```

Tám đỏ lan toả, **tất cả là hậu quả trực tiếp của việc xoá**, đã xử lý từng cái:
`test_96` (bài bản chụp — gỡ) · `test_97` (5 bài gỡ, phần **sở hữu** giữ lại
thành `test_so_huu_tren_cua_CON_LAI`, vòng tròn round-trip đổi `/export` sang
`GET`) · `test_1728` (vế đối chứng dùng `/snapshots` làm *"đường có thật"* —
đổi sang một cửa v2 còn sống).

## Chưa làm được — nợ còn lại, đã khai

- **`plan_once` / `validate_plan` / `plan_v1` / `verifier` vẫn còn** trong
  `platform_core/agent/`, nay **không còn cửa HTTP nào** gọi. Người dùng duy
  nhất còn lại là `tools/mobile_qa.py` (`plan_v1.plan_to_canvas`). Gỡ chúng là
  một lượt riêng, và ⚠️ `plan_v1.canvas_to_plan` gọi `workflows.kiem_canvas` —
  plan MASTER đã ghi một lần xoá hụt ở đúng chỗ này (*"hoá ra đó là cổng an
  ninh của đường lưu"*), nên không gộp vào lượt này.
- `frontend/agent-canvas/src/workflowApi.ts` vẫn **export** các hàm v2 giờ đã
  404 chắc chắn (`assistantPreview`, `shareWorkflow`, `cloneWorkflow`,
  `exportWorkflow`, `snapshots`…). Không ai gọi (`test_1728` đo), nhưng chúng
  nên bị gỡ — **frontend thuộc làn p9**.
- Nợ §5 liên quan *"`previewAssistant` (SSE) nhận `Accept: application/json`"*
  **tự hết**: cửa ấy không còn.
