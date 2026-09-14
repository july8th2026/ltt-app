# VPS V4 — Blockers and Gates

## Active blockers

| ID | Scope | Evidence | Blocks | Unblock action |
|---|---|---|---|---|
| B01 | Exact Admin IA | **RESOLVED 2026-09-13**: PO approved generic admin contract; local browser verified exact menu | No longer an authority blocker | Offline certification still required |
| B02 | Live runtime | **PARTIAL 2026-09-14**: Machine B access, coherent collector generation and app-owned mirror passed; machine health remains CRITICAL for data protection. A later manual refresh hung and was cleanly terminated | Activation requires a newly fresh generation, not the earlier success | Repeat canonical collector immediately before activation; exit 3/hang blocks |
| B03 | PVE TLS | **RESOLVED IN CODE/EVIDENCE 2026-09-14**: private root CA exported outside Git; management-IP transport validates exact cert name `pve`; dummy-token probe reached 401 | Production still needs the two env references installed at deploy | Configure `LTT_VPS_PROXMOX_CA` and `LTT_VPS_PROXMOX_TLS_NAME`; never disable verify |
| B04 | Live free IP | **MANUAL BILLING STOP 2026-09-14**: OVH has eight routed/protected IPv4 and zero free. Exactly one unpaid cart `efae624e-6114-46b9-ace5-3063f9fc1580` was prepared for one `ip-failover-arin` in SG/SGP at USD 2.39 including tax; `checkout_performed=false`, expiry `2026-09-15T08:53:23Z` | One-IP/one-VM live acceptance | PO runs the canonical manual checkout flow, accepts the contract/payment, then wait for provider delivery; do not create a second cart or auto-checkout |
| B05 | Owner canonical ID | **RESOLVED 2026-09-14**: read-only exact-email lookup returned exactly one canonical user ID | No longer blocks live create | Recheck owner active/allowlisted at create-time preflight |
| B06 | OVH mapping driver | **RESOLVED LIVE 2026-09-14**: `ltt-gwnat` installed on gateway and health returned `ok`; protected removal RC 5 and conflicting ensure RC 4. Mapping/protected files kept the identical pre/post SHA-256 `5ebaf20b44b74fc7a3379e2d2a7dca2357f70b85f6b33f281fd75ad813241766`; no mapping was mutated | No longer blocks the first new mapping | Re-run health and exact read-back immediately around the one authorized new mapping |
| B07 | Canonical reconciliation | **REOPENED 2026-09-14**: `main...HEAD` measured 1 behind/9 ahead; current `main` is `b80f837c`. Its worktree also contains unrelated uncommitted CMC/decision/plan edits owned by other sessions | Deploy/final frozen-candidate gate | Wait for the owning session to finish, then reconcile once and rerun only affected targeted checks before the single final gate |

## Production-readiness gates, not blockers for multi-profile code

| Gate | State at discovery | Rule |
|---|---|---|
| Backup V2 | CAPACITY_BLOCKED; destination shortage measured | Do not delete old backup; solve capacity under Machine B change gate |
| Restore drill | NOT VERIFIED | Only after verified V2 backup; isolated network; approval for restore boot/downtime |
| Dual WAN | NOT VERIFIED | Backlog unless required; WAN cut needs approval; no UDP load balancing |
| PVE upgrades | 146 pending in stale snapshot | Simulate first; no service/host restart without maintenance approval |
| VirtIO/QGA | Existing protected VMs remain untouched | Test only on new lab VM after primary path passes |
| Zero-touch Windows | DEFERRED | Manual ISO installer is MVP |

## Conditional stop points

Login/MFA/CAPTCHA, unexpected provider billing, production downtime, host reboot,
WAN cut, restore boot and ambiguous destructive ownership. All other safe offline
work continues automatically.
