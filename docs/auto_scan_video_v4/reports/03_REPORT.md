# PHASE 03 REPORT — REBASE CLASSIFICATION AND ARCHITECTURE ADR

## Verdict

**PASS**

## Source / HEAD

`phien/asv-v4` @ `d7f5a73` (Phase 02 commit) + this phase's diff.

## Objective

Classify every current ASV module as KEEP/EXTEND/REFACTOR/REMOVE/ADD, freeze the migration
architecture with no big-bang rewrite, and encode the forbidden dependencies as static guards.

## Changed paths

| Path | Kind |
|---|---|
| `docs/auto_scan_video_v4/REBASE_MAP_V4.md` | new — all 33 modules + 8 new + migration order |
| `docs/auto_scan_video_v4/adr/ADR-V4-002-kien-truc-rebase.md` | new — `AsvWorkItem`, DAG, billing |
| `tests/test_427_asv_v4_kien_truc.py` | new — 16 checks |
| `docs/auto_scan_video_v4/STATE_V4.md` | phase row |
| `ho_so_he_thong.txt` | regenerated |

No app code, no platform code, no migration — Phase 03 forbids implementation migration.

## Before -> After

| | Before | After |
|---|---|---|
| module fates | undecided | **17 KEEP · 6 EXTEND · 7 REFACTOR · 8 ADD · 0 REMOVE** |
| per-segment durability | file-existence on disk | `AsvWorkItem` designed, with `UNIQUE(run_id, stage, item_key)` |
| "no second queue" | policy in prose | plus a schema guard listing the 8 columns that would make it one |
| queue/GPU guards | 1 app, non-recursive | 4 apps, recursive |
| billing roll-up | run ← stage | run ← stage ← item, with the double-count rule named |

## Contracts / migrations

`AsvWorkItem` is **designed, not created**. Phase 05 owns the migration: `upgrade()` creates
one table, `downgrade()` drops it, no existing column changes type or meaning. `preset` and
`voice_mode` go into the existing `AsvRun.settings` JSON — no migration, no backfill, and a row
without `preset` reads as `localize_preserve_picture`, which is what those runs actually did.

## Tests and commands

```bash
python -m pytest tests/test_427_asv_v4_kien_truc.py -q          # 16 passed in 0.60s
python -m pytest tests/test_421… tests/test_400… tests/test_417… \
                tests/test_425… tests/test_426… tests/test_427… -q
```
→ **112 passed, 1 xfailed in 73.66 s**

```bash
python tools/gate.py --quick --phien asv-v4
```
→ **`RESULT: PASS`**

## The two guards that read wider than they were

`tests/test_421` forbids a second queue and a second GPU lock. Correct policy; both scan:

```python
for tep in sorted((APP / "auto_scan_video").glob("*.py")):
```

Two gaps, neither visible from the test names:

1. **`glob` is not recursive.** `AGENTS.md` §8.1 requires multi-domain apps to put business
   rules in `services/`, and the rebase map adds eight domain modules. The first `services/`
   directory silently leaves the guard's field of view — with no error, while the test name
   still reads as though it is watching.
2. **The three executor apps are not scanned at all.** `asv_media`, `asv_gpu` and `asv_voice`
   each run a `jobs.py` **inside a worker process** — the exact place a stray `ThreadPoolExecutor`
   would do the most damage.

`test_427` §1 widens both to `rglob` across all four apps, and
`test_tam_nhin_mo_rong_THAT_SU_rong_hon` asserts the new file set is a **strict superset** of
the old one. Without that assertion §1 could be a re-run of `test_421` under a different name:
same cost, zero added protection.

This is not new policy. The policy was already decided in V2 — it just was not looking
everywhere it claimed to.

## Self-review findings (hostile pass)

**Did I duplicate `test_421`?** That was the live risk, and it is why
`test_tam_nhin_mo_rong_THAT_SU_rong_hon` exists: it fails if the widened scan returns the same
files. Stated in the file's own docstring so a reader does not assume overlap is intentional.

