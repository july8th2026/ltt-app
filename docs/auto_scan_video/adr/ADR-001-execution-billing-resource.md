# ADR-001 — Execution, Billing and Resource model for Auto Scan Video

- **Status:** ACCEPTED
- **Date:** 2026-09-01 (Phase 03)
- **Evidence SHA:** `c31b1ae`, worktree `phien/asv`
- **Supersedes:** nothing. **Depends on:** `MVP_CONTRACT.md` (`auto_scan_mvp_v1`)

---

## Context

`auto_scan_mvp_v1` is nine stages needing four different capability classes, with paid
remote calls in two of them and heavy GPU work in two others. Three choices can corrupt it
before any engine is written: where execution lives, who owns the money, and how a stage
reaches a worker that can actually run it.

---

## Existing mechanisms traced

| Mechanism | Where | Behaviour that matters here |
|---|---|---|
| queue SSOT | `platform_core/jobs.py` | `submit` (99) dedupes on `(user, dedupe_key)` while unfinished; `claim` (144) `FOR UPDATE SKIP LOCKED`; states `queued/running/done/error/cancelled` (`models.py:235-239`) |
| retry & orphans | `jobs.py:337 fail(retry=)`, `379 reclaim_orphans` | attempts/max_attempts + `next_run_at` backoff; running jobs with stale `heartbeat_at` are reclaimed |
| resource deferral | `jobs.py:259 defer_resource` | busy resource → back to `queued`, **not** an error. Delay from `AppManifest.cho_tai_nguyen_for` |
| provider ambiguity | `jobs.py:232/246/274`, `job_runner.py:119/127/573` | `provider_state`, `provider_dispatched_at`, `mark_ambiguous` → terminal `error`, no blind retry |
| money | `credit.py` | `giu_cho(user, amount, job_id)` (260), `quyet_toan(user, job_id, actual)` (393), `hoan` (439), `so_da_giu` (251); stranded-hold sweeps (548/643) |
| settlement hook | `job_runner.py:652` | **no-ops when `so_da_giu(job.id) == 0`** — the property that makes child jobs free |
| run aggregate precedent | `platform_core/agent/*`, `apps/agent/jobs.py` | tick-then-re-enqueue; row-locked checkpoint; one hold on `run.id`; children via plain `jobs.submit` |
| optimistic concurrency precedent | `app_projects.py:85 save` | `UPDATE … WHERE revision = :r`, `rowcount != 1` ⇒ `ProjectConflict` |
| GPU | `gpu_lease.py` `acquire/hold/heartbeat/release/reclaim_orphans`; `gpu.py:103 env_for`; `job_runner.py:97 JobContext.gpu_env` | platform assigns the card; handler receives env |
| artifacts | `storage.py:80 promote`; `upload_sessions.py` `confirm→promote→compensate→sweep→reconcile` | staging→validate→promote already exists |
| app tables | `AppManifest.table_prefix` (`registry.py:315`); `alembic/versions/20260831_1600_voice_du_an.py` | additive `create_table` + full `downgrade` |

---

## Decision

### D1 — Execution: app-owned run aggregate + child `Job` rows. One queue.

`platform_core.jobs` remains the **only** executable queue (O2/I1). Auto Scan adds no
scheduler, no thread pool, no polling loop.

A run is coordinated by a job of its own, `asv.advance`, which **ticks once and re-enqueues
itself** with a short delay while the run is active — copied from `apps/agent/jobs.py:31-37`.
It never blocks a worker waiting for children, which `EXECUTION_GUARDRAILS §1` forbids.

**Rejected: reuse `AgentRun`.** The guardrail permits it "after proving planner/approval/
Canvas semantics do not leak". They do not survive that proof: `AgentRun` carries
`budget_max`, `approved_at`, `approved_by`, `decision_log`, `version` (`models.py:471-477`),
`budget.approve()` *requires* an explicit human approval transition (`budget.py:81`), and the
same table family backs `AgentWorkflow` — Canvas (`models.py:493`). A fixed pipeline has no
plan to approve and no graph to edit. Importing that vocabulary would put O18/I17 one
convenience commit away from being violated. **We take the pattern and leave the table.**

**Rejected: a parent coordinator job that loops until children finish.** Holds a worker for
the whole run; with the default fleet size (= GPU count) two concurrent runs can deadlock the
platform.

### D2 — State: normalized stage rows, not a JSON checkpoint blob

Two tables, prefix `asv_` (`table_prefix="asv"`):

```
asv_run     id, owner_id String(36), status, settings JSON, contract_version,
            credit_held, credit_actual, revision Integer, created_at, finished_at, error
asv_stage   id, run_id, stage, status, attempt, fingerprint, outputs JSON,
            job_id, credit_actual, revision, started_at, finished_at, error
            UNIQUE(run_id, stage)
```

