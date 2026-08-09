# A5 — Scorecard

**Q 43 · M 38 · E 95 · BLOCKED**

| Nhóm | W | 0–5 | Quy đổi | Nhận định |
|---|---:|---:|---:|---|
| Giá trị lõi | 15 | 2.2 | 6.6 | graph có thật nhưng starter/run lỗi semantics và execution |
| Độ đầy đủ | 12 | 2.3 | 5.5 | thiếu library/customer mode/lifecycle/recovery |
| Control/correctness | 12 | 1.7 | 4.1 | duplicate child, cancel tree, legacy/locale controls |
| UX/workflow/IA | 12 | 2.0 | 4.8 | hai mental model; node/catalog vẫn thiên dev |
| UI/design | 8 | 2.8 | 4.5 | visual sạch hơn, hierarchy/mật độ node chưa customer-grade |
| Responsive/a11y | 7 | 2.2 | 3.1 | mobile view-only/disabled catalog; WCAG chưa chứng minh |
| Performance/reliability | 9 | 2.0 | 3.6 | dual runner, redirect đôi, bundle memory, SLO unknown |
| AI/economics | 8 | 2.1 | 3.4 | planner/ToolSpec mạnh; manual text đốt model, rate coarse |
| Security/privacy/credit | 10 | 2.0 | 4.0 | ownership tốt; credit/cancel/lifecycle/provider data gap |
| Ops/observability | 7 | 2.4 | 3.4 | run/job logs có; reconciliation/canary customer path thiếu |
| **Tổng** | **100** |  | **43.0** | major repair/reframe |

E95: E1 source + official market docs, E2 225 backend/52 frontend/typecheck,
E3 browser/credit/jobs/desktop/mobile/console/network. Production Postgres race,
provider output/SLO, GPU/load, WCAG assistive tech và user test thật còn UNKNOWN.

| Gate | Result | Điều kiện mở lại |
|---|---|---|
| G0 Scope | PASS | charter khóa |
| G1 Core | FAIL | 3 golden journey chạy đúng, một lần mỗi step, output thật |
| G2 Security | FAIL | data-to-provider disclosure + asset/share/import lifecycle/threat test |
| G3 Money | FAIL | no duplicate, exact attempt accounting, cancel/settle/reconcile all-path |
| G4 Honest UI | FAIL | manual/generate/run/cancel/locale phản ánh đúng |
| G5 Recovery | FAIL | child cancel/resume/retry, workflow library, artifact retention/restore |
| G6 Accessibility | FAIL | customer desktop/mobile runner đạt WCAG 2.2 AA |
| G7 Performance | UNKNOWN | Postgres concurrency + large graph/bundle/provider/GPU budgets |
| G8 Operations | FAIL | production canary/SLO/alert/reconciler/retention/rollback evidence |
