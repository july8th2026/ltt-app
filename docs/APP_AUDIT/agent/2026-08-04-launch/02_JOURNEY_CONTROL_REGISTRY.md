# 02 — Journey & control registry

| Journey | Entry | Controls chính | Success | Failure/Recovery |
|---|---|---|---|---|
| Tạo workflow | `/agent/canvas` | rail `+`, search, tool card | node xuất hiện, autosave | toast/state lưu; retry/conflict reload |
| Cấu hình node | click node | composer nhanh, Nâng cao | params cập nhật/quote lại | validation chỉ đúng field/node |
| Nối graph | port output | drag hoặc picker tương thích | edge + param reference | input sai loại không xuất hiện/bị từ chối |
| Tổ chức | Workspace/rail | page/frame/note/comment/layers | document v2 round-trip | undo/redo/snapshot |
| Chạy | `Chạy` | validate, scope, cache, create, approve | checkpoint/artifact/actual credit | cancel/replay/error context |
| AI hỗ trợ | `AI` | analyze/improve, preview diff, apply | signed proposal được validator nhận | tamper/invalid không mutate |
| Chia sẻ | `↗` | snapshot, view/clone link | private share có hạn | revoke/restore |
| Mobile | route Canvas | Canvas/Công cụ/Inspector + Chạy | inspect/approve/run | authoring read-only được nói rõ |

Mọi control chính có accessible name; icon rail có `title` và target 38 px trong
rail 48 px. Connector dùng vùng tương tác 44 px; edge interaction stroke 18 px.
