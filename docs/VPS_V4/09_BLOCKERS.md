# VPS V4 — Blockers and Gates

## Active blockers

| ID | Scope | Evidence | Blocks | Unblock action |
|---|---|---|---|---|
| B01 | Exact Admin IA | **RESOLVED 2026-09-13**: PO approved generic admin contract; local browser verified exact menu | No longer an authority blocker | Offline certification still required |
| B02 | Live runtime | **PARTIAL 2026-09-14**: Machine B access, coherent collector generation and app-owned mirror passed; machine health remains CRITICAL for data protection. A later manual refresh hung and was cleanly terminated | Activation requires a newly fresh generation, not the earlier success | Repeat canonical collector immediately before activation; exit 3/hang blocks |
| B03 | PVE TLS | **RESOLVED IN CODE/EVIDENCE 2026-09-14**: private root CA exported outside Git; management-IP transport validates exact cert name `pve`; dummy-token probe reached 401 | Production still needs the two env references installed at deploy | Configure `LTT_VPS_PROXMOX_CA` and `LTT_VPS_PROXMOX_TLS_NAME`; never disable verify |
| B04 | Live free IP | **CONFIRMED 2026-09-14**: OVH has eight routed failover IPv4 and all eight are protected/mapped; free count is zero | One-IP/one-VM live acceptance | Prepare at most one Additional IP order, then stop for manual checkout/payment |
| B05 | Owner canonical ID | **RESOLVED 2026-09-14**: read-only exact-email lookup returned exactly one canonical user ID | No longer blocks live create | Recheck owner active/allowlisted at create-time preflight |
| B06 | OVH mapping driver | Read-only baseline proves actual `gwnat` chains + `/etc/wireguard/anh-xa-ip.txt`. Fail-closed app adapter and root-owned atomic helper are implemented/tested offline | Live gateway mutation/activation | After final app gate, install helper, verify health/list/protected-removal/conflict refusal before any new mapping |
| B07 | Canonical reconciliation | **RESOLVED 2026-09-14**: final rebase onto `f0bd4c05` is complete; branch measured 0 behind/5 ahead and the upstream delta was documentation-only. Broad VPS phase 1 remained 789 PASS/8 skip; authenticated live LLM comparison and skip sentinel are green without a baseline change | No longer blocks final gate | Recheck `main...HEAD` immediately before freezing; a new upstream commit reopens this gate |

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
