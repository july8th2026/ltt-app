# A5 — Scorecard

**Q 48 · M 42 · E 58 · BLOCKED** — E94 cũ được hiệu chỉnh ở H28.

| Nhóm | W | 0–5 | Quy đổi | Nhận định |
|---|---:|---:|---:|---|
| Giá trị lõi | 15 | 3.0 | 9.0 | chat/file/image thật; context branch/recovery sai |
| Độ đầy đủ | 12 | 2.4 | 5.8 | thiếu table stakes message/project controls |
| Control/correctness | 12 | 2.0 | 4.8 | money receipt, delete, duplicate/branch lỗi |
| UX/workflow/IA | 12 | 2.2 | 5.3 | dễ bắt đầu; output/file/history chưa customer-grade |
| UI/design | 8 | 3.2 | 5.1 | sạch; plain output và sidebar mobile yếu |
| Responsive/a11y | 7 | 3.2 | 4.5 | không overflow; aria live/delete label có gap |
| Performance/reliability | 9 | 1.8 | 3.2 | timeout none, no run/recovery/rate control |
| AI/economics | 8 | 2.5 | 4.0 | SSE/partial work; provider contract/quality unknown |
| Security/privacy/credit | 10 | 1.6 | 3.2 | auth/lifecycle/consent/receipt blockers |
| Ops/observability | 7 | 2.0 | 2.8 | lifecycle log có; no reconciler/SLO/provider runbook |
| **Tổng** | **100** |  | **47.7 → 48** | major rebuild/repair |

M42: LTT có search/export/branch hình thức và receipt khác biệt, nhưng thua table stakes về context durability, output controls, project knowledge, web/citations và data control. E58: E1 source/official docs, E2 20 targeted tests, E3 browser/SSE/Storage deletion artifact; production provider quality/SLO và legal confirmation UNKNOWN.

| Gate | Result | Reopen condition |
|---|---|---|
| G0 | PASS | charter khóa |
| G1 Core | FAIL | branch/restart/reload giữ AI context; formatted usable output |
| G2 Security | FAIL | provider authorization/data controls + safe image/file path + deletion |
| G3 Money | FAIL | max quote/confirm, idempotency, error/stop receipt, orphan hold reconcile |
| G4 Honest UI | FAIL | ready/file/partial/delete states phản ánh thật |
| G5 Recovery | FAIL | durable run/thread rebuild, deadline/retry/resume |
| G6 Accessibility | FAIL | WCAG core + mobile sidebar + live label evidence |
| G7 Performance | UNKNOWN | provider/sidecar P50/P95/concurrency/rate-limit soak |
| G8 Operations | FAIL | quota/SLO/alert/runbook/retention/compliance evidence |