**This is deliberately better than the precedent it copies.** `AgentRun.checkpoint` is a JSON
document read-modify-written by every tick (`executor.py:70-126,261-332`); it is safe *only*
because every writer passes through `runs.get_owned(..., lock=True)` at line 227. That makes
correctness depend on a discipline no type system enforces — RISK-00-04.

One row per `(run_id, stage)` removes the hazard instead of guarding it: **two stages
finishing at the same instant write two different rows and cannot collide at all.**

Concurrency rules (I18, guardrail §7):
- a stage job writes **only its own** `asv_stage` row, guarded by
  `UPDATE … WHERE id = :id AND revision = :r`; `rowcount != 1` ⇒ conflict, retry the read
  (the `app_projects.save` pattern, `app_projects.py:85`);
- `asv_run` has exactly **one** writer, the `asv.advance` coordinator, which takes
  `SELECT … FOR UPDATE` on the run row first;
- `asv.advance` is idempotent and safe to run repeatedly after a crash.

⛔ `owner_id` is `String(36)`, never an integer. `alembic/versions/20260831_1000_voice_owner_uuid.py`
exists because declaring it `BigInteger` once made **every customer share one owner**.

### D3 — Stage ↔ Job state mapping

No second public state machine (guardrail §5). `asv_stage.status` **projects** platform job
states plus two states the platform has no opinion about:

| `asv_stage.status` | Source |
|---|---|
| `pending` | no child job yet (dependencies unmet) |
| `queued` / `running` | mirror of the child `Job.status` |
| `succeeded` | child `done` **and** outputs promoted, validated, fingerprinted |
| `failed_retryable` | child `error` with `attempts < max_attempts`, or `defer_resource` |
| `failed_terminal` | child `error` exhausted, or `mark_ambiguous` |
| `cancelled` | run cancelled |
| `invalidated` | fingerprint mismatch or a durable output vanished (I10) |

Note `succeeded` ≠ `Job.done`. A job finishing is not a stage succeeding — see D7.

### D4 — Billing: one hold on the run, children hold nothing, actual is **measured**

1. At run submit, inside one transaction: create `asv_run`, then
   `credit.giu_cho(db, user_id, estimate, run.id)`. The hold identity is the **run id** —
   legitimate because `giu_cho` keys on an opaque string and `agent/budget.py:90` already
   does exactly this.
2. Stage child jobs are submitted with plain `jobs.submit`, **never**
   `job_submit.submit_with_credit`. They therefore carry no hold, and
   `job_runner._quyet_toan_credit` no-ops on them (`job_runner.py:660`). This is what makes
   parent+child double-charging structurally impossible rather than merely avoided (I3/G3).
3. At terminal, once: `credit.quyet_toan(db, user_id, run.id, actual)`. Unused hold refunds.
4. **`actual = Σ asv_stage.credit_actual`**, each written by the stage from what it really
   consumed (TTS characters, LLM tokens, GPU seconds).

