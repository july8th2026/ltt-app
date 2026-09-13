# VPS V4 — Implementation Plan

Decision-lock gate completed by `02_DECISION_LOCK.md`. Production code may be
changed only in the phases whose dependencies are locked. Each behavior change
starts with a failing test.

## Rollback before code

- Work only on dedicated branches; do not merge automatically.
- Schema changes are additive first. Rollback app uses old columns/paths; no
  legacy column/drop occurs in V4 migration.
- Profile rollout starts disabled, then STANDBY, then ACTIVE/default only after
  preflight. Rollback returns OVH to STANDBY and Vultr to its prior state without
  repinning instances.
- No live resource is deleted automatically. Ambiguous external state becomes
  `NEEDS_REVIEW`/`QUARANTINED`.
- VM100–107 hard scope guard is tested before any live mutation.

## Dependency order

### P0 — Documentation and baseline

- [x] Discover repos/worktrees/runtime/code/provider facts.
- [x] Classify questions; lock D01–D10 and code/infra answers.
- [x] Model current/target architecture and rollback.
- [x] Run focused existing VPS baseline: 640 passed/3 skipped + sentinel PASS.

### P1 — Domain and migration

- [x] Tests for profile states/default invariant/selector/pinning/backfill.
- [x] Add profile, health and mutation journal tables; evolve IP/instance
  additively; add single-head Alembic migration.
- [x] Seed deterministic `VULTR-SGP` and `OVH-SGP-PROD` without activating an
  unverified profile. Production activation is a later controlled transaction.
- [ ] Read-only production migration inventory; ambiguous rows NEEDS_REVIEW.

2026-09-13 checkpoint: model/selector/pin/backfill and additive migration coded.
Isolated PostgreSQL up/down and concurrent default uniqueness PASS in focused
diagnostics. Canonical migration-head reconnection is pending external CMC
integration; P1 exit is not yet certified.

Exit: migration up/down in isolated DB, one-default race test, no legacy break.

### P2 — Contracts and adapters

- [x] Write common contract tests.
- [x] Add small compute/public-IP/gateway protocols and factory by profile.
- [x] Wrap Proxmox, Vultr and current gateway minimally.
- [x] Add `OvhStaticIpPoolBackend` for pre-owned inventory.
- [ ] Add separate, non-default acquisition service with journal/readback and
  hard D10 guard after the live OVH account capability is identified.
- [x] Concurrent IP allocation and timeout/response-lost tests.

2026-09-13 checkpoint: protocols, guarded Proxmox/Vultr/legacy nft wrappers,
static pool and two-worker PostgreSQL allocation implemented/tested. Actual
OVH `gwnat` adapter and explicit acquisition service remain open; factory blocks
the incompatible legacy driver rather than touching protected mappings.

Exit: Vultr regression green; OVH has no Vultr fields/assumptions.

### P3 — Preflight, runtime, health and capacity

- [x] Strict Machine B artifact reader with schema/generation/freshness tests.
- [x] Per-profile checks and aggregate state.
- [x] Sellable capacity = minimum applicable compute/IP/gateway capacity.
- [x] Activation/default service with DB lock + fresh preflight.
- [x] Provenance fields for app/infra/schema/runtime. Machine B SHA remains
  explicit `UNKNOWN` until all four canonical artifacts publish one coherent
  `source_revision`; checkout/dev SHA is never substituted.

2026-09-13 checkpoint: strict coherent runtime, nested malformed-shape/future
timestamp checks, sellable compute/IP/gateway minimum and fresh activation
health implemented; selected batch 36 passed/1 skipped + sentinel PASS. Final
operator-visible app/Machine-B/schema/runtime provenance is implemented. Live
Machine B SHA and live fail-closed exit evidence remain P7 gates.

Exit: stale/mixed/invalid TLS/host-key/credential states fail closed.

### P4 — Provisioning and reconciliation

- [x] Create service selects profile and persists ID before enqueue.
- [x] Coordinator uses pinned profile only and journals every external mutation
  used by the OVH static-pool path.
- [x] Implement retry/compensation matrix and crash recovery for the active OVH
  static-pool path, including a failed final business commit after all external
  readbacks. Dynamic paid Vultr acquisition remains fail-closed in STANDBY.
- [x] Profile-aware lifecycle and reconciliation findings.
- [x] Guard protected VMIDs/resources and no-auto-delete ambiguous findings.

2026-09-13 checkpoint: POST pins before billing/enqueue; pinned factory for
jobs, console and maintenance; per-step guards; PUBLIC_MAPPING journal/readback;
read-only reconciliation. All-mutation journal and crash recovery remain open.
The measured step-by-step state is maintained in
`11_FAILURE_COMPENSATION_MATRIX.md`; VM create/config, DHCP/bandwidth, mapping
boot and destroy are wired. Dynamic Vultr acquisition remains fail-closed in
STANDBY pending durable provider-label recovery. Final-business-commit failure
injection now proves a retry adopts durable `OBSERVED` evidence and does not
repeat the provider call.

Exit: default switch and profile-disable-mid-job tests; injected failure after
each external mutation converges or becomes explicit NEEDS_REVIEW.

### P5 — Web/access/admin

