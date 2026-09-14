# VPS V4 — Dependencies

| Dependency | Owner/source | Required for | Current evidence/state | Failure behavior |
|---|---|---|---|---|
| PostgreSQL + Alembic | LTTSTUDIOSAPP | profile/default/race safety/journal | Existing; one head `d9a1f6c2b3e5` at discovery | No provisioning |
| Job queue | platform | long operations | Existing/proven | No synchronous fallback |
| Proxmox API | Machine B | compute | PVE 9.2.2 read-only inventory reached; app TLS probe reached HTTP 401 using a deliberately invalid token | Profile unhealthy on transport/auth failure |
| PVE CA | protected production config | TLS trust | Root CA exported outside Git; chain + exact certificate name `pve` verified against management IP | Fail closed; no `verify=False` |
| Machine B artifacts | `H:\PROXMOX` collector | runtime/preflight/provenance | Canonical generation `2026-09-14T03:06:29Z` mirrored coherently; collector success/exit 2, machine health CRITICAL due data protection | UNKNOWN/STALE; cannot activate; repeat immediately before activation |
| OVH Additional IP inventory | OVH API/account | OVH pool/live test | Eight protected IPv4, zero free; exactly one unpaid SG/SGP cart at USD 2.39 including tax | Q125 automatic guarded acquisition integration pending; adopt/revalidate existing cart, no duplicate purchase or inferred order ownership |
| OVH credentials | canonical secret store | inventory/order if required | Read-only signed API ownership/inventory passed; store only credential ref/status | Invalid → preflight fail |
| Gateway SSH host key | canonical secret/config | nft mapping | Strict pinned-key read-only inventory passed | Mismatch fails closed |
| WireGuard/private network | Machine B/gateway | customer path | Fresh read-only baseline: WG active/recent, 8 SNAT + 16 DNAT, exact VM100–107 map | No mutation until helper deployment/read-back |
| Official Windows ISO | PVE storage/config | D08/D43 | Five ISO config variables reported present; exact live media not read back | No VM creation |
| Canonical owner | production DB | D09 | Not queried yet | Zero/multiple → block |
| App-admin extension | platform contract | exact ADMIN IA | C01 approved; local rendered desktop/mobile regression passed | Deploy/browser verification still required |
| Playwright login | PO + test account env | browser E2E | Password must not be typed by agent | Pause at login/MFA/CAPTCHA |
| Backup V2 capacity | Machine B change gate | full production readiness | CAPACITY_BLOCKED (~146 GB shortage at snapshot) | Report separately, no deletion shortcut |

## Credential model

Profile rows use `credential_ref`, for example a stable logical configuration
name. Resolution stays at process/config boundary. UI shows only configured/not
configured, last test time and sanitized result. Replace is an operator procedure
against the canonical secret store until the platform has an approved secure
write contract; no plaintext credential column is introduced.

## Compatibility

The migration preserves `gateway_id`, `vultr_id` and current adapters during
transition. New code reads profile fields for pinned rows, while legacy rows
without sufficient evidence are read-only/NEEDS_REVIEW rather than guessed.
