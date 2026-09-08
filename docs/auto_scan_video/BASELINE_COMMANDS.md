# BASELINE COMMANDS (Phase 00 output — Phase 01 runs and freezes them)

Prompt 00 requires *a list* of baseline commands and explicitly forbids repairing failing
code. Phase 01 executes these and freezes the BEFORE behaviour.

## Repo-native quality gate (use these, not bare `pytest`)

Test levels and when to use each: **`docs/00_LTT_OPERATING_CONTRACT.md` §4.**

```bash
python tools/gate.py --doi         # the working loop — only tests touching what changed
python tools/gate.py               # VERDICT — the only thing that counts
```

⛔ Do **not** run `test_nhanh.py` and then `gate.py`. The `bo test` step *inside*
the gate **is** `test_nhanh.py` (`tools/gate.py:844`) — running both pays ~4
minutes twice for the same pass/fail set. *(This file listed them as two separate
baseline commands until 2026-09-08; that is where the habit came from.)*

Never run `python -m pytest` across the repo — it misses the frontend tests under
`frontend/*` and is single-threaded.

## Targeted suites relevant to Auto Scan Video

| Area | Command | Why it matters here |
|---|---|---|
| multi-process worker correctness | `python -m pytest tests/test_214*.py` | I1/I18 — the only proof that background loops behave with N worker processes |
| credit ledger | `python -m pytest tests/ -k credit` | I2/I3/I4 |
| concurrency on PostgreSQL | `LTT_TEST_DATABASE_URL=... python -m pytest tests/test_73_dong_thoi_pg.py` | skipped by default; needs a real PG |
| app contract lint | `python tools/lint_app_contract.py` | route-size ceiling, file placement |
| silent-except ratchet | `python tools/check_silent_except.py` | H22.12 ratchet — must not grow |
| multiproc check | `python tools/check_multiproc.py` | H36.9, wired into the gate |

## Known environment-conditional skips (record, do not "fix")

Observed 2026-09-01 in `tools/check_bo_qua` output:

- `test_73_dong_thoi_pg.py` — needs `LTT_TEST_DATABASE_URL`
- `test_74_smoke_playwright.py` — needs `LTT_SMOKE_URL`
- `test_334_ngan_sach_ltt_llm.py::_health` — needs `LTT_LLM_TOKEN`
- `test_293`, `test_299`, `test_362`, `test_388` — machine/state conditional

These are `PENDING_EXTERNAL_EVIDENCE` shaped, not failures.

## Baseline gate result observed in Phase 00 — **INVALID AS EVIDENCE**

Two runs of `python tools/gate.py --vong-lap` at ~16:10 and ~16:14 both returned
`RESULT: FAIL`, failing at step `bo qua im lang` (the silent-skip ratchet,
`tests/test_306_banh_coc_bo_qua_va_dich.py::test_bo_qua_hien_tai_dat_moc`).

The two runs reported **different skip sets**, and the gate itself printed:

```
RESULT: FAIL (2/22)  [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]
```

*(“the tree changed mid-run — do not use as evidence”)*

Cause: **this working tree has concurrent live sessions.** `ListAgents` at 16:16 showed two
interactive peers (`lttstudiosapp-01`, `lttstudiosapp-bb`) started 18 minutes earlier, and
`docs/audit_ltt_llm/evidence/` had an mtime of 16:09 — untracked work that is not Phase 00's.

Consequences, recorded rather than acted on:
1. Phase 00 changed **no code** (docs-only, new folder), so this failure is not attributable
   to this phase and O21 forbids repairing it here.
2. **No gate result from this tree is trustworthy while peers are writing.** Phase 01 must
   establish a file-boundary agreement with the live sessions, or run its baseline on a
   quiet tree, before recording any BEFORE state.
3. `--vong-lap` is a diagnostic and says so itself — it was never going to be the evidence.
