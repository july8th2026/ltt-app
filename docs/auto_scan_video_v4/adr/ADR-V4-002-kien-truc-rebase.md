# ADR-V4-002 — Per-item durability, the widened DAG, and one billing owner

- **Status:** ACCEPTED (Phase 03, V4)
- **Date:** 2026-09-03
- **Evidence SHA:** `d7f5a73`, branch `phien/asv-v4`
- **Amends:** `docs/auto_scan_video/adr/ADR-001-execution-billing-resource.md` (D2, D4) — amends,
  does not supersede. D1, D3, D5–D10 stand unchanged.
- **Depends on:** `ADR-V4-001` (two presets), `CAPABILITY_INVENTORY_V4.md` (§3)
- **Tests:** `tests/test_427_asv_v4_kien_truc.py`

---

## Context

ADR-001 chose **normalized stage rows, not a JSON checkpoint** (D2), and that choice has held
for twenty phases: two stages finishing at once write different rows and cannot collide.

V4 pushes past what stage rows can express. Three of its requirements need a unit *smaller*
than a stage:

- **G5** — "expensive segment work can checkpoint/reuse valid units".
- **G12** — a bounded per-segment adapt → synthesize → measure loop, reusing valid segments.
- **G14** — repair targets the minimal failed scope, not the whole run.

And Phase 02 found the concrete cost of not having one. `speech.ltt` → `ltt_voice.synthesize`
is a proper public ToolSpec, but **one job produces one file keyed on `job_id`, and
`asv_stage` holds exactly one `job_id` per stage.** V2 could not delegate per-segment TTS, so
it called the declared service functions in-process and tracked progress by *whether the file
existed on disk*. File-existence is a checkpoint with no fingerprint, no cost, no attempt
count and no owner column.

## Decision

### D-V4-10 — Add `AsvWorkItem`: a checkpoint row, not a queue row

```python
class AsvWorkItem(Base):
    __tablename__ = "asv_work_item"

    id:            str(48)   # PK
    run_id:        str(48)   # indexed
    owner_id:      str(36)   # indexed — owner in the COLUMN, not only in the key
    stage:         str(32)   # which stage owns this item
    item_key:      str(64)   # segment id / scene id, unique WITHIN (run, stage)
    status:        str(24)
    attempt:       int
    fingerprint:   str(64)   # same construction as asv_stage.fingerprint
    outputs:       JSON      # asset refs, measured duration, model/engine version
    credit_actual: int       # MEASURED, never priced
    revision:      int       # optimistic concurrency, same pattern as AsvStage
    error:         Text
    started_at / finished_at

    UniqueConstraint("run_id", "stage", "item_key")
```

The unique constraint is the load-bearing part: two concurrent writers cannot create two rows
for the same unit of work, so "did segment 47 already get synthesized" has exactly one answer.

### D-V4-11 — It is provably not a second queue

`V4_OPERATING_CONTRACT` A.5: *"`platform_core.jobs` remains queue SSOT. V4 may add
item/segment checkpoint rows but never a second worker-claim queue."*

A checkpoint table and a queue table differ by **exactly** the columns that let a worker claim
work. So the rule is enforced by their absence, not by intent:

| Forbidden column | What having it would mean |
|---|---|
| `claimed_by` / `worker_id` / `locked_by` | a worker selects work here instead of from `Job` |
| `lease_until` / `visible_at` / `available_at` | a second lease/visibility timer |
| `priority` | a second scheduling policy |
| `heartbeat_at` | a second liveness protocol |

`tests/test_427` asserts none of these names appears in `tables.py`, **and** proves the
detector fires on a synthetic table that has them. A guard over a table that does not exist yet
passes for the wrong reason; the self-test is what makes it mean something before Phase 05.

Positively: items are **written by the stage handler that already holds a platform `Job`**.
Nothing reads `asv_work_item` to decide what to run next. `jobs._nop_giai_doan_san_sang`
remains the only place work is dispatched, and it dispatches stages.

### D-V4-12 — Cost rolls up once, and a stage cannot double-count

ADR-001 D4 froze `actual = Σ asv_stage.credit_actual`, measured never recomputed. V4 adds one
level and one rule:

```
run.credit_actual  = min( Σ stage.credit_actual , run.credit_held )
stage.credit_actual = Σ item.credit_actual        if the stage owns items
                    = its own measured value      otherwise
```

