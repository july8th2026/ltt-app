# AUTO SCAN VIDEO — TEST MATRIX

Opened Phase 04. `T389` = `tests/test_400_asv_bat_bien_thi_hanh.py`,
`T390` = `tests/test_401_asv_ranh_gioi_va_artifact.py`.

## Invariant regression command subset

```bash
python -m pytest tests/test_400_asv_bat_bien_thi_hanh.py tests/test_401_asv_ranh_gioi_va_artifact.py -q
```

Run after **every** Auto Scan change, before the full gate. Currently ~2 s.

Full verdict stays `python tools/gate.py --phien asv` in `D:\LTTSTUDIOSAPP-asv`, compared
against the Phase 01 regression contract: a regression is any failing step **outside**
`{bo qua im lang, dich thieu ban EN, system profile, bo test::test_306}`.

## Matrix

| ID | Invariant / feature | Unit | Integration | Real runtime | Failure injection | Required by phase | Status / evidence |
|---|---|---|---|---|---|---|---|
| M01 | I3 child jobs hold no credit | ✅ T389 | — | — | — | 04 | PASS |
| M02 | I3 settlement no-ops at zero hold | ✅ T389 | — | — | — | 04 | PASS |
| M03 | I2 hold keyed on a run id (not a job id) | ✅ T389 | — | — | — | 04 | PASS |
| M04 | I2 settling below the hold refunds the rest | ✅ T389 | — | — | — | 04 | PASS |
| M05 | I2 settlement is idempotent | ✅ T389 | — | — | — | 04 | PASS |
| M06 | I12 claim filters by `manifest.requires` | — | ✅ T389 | — | — | 04 | PASS |
| M07 | I12 a union-`requires` app is rejected by **both** narrow lanes | — | ✅ T389 | — | — | 04 | PASS — proves *why* D5 splits the app |
| M08 | I4 busy resource re-queues, burns no attempt | — | ✅ T389 | — | — | 04 | PASS |
| M09 | I4 dedupe returns the running job | — | ✅ T389 | — | — | 04 | PASS |
| M10 | I13 a cancelled job is never re-claimed | — | ✅ T389 | — | ✅ | 04 | PASS |
| M11 | I5 ambiguous dispatch is terminal, never retried | — | ✅ T389 | — | ✅ | 04 | PASS |
| M12 | I19 identical content, two owners ⇒ two jobs | — | ✅ T389 | — | — | 04 | PASS |
| M13 | **I7 user-owned key must not go to another user** | ✅ T389 | — | — | — | **07** | 🔴 **RED (`xfail strict`)** — RISK-00-06 |
| M14 | detector for §1 source guards actually fires | ✅ T390 | — | — | — | 04 | PASS — keeps M15–M18 non-vacuous |
| M15 | I11 Auto Scan never selects a GPU itself | ✅ T390 | — | — | — | 04 | PASS (binds Phase 05+) |
| M16 | O9 Auto Scan never imports `core/` | ✅ T390 | — | — | — | 04 | PASS (binds Phase 05+) |
| M17 | I3 stage code never calls `submit_with_credit` | ✅ T390 | — | — | — | 04 | PASS (binds Phase 05+) |
| M18 | guard path list matches real `apps/` | ✅ T390 | — | — | — | 04 | PASS |
| M19 | I14 `promote` moves and deletes staging | ✅ T390 | — | — | — | 04 | PASS |
| M20 | I8 `promote` with no staging raises, creates nothing | ✅ T390 | — | — | ✅ | 04 | PASS |
| M21 | D7 same-fingerprint rewrite is idempotent | ✅ T390 | — | — | ✅ | 04 | PASS |
| M22 | I6/I19 artifact keys carry owner + run | ✅ T390 | — | — | — | 04 | PASS |
| M23 | fixture has both streams | ✅ T390 | — | ✅ ffmpeg | — | 04 | PASS |
| M24 | fixture without audio exists (for the §2 reject rule) | ✅ T390 | — | ✅ ffmpeg | — | 04 | PASS |
| M25 | I1/I18 multi-process invariants | — | — | ⛔ needs PG | — | 17 | **SKIP_MISSING_EXTERNAL** — `test_214` ×7 need `LTT_TEST_DATABASE_URL` |
| M26 | I18 two stage rows persist concurrently | — | ⏳ | — | ⏳ | **05** | not yet — needs `asv_stage` |
| M27 | I9 resume from earliest invalid stage | — | ⏳ | — | ⏳ | **05** | not yet |
| M28 | I10 fingerprint invalidation cascades | — | ⏳ | — | ⏳ | **06** | not yet |
| M29 | I13 late child completion cannot un-cancel a run | — | ⏳ | — | ⏳ | **17** | not yet |
| M30 | ceiling guard: exceeding the hold fails, never overspends | — | ⏳ | — | ⏳ | **05** | not yet — RISK-03-02 |
| M31 | delegated `ltt_llm` / `ltt_voice` accept our params | — | ⏳ | ⏳ | — | **11/12** | not yet — RISK-03-01 |
| M32 | QC can block delivery | — | ⏳ | ⏳ | ⏳ | **18** | not yet |

## Notes on what is deliberately *not* here

- **No test of Auto Scan code**, because none exists. T389/T390 pin the platform behaviour
  ADR-001 relies on, plus guards that begin biting the moment Phase 05 creates the app
  directories.
- **M13 must not be made green by weakening it** (Prompt 04, explicitly forbidden). It is
  `xfail(strict=True)`, so if Phase 07 fixes the allocator the test *fails as unexpectedly
  passing* — forcing whoever fixes it to flip the marker deliberately rather than silently.
- **M14 exists because M15–M18 scan a directory tree that is currently empty.** A guard over
  nothing passes regardless of what it asserts; M14 fires the detector at a synthetic
  violation so the other four are known to be wired up.
