# LTT VIDEO ARCHITECTURE V2.1 — WanGP ONE ENGINE

## 1. Runtime target

```text
USER/STAFF
   ↓
LTT VIDEO GUI
   ↓
A-CONTROL
 ├ Auth / Role / App access
 ├ LTT Job Queue
 ├ User media ownership
 ├ R2 / History
 ├ Task Resolver
 ├ Quality Profile Resolver
 ├ WanGP Client
 └ Cloud Lifecycle
   ↓ private authenticated integration
C-CLOUD
 ├ WanGP Runtime
 ├ WanGP API/MCP
 ├ Deepy Prime
 ├ Selected Models
 ├ Pre/Postprocess
 └ GPU
   ↓
LTT R2 result
```

## 2. Critical design rules

### A. LTT queue is source of truth
WanGP queue is only an execution queue local to C-CLOUD.

### B. WanGP WebUI is optional
It is enabled only for:
- POC;
- benchmark;
- admin/debug.

Employees do not need it.

### C. WanGP Client is the only Video Engine interface
No generic “provider cascade” for Video V2.

Conceptual interface:

```text
health
capabilities
stage_media
submit
progress
cancel
result
cleanup
```

Only one implementation after cutover:
`WanGPVideoEngine`.

### D. Stable profile boundary
LTT browser never sends arbitrary WanGP widget/settings blobs.

`profile_id` maps to tested WanGP model/template/settings.

Two profile classes:

1. **Verified Baseline Profile**
   - produced in P02;
   - proves the task works;
   - used to build/integrate LTT path.

2. **Optimized Quality Profile**
   - produced in P07;
   - benchmark winner;
   - replaces baseline profile as default.

This prevents circular dependency where GUI needs a profile before quality benchmarking exists.

## 3. Canonical request

```json
{
  "contract_version": "ltt-video-wangp/1",
  "job_id": "uuid",
  "profile_id": "ltt.video.i2v.baseline.v1",
  "prompt": "string",
  "media": [
    {"role": "start_image", "storage_key": "ltt-owned-key"}
  ],
  "overrides": {
    "aspect_ratio": "16:9",
    "duration_s": 5,
    "seed": -1
  }
}
```

A-CONTROL resolves owned storage key to a scoped transfer mechanism.
Browser never supplies trusted user identity or arbitrary cloud paths.

## 4. Canonical result

Job is not `done` until output is verified in LTT-owned storage.

```json
{
  "job_id": "uuid",
  "status": "done",
  "outputs": [
    {"storage_key": "...", "media_type": "video"}
  ],
  "runtime": {
    "engine": "wangp",
    "wangp_sha": "...",
    "profile_id": "..."
  },
  "metrics": {
    "generation_seconds": 0,
    "measured_cost_usd": 0
  }
}
```

## 5. Media boundary

```text
Browser
  → LTT upload
  → ownership recorded
  → R2
  → short-lived/scoped transfer
  → C-CLOUD scratch / WanGP
  → generation
  → scoped result transfer
  → R2
  → verify
  → mark done
  → cleanup C-CLOUD scratch
```

Forbidden on C-CLOUD:
- DB password;
- LTT session signing secret;
- R2 master key;
- unrestricted user credentials.

## 6. Agent

Deepy Prime is the first agent.

Deepy may:
- understand user request;
- discover model capability when needed;
- use curated templates;
- plan multi-step generation.

LTT still owns:
- allowed profile/task;
- permissions;
- media ownership;
- cost/budget;
- release gate.

## 7. Cloud lifecycle

Cloud lifecycle is implemented **after real engine integration**, not used as a P02 deletion prerequisite.

Before automation, P01/P02 may start/stop a test Pod manually with strict cost controls.

Final automated lifecycle:

```text
STOPPED
  → STARTING
  → HEALTHY
  → BUSY
  → IDLE
  → STOPPED
```

A first queued LTT job may trigger start.
Health means WanGP + required profile/model ready, not merely provider “RUNNING”.

## 8. Deletion/cutover rule

Physical source deletion happens only after P05 REAL LTT↔WanGP integration passes.

Sequence:
1. P02 proves WanGP engine capability.
2. P03 locks one-engine architecture and creates restore point.
3. P04 builds clean LTT app/client with no legacy fallback.
4. P05 proves real LTT/R2/cancel path.
5. P06 cuts over and deletes legacy runtime source.
6. P07 optimizes quality/Deepy.
7. P08 automates cloud lifecycle.
8. P09 final E2E.

Git history/tag is archive. Production source is not.
