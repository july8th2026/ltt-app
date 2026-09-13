# VPS V4 — Dependencies

| Dependency | Owner/source | Required for | Current evidence/state | Failure behavior |
|---|---|---|---|---|
| PostgreSQL + Alembic | LTTSTUDIOSAPP | profile/default/race safety/journal | Existing; one head `d9a1f6c2b3e5` at discovery | No provisioning |
| Job queue | platform | long operations | Existing/proven | No synchronous fallback |
| Proxmox API | Machine B | compute | Existing config; live freshness unavailable | Profile unhealthy |
| PVE CA | protected production config | TLS trust | `LTT_VPS_PROXMOX_CA` missing | Fail closed; no `verify=False` |
| Machine B artifacts | `H:\PROXMOX` collector | runtime/preflight/provenance | H: unavailable; repo snapshot stale | UNKNOWN/STALE; cannot activate |
| OVH Additional IP inventory | OVH API/account | OVH pool/live test | Snapshot shows protected mapped set, no live free count | No allocation/order by guess |
| OVH credentials | canonical secret store | inventory/order if required | Store only credential ref/status | Invalid → preflight fail |
| Gateway SSH host key | canonical secret/config | nft mapping | Existing architecture | Mismatch fails closed |
| WireGuard/private network | Machine B/gateway | customer path | Healthy only in stale snapshot | No live acceptance |
| Official Windows ISO | PVE storage/config | D08/D43 | Five ISO config variables reported present; exact live media not read back | No VM creation |
| Canonical owner | production DB | D09 | Not queried yet | Zero/multiple → block |
| App-admin extension | platform contract | exact ADMIN IA | Missing | C01; app-local work only |
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