> 🔴 **We do not reuse `agent/executor.actual_cost`, and this is the point of D4.**
> That function recomputes `registry.credit_for(job_type, params) × attempts`
> (`executor.py:130-144`) and *ignores* `result["credit_cost"]`. It prices what was
> **asked for**, not what was **delivered**. CLAUDE.md records this exact defect reaching
> production twice — H38 (fixed 23/08) and H37/D-051 (fixed 24/08: "asked 4 images, machine
> returned 2, customer charged 4"). Auto Scan's per-stage cost is inherently variable, so
> inheriting that function would reproduce a known money bug on day one. RISK-00-05 closed.

**Ceiling guard (I2):** before any stage makes a paid call, assert
`Σ credit_actual + this_stage_estimate ≤ asv_run.credit_held`. Exceeding it fails the stage
`failed_terminal` with a policy reason rather than spending money outside the hold.

**Retries (I4):** a runtime/provider retry of the same stage attempt creates no new hold. It
adds to `credit_actual` only for resources actually consumed — a crash *before* dispatch
costs nothing; an ambiguous dispatch is charged, because the provider may have billed us.
A **user-requested new run** is a new `asv_run` with its own hold. The two are distinguished
by which object exists, not by a flag.

### D5 — Worker routing: one customer app, three hidden runtime executors

Claim eligibility is app-scoped: `set(manifest.requires).issubset(worker_capabilities)`
(`jobs.py:158-164`). Per-`job_type` routing does **not** exist. A single app declaring
`requires=("api","ffmpeg","gpu","voice")` would be claimable only by a lane holding all four
— on a fleet with lanes, most stages would never run.

Evaluated in the order guardrail §3 mandates:
1. *per-job capability routing* — **absent**, confirmed at `jobs.py:158`.
2. *hidden runtime executor apps* — **supported by today's contract**, no core change:
   `surface="runtime"`, `catalog_parent`, `public=False`, and `requires` is a free-form tuple
   (`apps/ltt_voice` invents `"voice"`). Live precedent: `apps/anhnoibo` runs under
   `catalog_parent="taoanh"`.
3. *extend platform core* — **not needed**, therefore not done (O20).

| App | `surface` | `requires` | Stages |
|---|---|---|---|
| `auto_scan_video` | `customer` | `("api",)` | UI + submit + coordinator `asv.advance` |
| `asv_media` | `runtime` | `("ffmpeg",)` | MEDIA_PREPARE, TIMING_ALIGN, COMPOSE, **RENDER**, QC |
| `asv_gpu` | `runtime` | `("gpu",)` | AUDIO_PREPARE (demucs), TRANSCRIBE (whisper) |

All three carry `catalog_parent="auto_scan_video"`; the customer sees **one** product (G1).

**RENDER sits in the ffmpeg lane, not the GPU lane** — a direct consequence of MVP-contract
D-ASV-03 (copy the video stream). The longest stage no longer competes for a card.

**CONTENT_PROCESS and VOICE_SYNTHESIS get no executor of their own.** They submit child jobs
to apps that already own those capabilities:

| Stage | Delegated to | Why delegate rather than wrap |
|---|---|---|
| CONTENT_PROCESS | `ltt_llm.chat` | `requires=("api",)` correctly declared; public API tool; own token-budget authority |
| VOICE_SYNTHESIS | `ltt_voice.synthesize` | `requires=("voice",)` correctly declared; public API tool `speech.ltt`; own tables and lease |

**TRANSCRIBE is wrapped in code, not delegated as a job** — the opposite call, for a specific
reason: `apps/autosubvideo` declares `requires=("ffmpeg",)` while declaring GPU VRAM for
`transcribe`/`diarize` (`manifest.py:47,51` — RISK-00-11). Delegating to it would inherit a
mis-declared manifest and route GPU work to an ffmpeg lane. `asv_gpu` therefore imports the
runner module and declares its own honest `gpu_vram_mb`.

⇒ **Rule: delegate as a child job when the target's manifest is honest and its contract is
public; wrap the code when it is not.**

**Deployment consequence (RISK-00-02):** if `LTT_WORKER_POOLS` is set and lacks a lane for
any of `api` / `ffmpeg` / `gpu` / `voice`, those stages sit `queued` forever with no error.
`setup/4-nghiem-thu.ps1` already asserts this for `voice`; the same assertion must cover the
Auto Scan apps before release.

### D6 — GPU: handlers never choose a card

`asv_gpu` declares `gpu_vram_mb` per `job_type`, measured before it is declared. The platform
acquires the lease (`gpu_lease.hold`), and the handler passes `ctx.gpu_env(base=os.environ)`
to every subprocess. Handlers may not read `CUDA_VISIBLE_DEVICES`, call `nvidia-smi`, or
import anything resembling `gpu_arbiter` (I11/O6).

🔴 **Migration hazard, five known sites:** `Bot_Whisper_FULL/engine/stt.py:274`,
`whisper_integration.py:207`, `Bot_PausePipeline/engine/stt.py:82-89`,
`DUNGVIDEO-FULL/engine/runner.py:697` all call `gpu_arbiter` for card selection. Copying any
of those files without cutting that import re-introduces the legacy plane on a paid path.
Phase 04 adds a static check; `Cut_only ver2/nerf_engine` is clean and needs none.

### D7 — Artifact completion protocol

A stage is `succeeded` only after **all five**, in order (O12/I8/I14):

1. engine returns;
2. output validates (ffprobe/JSON schema/non-zero duration as the stage defines);
3. `storage.promote(staging_key, final_key)` succeeds;
4. durable refs + fingerprint written to `asv_stage`;
5. the transaction commits.

Crash recovery, per gap:
- **1→2**: staging key orphaned; `upload_sessions.sweep` reclaims it. Stage re-runs.
- **2→3**: same.
- **3→4**: promoted object exists but nothing references it. On re-run the fingerprint is
  recomputed and the object is overwritten at the same deterministic key — the write is
  idempotent because the key is derived from the fingerprint, not from a timestamp.
- **4→5**: rolled back with the transaction; identical to 3→4.

**No stage may write into another stage's namespace.** Keys are
`asv/{owner_id}/{run_id}/{stage}/{fingerprint}.{ext}`.

### D8 — Fingerprint and cache

```
fingerprint = sha256(
    stage_name, contract_version="auto_scan_mvp_v1",
    engine_id + engine_version,          # model/binary identity
    canonical_json(effective_settings),  # only settings this stage reads
    upstream_output_refs_with_hashes,    # lineage, not just filenames
)
```

A cache hit requires **fingerprint match AND every referenced durable output still exists and
validates** (I10). A filename existing is not cache validity (O13). A missing or corrupt
output invalidates that stage and everything downstream of it.

**Cache lookup is filtered by `owner_id` unconditionally** (I19, guardrail §8). Two customers
uploading the identical file compute identical fingerprints, and MVP still recomputes for
each. Cross-tenant reuse would leak the existence and content of one customer's material to
another and is forbidden without a separate privacy ADR.

### D9 — Cancellation

`cancel` sets `asv_run.status = cancelled` under the run row lock, then cancels non-terminal
child jobs (`jobs.cancel`, which only acts on `queued`/`running`).

**A late child completion can never resurrect the run** (I13/G10): `asv.advance` re-reads
`asv_run.status` under the lock at the top of every tick and returns immediately if terminal.
A stage row may still be written to `succeeded` after cancellation — that is honest, the work
did happen — but the run stays `cancelled` and settles once at cancellation time.

### D10 — Migration and rollback

Additive only (O16). One migration creating `asv_run` and `asv_stage`, with a `downgrade()`
that drops both tables and their indexes — the shape of
`alembic/versions/20260831_1600_voice_du_an.py`. No existing column or table is altered,
renamed or dropped, so rollback is `alembic downgrade` plus removing the app directories.

---

## Invariants protected

| Inv | Owner mechanism | Planned test (Phase 04) |
|---|---|---|
| I1 | D1 — only `platform_core.jobs` claims | assert no second claim path; `asv.advance` re-enqueues rather than blocks |
| I2 | D4 — hold and run created in one transaction | rollback leaves neither |
| I3 | D4 — children use `jobs.submit`; `_quyet_toan_credit` no-ops at zero hold | assert `so_da_giu(child.id) == 0` for every stage job |
| I4 | D4 — retry adds no hold; new run = new hold | retry a stage, assert holds unchanged |
| I5 | D5/D6 — delegated apps use `provider_dispatched/rejected`; ambiguous ⇒ terminal | inject crash after dispatch, assert no auto-retry |
| I6 | D2 `owner_id` + server-side resolution everywhere | user B cannot read A's run/stage/output by UUID |
| I7 | unchanged allocator; Auto Scan uses the platform pool only | see ADR-002 (Phase 07) |
| I8 | D7 five-step completion | kill between each pair of steps |
| I9 | D2/D3 — resume from earliest non-`succeeded` stage | restart mid-run |
| I10 | D8 fingerprint + existence check | corrupt an output, assert invalidation cascades |
| I11 | D6 — `ctx.gpu_env`, no `gpu_arbiter` | static check over Auto Scan paths |
| I12 | D5 — narrow `requires` per executor | assert each job type's app requires exactly its capability |
| I13 | D9 — status re-read under lock | complete a child after cancel, assert run stays cancelled |
| I14 | D7 — promote before reference | partial temp file never referenced |
| I18 | D2 — one row per stage + optimistic revision | two concurrent stage completions, assert both persist |
| I19 | D8 — owner-scoped lookup | same fingerprint, two owners, two computations |

---

## Compatibility impact

None to existing apps. No `platform_core/` or `server/` file is modified. No allocator
behaviour changes (O15, Prompt 03 "explicitly forbidden"). Three new app directories and one
additive migration.

---

## Tests required before Phase 05 closes

1. child stage jobs hold zero credit;
2. run settles exactly once, and `actual` reflects **reported** cost, not recomputed price;
3. exceeding the hold fails the stage instead of spending;
4. two stages completing concurrently both persist (I18);
5. each executor's `requires` is a strict subset of its stages' real needs;
6. cancel-then-late-completion leaves the run cancelled;
7. a run whose `LTT_WORKER_POOLS` lane is missing is detectable at startup, not at runtime.

---

## Alternatives rejected

| Option | Why rejected |
|---|---|
| Reuse `AgentRun` + `agent/executor` | imports approval/budget/Canvas vocabulary into a fixed pipeline (O18/I17); its JSON checkpoint is lost-update-prone without an external discipline |
| Single app, `requires=("api","ffmpeg","gpu","voice")` | claimable only by a lane holding all four; starves API stages behind GPU capacity |
| Per-stage credit holds | parent+child double hold; forbidden by I3 |
| Extend `jobs.claim` with per-job capabilities | a platform-core change when an app-level answer exists (O20); `surface="runtime"` already solves it |
| JSON checkpoint on the run row | RISK-00-04; normalized rows remove the hazard rather than guarding it |
| Content-addressed cross-tenant cache | leaks one customer's material to another (I19) |
| Delegate TRANSCRIBE to `autosubvideo.transcribe` | inherits a manifest that declares `ffmpeg` while needing GPU (RISK-00-11) |
