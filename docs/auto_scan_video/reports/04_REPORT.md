# PHASE 04 REPORT — Invariant and Safety Test Harness

**The first phase that writes code.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- pre-existing dirty: none beyond my own untracked `docs/auto_scan_video/`
- previous gate: Phase 03 **PASS** (ADR-001 accepted)
- allowed change scope: tests/fixtures + minimal test-only helpers. **No production change
  was needed** — no test seam had to be opened, so none was.

## Trace performed

`tests/conftest.py` (the `app_thu` synthetic app, `bao_dam_user`, and its warning against
new `autouse` fixtures) · `tests/test_68_credit.py:22` (the temp-SQLite `db` fixture shape
reused here) · `platform_core/jobs.py` (`submit`, `claim`, `cancel`, `defer_resource`,
`mark_provider_dispatched`, `mark_ambiguous`) · `platform_core/credit.py` (`giu_cho`,
`quyet_toan`, `so_da_giu`) · `platform_core/job_runner.py:652` · `platform_core/storage.py`
(`Storage.promote` 80, `LocalStorage.promote` 262) · `platform_core/media.py:probe`.

## Decisions

**D-04-01 — these are tests of the ground, not of the product.**
No Auto Scan code exists yet, so the harness pins the **platform behaviour ADR-001 depends
on**. Every one of those dependencies was previously unprotected by any test that mentions
Auto Scan; if one changed, the failure would surface as a money bug inside a product that
does not exist yet — the worst possible place to discover it.

**D-04-02 — a guard over an empty directory is not a guard.**
The §1 source boundaries in T390 scan `apps/auto_scan_video`, `apps/asv_media`,
`apps/asv_gpu` — none of which exist until Phase 05. Four green lights wired to nothing
would be worse than no lights, so they are paired with
`test_may_do_vi_pham_THUC_SU_bat_duoc_vi_pham`, which fires the same detector at a synthetic
`from gpu_arbiter import current_gpu` and asserts it catches it. A fifth guard
(`test_danh_sach_duong_auto_scan_khop_thuc_te`) fails if `apps/asv_*` ever gains a directory
the list does not watch — the way a boundary quietly stops existing.

**D-04-03 — prove the routing failure, don't just assert the fix.**
`test_app_gop_ca_hai_nang_luc_bi_ca_HAI_lan_le_tu_choi` submits a job for an app declaring
`requires=("ffmpeg","gpu")` and shows a `{ffmpeg}` worker and a `{gpu}` worker **both**
decline it, while a `{ffmpeg,gpu}` worker takes it. That is RISK-00-01/02 reproduced as an
executable fact, which is what makes ADR-001 D5's app split legible to a future reader
instead of looking like architectural taste.

**D-04-04 — one strict RED target, and only one.**
Prompt 04 item 4 mandates a red test for owner-scoped credential allocation.
`test_RED_khoa_rieng_cua_nguoi_dung_khong_duoc_cap_cho_nguoi_khac` is
`xfail(strict=True)`, so when Phase 07 fixes the allocator it fails as *unexpectedly
passing*, forcing a deliberate flip rather than a silent one. Resisted the temptation to
mark the not-yet-buildable items (M26–M32) the same way: a pile of xfails reads as coverage
while asserting nothing. They are listed in `TEST_MATRIX.md` with an owning phase instead.

**D-04-05 — synthetic media only.** `tests/fixtures/asv_media.py` builds fixtures from
ffmpeg `lavfi` sources: no copyright, no PII, no approval question, and reproducible — Phase
01 measured three invocations byte-identical. A cache/fingerprint test (Phase 06+) needs an
input whose identity does not drift. `tiny_mp4_silent()` exists specifically so the
`MVP_CONTRACT.md` §2 "reject a video with no audio at submit" rule can be tested.

## Changes

| Path | Change | Why | In scope? |
|---|---|---|---|
| `tests/test_400_asv_bat_bien_thi_hanh.py` | new, 13 tests | platform guarantees ADR-001 rests on | yes |
| `tests/test_401_asv_ranh_gioi_va_artifact.py` | new, 11 tests | source boundaries + D7 artifact protocol + fixture checks | yes |
| `tests/fixtures/asv_media.py` | new | deterministic tiny media | yes |
| `docs/auto_scan_video/TEST_MATRIX.md` | new | M01–M32 + regression subset | yes |
| `docs/auto_scan_video/reports/04_REPORT.md` | new | closeout | yes |
| `docs/auto_scan_video/STATE.md` | updated | ledger, phase history | yes |

**Zero production files touched** — no `platform_core/`, `server/`, `apps/`, migration or
dependency change.

## Tests

