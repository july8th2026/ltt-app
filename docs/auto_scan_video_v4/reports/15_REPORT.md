# Phase 15 — Voice synthesis and bounded dubbing fit

**Verdict: PASS.**
Source SHA at start `1773ecc`. Branch `phien/asv-v4`.

---

## 1. A four-rung ladder, and its order is the policy

How many seconds a Vietnamese sentence takes to read is not knowable in advance.
Phase 14 tells the model the budget, and most lines come back fitting — but "most"
is not "all", and what does not fit must be fixed **individually**.

    1. Synthesize, and MEASURE on the real file    (never trust the TTS header)
    2. Out of tolerance -> ask the model to rewrite that ONE line, re-read it
    3. Out of rounds    -> allow light time-stretch inside the declared cap
    4. Still not fitting -> mark CAN_SUA, do not deliver blind

⛔ Rung 2 regenerates **one segment**. Regenerating the whole script for one bad
line is forbidden in as many words by `V4_RESOURCE_CPU_GPU_POLICY`, and it makes
no sense financially either: one bad sentence would spoil the bill for the other
hundred.

⛔ Rung 3 must not come before rung 2. Stretching audio distorts the voice;
rewriting a sentence does not. Fix the **content** before the **signal** — a
slightly different sentence still sounds like a person, a sentence squeezed by
1.3× does not.

## 2. 🔴 The third rung could never be reached, and nothing would have shown it

`DUNG_SAI_DAI` was 0.15 and the stretch cap `TRAN_TANG_TOC` is 1.15 — **the same
number**. So a segment was either inside tolerance (`VUA`) or already past the
stretch cap (`CAN_SUA`); there was no band in which "does not fit, but a light
stretch is enough" could exist. A four-rung ladder on paper had three rungs when
it ran.

⭐ And it failed in the worst way: **not at all**. Every segment still got a valid
status, the report was still complete, one policy branch simply never executed.
It surfaced only because a test tried to place a segment into `CO_GIAN` and
could not.

The relationship — not just the value — is now pinned twice: by a test, and by an
assertion at **module load**, so a self-contradictory policy stops the app from
starting rather than waiting for someone to run the suite.

    DUNG_SAI_DAI = 0.08     # < tran_co_gian() - 1 = 0.15, enforced

⚠️ 0.08 itself is unmeasured — chosen toward safety. Phase 21 measures it. The
*relationship* is now structural.

## 3. Asymmetric tolerance, for a reason that is not symmetry

    longer than the slot  -> the line runs into the next shot, or over the next line
    shorter than the slot -> a gap, which `thoi_gian.py` already knows how to absorb

Two unequal consequences, so two unequal thresholds (0.08 vs 0.35). Calling the
model to *lengthen* a line that is merely 20 % short would be paying for something
nobody hears.

And the rewrite prompt carries the **measured** duration, not only the target:
"this reads as 4.8 s, the slot is 3.2 s, aim for 3.0 s" is a checkable goal, which
is why a second round is usually unnecessary. The target is deliberately **below**
the slot — landing exactly on it leaves no room for the TTS's own variance to push
it back over.

## 4. The voice debt from Phase 14 is paid

`giai_doan_giong` now reads `ma_giong` **from the DubbingDocument**, not from
`settings`. Phase 14 froze the voice into the document because lines are written
*for* a voice; until this change the stage still read its own key, so a run could
have its lines written for one voice and **spoken by another**, with nothing
raising — each side found a perfectly valid value of its own. `settings` remains
only as a fallback for runs created before the field existed.

## 5. Cost recorded once, by a database constraint rather than a promise

Each delivered segment writes one ledger row in **seconds** (not calls — a segment
three times as long is not the same cost), keyed
`giong:<segment>:<fingerprint>`. `UNIQUE(run_id, ma_dispatch)` refuses the second
write, so "exactly once" is enforced by the schema, not by the control flow being
careful.

The per-segment checkpoint carries the fingerprint, so a rerun reuses audio that
is still valid and pays for nothing it already has.

⭐ Two counters are reported, not one: `so_doan_moi_sinh` counts **segments**,
`so_luot_doc` counts **TTS calls** — a segment fitted after two rewrites is three
calls. Collapsing them would make the cost report lie exactly where it matters
most, and would have silently broken a pin `test_409` already had right.

## 6. Tests and evidence

`tests/test_441_asv_v4_nan_cho_vua.py` — **20 tests**: policy · rewrite prompt ·
loop bound · reuse · ledger · voice source · the index handed to timing.

**Mutation testing — 15 mutations, 15 red** (after the holes below).
One is caught **by hanging**, which is the correct signal: removing the loop bound
does not make the suite fail, it makes it never finish.

### 🔴 A contaminated measurement, and how it was caught

The first mutation run was still alive when a second one started. Both edit the
same file, and the second run's "restore" wrote back a copy that already contained
the first run's mutation — leaving `if so_vong >= VONG_TOI_DA` as `if False` **in
the working tree**.

The result was not an error but **five fabricated "caught" verdicts**: with the
bound gone, every test touching the fit loop hung, and the script counted hanging
as caught. A complete-looking table, and wrong.

⭐ It was caught by a number that made no sense: *"voice read from settings"* has
no reason to hang. That is the point at which one stops reading the table and goes
to look at the tree. The runner now refuses to start while another run's temp
files exist, and the lesson is recorded next to the two related ones already known
in this repo.

### Two real holes the clean run then found

1. **`khe_cua` could return the end timestamp instead of the duration** and stay
   green — every fixture in the group starts at `bat = 0.0`, where `ket` *equals*
   `ket - bat`. The same blind-fixture family as phases 10, 12 and 14. If it had
   shipped: the tenth segment's slot would read as 100 s instead of 3 s, so
   nothing would ever be judged too long and **the whole ladder would silently
   switch off**.
2. **The fingerprint could ignore the adapted text** and stay green. After a
   rewrite the segment is the result of a *different* sentence; if the fingerprint
   does not change, the next run **reuses the old audio** — precisely what the fit
   loop exists to replace. And there is no error: a valid audio file sits in the
   right place, reading the sentence from before the fix.

Regression: ASV cluster green; `lint_app_contract` 20 apps, 0 ERROR, 0 WARN.

## 7. Debt carried forward

⚠️ **Rung 3 is declared, not applied.** `CO_GIAN` and its factor are written into
the voice index for TIMING to act on; the actual `atempo` pass belongs to Phase 16.
Nothing stretches audio yet.

⚠️ **`CAN_SUA` has no consumer.** The status is recorded and correctly excluded
from `dat`, but no stage refuses delivery on it yet — QC (Phase 18/19) is where
that decision belongs.

⚠️ **No real TTS or real LLM has run this loop.** Every test stubs both. The
rewrite prompt and the convergence assumption behind `VONG_TOI_DA = 2` are
unexercised against live models.

⚠️ **`DUNG_SAI_DAI`, `DUNG_SAI_NGAN`, `VONG_TOI_DA` are unmeasured.** Phase 21.

## 8. Exit gate

**PASS.** Every retained segment ends with either a measured, fitting audio
artifact or an explicit `CAN_SUA` verdict; the fit loop is bounded by a hard cap
that a mutation can only defeat by hanging; unchanged segments are reused; and each
delivered segment is billed exactly once, enforced by a unique constraint.
