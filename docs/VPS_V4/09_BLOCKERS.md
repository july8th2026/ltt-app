# VPS V4 — Blockers and Gates

## Active blockers

| ID | Scope | Evidence | Blocks | Unblock action |
|---|---|---|---|---|
| B01 | Exact Admin IA | **RESOLVED 2026-09-13**: PO approved generic admin contract; local browser verified exact menu | No longer an authority blocker | Offline certification still required |
| B02 | Live runtime | `H:\PROXMOX` not mounted on current machine | OVH activation/live acceptance | Restore canonical mount/access and run collector |
| B03 | PVE TLS | Production config check reports `LTT_VPS_PROXMOX_CA` missing | Production preflight/compute mutation | Install canonical CA reference, verify hostname/fingerprint |
| B04 | Live free IP | Latest evidence is stale and accounts for eight protected mappings | IP reserve/order decision | Fresh OVH + gateway inventory/readback |
| B05 | Owner canonical ID | Production DB not queried yet | Live create | Read-only exact-email lookup; zero/multiple block |
| B06 | OVH mapping driver | Machine B docs `04-CONG-OVH.md` / `10-VAO-VA-DUNG-GATEWAY.md`: actual `gwnat` chains + `/etc/wireguard/anh-xa-ip.txt`, not legacy `vao/ra` nft maps | OVH gateway mutation/activation | Fresh live baseline plus scoped persistence adapter preserving every protected mapping; current factory rejects `ovh_gwnat` before client construction |
| B07 | Canonical reconciliation | VPS base `3b5adcb7`; main now `73e35319`, with later LLM migrations and an in-progress root-history rewrite in a dirty canonical tree | Handoff/integration/deploy/push | Canonical integrator ports capabilities onto the final current base and reconnects additive migration to head `a3f7c214e8b9`; never merge/push old lineage into rewritten main |

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