⛔ **A stage that owns items must not also write its own `credit_actual`.** That is the whole
double-count surface, and it is one line to get wrong. Phase 06 owns the enforcement; the
invariant is frozen here.

Retrying a valid item costs **0**: the fingerprint matches, the outputs validate, no engine
runs. This is the same cache rule as D8, one level down.

### D-V4-13 — The DAG widens; the coordinator does not change

`pipeline.CHUOI` grows from 9 stages to ~15 and becomes preset-aware. What does **not** change:

- `_kiem_tra_chuoi()` — the import-time topology check. A broken chain must still explode at
  app load, not while a customer waits.
- `ha_nguon_cua()` — the downstream closure. Its docstring warns that today the closure
  happens to equal "every later stage in `CHUOI`", and that writing `CHUOI[i+1:]` instead
  would be *equal by accident, not by definition*. V4 adds genuinely parallel branches
  (scene/VLM alongside audio/ASR), so the two stop being equal. `test_417` pins both
  directions; it will be what tells us they diverged.
- `jobs._advance` — lock, reconcile, invalidate, submit, re-enqueue. New stages ride it as-is.

Stage names are append-only. A run created under the 9-stage chain keeps its rows and its
`contract_version`; that column exists for exactly this.

### D-V4-14 — Preset lives in `AsvRun.settings`, not in a new column

`settings` is already `JSON` and already carries `timing_mode`/`voice_id`. Adding `preset` and
`voice_mode` there needs no migration and no backfill: a row without `preset` reads as
`localize_preserve_picture`, which **is** what those runs did.

⚠️ The counter-argument, recorded because it is not weak: a first-class column would be
indexable and typed. But V4 never queries runs *by* preset, and a nullable column plus a
backfill on a live table is a migration whose only benefit is aesthetic. Revisit if a real
query appears.

### D-V4-15 — Widen two existing architecture guards that are narrower than they read

`tests/test_421` forbids a second queue (`ThreadPoolExecutor`, `multiprocessing`, schedulers)
and a second GPU lock (`gpu_arbiter`, `gpu_lock`, …). Both scan:

```python
for tep in sorted((APP / "auto_scan_video").glob("*.py")):
```

Two gaps, both invisible from the test's name:

1. **`glob` is not recursive.** `AGENTS.md` §8.1 says multi-domain apps put business rules in
   `services/`, and V4 adds eight domain modules. The first `services/` directory silently
   leaves the guard's field of view.
2. **The three executor apps are not scanned at all** — `asv_media`, `asv_gpu`, `asv_voice`
   each have a `jobs.py` that runs inside a worker, which is precisely where a stray thread
   pool would do damage.

Widened in `test_427` to `rglob` across all four apps. This is a guard-scope fix, not new
policy: the policy was already decided, it just was not looking everywhere it claimed to.

## Consequences

1. Phase 05 owns the migration. `upgrade()` creates one table; `downgrade()` drops it. No
   existing column changes type or meaning.
2. Phase 09 can **re-decide** delegation to `ltt_voice.synthesize`, because per-segment state
   becomes representable. It must decide on evidence — N job rows per run is a real cost, and
   in-process with proper checkpoints may still win.
3. Phase 15's fit loop gets a natural bound: attempts live on the item, so "bounded" is a
   column comparison rather than an in-memory counter that a worker crash resets.
4. Phase 19's RepairPlan targets `(run, stage, item_key)` — the minimal unit that exists.

## Rejected alternatives

| Option | Why not |
|---|---|
| JSON blob of items inside `asv_stage.outputs` | This is D2's rejected option one level down, with the same defect: two workers finishing two segments write the same row and one update is lost. ADR-001 rejected it for stages after `RISK-00-04`; nothing changed to make it safe for items. |
| One child `Job` per segment | Would work, and is the *reason* `speech.ltt` looks unusable. But it puts N rows per run into the platform queue and makes stage-level progress a `COUNT(*)` over jobs. Keep the option open (D-V4-11 does not forbid delegation) — just do not force it before Phase 09 has evidence. |
| Keep file-existence as the checkpoint | It is what V2 does. It carries no fingerprint (so a model-version bump silently reuses stale audio), no cost, no attempt count, and no owner column. G5 and G12 are unachievable on it. |
| A `priority` column "for later" | It is the first column of a scheduler. See D-V4-11. |
