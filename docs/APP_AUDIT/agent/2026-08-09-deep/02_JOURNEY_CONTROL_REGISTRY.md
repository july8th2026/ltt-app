# A2–A3 — Journey & Control Registry

## Journey/state matrix

| Journey/state | Kết quả | Evidence |
|---|---|---|
| First run/starter | PARTIAL: rõ 3 mẫu nhưng Text nhập tay vẫn là job AI trả phí | E3 `01`, `02` |
| Tạo/nối node | LIVE phần graph/type/cycle; node quá lớn, nhiều cổng kỹ thuật | E1/E3 |
| Upload/generate media | PARTIAL: media đổi generator thành asset node; Text không có literal/manual mode | E1 |
| Run riêng node | BROKEN trong lần audit: scope gồm prerequisite đúng nhưng submit trùng, settle sai | E3 `02`, `03` |
| Quote/approve | PARTIAL: trần rõ; execution không tuân trần theo semantics mong đợi | E3 |
| Running/cancel/retry | PARTIAL: UI có; cancel không hủy child tool job đang chạy | E1 |
| Done/error/artifact | PARTIAL: inspector có step/error/replay; hiển thị raw node ID và thiếu remediation | E3 |
| Save/conflict/offline | LIVE source/test; chưa browser conflict/offline đa tab | E1/E2 |
| Workflow library | MISSING: API có list/clone/archive nhưng Canvas luôn mở item đầu tiên | E1 |
| Share/import/export | PARTIAL: contract tốt; discoverability/revoke/library/customer runner thiếu | E1/E3 |
| Mobile | PARTIAL: chỉ xem; tools/rename/run disabled, catalog dài nhưng không giải thích | E3 `05` |
| Locale | BROKEN: `/en/agent` English pha VI; `/en/agent/canvas` phần lớn VI | E3 |

## Control Registry rút gọn

| Screen → control | Verdict | Action/credit/state/recovery |
|---|---|---|
| Canvas → tên workflow/autosave | LIVE | PUT revision; saving/saved/conflict/retry; mobile disabled |
| Toolbar → theme | LIVE | lưu user preference |
| Toolbar → command palette | PARTIAL | có shortcut; chưa có help/shortcut map đầy đủ |
| Toolbar → AI | PARTIAL | analyze/improve preview signed; provider call chưa có receipt/rate chuyên biệt |
| Toolbar → version/share | PARTIAL | snapshot/restore/link; không quản lý link/revoke trên UI |
| Toolbar → Run | PARTIAL | scope/quote/approve tốt; dual tick và cancel child sai |
| Rail → add tools | PARTIAL | simple tốt; advanced quá dày; mobile toàn nút disabled |
| Rail → workspace | PARTIAL | page/frame/note/comment/import/export; lộ auto routing/model count |
| Rail → layer list | LIVE | chọn node; chưa reorder/collapse/search |
| Rail → undo/redo | LIVE | document graph; chưa browser stress |
| Canvas → starter cards | MISLEADING | “viết một lần” tạo thêm text generation 3 credit |
| Canvas → node inline prompt | MISLEADING | text nhập tay bị gửi qua `text.generate` thay vì literal output |
| Node → Upload | LIVE media | upload owner-key; đổi sang asset tool; thiếu lifecycle/clear receipt |
| Node → Generate AI | PARTIAL | chuyển generator/inspector; không nêu mode/cost trước chuyển |
| Node → Detail | PARTIAL | core params gọn; model catalog/capability mapping còn mơ hồ |
| Node → quote/run | BROKEN audit run | tạo AgentRun; E3 duplicate child/6 credit/error |
| Node/edge → `+` quick connect | LIVE | lọc type/cycle; insertion có type contract |
| Right-click pane | PARTIAL | add/layout/hide; advanced catalog dài và menu bị cắt theo viewport |
| Right-click node | PARTIAL | run block/from here/copy/delete; hai phạm vi khó phân biệt |
| Run → schedule | PARTIAL | datetime-local→UTC; không timezone label/notification |
| Run → cancel | MISLEADING | kết thúc AgentRun nhưng chỉ cancel `agent.advance`, không child tool |
| Run inspector → history/replay | PARTIAL | immutable run; raw node IDs, không retry failed step/remediation |
| Workspace → clone/import/export | PARTIAL | tạo được nhưng không có library để mở/chuyển bản |
| Legacy `/agent` planner | REDUNDANT/MISLEADING | một mental model thứ hai, lộ dev jargon cho customer |

Mỗi control P0/P1 phải được tái kiểm browser desktop/mobile, console/network và
credit ledger/job timeline trước khi đổi verdict sang LIVE.
