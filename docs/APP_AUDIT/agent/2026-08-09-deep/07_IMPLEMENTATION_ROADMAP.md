# A9–A10 — Implementation Roadmap

## Phase 0 — Money/core blocker

- Loại dual runner: worker là execution owner; browser chỉ subscription/poll.
- Unique/idempotent `(run, version, step, attempt, fanout)`; sửa attempt/actual
  accounting và reconciler orphan hold/job.
- Cancel toàn child tree; settle chỉ sau terminal; Postgres concurrency/crash test.
- Tách Text Input 0 credit khỏi Text Generate; migrate 3 starter.
- **PASS:** 3 golden journey chạy 20 lần không duplicate; quote=hold=receipt;
  cancel/refund/provider/artifact nhất quán. Rollback: feature flag Canvas run.

## Phase 1 — Customer product/table stakes

- `/agent` thành Workflow Library: new/open/search/filter/page/archive/trash/
  restore; canvas nhận workflow ID ổn định.
- Compact Text/Image/Video/Audio block: input/manual/generate/output rõ; advanced
  params progressive disclosure; plain-language error/remediation.
- Asset/result registry, retention/export/delete/GC; run history pagination.
- **PASS:** creator mới hoàn thành prompt→image, image→analysis, image→video
  không cần hướng dẫn dev; không mất project/output.

## Phase 2 — UX/UI/a11y parity

- Customer APP mode: chọn inputs/outputs, run/result/asset tabs; mobile runner.
- Chuẩn hóa dark theme, density, port labels, scope preview; VI/EN parity.
- Keyboard/focus/touch/live-region/contrast theo WCAG 2.2 AA.
- Share management/revoke/copy confirmation; unsaved/conflict recovery.

## Phase 3 — Differentiation

- LTT starter/technique templates theo JTBD và handoff qua app nội tại.
- AI assistant hội thoại có selection context, diff/preview/apply/undo và quota.
- Batch/router/brand element chỉ sau telemetry chứng minh nhu cầu; layer editor
  và third-party marketplace tiếp tục DEFER.

## Phase 4 — Performance/ops

- SSE/status subscription; bỏ locale redirect API; virtualize large graph/list.
- Stream ZIP hoặc background bundle; quota/size/retention rõ.
- SLO P50/P95 queue/provider/GPU, cancellation latency, duplicate rate = 0,
  cost/success, orphan asset/hold; alert/runbook/restore rehearsal.

## Phase 5 — Release

- Full `tools/gate.py`; browser A–Z desktop/mobile/VI/EN; PostgreSQL concurrency,
  provider/GPU canary, crash/cancel/reconcile, security abuse và rollback.
- Re-audit Q/M/E/G0–G8; rollout internal→beta có quota→public. Không COMMERCIAL
  khi G2/G3/G5/G7/G8 chưa PASS.

Closed loop: task completion, time-to-first-result, graph setup time, validation
error, duplicate/step, cancel latency, job success, refund/dispute, cost/success,
workflow restore, asset deletion SLA, mobile completion và support rate.
