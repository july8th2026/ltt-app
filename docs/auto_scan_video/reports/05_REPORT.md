# PHASE 05 REPORT — App Shell and Dummy Vertical Slice

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 04 **PASS** (23 tests + 1 strict xfail; gate at baseline)
- allowed change scope: Auto Scan customer app, its runtime executor shells, additive
  app-owned tables/migration

## Trace performed

`platform_core/registry.py` (`AppManifest` fields, `discover`, `load_app_tables` 943,
`job_type_owners`) · `platform_core/jobs.py` (`submit`, `claim`, `resolve_handler` 420,
`cancel`, `complete`, `fail`) · `platform_core/job_runner.py` (`JobContext`) ·
`platform_core/db.py:154` (**`expire_on_commit=False`** — see below) ·
`platform_core/app_projects.py:85` (optimistic-concurrency pattern) ·
`apps/anhnoibo/manifest.py` (the `catalog_parent` precedent) · `apps/ltt_voice/tables.py`
(app-table conventions, the `owner_id` trap) ·
`alembic/versions/20260831_1600_voice_du_an.py` (migration shape) ·
`tools/lint_app_contract.py` (`APP_DUOC_DUNG_APP`, `BE_MAT_CONG_KHAI`).

## What was built

| Path | What |
|---|---|
| `apps/auto_scan_video/` | customer app: `manifest`, `tables` (`asv_run`, `asv_stage`), `pipeline` (fixed 9-stage chain), `features` (run lifecycle, money, ownership), `thi_hanh` (shared stage body), `jobs` (the `advance` coordinator), `__init__` (declared public surface) |
| `apps/asv_media/` | hidden runtime executor, `requires=("ffmpeg",)`, 7 stages |
| `apps/asv_gpu/` | hidden runtime executor, `requires=("gpu",)`, 2 stages |
| `alembic/versions/20260901_1800_asv_run_va_stage.py` | additive migration + full downgrade |
| `tests/test_402_asv_mach_doc_gia.py` | 14 tests proving the spine |
| `tools/lint_app_contract.py` | **+2 declared cross-app edges** (see D-05-02) |

## Decisions

**D-05-01 — the fixed chain lives in source, not in the database.**
`pipeline.CHUOI` is a module-level tuple. If the order were data it would be editable, and
that editable place is how Canvas walks in through the back door (I17/O18). A module-level
`_kiem_tra_chuoi()` runs at import so a broken chain fails at **app load**, not while a
paying customer waits.

**D-05-02 — the app-contract linter caught a design error, and the fix was structural.**
The first cut put the stage body in `asv_media/jobs.py` and had `asv_gpu` import
`_chay_giai_doan` from it. `tools/lint_app_contract.py` refused, and it was right: a
leading-underscore name is a private promise, and reaching across apps for it is exactly
what the app contract exists to stop.

The wrong fix was available and easy — declare an exception and move on. Instead the shared
body moved to the app that **owns the run/stage model** (`auto_scan_video/thi_hanh.py`), the
executors became thin routing layers, and the `asv_gpu → asv_media` edge disappeared
entirely. Declared surface is now two names, both public, in both required places
(`BE_MAT_CONG_KHAI` in `__init__.py` **and** `APP_DUOC_DUNG_APP` — the linter demands they
match exactly).

**D-05-03 — `credit_cost` returns 0 for every stage job, permanently.**
Not a placeholder. Only `asv_run` holds money (ADR-001 D4). A stage manifest declaring a
non-zero price would charge the customer twice for the same work — once at the run, once at
the stage — and **the ledger would still balance**, so nothing would look wrong. The
coordinator returns 0 for the same reason, plus one of its own: it re-enqueues itself every
~2 s, so a non-zero price would bill on every tick.

**D-05-04 — job `done` never implies stage `succeeded`.**
`_thu_ket_qua_job_con` deliberately does *not* promote a stage when its child job completes.
Only the stage handler marks success, and only after ADR-001 D7's five steps. If the
coordinator inferred it, a handler that died after the engine returned but before promotion
would produce a "successful" stage pointing at a file that does not exist — I8 violated,
customer receives an empty video. That path instead logs and re-runs.