- [x] Enforce authenticated + owner allowlist by canonical user ID.
- [x] Remove/reject customer profile/provider/gateway selection.
- [x] Lock WEB_ONLY with route/catalog/API-key tests.
- [x] Build app-owned admin services/forms/actions, auth/CSRF/audit and secret
  redaction tests.
- [x] Integrate exact admin IA only after C01 answer. If generic extension is
  approved, document the contract gap before touching `server` as AGENTS asks.
- [x] Browser verify real rendered flow, console and failed requests; add/update
  Playwright regression.

2026-09-13 checkpoint: authenticated rollout/allowlist/web-only implemented.
C01 approved; generic admin IA plus app-owned create/edit reference forms,
preflight/status/reconciliation actions, component health, capacity/VM counts,
IP inventory, auth/CSRF/audit implemented. Real local desktop/mobile
Playwright regression PASS including new forms, read-only IP inventory,
reconciliation and deploy provenance with no overflow/errors. Provider purchase
is deliberately absent from the normal UI and remains a controlled P7 action.

Exit: user A/B isolation, admin-only mutations, no secrets, GUI verified.

### P6 — Hoàn thiện code và kiểm thử vận hành offline

- [x] Focused backend/domain/failure/security suites.
- [ ] PostgreSQL concurrent tests and migration single-head checks.
- [x] Frontend build last if frontend/tests changed. `NOT_NEEDED`: no
  `frontend/` source or frontend test changed.
- [x] `python tools\scan_source_secrets.py` → first **3,283 files/790,918
  lines**, repeat after annotation **3,283 files/790,922 lines**; both
  **0 finding, PASS**.
- [ ] Fix every known in-scope regression and complete the failure/compensation
  matrix with focused behavioral tests.
- [ ] Freeze one release candidate only after all targeted PostgreSQL, browser,
  security and static checks are green.

2026-09-13 freeze candidate: independent broad VPS regression after the last
log-contract correction is **771 passed/3 skipped**, phase-2 sentinel **1
passed**, RESULT PASS. The earlier 770/3/1 run started only after the lock helper
degraded at its 15-minute limit while another gate still held resources; it is
recorded as diagnostic evidence only and is not certification.

First full-gate attempt was correctly red in four static steps (ruff, mypy,
i18n and server route-size) and exited before the seven long final steps; it is
not certification. All four now pass without raising baselines: ruff 933/12,
mypy 585/14 (two fewer assignments), untranslated-shape guard 712 unchanged,
and `server/admin.py` restored to 1,622 lines. Admin Playwright passed again;
post-fix broad VPS is **771 passed/3 skipped + sentinel PASS**. The final gate
is deliberately deferred until every code phase and targeted operational test
is complete; it is not run between phases.

### P7 — Final release gate

- [ ] Review the complete diff, migration lineage, runbook and rollback.
- [ ] Run required final build only if frontend inputs changed.
- [ ] Run one final `python tools\gate.py` on the frozen, unchanged release
  candidate; this is the only full gate in the remaining implementation flow.
- [ ] If any code/test/runtime file changes after this PASS, invalidate the
  candidate and rerun the final gate before deploy.

Exit: full gate PASS on the exact commit/release candidate intended for deploy.

### P8 — Deployment, live acceptance, red team and delivery

- [ ] Deploy only after app gate and operator runbook/rollback review.
- [ ] Resolve exactly one owner record; no credential output.
- [ ] Mount/access `H:\PROXMOX`, run canonical collector, require fresh coherent
  generation and PVE CA.
- [ ] Inventory provider/IP/mappings; use free intended IP or order max one at
  explicit billing gate if quote is unexpected.
- [ ] Preflight OVH, activate/default; Vultr STANDBY.
- [ ] Playwright starts from real web UI; pause only for user login/MFA/CAPTCHA.
- [ ] Create one clearly named VM outside VM100–107; verify ISO installer,
  network, console, owner, profile, lifecycle and readbacks.
- [ ] Test default switch without resource purchase, restore OVH default.
- [ ] At cleanup gate, retain stopped or destroy exactly as PO decides.
- [ ] Answer all §68 questions with linked evidence.
- [ ] Separate implementation quality/live evidence/production readiness scores;
  never average away P0.
- [ ] Update decision/plan/journal/final report.
- [ ] Post-deploy smoke/live acceptance, logical commits and push branch; no
  merge/force-push. Do not add a second full gate unless a post-gate code change
  invalidated the certified candidate.

## Test cadence from 2026-09-13

- During P1–P6, run the smallest complete focused suite for the behavior being
  changed, plus PostgreSQL concurrency/migration and rendered Playwright checks
  where applicable. Check whole-machine CPU and the repository lock before
  every heavy batch.
- Do not run `python tools\gate.py` as a phase transition or diagnostic tool.
  Resolve known failures with focused tests first.
- Freeze code, then run exactly one full final gate in P7 immediately before
  deploy readiness. A later code change requires a new final candidate and
  therefore a replacement gate result, never an extra ceremonial gate.

## Explicitly deferred

`MIGRATE_NETWORK_PROFILE`, zero-touch Windows, adoption of VirtIO/QGA defaults,
Backup V2/restore drill, dual WAN/WAN-cut, and PVE reboot/package maintenance.
They remain visible gates and cannot be described as passed.
