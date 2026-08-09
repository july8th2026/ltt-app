# A1 — Current Truth

## Bề mặt sản phẩm

| Bề mặt | Truth hiện tại |
|---|---|
| `/agent` | form Agent legacy `goal → AI plan → approve`; lộ tool ID, fan-out, retry, decision log |
| `/agent/canvas` | React Flow Canvas v2, autosave, node/edge, run scope, quote/approve, snapshot/share/import/export |
| Workflow | owner-scoped, optimistic revision, snapshot; API list không phân trang và UI không có thư viện/chuyển workflow |
| Tool | discover từ `ToolSpec`; simple palette có Text/Image/Video/Audio; advanced phơi toàn bộ tool được cấp quyền |
| Execution | `AgentRun` immutable plan, hold trần, child `Job`, worker `agent.advance`; browser cũng POST `/tick` |
| Storage | upload owner-keyed, magic/ffprobe validation, Range; không có record/TTL/GC cho asset Canvas |
| Sharing | token hash, hết hạn 1–168 giờ, view/clone, revoke API |

## Dependency và ranh giới

- App: `apps/agent/`; runtime chung: `platform_core/agent/`; frontend:
  `frontend/agent-canvas/`.
- Tool thực thi thuộc app nguồn; Agent không có executor provider thứ hai.
- Auth/ownership/CSRF, quote hash/version và hold/settle đều server-side.
- Rollback runtime nếu BUILD: rollback commit; migration additive; không được xóa
  workflow/run/artifact trước backup và rehearsal.

## Bằng chứng chạy thật

- 201 backend test Agent lõi PASS; 24 test media/input PASS; 52 Vitest PASS và
  TypeScript typecheck PASS. Lần chạy gộp đầu tiên TIMEOUT 125 giây, không tính PASS.
- Browser: starter Text→Image, inline edit, node run, quote/approve/error, run
  inspector, context menu pane/node, workspace/snapshot, legacy planner,
  desktop/mobile, console/network.
- Console 0 error/warning. Network không có failed request, nhưng nhiều API GET
  bị 302 `/agent/api/* → /en/agent/api/*` rồi gọi lại.
- Browser tạo **hai child job text cùng run**; quote 8 nhưng run lỗi, settle 6,
  refund 2 và không chạy image. Đây là E3; production PostgreSQL chưa được chạy
  race/cancel canary nên impact production là UNKNOWN.

## Truth khác tài liệu H26

H26 ghi Text→Image 8/8 và Q86. H27 tái hiện một phiên mới cho kết quả core FAIL;
do LTT-AQA cấm kế thừa PASS, điểm H26 chỉ còn là bằng chứng lịch sử, không phải
trạng thái chất lượng hiện tại.
