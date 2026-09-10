# PHASE 13 REPORT — Timing, Pause and Alignment

**The phase where the product owner corrected a design assumption I had frozen in Phase 02.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 12 **PASS**
- allowed change scope: timing service, tests; **plus** an ADR amending `MVP_CONTRACT.md`
  (§9 requires an ADR for contract changes — [`ADR-003`](../adr/ADR-003-mo-hinh-thoi-gian.md))

## The correction

`MVP_CONTRACT.md` §6 (Phase 02) defined `fit_original` as *"each segment's voice is fitted to
its source segment window"*. The product owner pointed out what that assumption misses:

> *"Thực tế việc nói liền rất ít xảy ra. Đều có khoảng lặng."*

**People do not speak continuously.** The pauses between sentences are unspent time budget.
Combined with RISK-02-01 (Vietnamese is typically longer than the source), the old rule made
overflow the **norm**, and the only remaining response was truncation — losing dialogue on
most lines.

Measured on a normal speech rhythm (1 s speech, 1 s pause) with a Vietnamese track **60 %
longer**:

| Model | Lines compressed | Max speed-up | Lines lost |
|---|---|---|---|
| Phase 02 `fit_original` | **all 5** | 1.6× | 0 |
| ADR-003 | **0** | 1.0× | 0 |

The pause absorbs the whole difference. Nothing needed compressing at all.

## Community research (as requested)

Read the actual source of three dubbing projects, not their READMEs alone.

### `ThioJoe/Auto-Synced-Translated-Dubs` (1.7k ★)
Force-fit by time-stretching to the exact window; on overflow it only **warns**:
`"WARNING: Audio clip {key} is {difference}ms longer than expected and may overlap"`.
No overflow model. Simplest, and worst when the target language is longer.

### `R3gm/SoniTranslate` (1.4k ★) — `acceleration_rate_regulation`
When required speed-up exceeds 1.3×, it looks at the **next segment's start**:
```python
duration_with_next_start = next_start - start        # includes the pause
extra_time = duration_with_next_start - duration_true
smoth_duration = duration_true + extra_time * (0.5 if same_speaker else 0.7)
```
**Two things worth taking:** borrow the pause instead of compressing, and borrow only *part*
of it (50–70 %) so a rest remains. Its `avoid_overlap` also tolerates a controlled 0.2 s
overlap (same speaker) / 0.5 s (different).
**Rejected:** `max_accelerate_audio = 2.1` — twice as fast is no longer a human voice. And it
caps nothing cumulative.

### `lukaszliniewicz/Subdub` — `align_audio_blocks` ⭐ closest to our problem
The key is one line:
```python
block_duration = next_block_start_ms - block_start_ms   # NOT end - start
```
plus a carried `total_shift` that is **actively repaid**: overflow adds to it, spare pause
subtracts from it, and speed-up (default **1.15×**) accelerates repayment.
**Rejected:** no hard cap at all — on continuous speech the debt grows monotonically.

### The answer to *"không quá 3 đoạn hay như nào đó"*
The community answer is **better than a segment count for the normal case**: debt is repaid
continuously by the pauses themselves, so it self-adapts. But the owner's instinct is right
for the **pathological** case — none of the three projects bounds the debt, so on
gap-less speech it grows without limit. ADR-003 therefore takes both: continuous repayment
**plus** a hard 3-segment cap.

## Decisions (ADR-003)

| | |
|---|---|
| **D1** | segment budget runs until the **next segment starts** |
| **D2** | borrow at most **70 %** of a pause, so the dub keeps its rhythm |
| **D3** | carried drift debt, repaid at every pause |
| **D4** | speed-up (**≤ 1.15×**) only to **repay debt**, never to force a fit |
| **D5** | hard cap: debt ≤ budget of **3** following segments; beyond that drop a segment and QC reports it |
| **D6** | tolerate ≤ **200 ms** overlap between neighbours |

Contract amended: §6 rewritten, T7 redefined (drift vs *planned* position, since drift vs the
source is now by design), **T11** and **T12** added.

**Three numbers, three different origins — and that distinction is recorded in the code:**
`0.7` and `1.15` are **borrowed** from projects that shipped; `3` is **ours**, and it is a
reasoned choice, not a measurement. All three are stated as such.

## Changes

