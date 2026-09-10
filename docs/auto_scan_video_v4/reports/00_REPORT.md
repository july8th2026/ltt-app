# PHASE 00 REPORT — PROVENANCE AND BOOTSTRAP

## Verdict

**PASS**

## Source / HEAD

| | Value |
|---|---|
| repo | `giaitritruyenthongltt-spec/LTTSTUDIOSAPP` |
| source branch | `phien/asv` |
| **actual HEAD** | `706faca50c75fb5b6dbad6c346b96c98a6736a11` |
| pack's authored SHA | `706faca50c75fb5b6dbad6c346b96c98a6736a11` |
| delta | **none** — `git rev-parse phien/asv`, `origin/phien/asv` and the pack all agree |
| V4 branch | `phien/asv-v4`, created from that commit |
| worktree | `D:\LTTSTUDIOSAPP\.claude\worktrees\auto-scan-video-v4-mvp-7173d9` |

`start_here.md` §1 says "actual HEAD wins" and requires the delta to be recorded. The delta is
empty, so no impact audit was needed. `git fetch origin phien/asv` was run first — this is
verified, not assumed from a stale local ref.

### Worktree — one deviation, recorded not hidden

The pack *suggested* `D:\LTTSTUDIOSAPP-asv-v4`. This session was launched by the harness
inside an already-isolated worktree whose operating contract is "run everything here, never
`cd` to the repository root". Creating a second checkout would have left a stray tree on the
user's disk and split the work across two directories with no benefit.

The **binding** requirement of §2 is *"never develop V4 in `master`, the existing `phien/asv`
worktree, or the production tree"*. All three hold:

```
D:/LTTSTUDIOSAPP                                          [admin-mvp-v3]   <- not here
D:/LTTSTUDIOSAPP-asv                              706faca [phien/asv]      <- not here
D:/LTTSTUDIOSAPP/.claude/worktrees/auto-scan-...  706faca [phien/asv-v4]   <- HERE
```

⛔ `C:\LTTPlatform` exists ⇒ **this machine is production**. Never deploy from this tree.

## Objective

Establish exact source, dedicated worktree, reproducible baseline, and a read-only snapshot
of the current runtime. No production behaviour may change.

## Changed paths

Docs only. `git status --porcelain` shows exactly one untracked entry:

```
?? docs/auto_scan_video_v4/
```

- `docs/auto_scan_video_v4/STATE_V4.md`
- `docs/auto_scan_video_v4/reports/00_REPORT.md`
- `docs/auto_scan_video_v4/evidence/00_gate_baseline.txt`

Zero application, platform, test or migration files touched. Nothing under
`docs/auto_scan_video/` (V2 history) was edited or deleted.

## Before -> After

No behavioural change. This phase only *observes*.

## Contracts / migrations

None added, none changed. No Alembic revision created.

## Tests and commands

### Certified baseline

```bash
python tools/gate.py --phien asv-v4 --cho 60
```

| | |
|---|---|
| started / finished | 2026-09-03 00:35:35 → 00:47 (local) |
| duration | **675 s (11.2 min)** — 600 s parallel phase + 74 s serial phase |
| verdict | **`RESULT: FAIL (1/26)`** |
| pytest | **2 failed · 5 769 passed · 32 skipped** |
| tree-changed warning | **absent** |
| result json | `test-results/gates/20260902T174701Z-11816.json` |
| raw log | `evidence/00_gate_baseline.txt` |

**Why the baseline is admissible as evidence.** `docs/auto_scan_video_v4/STATE_V4.md` was
written while the gate's pytest step was still running, which is exactly the mistake that
invalidated V2's Phase 00 baseline three times (V2 RISK-00-16). It did **not** invalidate this
one, and the reason is checkable rather than hopeful: `tools/gate.py:834 _anh_chup_cay()`
snapshots only `apps`, `platform_core`, `server`, `tools`, `tests`, `alembic`, `locale` —
**`docs/` is outside the snapshot**, no test reads that file, and the run printed no
`CAY DA DOI GIUA CHUNG` line. Recorded because "it happened to be harmless" and "it was safe"
are different claims, and only the first one is true here.

### Failure ownership — the part that makes the number mean something

| Failure | Root cause, proven | Owner | ASV? |
|---|---|---|---|
| `test_82_upscalevideo.py::test_vendor_engine_co_mat` | `.gitignore:151` ignores `apps/*/vendor/` **on purpose** (Real-ESRGAN binaries are never committed). `git ls-files apps/upscalevideo/vendor` → **0 files**; the main tree has 1 entry, this fresh worktree has 0. Every new worktree fails this and always will. | worktree environment | **no** |
| `test_361_cua_so_yen.py::test_xep_hang_roi_vao_duoc_khi_nguoi_truoc_nha` | **Passes when run alone** (`1 failed, 1 passed` — the pass is this one). It went red inside the gate because the gate itself was holding the quiet-window lock that the test asserts on. The measuring instrument perturbed the measurement. | gate self-interference | **no** |

⇒ **Zero failures belong to Auto Scan Video.**

### Steps that self-declared BOQUA (gate prints them as "not evidence")

