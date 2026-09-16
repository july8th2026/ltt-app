# VPS V4 — Test Matrix

| Area | Positive | Negative/failure | Live/read-back |
|---|---|---|---|
| Profile model | create all four states | invalid state; ACTIVE without accept; >1 default | DB inventory |
| Default | healthy ACTIVE becomes default | unhealthy/STANDBY/default race rejected | switch OVH→Vultr→OVH |
| Pinning | profile stored before enqueue | default changes mid-job; submitted profile ignored/rejected | existing OVH VM remains pinned |
| Legacy migration | evidenced Vultr row backfilled | ambiguous row NEEDS_REVIEW | production read-only counts |
| Compute contract | create/status/lifecycle delegation | timeout/task fail/response lost | one blank VM outside 100–107 |
| Vultr adapter | existing allocate/bind/unbind/release semantics | ownership mismatch/timeout | No paid resource required |
| OVH pool | reserve/bind/unbind/release/read | duplicate concurrent reserve, wrong owner, quarantine | provider inventory/readback |
| Gateway | ensure/get/verify/remove mapping | unreachable/conflict/wrong private IP/host-key mismatch | nft/WG readback |
| Mutation journal | intent→observed→complete | worker death after VM/IP/map; DB commit fail | reconcile external refs |
| Provision flow | exact sequence and final observed state | disabled profile mid-job; PVE failure | web-created VM |
| Reconciliation | all canonical finding codes | ambiguous never auto-deletes | DB/provider/gateway/PVE agree |
| Health/runtime | per-profile healthy fresh generation | stale/mixed/schema/collector fail/invalid creds | collector and provider live |
| Capacity | min(compute, IP, gateway) | unreadable component = zero/fail closed | compare live inventory |
| Ownership | owner sees/operates own VM | user A cannot see/operate B | D09 owner readback |
| Web only | session web works | no ToolSpec/catalog/API route; API key cannot mutate | production route probes |
| Customer input | region/plan/OS accepted | provider/profile/gateway mass-assignment rejected | browser form has no field |
| Admin | authorized action + audit | non-admin/CSRF fail; secret redaction | rendered page after C01 |
| Windows | ISO attached/installer/disk visible | missing/untrusted ISO fails before create | console screenshot, no secret |
| Lifecycle | stop/start/restart operation + UPID | task failure cannot report success | actual/DB/UI agree |
| Protected set | new VMID allowed | any VM100–107 mutation rejected | inventory unchanged |
| Security | errors/logs sanitized | secret-like input never emitted; TLS/key mismatch | secret scan 0 |

## Required failure injection points

VM create, private IP/DHCP, public-IP reserve, provider bind where applicable,
gateway mapping and final DB commit. Each test asserts external change, durable
journal state, retry behavior, compensation and reconciliation outcome.

## Verification layers

1. Unit/contract tests with deterministic fakes.
2. PostgreSQL integration for locking, partial indexes and concurrent workers.
3. Existing VPS regression to protect strong V2 behavior.
4. Full repository gate.
5. Fresh live read-back and Playwright UI flow; console errors and failed network
   requests must both be zero except explicitly asserted negative requests.

No offline test is reported as live evidence.
