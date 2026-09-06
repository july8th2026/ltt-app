# Decision Register V2.1

## LOCKED

### D-V2-001 — One engine
After cutover, Video engine = WanGP only.

### D-V2-002 — Native LTT GUI
LTT GUI is the employee-facing product UI.

### D-V2-003 — WanGP WebUI not production user path
WebUI is operator/debug/benchmark only.

### D-V2-004 — A-CONTROL owns product state
Auth, user, jobs, ownership, R2, history, budget and cloud lifecycle stay in LTT.

### D-V2-005 — C-CLOUD owns execution
WanGP + Deepy + models + GPU execute on C-CLOUD.

### D-V2-006 — Profiles
Verified baseline profiles first; optimized quality profiles later.

### D-V2-007 — Deepy first
No parallel LTT agent before Deepy benchmark.

### D-V2-008 — B-LAN protected
Video V2 does not use or modify B-LAN.

### D-V2-009 — Delete legacy after replacement E2E
WanGP engine capability alone is insufficient for deletion.
Real LTT↔WanGP/R2/cancel path must PASS first.

### D-V2-010 — No runtime fallback
During replacement development legacy may still exist in Git/source,
but new V2 code cannot call/cascade/fallback to it.

### D-V2-011 — Internal-only
Commercial/public gate CLOSED.

## OPEN
- O-001: direct MCP vs thin cloud bridge after P02 evidence.
- O-002: exact GPU/region.
- O-003: local vs remote Deepy LLM.
- O-004: optimized model winners.
- O-005: idle TTL.