| Command | Before | After | Evidence |
|---|---|---|---|
| `pytest tests/test_400… tests/test_401…` | did not exist | **23 passed, 1 xfailed** | new harness |
| `pytest tests/test_306… + new` | 4 failed | **4 failed, 33 passed, 1 xfailed** | the four are the identical pre-existing `test_306` cases |
| `python tools/gate.py --phien asv` | `FAIL (4/26)` | **`FAIL (4/26)`** | identical step set |

Gate steps failing, before and after: `bo qua im lang`, `dich thieu ban EN`,
`system profile`, `bo test (song song)`. **Same four. No new failure, no new skip.**

Per the Phase 01 §4a-iv regression contract — a regression is any failing step *outside*
that set — **this phase does not regress.** `trung so test` also passed, confirming 389/390
were free numbers.

## Invariant regression

First run of the invariant subset (it is created by this phase):

```bash
python -m pytest tests/test_400_asv_bat_bien_thi_hanh.py tests/test_401_asv_ranh_gioi_va_artifact.py -q
# 23 passed, 1 xfailed in ~2s
```

| Invariant | Result | Evidence |
|---|---|---|
| I2 atomic money | PASS | M03, M04, M05 |
| I3 one billing owner | PASS | M01, M02, M17 |
| I4 retry accounting | PASS | M08, M09 |
| I5 provider ambiguity | PASS | M11 |
| I6 owner isolation (artifact layer) | PASS | M22 |
| I7 credential isolation | 🔴 **RED, owned by Phase 07** | M13 `xfail(strict)` |
| I8 durable DONE | PASS | M20 |
| I11 resource control | PASS (binds Phase 05+) | M14 + M15 |
| I12 worker routing | PASS | M06, M07 |
| I13 cancellation | PASS (job layer) | M10; run layer → Phase 17 |
| I14 safe promotion | PASS | M19, M21 |
| I19 cache privacy | PASS | M12, M22 |
| I9, I10, I18 | not yet testable | need `asv_run`/`asv_stage` → Phases 05/06 |

## Diff review
- changed paths: `tests/` (2 files + 1 fixture module) and `docs/auto_scan_video/`
- no production source, no migration, no dependency, no generated artifact, no media binary
  committed (fixtures are generated into `tmp_path` at run time)
- `secret scan` PASS in the full gate

## Risks / external evidence pending

- **M25** — I1/I18 multi-process proof still `SKIP_MISSING_EXTERNAL`: `test_214` ×7 need
  `LTT_TEST_DATABASE_URL`. PostgreSQL is running locally on 5432, so this is an operator
  decision rather than missing infrastructure. **Blocks G2 before RC**, not Phase 05.
- **RISK-04-01 (P2, new)** — M15–M18 are structural guards over *future* paths. M14 proves
  the detector fires and M18 catches an unwatched directory, but neither can prove the guard
  is well-*scoped* until real code exists. Re-examine at the end of Phase 05.
- Unchanged: RISK-00-02, -06 (M13 owns it), -07 (M15 owns it), -08, -09, -10, -11, -12, -14,
  -15, -16; RISK-01-01; RISK-02-01…03; RISK-03-01…03.

## Exit gate

**PASS.**

Gate text: *"PASS when architecture regressions would be caught before engine code is
migrated."*

Walked each way ADR-001 could be silently violated during Phases 05–16 and checked something
now fails if it happens:

| Way the architecture could be broken | Caught by |
|---|---|
| a stage job starts holding credit | M01, M17 |
| the run gets charged twice | M02, M05 |
| settlement stops refunding, so measured cost becomes unusable | M04 |
| the app is collapsed into one union-`requires` manifest | M07 |
| a migrated engine picks its own GPU | M14 + M15 |
| a paid provider call is retried after an ambiguous dispatch | M11 |
| a partial artifact becomes a durable output | M19, M20, M21 |
| cache reuse crosses a tenant boundary | M12, M22 |
| `core/` legacy gains a new caller | M16 |
| a new `apps/asv_*` escapes the guards entirely | M18 |

Two things the gate does **not** yet cover, stated rather than glossed: run-level
cancellation (I13's second half) and checkpoint concurrency (I18) both need tables that do
not exist until Phase 05. They are M26/M29 in the matrix with owning phases, not silent gaps.

## Next phase prerequisites

Phase 05 (App Shell + Dummy Vertical Slice) creates the first Auto Scan code. On creation:
1. M15–M18 stop being vacuous and start binding — expect them to bite if the shell is built
   carelessly, which is their purpose;
2. `DUONG_AUTO_SCAN` in T390 must match the real directories or M18 fails;
3. M26 (concurrent stage rows), M27 (resume), M30 (ceiling guard) become writable and are
   Phase 05's test backlog;
4. run the invariant subset after every edit, the full gate before declaring done.
