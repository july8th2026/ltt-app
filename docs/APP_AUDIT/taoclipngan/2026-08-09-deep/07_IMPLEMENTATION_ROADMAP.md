# A9–A10 — Implementation Roadmap

## Phase 0 — Mở gate blocker

- Rebase/clamp SRT và golden ZIP test.
- Hợp nhất admission: signed size/type/expiry, stream cap, ffprobe canonical, orphan cleanup.
- Quote/hold theo duration đã probe; test insufficient/increase-hold/idempotency.
- Cooperative cancel, subprocess timeout/kill, partial state và artifact cleanup.
- Retention/delete/export/GC cho source, clip, manifest, package.
- **PASS:** G1–G5 qua matrix thật; rollback chỉ additive/migration có downgrade.

## Phase 1 — Core/table stakes

- Polling/SSE progress, retry/cancel UX, error recovery có hành động.
- Clamp/normalize duration contract; history/source pagination/search/delete.
- Project grouping; package revision/conflict rõ.
- **PASS:** task upload→result→recover→export đạt trên desktop/mobile, không raw error.

## Phase 2 — UX/UI/parity chọn lọc

- Text-based trim, transcript timing, caption style và manual reframe tối thiểu.
- Brand template version/logo/font/safe-zone; platform metadata editor/preview.
- Compare sync playback và chọn winner; EN/i18n/WCAG 2.2 AA.
- **PASS:** user test creator hoàn tất không cần hướng dẫn; G4/G6 PASS.

## Phase 3 — Differentiator

- Prompt/topic curation và score explanation calibrated cho tiếng Việt.
- URL import + Asset/Seedance/AutoSub/Publish Bot handoff.
- Genre/preset nội địa được đo adoption/output quality; không build-all connector.

## Phase 4 — Cost/performance/ops

- Stage checkpoint/resume, GPU admission/ETA, direct bundle delivery.
- Metrics queue/stage/render/cancel/partial/cost-success; alerts/runbook/restore.
- Golden set + blind review cho highlight/reframe/caption; P50/P95/soak/failure injection.
- **PASS:** G7/G8 theo SLO đã khóa.

## Phase 5 — Release

- Full gate, browser A–Z desktop/mobile/VI/EN, canary file thật, ledger reconciliation.
- Backup/rollback rehearsal, artifact lifecycle dry-run, beta telemetry trước public.
- Re-audit Q/M/E/G0–G8; chỉ deploy khi Decision Gate và release gate cho phép.

## Closed-loop metrics

Task completion, time-to-first-clip, output acceptance, edit/export rate, SRT failure, retry/cancel, job/partial success, credit dispute/refund, GPU minutes/success, queue/render P50/P95, retention/delete success và support rate.
