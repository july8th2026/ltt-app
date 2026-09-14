# VPS V4 — Final Report

Status: **IN PROGRESS — OFFLINE CODE NEAR FREEZE; READ-ONLY LIVE PREFLIGHT PARTIAL; RESOURCE CREATE BLOCKED**

## Revisions

- HEAD BEFORE: `3b5adcb7ffa43c8c553ac38d457e22e3cde60e30`
- HEAD AFTER: pending
- Machine B source commits: `4428223` TLS callback fix; `c5c2453` read-only CA export
- Worktrees: `D:\LTTSTUDIOSAPP-vps-v4`, `D:\LTT-VM-Promox-v4`

## Decisions locked

D01–D10 and derived technical decisions are in `02_DECISION_LOCK.md`. C01 was
approved 2026-09-13 for the generic admin contract. Cleanup choice remains open.

## Architecture before/after

Before: gateway plus direct Proxmox/Vultr/nft orchestration; no instance profile
pin. Target: profile selector, persisted pin, three backend contracts, durable
mutation journal and per-profile health/reconciliation. See `03` and `04`.

## Acceptance matrix

- [x] InfrastructureProfile model
- [x] one-default invariant
- [x] instance profile pinning
- [x] Vultr adapter preserved / STANDBY
- [ ] OVH adapter / ACTIVE / DEFAULT
- [x] OVH credential ownership/read-only inventory and public-IP pool sync
- [x] race-safe allocation
- [x] gateway contract + actual `gwnat` adapter/helper offline (live install blocked B06)
- [x] profile preflight/health/reconciliation
- [x] Admin profile UI
- [x] web-only policy
- [x] owner-only MVP access
- [ ] one OVH IPv4 live
- [ ] one OVH VPS live with correct owner
- [ ] Windows installer/disk visible and console
- [ ] public/private/WG connectivity
- [ ] stop/start/restart
- [ ] cleanup or explicitly retained state
- [x] default switch preserves existing pin
- [x] scoped failure injection/security/secret scan
- [ ] final full gate

## Live test VPS

NOT CREATED. App instance ID, VMID, profile, canonical owner ID, private/public
IP and current state are pending live gate. No production resource identifier
is fabricated here.

## Tests and evidence

- Discovery/config check: completed as recorded in `00_DISCOVERY.md`.
- Focused baseline: 640 passed/3 skipped plus phase-2 sentinel, PASS before V4.
- Focused domain/backends/pinned guards/config/runtime: 48 passed/1 skipped +
  sentinel, PASS; admin-nav/layering regression 64 + sentinel, PASS.
- Admin auth/CSRF/audit/failure persistence: 14 passed/1 skipped + sentinel, PASS.
- Real PostgreSQL schema, additive migration up/down, two-worker default
  uniqueness and two-worker static IP allocation passed in opt-in focused
  batches. UUID test DB/schema only; canonical migration-head gate still open.
- Local browser: real desktop/mobile menu/access/preflight/disable flow PASS,
  create/edit canonical references, component health/capacity counts and IP-pool
  surface PASS; no unexpected JS/console/network/server errors. Fixture data
  only; not live.
  Screenshots in `evidence/admin-desktop.png` and `evidence/admin-mobile.png`.
- Broad VPS diagnostic after replacing legacy AST checks with behavior probes:
  **768 passed/3 skipped + sentinel PASS**. A preceding run exposed nine scoped
  compatibility/test defects; all nine were fixed before this green rerun.
- Ownership/mutation/admin/PostgreSQL batch: **29 passed/1 skipped + sentinel
  PASS**. Deploy provenance/runtime/log-redaction batch after one timezone-shape
  correction: **26 passed/1 skipped + sentinel PASS**.
- Final independent broad VPS freeze candidate: **771 passed/3 skipped +
  sentinel PASS**, 63 seconds. The immediately preceding 770/3/1 run overlapped
  another gate only after the lock helper's 15-minute no-lock degradation and
  is retained as diagnostic, not certification; it exposed and led to removal
  of a legacy test requirement to copy raw provider URLs into application logs.
