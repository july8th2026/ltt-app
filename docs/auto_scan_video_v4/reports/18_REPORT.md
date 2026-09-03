# Phase 18 — Technical QC

**Verdict: PASS.**
Source SHA at start `5cbd643`. Branch `phien/asv-v4`.

---

## 1. 🔴 QC was blocking exactly what it was supposed to let through

Phase 17 made the cutting preset a real render path. QC did not know it existed,
and two of its twelve checks would fail on **every** smart run:

**T3** compared the output's video-stream hash against the source. Correct for
the preserve preset, which stream-copies. The smart preset **re-encodes** — it
must, because stream-copy can only cut at keyframes and the measured GOP is
8.333 s — so the hash can never match. Comparing it there pins a property we
deliberately do not have.

**T2** compared the output duration against the **source**. The smart preset's
output is shorter than the source by exactly the removed scenes — that is *the
product's purpose*, not a defect.

⇒ QC is now mode-aware. T3 is `KHONG_AP_DUNG` in cut mode with the reason
recorded; T2 compares against an **expected** duration computed from the time
map. Neither check was loosened: in preserve mode T3 still demands a bit-identical
stream, and T2 still refuses an output longer than expected — that one is a
separate pin, not a consequence of the ±0.5 s tolerance, because an output 0.3 s
longer still breaks the §3 promise.

The exit gate names this exactly: QC must not "assume source video hash equality
in smart mode".

## 2. A new check for a failure nothing could catch: T13

A file can be **valid, the right duration, correctly loudness-normalised, and
entirely black**. Before this phase no check would notice: T1 only asks whether a
video stream exists, and an all-black stream is a video stream.

T13 samples 12 frames spread across the output and measures mean luma.

⚠️ The threshold is deliberately **very low** (2.0/255). A real night scene can
average under 10, and this is not a judgement about artistic quality — it catches
"there is nothing there", with a number that cannot be confused with a dark
scene. Semantic judgement belongs to Phase 19, which this phase is forbidden from
doing.

⛔ And a failed *measurement* is `KHONG_AP_DUNG`, never `HONG`. Turning "could not
measure" into "failed" manufactures false alarms, and false alarms are how people
learn to stop reading the report.

🔑 Sampling rather than scanning: a 2-hour output has 216,000 frames, and the
question "is it blank?" does not need 216,000 measurements.

## 3. An optimisation refused, because the measurement said so

The phase asks to "profile expensive full-stream hashing; replace with a cheaper
equally-valid method **only if correctness evidence supports it**".

Measured on a 154 MB / 10-minute file:

| method | time |
|---|---|
| **MD5 of the whole video stream (current)** | **0.27 s** |
| ffprobe packet count | 0.10 s |
| MD5 of the first 10 s | 0.03 s |
| ffprobe stream size | 0.03 s |

Hashing is a stream copy into a hash — no decoding — so it costs I/O, not CPU.
Extrapolated to the 2-hour ceiling: ~3.5 s, next to a render measured in minutes.

⇒ The premise does not hold on this system. Every cheaper alternative is
**strictly weaker evidence**, and there is no cost to trade it for. Kept as-is,
with the numbers recorded so the next person does not re-litigate it from
intuition.

⭐ What *did* change: hashing is now **skipped entirely in cut mode**. Not to save
time, but because computing a comparison whose answer we already know is not
evidence — it is noise with a runtime cost.

## 4. Tests and evidence

`tests/test_444_asv_v4_qc_hai_che_do.py` — **16 tests** in five groups.

**Mutation testing — 13 mutations, 13 red** (after the holes below).

### 🔴 Two holes, both at the seam rather than in the policy

The first four groups call `qc.kiem` directly with explicit arguments. So two
mutations that made **`giai_doan_qc` pass the wrong values** stayed green:

  * reading the render mode from `settings` instead of from the manifest
  * not passing `thoi_luong_mong_doi` at all

⭐ That is precisely where a smart run would fail in production: the policy
correct, complete, and never called with the right arguments. The new group runs
the **whole chain** through both presets and reads the stored QC report —
asserting the cut run records `cat_ma_hoa_lai` with a real expected duration and
`T3 = KHONG_AP_DUNG`, and that the preserve run still compares hashes.

⚠️ Reading the mode from the **manifest** rather than `settings` is itself the
point: the manifest is what was actually rendered. If the two ever disagree, the
truth is what ran — re-deriving it here would have QC measuring a different run
from the one that happened.

Regression: ASV cluster **978 passed**, 3 skipped, 1 xfailed.

## 5. Debt carried forward

⚠️ **T13's threshold is unmeasured against real content.** 2.0 is chosen to be
unmistakable, not calibrated. A corpus of real night scenes would let Phase 21
tighten it.

⚠️ **Smart mode has no positional check on the retained scenes.** T2 verifies the
total duration and T3 is skipped; nothing yet verifies that the *order* of
retained ranges in the output matches the plan. The concat filter's order is
pinned in Phase 17's tests as a command, but not measured on a rendered file.
That measurement belongs with E2E acceptance (Phase 22).

⚠️ **QC evidence persistence was already correct** and is untouched: the report is
stored before the verdict is acted on, so a failing run still leaves its report —
`test_420` already pinned that and it still passes.

## 5b. ⚠️ A flaky test outside ASV, recorded rather than waved away

The first full-gate run failed on
`tests/test_231_nexus_e2e.py::test_khach_ghep_may_va_thay_no_hien_ra` — a **Nexus**
test, among 6,767 passing. The second run passed with no change to the tree.

Evidence it is not caused by this phase:

  * passes in isolation, and passes three times under `-n 6` within its own file;
  * every change in phases 15-18 is inside `apps/auto_scan_video`, `apps/asv_gpu`,
    their tests, docs and the locale catalogue — Nexus is untouched;
  * the `_Empty` / `_Err` lines in the log are **not** the cause: they are
    `PytestUnhandledThreadExceptionWarning`s from a background thread in
    `test_81_autosubvideo` reading a mocked `proc.stderr`.

⛔ What I do **not** have is a root cause. The suspicion is state leaking between
files under xdist — this repo already has a recorded case of that shape ("green
alone, red in the gate") — but suspicion is not knowledge.

⭐ It is recorded here because a flaky test erodes the one tool the repo uses to
say "done". Phase 18's own verdict does not rest on it: the ASV cluster is green,
this phase's 16 tests are green, and 13/13 mutations are caught. But the next
person to see a red gate deserves to know this one has been seen before.

## 6. Exit gate

**PASS.** Technical QC blocks bad output — including the all-black case that
nothing previously caught — and it no longer assumes source-hash equality in
smart mode: the assumption is replaced by a mode-specific expectation, recorded
in the report so a reader can tell which rules produced which verdict.