| Step | Reason, verified |
|---|---|
| `bat bien da tien trinh` | `tools/check_multiproc.py` prints the instruction to set `LTT_TEST_DATABASE_URL` before running. Needs a scratch PostgreSQL DB whose name contains `test`. PG is live on 5432. **This is the I1/I18 evidence gap and it blocks G4.** |
| `frontend agent-canvas` / `autosub-studio` / `prompt-ai-ommi` | `frontend/agent-canvas/node_modules` absent — `npm install` has never run in this worktree. |

### Comparison with V2's frozen baseline — and why it is not the same number

V2's `STATE.md` records `RESULT: FAIL (3/26)` with **7** test failures at
`phien/asv = 0fef74c`. This phase measures **1/26** with **2** failures. That is not a
contradiction and not an improvement I made: three commits sit between the two measurements —

```
0fef74c ... 03845cb  gate dem LOI thay vi dem tien trinh
            b027e08  Merge branch 'admin-mvp-v3' into phien/asv
            706faca  wip(auto_scan_video): pha 21 dang do   <- HEAD
```

`b027e08` merges `admin-mvp-v3`, which is where the peer-owned fixes lived
(`platform_core/public_api/dieu_khoan.py`, `voice_tu_dien` retention class, the drill entry).
V2's own STATE was written against `0fef74c` and was already stale relative to its own branch
HEAD. **The number that governs V4 is the one measured here**, on the actual HEAD.

### Invariant regression (V2's subset — V4's own is built in Phase 04)

```bash
python -m pytest tests/test_400_asv_bat_bien_thi_hanh.py tests/test_401_asv_ranh_gioi_va_artifact.py -q
```
→ **24 passed in 2.38 s**

## Runtime traced

`run -> advance -> stage -> job -> artifact -> settlement` — full trace in `STATE_V4.md`
§"Current ASV runtime". Load-bearing points confirmed by reading the code, not the old docs:

- `jobs._advance` locks the run row **before anything else**; a late child cannot revive a
  cancelled run (I13).
- `_thu_ket_qua_job_con` **refuses** to infer `job done ⇒ stage succeeded`; a handler that
  died after the engine returned but before `storage.promote` is marked retryable, not done
  (I8).
- `_vo_hieu_giai_doan_da_lech` re-checks fingerprints at the top of every tick and resets the
  drifted stage **plus its downstream closure** via `pipeline.ha_nguon_cua`.
- `features.quyet_toan` settles once, idempotently, from **measured** `Σ asv_stage.credit_actual`
  clamped to `credit_held` — never recomputed from a price table (ADR-001 D4).

Nine stages, four apps, lanes and admission resources: table in `STATE_V4.md`.

## Self-review findings (hostile pass, `V4_TEST_REVIEW_PROTOCOL` layer 4)

- *Did I duplicate an existing capability?* No code written.
- *Did I broaden scope?* One deviation (worktree path), argued and recorded above rather than
  taken silently.
- *Did I break old callers?* Nothing touched.
- *Did I add a silent fallback?* No.
- *Is any claim in this report unproven?* The two failure attributions were each re-derived
  from a second, independent command (`git ls-files` + `.gitignore` for one, an isolated
  pytest run for the other) rather than from V2's prose. The V2-vs-V4 baseline delta was
  explained from `git log`, not guessed.
- *Am I trusting a doc where code was available?* V2's `STATE.md` claims `test_362` ×2 "can
  never pass inside a linked worktree". They passed here. I did **not** carry that claim
  forward — the measured result replaces it.

## Risks / external evidence

11 V4 critical risks recorded in `STATE_V4.md`, each with file and line. The five with a
P0 severity are V4-R01 (whole video read into RAM), V4-R02 (reach-through into LTT Voice
internals), V4-R04 (unguarded real-demucs test), V4-R05 (test interpreter is CPU-only while
production is CUDA), V4-R07 (paid translation ordered before any EditPlan/VoiceBinding).

External evidence pending: real-GPU resource ledger, `LTT_TEST_DATABASE_URL`, `LTT_LLM_TOKEN`,
real LTT Voice synthesis, representative customer videos. None of them is required by *this*
phase's exit gate.

## Exit gate proof

> *PASS only when the new worktree is isolated, exact HEAD recorded, baseline reproducible,
> current runtime traced and no production behavior was modified.*

| Condition | Evidence |
|---|---|
| new worktree isolated | `git worktree list` — `phien/asv-v4` is a distinct tree from `D:\LTTSTUDIOSAPP` (`admin-mvp-v3`) and `D:\LTTSTUDIOSAPP-asv` (`phien/asv`) |
| exact HEAD recorded | `706faca50c75fb5b6dbad6c346b96c98a6736a11`, fetched and compared, delta empty |
| baseline reproducible | one command, 675 s, verdict + both failures attributed to non-ASV causes with independent proof; raw log committed under `evidence/` |
| runtime traced | seven-step trace above, read from `jobs.py`/`features.py`/`thi_hanh.py`/`pipeline.py` |
| no production behaviour modified | `git status --porcelain` = one untracked docs directory |

**PASS → continue automatically to Phase 01.**
