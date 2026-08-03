# 08 — Ticket Backlog tuần tự

| # | Vé | Hạng mục | Priority | Phụ thuộc |
|---:|---|---|---|---|
| 1 | AG2-DEC-001 | Khóa D1–D12, acceptance matrix và rollback | P1 | — |
| 2 | AG2-DATA-001 | CanvasDocument v2 + JSON schema + limits | P1 | 1 |
| 3 | AG2-DATA-002 | Migration/import v1→v2 + round-trip fixtures | P1 | 2 |
| 4 | AG2-DATA-003 | Page/frame/note/comment/version/share persistence & ownership | P1 | 2 |
| 5 | AG2-UI-001 | Immersive route shell/topbar/rail/drawers | P1 | 3 |
| 6 | AG2-UI-002 | Pages/layers/frame/grid/minimap/connection visibility | P1 | 5 |
| 7 | AG2-UI-003 | Keyboard map, focus/a11y, command palette | P1 | 5 |
| 8 | AG2-LAYOUT-001 | Layered DAG + disconnected/frame-aware auto layout | P2 | 6 |
| 9 | AG2-MODEL-001 | ModelCapability v2 contract | P1 | 1 |
| 10 | AG2-MODEL-002 | Catalog/servers/price-preview APIs + cache/fallback | P1 | 9 |
| 11 | AG2-UI-004 | Inline composer generated from schema | P1 | 10 |
| 12 | AG2-ASSET-001 | Typed Asset node + R2 picker/upload/provenance | P1 | 3 |
| 13 | AG2-TOOL-001 | Generic `text.generate` | P1 | 9 |
| 14 | AG2-TOOL-002 | Batch Images contract | P1 | 9,12 |
| 15 | AG2-TOOL-003 | Video provider/mode expansion | P1 | 9,10 |
| 16 | AG2-TOOL-004 | Audio/TTS + voice catalog/preview | P1 | 9,10,12 |
| 17 | AG2-TOOL-005 | Extract Frames via FFmpeg | P1 | 12 |
| 18 | AG2-TOOL-006 | Merge Image | P1 | 12 |
| 19 | AG2-TOOL-007 | Merge Video | P1 | 12 |
| 20 | AG2-TOOL-008 | Social URL import with SSRF/policy controls | P1 | 12 |
| 21 | AG2-TOOL-009 | Image upscale engine benchmark then ToolSpec | P2 | 12 |
| 22 | AG2-RUN-001 | Selection/upstream closure planner | P1 | 3 |
| 23 | AG2-RUN-002 | Scoped quote/hash/approval/hold/settle | P1 | 22 |
| 24 | AG2-RUN-003 | Node/frame execution, cache, cancel/retry/resume | P1 | 23 |
| 25 | AG2-RUN-004 | Frame template + download resource bundle | P2 | 24 |
| 26 | AG2-ASST-001 | Workflow context serializer + assistant session/SSE | P1 | 3,9 |
| 27 | AG2-ASST-002 | Tool calls: analyze, improve, add nodes, patterns, list workflows | P1 | 26 |
| 28 | AG2-ASST-003 | RAG pattern store + version/provenance | P2 | 27 |
| 29 | AG2-ASST-004 | Graph diff/preview/apply through validator | P1 | 27 |
| 30 | AG2-VER-001 | Coalesced editor snapshot/diff/restore | P1 | 4 |
| 31 | AG2-SHARE-001 | Private link, view/clone roles, revoke/audit/rate-limit | P1 | 4 |
| 32 | AG2-COLLAB-001 | Comment/sticky lifecycle + activity drawer | P2 | 4,31 |
| 33 | AG2-MOBILE-001 | Inspect/approve/run/artifact responsive journey | P2 | 5,24 |
| 34 | AG2-PERF-001 | 100-node benchmark, virtualization/layout worker | P1 | 8 |
| 35 | AG2-OPS-001 | Metrics/SLO/alerts/runbook/provider kill switch | P1 | 24 |
| 36 | AG2-QA-001 | Behavior/visual/a11y/security/load parity suite | P1 | 1–35 |
| 37 | AG2-REL-001 | Canary, scorecard re-audit, G0–G8, rollback drill | P1 | 36 |

## Definition of Done mỗi vé

Contract và error/credit/ownership trước UI; test hẹp xanh; browser render thật; console 0 lỗi không giải thích; failed request 0 ngoài trường hợp đã mock; responsive/keyboard phù hợp; telemetry có tên; docs/plan/journal cập nhật; rollback khả thi. Không đánh dấu hoàn thành dựa trên code tồn tại hoặc test collect.
