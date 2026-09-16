# VPS V4 — Final Report

Status: **IN PROGRESS (16/09) — r1 DEPLOYED; FIRST REAL VPS LIVE WITH ONE OVH IP;
R1–R21 FIXED WITH TARGETED TESTS; SESSION L3 + MAIN MERGE + DEPLOY PENDING
(plan 14 §6 G3–G8)**

## Revisions

- HEAD BEFORE: `3b5adcb7ffa43c8c553ac38d457e22e3cde60e30`
- HEAD AFTER: pending completion of deploy/live/red-team work; no release
  candidate is frozen before those phases.
- Machine B source commits: `4428223` TLS callback fix; `c5c2453` read-only CA
  export; `236d768` safe unpaid-cart preparation
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
- [x] OVH adapter / ACTIVE / DEFAULT
- [x] OVH credential ownership/read-only inventory and public-IP pool sync
- [x] race-safe allocation
- [x] gateway contract + actual `gwnat` adapter/helper installed and refusal-tested live
- [x] profile preflight/health/reconciliation
- [x] Admin profile UI
- [x] web-only policy
- [x] owner-only MVP access
- [x] one OVH IPv4 live (order 22703620, USD 2.39, BOUND, gwnat mapping observed)
- [x] one OVH VPS live with correct owner (`d96b66f3`, VM 204, owner D09 account)
- [ ] Windows installer/disk visible and console (R20 fix awaiting deploy)
- [ ] public/private/WG connectivity (after owner installs Windows)
- [ ] stop/start/restart (soft stop failure measured → R21; re-check after deploy)
- [x] cleanup or explicitly retained state (owner keeps the VPS for real use)
- [x] default switch preserves existing pin
- [x] scoped failure injection/security/secret scan
- [ ] final full gate

## Live test VPS

Created 16/09 17:34 (after one failed attempt refunded 17:33:14):
instance `d96b66f3-3d95-4fa5-8615-5f58801796a7`, VMID 204, profile
`OVH-SGP-PROD` (0402, PINNED), private `10.50.0.50`, one OVH Additional IPv4
(order 22703620, redacted in reports), all seven journal steps OBSERVED after two
guarded operator recoveries (R18 order status, R19 PVE WARNINGS). Kept by the
owner for real use; not destroyed.

## Scorecard (16/09, three separate dimensions — never averaged)

| Dimension | State | Evidence / blocker |
|---|---|---|
| Implementation quality | Strong but not certified | R1–R21 fixed with targeted tests and counterfactuals; static ratchets clean and lowered; **session L3 not yet run** |
| Live evidence | Partial | real create with real IP purchase, refund path, gateway refusal RC 5; console/lifecycle/default-switch/in-guest network pending re-check after deploy |
| Production readiness | **Not FULL PRODUCTION READY** | Backup V2 CAPACITY_BLOCKED, restore drill and dual-WAN unverified; release to `main` pending |

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
  then one frozen-candidate gate runs only after deploy/live/red-team work.
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
- Final reconciliation onto `main` `f0bd4c05` was clean; its last delta was
  documentation-only. The affected upstream LLM test was repaired at
  `15f71050`: it now
  authenticates protected `/health`, reads the deployed `tran.images` schema,
  and fails closed instead of adding an undeclared skip. Authenticated live
  comparison passed **4/4**, skip sentinel PASS, targeted ruff/compile/diff
  PASS, and secret scan **3,650 files / 893,571 lines / 0 findings**.
- The gateway helper was then installed live without changing any mapping.
  Health returned `ok`; protected removal returned RC 5 and a conflicting
  ensure returned RC 4. The protected mapping/config SHA-256 remained
  `5ebaf20b44b74fc7a3379e2d2a7dca2357f70b85f6b33f281fd75ad813241766`.
- The D10 flow prepared exactly one unpaid OVH cart,
  `efae624e-6114-46b9-ace5-3063f9fc1580`, for one SG/SGP Additional IPv4 at
  USD 2.39 including tax. No checkout was submitted. Q130 supersedes manual
  per-order payment approval: automatic cart/checkout/delivery integration is
  being implemented, not enabled yet. The cart expires `2026-09-15T08:53:23Z`.
- Canonical `main` advanced again to `b80f837c`; the VPS branch is currently
  one commit behind/nine ahead. Its main worktree has unrelated uncommitted
  changes, so no reconciliation or deploy was attempted over another session.

The OVH static-pool path now journals/read-backs VM create/config, DHCP plus
bandwidth, mapping, boot and destroy; ambiguous cleanup retains associations in
QUARANTINED. The actual OVH gateway helper is fail-closed and preserves the
protected baseline and is now installed live. Dynamic
Vultr paid-IP acquisition remains disabled/STANDBY. Deploy provenance is
operator-visible; Machine B source revision remains `UNKNOWN` in runtime
artifacts rather than substituting a checkout SHA.

## Backup/restore/network resilience

Q130 checkpoint: reserve-first worker, subscription guard, contract-content
fingerprints, GET-only adoption and durable one-cart/one-instance claim are
implemented. Focused acquisition/capacity/inventory: 43 PASS; isolated real
PostgreSQL migration/concurrency/JSON persistence: 5 PASS. The actual app reader
resolved eight IPs from a historical order through exact IP-service identities;
the actual app cart driver validated the existing one-IP/USD 2.39 cart using a
mutation-prohibited transport. No live checkout, new IP/VM, deploy or final full
gate has occurred; automatic acquisition remains disabled pending rollout.

Backup V2 is CAPACITY_BLOCKED; restore and dual-WAN are NOT VERIFIED. Therefore
the program cannot be called FULL PRODUCTION READY even after software work.

## Scorecard

Scores will be measured after implementation. No baseline number is invented.
Dimensions remain separate: implementation quality, live evidence, production
readiness. A P0 blocker is reported directly and never averaged away.

## Git/CI/push

Commits, CI result and push status: pending. Branch will not be auto-merged or
force-pushed.