**Is the schema guard a green light wired to nothing?** Today, yes on its own —
`AsvWorkItem` does not exist, so `test_khong_bang_ASV_nao_mang_cot_cua_mot_hang_doi` runs over
a near-empty set. Paired with `test_bo_do_cot_hang_doi_that_su_bat_duoc`, which runs the
detector over a synthetic table carrying `claimed_by` + `lease_until` and asserts it fires,
**and** over a legitimate checkpoint table and asserts it stays quiet. Both directions, because
a detector that fires on everything is as useless as one that fires on nothing.

**Did the column detector repeat Phase 02's text-scan mistake?** No, and deliberately so:
`_ten_cot` walks the AST. The forbidden column names are quoted in `ADR-V4-002` and will be
quoted in `tables.py` when Phase 05 explains their absence — a text scan would flag the very
comment that documents the rule.

**Did I broaden scope?** No implementation, no migration, no engine touched. Two docs, one test
file.

**Did I rebuild something proven?** The default in the rebase map is KEEP, and 17 of 33 modules
take it. The coordinator (`jobs.py`), the canonical transcript (`ban_ghi.py`), the reference
re-verification before spending a render slot (`giai_doan_ban_dung.py`) and the LTT Voice
adapter (`giong_noi.py`) are explicitly untouched.

**Where could a worker crash leave a false DONE?** The item table inherits the stage protocol:
an item is written by the handler that already holds a platform `Job`, after validate and
promote. Nothing infers success from `job.status == done` — the rule `_thu_ket_qua_job_con`
enforces at stage level is what item rows must follow, and Phase 05 owns proving it.

## The design decision, and the one I argued against myself

`AsvWorkItem` is a **checkpoint** table. The rule that keeps it one is enforced by absence:
eight column names (`claimed_by`, `worker_id`, `locked_by`, `lease_until`, `visible_at`,
`available_at`, `priority`, `heartbeat_at`) are exactly what would let a worker select work
from it instead of from `Job`.

I considered and rejected `priority` "for later". It is the first column of a scheduler, and
`V4_OPERATING_CONTRACT` A.5 allows checkpoint rows and forbids a second worker-claim queue —
the distinction is not a matter of degree.

The alternative that is **not** weak, and is deliberately left open: one child `Job` per
segment. That would work, and it is the reason `speech.ltt` currently looks unusable. It costs
N queue rows per run and turns stage progress into a `COUNT(*)` over jobs. D-V4-11 does not
forbid it — Phase 09 decides, on evidence, once per-segment state is representable at all.

## Risks / external evidence

No new external evidence required. No new risks; V4-R14 (unexported sample-voice catalogue)
gains a scheduled home — Phase 09, after Phase 05.

## Exit gate proof

> *PASS when the migration can proceed incrementally and rollback/compatibility strategy is
> explicit.*

| Requirement | Evidence |
|---|---|
| 1. file/module-level rebase map | `REBASE_MAP_V4.md`, all 33 modules; `test_427` fails if any module is missing from it |
| 2. KEEP proven foundations | 17 KEEP, 0 REMOVE; the default is KEEP and the exceptions are argued |
| 3. mark private AI reach-throughs | **none exist** (Phase 02); recorded rather than invented |
| 4. `AsvWorkItem` decision | D-V4-10/11/12: schema, `UNIQUE(run_id, stage, item_key)`, revision, owner column, fingerprint, measured cost, and proof it is not a queue |
| 5. freeze DAG / names / versioning / migration compat | D-V4-13/14; stage names append-only, `contract_version` carries old runs, preset in existing JSON |
| 6. one-parent billing, measured child usage | D-V4-12 with the double-count rule named; `test_quyet_toan_van_do_chu_khong_tinh_lai` pins that settlement reads measured totals and calls no pricing function |
| 7. architecture lint for forbidden deps | `test_427` §1 §2, each with a self-test proving the detector fires |
| rollback explicit | new table ⇒ `downgrade()` is `drop_table`; no column changes meaning |

**PASS → continue automatically to Phase 04.**
