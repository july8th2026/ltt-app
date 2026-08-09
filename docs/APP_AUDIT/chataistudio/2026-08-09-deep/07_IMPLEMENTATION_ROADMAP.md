# A9–A10 — Implementation Roadmap

## Phase 0 — Blocker

- Chốt provider API/business authorization, data controls, DPA/retention/abuse.
- Durable `ChatRun`/turn idempotency; one-active-turn; max-cost hold/confirm; all-terminal receipt/reconciler.
- Replay/fork/compaction context từ DB; sidecar restart test.
- Safe output handle thay arbitrary path; file parser budgets.
- Reference-aware delete/TTL/GC cho upload/output/thread và self-service export.
- **PASS:** G1–G5, no orphan hold/object/context loss under crash/race.

## Phase 1 — Customer table stakes

- Markdown/code/table/link render an toàn; copy/regenerate/edit/branch-from-message.
- Retry/cancel deadline, action-oriented errors, ready/quota state thật.
- Rename/pin/archive/pagination; attachment card nhất quán live/reload; privacy notice.
- **PASS:** core task user test không cần dev explanation.

## Phase 2 — UX/a11y/parity

- Mobile conversation drawer, keyboard/focus/live-region, WCAG 2.2 AA.
- Model/capability picker allowlist; customer instructions; export bundle đúng.
- Per-message receipt/source/feedback; VI/EN parity.

## Phase 3 — Differentiation

- LTT templates và handoff có xác nhận sang Tạo ảnh/Seedance/Prompt AI/Agent.
- Web search/citation hoặc file knowledge chỉ khi provider/privacy/cost contract rõ; không tạo runtime project thứ hai.

## Phase 4 — Ops/performance

- Provider fallback/quota/backpressure/circuit breaker; P50/P95/load/soak.
- Metrics turn/context rebuild/cancel/orphan/refund/cost-success; alerts/runbook/restore.
- Blind output QA Vietnamese creative tasks và prompt-injection/file abuse suite.

## Phase 5 — Release

- Full gate + browser A–Z desktop/mobile/VI/EN + provider canary + crash/reconcile rehearsal.
- Re-audit Q/M/E/G0–G8; rollout internal→beta quota→public only after G7/G8.

Closed loop: completion, first-token P50/P95, stop/retry, context/branch correctness, orphan holds/objects, disputes/refunds, cost/success, file delete SLA, output acceptance and support rate.