- First `python tools\gate.py` attempt was **FAIL**, not certification: four
  static deltas (ruff/mypy/i18n/server route-size) were found before the final
  seven long steps completed. They were corrected without baseline increases;
  ruff, mypy, i18n, route-size, compile and diff checks now pass. Local
  Playwright and a post-fix broad VPS **771 passed/3 skipped + sentinel PASS**
  also pass; the full-gate rerun is pending.
- CPU whole-machine snapshot reached 45% during another session's gate; no
  additional test was started then. Recovery snapshot 40%, RAM free 13.4 GiB;
  respect its CPU/PostgreSQL locks and retain two-worker diagnostics.
  Whole-machine samples, not VPS-only attribution.
- Secret scan after documentation freeze: first **3,283 files/790,918 lines**,
  repeat after annotation **3,283 files/790,922 lines**; both **0 finding,
  PASS**.
- Full gate and production E2E pending; partial diagnostics are not
  certification. From the 2026-09-13 cadence decision, no further full gate is
  run between implementation phases: targeted operational suites must all pass,
  then one frozen-candidate gate runs immediately before deploy readiness.
- 2026-09-14 live read-only evidence: PVE 9.2.2 and nine running guests were
  inventoried; VM100–107 plus all eight public/private mappings remained
  protected; WireGuard/nft/storage/network were readable. OVH reported eight
  routed failover IPv4 and zero free Additional IP. Canonical generation
  `2026-09-14T03:06:29Z` mirrored coherently with collector `success`/exit 2;
  bundle integrity was HEALTHY while machine health remained CRITICAL for data
  protection. A subsequent manual refresh hung before publication and was
  terminated cleanly, so it is recorded as failed diagnostic, not evidence.
- The PVE private root CA is stored outside Git. Requests against the management
  IP with exact certificate name `pve` reached HTTP 401 using a deliberately
  invalid token: TLS trust/name passed without exposing a production token.
- Latest TLS/config harness: **105 passed + 201 passed**, RESULT PASS, journal
  `20260914_101533`. Ruff and mypy ratchets pass; latest secret scan covered
  **3,639 files / 891,767 lines**, zero findings. No baseline was accepted.
- First canonical rebase onto `main` `22841303` was clean and Alembic reported
  one head `f4a7c2d9e610`. The first post-rebase broad run found one PO entry
  separator defect; focused correction passed. Broad VPS then passed
  **789/8 skipped + sentinel** (`20260914_105241`). Isolated real PostgreSQL
  migration/default/IP concurrency passed **5/1 skip + sentinel**
  (`20260914_104756`). Canonical `main` moved again before freeze, so these are
  checkpoint evidence rather than the final gate basis.
- Post-rebase Playwright local desktop/mobile passed with no page errors,
  unexpected console errors, failed requests or 5xx responses. Production
  owner lookup returned exactly one canonical user ID without credential output.

The OVH static-pool path now journals/read-backs VM create/config, DHCP plus
bandwidth, mapping, boot and destroy; ambiguous cleanup retains associations in
QUARANTINED. The actual OVH gateway helper is fail-closed and preserves the
protected baseline but is not installed live before the final gate. Dynamic
Vultr paid-IP acquisition remains disabled/STANDBY. Deploy provenance is
operator-visible; Machine B source revision remains `UNKNOWN` in runtime
artifacts rather than substituting a checkout SHA.

## Backup/restore/network resilience

Backup V2 is CAPACITY_BLOCKED; restore and dual-WAN are NOT VERIFIED. Therefore
the program cannot be called FULL PRODUCTION READY even after software work.

## Scorecard

Scores will be measured after implementation. No baseline number is invented.
Dimensions remain separate: implementation quality, live evidence, production
readiness. A P0 blocker is reported directly and never averaged away.

## Git/CI/push

Commits, CI result and push status: pending. Branch will not be auto-merged or
force-pushed.
