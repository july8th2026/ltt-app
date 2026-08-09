# A7–A8 — Options & Decision Gate

## Ba phương án

| Phương án | Value | Coverage | Risk | TTV | Reuse | Confidence | Điểm/100 |
|---|---:|---:|---:|---:|---:|---:|---:|
| REPAIR — chỉ đóng P0/P1 | 5 | 3 | 4 | 5 | 5 | 5 | 82 |
| PARITY — Repair + library/customer mode/mobile/recovery | 5 | 5 | 3 | 3 | 5 | 4 | **88** |
| DIFFERENTIATED — build-all FAUNA/layer/batch/marketplace | 4 | 5 | 1 | 1 | 3 | 2 | 55 |

**Khuyến nghị A:** Repair ngay → Parity chọn lọc → mới Differentiation. Không
build thêm node/model trước khi golden journey, money và project recovery xanh.

## Decision Gate mặc định để Dev khóa trước BUILD

| Câu hỏi | A khuyến nghị | B/C và hệ quả |
|---|---|---|
| Entry `/agent` | **A: workflow/project library** | B legacy planner giữ advanced; C redirect thẳng canvas |
| Text semantics | **A: Text Input 0 credit + Text Generate** | B mode switch một node; C giữ hiện tại (REJECT) |
| Execution owner | **A: worker-only; UI chỉ poll/SSE** | B web-only; C dual runner (REJECT) |
| Customer complexity | **A: compact creative blocks mặc định** | B technical graph mặc định; C chỉ template form |
| Mobile | **A: customer APP runner/edit inputs/run/results** | B view-only có giải thích; C full graph editing mobile |
| Workflow data | **A: library + archive/trash/restore + TTL** | B chỉ list; C một workflow/user (REJECT) |
| Cancel | **A: propagate cooperative cancel toàn cây** | B cancel sau current step; C chỉ cancel orchestrator (REJECT) |
| Benchmark scope | **A: FLORA modality + Comfy APP mode + n8n/Make recovery** | B sao chép PlenX 1:1 (REJECT IP/product fit) |
| Differentiator | **A: quote/receipt + LTT app handoff/templates** | B layer editor; C model marketplace — DEFER |
| Rollout | **A: internal→beta canary→public** | B big bang (REJECT) |

H27 là audit-only; bảng này chưa cấp quyền BUILD. Khi người dùng nói triển khai,
áp dụng toàn bộ A nếu không có quyết định mới mâu thuẫn.