**D-05-05 — the migration declares UNIQUE inside `create_table`.**
The first version used `op.create_unique_constraint(...)` and **could not run on SQLite**
(`NotImplementedError: No support for ALTER of constraints in SQLite dialect`). Production is
PostgreSQL, so it would have "worked" — while being untestable locally, and the entire test
suite runs on SQLite. A migration that only runs in the one place nobody watches is worse
than one that fails loudly. Inline declaration works on both.

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_402_asv_mach_doc_gia.py` | **14 passed** |
| `pytest` invariant subset (389 + 390) | **23 passed, 1 xfailed** |
| all three Auto Scan files | **37 passed, 1 xfailed** |
| `python tools/lint_app_contract.py` | `ERROR: 0` — **PASS** |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — identical to baseline |

Gate failures, before and after: `bo qua im lang`, `dich thieu ban EN`, `system profile`,
`bo test` (the same four pre-existing `test_306` cases). **No regression** under the Phase 01
§4a-iv contract.

> One honest detour: the first full gate after this phase reported **`FAIL (5/26)`** — a real
> regression, caused by the linter finding described in D-05-02. It is recorded rather than
> quietly fixed, because it is the regression contract doing its job on the very first
> code-writing phase that could trip it.

### Migration + rollback evidence (required work item 9)

```
alembic upgrade head          -> asv_run, asv_stage created
alembic downgrade a5f31c07d2b4-> both dropped; 0 asv_* tables remain; 66 other tables intact
alembic upgrade head          -> recreated, UNIQUE constraint present
```

Single head confirmed (`e1a7c04b93d2`) across 43 migrations. Purely additive: no existing
column or table altered, renamed or dropped (O16).

## Failure injection (required verification)

| Injection | Expected | Observed |
|---|---|---|
| worker lacking GPU capability | GPU stages must not run | `test_lan_ffmpeg_KHONG_nhat_duoc_job_GPU` — ffmpeg stage succeeds, `audio_prepare` stays unclaimed, and a `{gpu}` worker then claims it |
| worker stops mid-run, returns later | resume from the earliest incomplete stage | `test_chay_lai_tiep_tu_giai_doan_dang_do...` — completed stages keep their `attempt` **and** fingerprint |
| cancel mid-run, then a full-capability worker arrives | run stays cancelled | `test_huy_giua_chung_thi_run_KHONG_BAO_GIO_thanh_done` |
| two workers write the same stage row, one holding a stale copy | visible conflict, no silent overwrite | `test_ghi_dong_giai_doan_bang_revision_CU_thi_bi_tu_choi` (two real sessions) |
| estimate too low | clean policy failure, never overspend | `test_tran_chi_chan_truoc_khi_tieu_vuot_hold` |

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I1 queue SSOT | PASS | only `platform_core.jobs`; coordinator re-enqueues (`test_dieu_phoi_KHONG_giu_worker_de_cho_con`) |
| I2 atomic money | PASS | hold + run + stage rows in one transaction |
| I3 one billing owner | PASS | `test_KHONG_job_giai_doan_nao_giu_credit` over all 9 child jobs |
| I4 retry accounting | PASS | M08/M09 + resume test |
| I6 owner isolation | PASS | `test_nguoi_khac_KHONG_doc_duoc_run_du_biet_id`, `owner_id` on every stage row |
| I8 durable DONE | PASS | D-05-04 |
| I9 resume | PASS | resume test compares `attempt` and fingerprint |
| I11 GPU control | PASS | AST guard over 12 real files |
| I12 routing | PASS | ffmpeg-lane test |
| I13 cancellation | PASS | cancel-then-full-worker test |
| I17 fixed model | PASS | `pipeline.CHUOI` in source; server decides order |
| I18 checkpoint concurrency | PASS | separate rows + optimistic revision, both tested |
| I7 | 🔴 RED, Phase 07 | unchanged |
| I5, I10, I14, I19 | PASS at platform layer | Phases 06/12 extend |

## Two findings worth carrying forward

**`platform_core/db.py:154` sets `expire_on_commit=False`.** Three tests failed at first
because the test session kept objects written by a *handler's own session*. That is not a
test artifact to paper over — it means any code re-reading a record another process wrote
must expire first. Documented at the helper that needed it, since Phases 06–17 will hit it
repeatedly.

**A guard that fails on the text explaining the guard is worse than no guard.**
The Phase 04 boundary checks were substring scans, and they flagged `apps/asv_gpu/jobs.py`
— a file whose docstring names `gpu_arbiter` four times *in order to forbid it*. That
teaches the next author to delete the warning for a green light. Rewritten to parse the
**AST**: comments never enter the tree, docstrings are identified and skipped, and non-docstring
string literals still count (`os.environ["CUDA_VISIBLE_DEVICES"]` is a real violation living
in a plain string). The self-test now proves both directions — sensitivity *and* specificity.

## Diff review
- changed paths: `apps/{auto_scan_video,asv_media,asv_gpu}/`, one alembic version,
  `tests/test_402...`, `tests/test_401...` (AST rewrite), `tools/lint_app_contract.py`
  (+2 declared edges), `docs/auto_scan_video/`
- `tools/lint_app_contract.py` is the only file outside Auto Scan's own paths. It is the
  mechanism the linter itself prescribes, and the change is two declarative entries — no
  logic touched
- scratch `tmp_asv_mig.db` created for rollback evidence and deleted
- secret scan PASS in the full gate; no generated artifact or media committed

## Risks / external evidence pending

- **RISK-05-01 (P2, new)** — `asv_gpu.gpu_vram_mb` (4 000 / 6 000 MB) are **estimates**, not
  measurements. The repo's rule is "CHUA DO THI KHONG CHAY". Must be measured in Phases
  09/10 before any engine runs.
- **RISK-05-02 (P2, new)** — merging `phien/asv` back may produce two alembic heads, since
  another lane is adding migrations against the same base. Check `alembic heads` at merge;
  join with a merge revision, never by editing a `down_revision` that has already run.
- **RISK-03-01** (delegated `ltt_llm`/`ltt_voice` param contracts) unchanged — Phase 05 keeps
  CONTENT/VOICE as dummy `asv_media` jobs; `pipeline.CHUOI` is the single line to change.
- Closed: RISK-04-01 — the boundary guards now scan 12 real files and the self-test proves
  the detector both fires and does not over-fire.

## Exit gate

**PASS.**

Gate text: *"PASS only when the dummy vertical slice proves queue, checkpoint, billing,
routing, owner scope and restart semantics end-to-end."*

| Required proof | Evidence |
|---|---|
| queue | 9 stages executed through real `jobs.claim` + `resolve_handler`, no second queue |
| checkpoint | separate stage rows; concurrent writes both persist; stale write rejected |
| billing | one hold on the run; **zero** on all 9 children; settle once; unused refunded; ceiling guard blocks overspend |
| routing | ffmpeg-only worker cannot touch GPU stages; a `{gpu}` worker then claims them |
| owner scope | run unreadable by another user who knows the id; `owner_id` on every stage row |
| restart/resume | completed stages keep `attempt` and fingerprint across a worker gap |
| coordinator does not hold a worker | returns immediately, leaves exactly one follow-up queued |

Explicitly forbidden and confirmed absent: no Whisper, Demucs, real LLM/TTS or render; app is
`enabled=False`, `public=False`, `lifecycle="development"`, executors `surface="runtime"` —
nothing is customer-visible.

## Next phase prerequisites

Phase 06 (Asset Lifecycle & Lineage) inherits:
1. `van_tay()` has the right **shape** but no `engine_id`/model version — Phase 06+ must add
   them, or a model upgrade will silently reuse stale results (O13);
2. stage outputs are dicts of fake keys; Phase 06 makes them real promoted artifacts through
   the D7 five-step protocol;
3. M28 (fingerprint invalidation cascades) becomes writable — `_gom_dau_vao` already carries
   upstream fingerprints so the cascade has something to key on.