| Path | Change |
|---|---|
| `docs/auto_scan_video/adr/ADR-003-mo-hinh-thoi-gian.md` | **new** — the model, with the community evidence |
| `docs/auto_scan_video/MVP_CONTRACT.md` | §6 rewritten; T7 amended; T11, T12 added |
| `apps/auto_scan_video/thoi_gian.py` | **new** — the planner |
| `apps/auto_scan_video/giai_doan_thoi_gian.py` | **new** — the stage body |
| `apps/auto_scan_video/thi_hanh.py` | dispatch |
| `tests/test_410_asv_thoi_gian.py` | **new**, 23 tests |
| `locale/en/LC_MESSAGES/messages.po` | +13 entries |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_410…` | **23 passed** |
| `pytest tests/test_402… test_403…` | **35 passed** — six real stages |
| `python tools/lint_app_contract.py` | `ERROR: 0` |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

Three scenarios exercised end to end:

| Scenario | Result |
|---|---|
| normal rhythm, Vietnamese +60 % | 0 compressed, 0 lost, 0 debt |
| dense speech, +50 % | 7/8 sped up to the 1.15× cap, debt bounded at 2.3 s, 0 lost |
| dense speech, +120 % (pathological) | 2/10 lines dropped, debt bounded, end 15.6 s < 30 s source |

## Two real bugs in my own model, both caught by tests

**1. "Cut" moved time backwards and erased the whole debt.** The first version set
`dat_tai = bat_goc` and `troi = 0` on a cut. Wrong twice over: it placed the segment before
the previous audio had finished (the overlap check caught it immediately), and it pretended
that dropping **one** segment repays **all** debt. Dropping one segment buys back exactly one
segment's budget — large debt legitimately needs several cuts, and that self-limits.

**2. The duration invariant was applied to only one mode.** The tail trim ran only when
`che_do == "natural"`, because §6 mentions `natural`. But the real constraint is **D-ASV-03**:
the video stream is copied, so total duration is fixed regardless of mode. `fit_original`
overflows less; that does not make it allowed. The test failed on exactly that path.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I8 durable DONE | PASS | plan is a fingerprinted, re-validated artifact |
| I10 cache correctness | PASS | all four constants are in the fingerprint — one parametrized test per constant |
| I17 fixed model | PASS | no new mode; still exactly `fit_original` / `natural` |
| D-ASV-03 copy path | PASS | dub can never exceed source duration, both modes |
| I16 safe logs | PASS | summary is counts and milliseconds, no dialogue |
| I1–I7, I9, I11–I14, I18, I19 | PASS | 35 chain tests green |

Also asserted: **the stage touches no audio file** — an AST scan rejects
`AudioSegment`/`atempo`/`concat`/`ffmpeg` in `thoi_gian.py`. Mixing planning into splicing
would hide a timing decision inside a mixing step, where nobody looks for it.

## Diff review
- changed paths: `apps/auto_scan_video/`, `docs/auto_scan_video/`, `tests/`, `locale/en/`
- one scratch script created and deleted; `.po` appended only, LF preserved
- secret scan PASS

## Risks / external evidence pending

- 🔴 **RISK-02-01 — model built, ratio still unmeasured.** The design now *handles*
  Vietnamese being longer; it does not yet know **by how much**. Every scenario above uses an
  assumed ratio (1.5×–2.2×). The real number needs one end-to-end run with the real model and
  the real voice engine. `TestChoBangChungNgoai::test_chua_do_ty_le_dai_that_cua_tieng_Viet`
  fails as soon as the voice engine is reachable.
- **RISK-13-01 (P1, new)** — `TY_LE_MUON_KHOANG_LANG` (0.7) and `TRAN_TANG_TOC` (1.15) are
  **borrowed** from projects tuned for English/Spanish. This repo's rule is that a borrowed
  threshold must be re-measured. A test pins both values so a change is deliberate.
- **RISK-13-02 (P2, new)** — `TRAN_TROI_SO_DOAN = 3` is a reasoned choice, not a measurement,
  and no reference project has an equivalent. Real validation needs human listeners on real
  content — Phase 21.
- **RISK-13-03 (P2, new)** — MVP has no diarization, so the planner cannot use SoniTranslate's
  same-speaker/different-speaker distinction (0.5 vs 0.7). It takes the wider 0.7 for all
  cases, recorded in the constant's comment.
- **RISK-05-01, -10-01, -10-02, -11-01, -11-02, -12-01, -12-02** unchanged.

## Exit gate

**PASS.**

Gate text: *"PASS when timing plan and final voice alignment are deterministic, bounded and
verifiable."*

- **Deterministic** — the planner is pure arithmetic over the translation and the *measured*
  durations of the generated audio. No randomness, no wall clock. Same inputs, same plan,
  same fingerprint.
- **Bounded** — three bounds, each with a test: speed-up ≤ 1.15×, overlap ≤ 200 ms, drift ≤
  the budget of 3 following segments. And the plan can never exceed the source duration.
- **Verifiable** — `kiem()` re-validates a plan read back from storage, and the summary
  surfaces exactly the numbers QC needs: segments dropped, segments sped up, max factor, max
  drift.

## Next phase prerequisites

Phase 14 (Composer & Render Manifest):
1. the timing plan is the composer's main input — it already carries `dat_tai_ms`, `dai_ms`,
   `he_so_toc` per segment, so the composer performs **no timing arithmetic of its own**;
2. `he_so_toc > 1.0` means the renderer must apply `atempo` — that belongs to RENDER, not to
   the composer (G9: composer ≠ renderer);
3. segments with `dai_ms == 0` were dropped and must be **skipped**, and QC must be able to
   count them (T12);
4. the manifest must be restartable, and it must not embed absolute paths that a re-run on
   another worker cannot resolve.
