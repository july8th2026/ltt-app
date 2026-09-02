# PHASE 16 REPORT — Real Fixed Pipeline Wiring

**The phase where most of the work turned out to be already done, and the remaining quarter was the part nobody had thought about.**

## Entry evidence
- starting SHA: `f4fb08b`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 15 closed at `FAIL (3/26)`, all failures owned elsewhere
- allowed change scope: fixed orchestration/wiring and stage configs only

## What was already true

Five of the nine required items were satisfied by Phases 05–15 and needed only pinning:

| item | state on entry |
|---|---|
| 1 — server-owned frozen stage order | `pipeline.CHUOI` in source, checked at import |
| 2 — stage → executor app / job type / lane | in `CHUOI`, pinned by `test_402` |
| 3 — fingerprints, output refs, checkpoints | ADR-001 D7 path, `AsvAsset` + `AsvStage` |
| 6 — one billing owner | hold on `run.id`; child jobs use `jobs.submit`, never `submit_with_credit` |
| 8 — cancellation propagation | `features.huy_run` + the re-read under lock in `_advance` (I13) |

Item 9 (**run completion waits for QC, not render**) was structurally true —
`len(da_xong) == len(pipeline.CHUOI)` counts all nine — but nothing had ever *tested* it, and
"structurally true" is how a condition quietly becomes false later. Now pinned two ways: a run
whose QC is reset does not reach `done` even when render succeeded, and `QC` is asserted to be
the last stage so adding a stage after it cannot silently invalidate the claim.

## What was missing: items 4 and 7

Both concern the same question, and it is a question a pipeline that only ever runs **start to
finish** never asks: *what happens when a stage in the middle has to be redone?*

### `pipeline.ha_nguon_cua(ten)` — the reverse of `GiaiDoan.sau`

⚠️ Today this returns exactly `CHUOI[i+1:]`, and saying otherwise would be false. The graph is
effectively linear; its only branch (`timing_align` depends on both `voice_synthesis` and
`audio_prepare`) does not produce any stage that comes later but does not depend on the earlier
one.

So why not write `CHUOI[i+1:]`? Because the two are equal **by circumstance, not by definition**.
Add one independent branch and they diverge — at which point `[i+1:]` silently invalidates too
much, i.e. bills the customer again for work whose inputs never changed. `test_417` pins *both*
the closure semantics and today's coincidence, so the day they separate, a test says so.

⛔ I wrote the docstring the other way first — claiming `content_process` does not depend on
`audio_prepare`. It does, transitively via `transcribe`. Corrected against measured output rather
than left as a plausible-sounding example.

### `features.thu_lai_giai_doan` — retry one stage, invalidate only what follows

Re-running the whole run when only `render` failed bills the customer again for transcription,
translation and speech synthesis — the three most expensive stages, none of them implicated.

Two refusals are deliberate:

- **A finished run cannot be retried.** `quyet_toan` has already refunded the unused hold, so
  further work would spend money with nothing held against it. Start a new run instead.
- **`attempt` is not reset.** It is a fact about the run's history, not a progress counter;
  erasing it erases the answer to "why did this run cost so much".

### Automatic invalidation — the half that had no owner

`thi_hanh.giai_doan_lech_van_tay` finds `succeeded` stages whose stored fingerprint no longer
matches their current inputs, and `jobs._vo_hieu_giai_doan_da_lech` resets them plus their
downstream closure, at the **start** of every advance tick — before `da_xong` is computed,
because a drifted stage counted as done could end the run on that same tick.

🔑 Why this is needed at all, given fingerprints already invalidate the *cache*: those are two
different mechanisms solving two different halves.

- The fingerprint makes sure a stale result is never **reused**.
- Nothing made sure the stage **runs again**. Its `asv_stage` row still says `succeeded`, and the
  coordinator only submits stages that are not succeeded.

Miss either half and the run finishes with a dubbing that mixes two different executions — with
no error anywhere.

⭐ The detector is deliberately **one hop**: faking `transcribe`'s stored fingerprint reports
`['transcribe', 'content_process']`, not all seven downstream. `render` reads `compose`'s
fingerprint, which has not changed yet. The transitive closure is the *caller's* job
(`vo_hieu_ha_nguon`), so the detector answers "which rows no longer match their inputs" and not
"what must be redone". Keeping those two questions apart is what makes both testable.

⚠️ My first test for this asserted `render` would appear in the drift list, and that
`transcribe` would not. Both were wrong, in opposite directions, in one line: the detector does
not read transitively, and `transcribe` obviously mismatches because its stored value is the one
I had just forged. The code was right; the test's reasoning was not.

## Exit gate

> *One service invocation completes the full fixed pipeline using real stage implementations and
> the same execution invariants as the dummy slice.*

`test_402::test_run_chay_het_CHIN_giai_doan_va_ve_done` still passes — the same test that proved
the dummy slice in Phase 05, now driving real MEDIA/AUDIO/TRANSCRIBE/CONTENT/VOICE/TIMING/
COMPOSE/RENDER implementations. The invariants it checks (single hold, no child job holds,
lane routing, settle-once) are unchanged.

Duplicate-work checks required by the prompt:

- **no duplicate holds** — `test_thu_lai_KHONG_giu_them_mot_khoan_credit_nao`: retry leaves
  `run.credit_held` and the account balance untouched.
- **no duplicate stage rows** — `test_moi_giai_doan_chi_co_MOT_dong_du_da_thu_lai`: nine rows,
  nine distinct names, after a retry and a full re-run.
- **no orphaned jobs after cancel** — `test_huy_KHONG_de_lai_job_con_dang_song`.

## Exit evidence

`python tools/gate.py --phien asv` → **FAIL (3/26)** — unchanged from Phase 15, same causes,
none in ASV work (peer's `dieu_khoan.py` layering + i18n, peer's `voice_tu_dien`, and the three
worktree-structural failures of RISK-14-02).

ASV-owned tests: **301 pass**, including under `-n 8`.

## Debt carried out of this phase

- `thu_lai_giai_doan` has no HTTP surface — routes are Phase 20 (UI). It is reachable only from
  code and tests today, which is correct for a phase whose prompt says *"No UI yet."*
- The drift detector recomputes every succeeded stage's fingerprint on every tick. Cheap now
  (nine stages, hashing a small dict) but it is per-tick work that grows with stage count
  (RISK-16-01).
