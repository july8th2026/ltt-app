# Phase 16 — Timing plan and audio master

**Verdict: PASS.**
Source SHA at start `1773ecc` (shared with Phase 15 — see §7).

---

## 1. 🔴 The cutting preset was placing every line on the wrong clock

`thoi_gian.lap_ke_hoach` planned on the **source** time axis: a line starting at
source second 120 was placed around second 120. Correct for
`localize_preserve_picture`, where the picture stream is copied untouched.

For `smart_localize` it is not: a cut scene **disappears from the output**, so
source second 120 may be output second 74 — or may not exist at all. And the
error is not a fixed offset: it **accumulates with every cut scene**, so the more
the editor removes, the further the ending drifts. Nothing raised.

`ban_do_thoi_gian.BanDoThoiGian` is the missing conversion. It is pure — it
depends only on the list of retained intervals — and it answers two questions:

    ra(t)          -> output timestamp, or **None** if t is inside a cut
    ra_gan_nhat(t) -> output timestamp, snapping to the next retained interval

⛔ A timestamp landing *inside* a cut returns `None`, never the nearest edge.
Snapping would turn a line that was **removed** into a line **placed wrong** —
trading a visible loss for a hard-to-find bug, the kind where the viewer hears an
answer to a question that is no longer there.

⭐ `ra_gan_nhat` exists for exactly one caller: the background bed. The bed is a
continuous signal — cut a piece out and rejoin, and the join must be a real
timestamp, never `None`. Dialogue must not use it, and the tests pin both halves.

## 2. 🔴 My own patch nearly re-created the bug it was fixing

`ngan_sach_doan(muc, i, tong_ms)` read `muc[i]["bat"]` — **source** time — and
subtracted it from `tong_ms`. The moment `tong_ms` became **output** time, that
function silently mixed two clocks: the difference between two source marks is
**not** their distance in the output when a cut sits between them.

It now takes **already-converted marks**. The conversion happens once, in one
place, and is passed down. A conversion scattered across a function is a
conversion that will be forgotten in one of the places.

⚠️ And the first test I wrote for this pinned the **signature** (`the first
parameter is named moc_ms`) rather than the **behaviour** — so a mutation that
simply passed source-derived marks in stayed green. Mutation testing caught it.
The replacement uses a fixture where the two clocks give **different placements**
(5.6 s vs 4.8 s) and pins the correct number.

## 3. The audio master: arithmetic and FFmpeg, nothing else

No model call anywhere in this phase — pinned by an AST test over both new
modules, checking both imports and call names.

**Batched, and not for tidiness.** One `filter_complex` with 400 voice inputs
exceeds Windows' 32,767-character command limit, and the limit **truncates
silently**: FFmpeg receives a chopped filter expression and reports a syntax
error that points nowhere near the cause. Batching also keeps the filter graph's
branch count bounded, which is what FFmpeg's memory scales with.

**`amix`, not `concat`.** The segments do not follow one another — they sit at
their own marks, with gaps between them and (within the allowed tolerance) they
may touch. `concat` assumes succession; `amix` sums signals at each instant,
which is the actual shape of the problem.

⛔ **Always `normalize=0`.** `amix` defaults to dividing by the input count, so
adding one more voice segment would quieten the entire bed. Loudness is
normalised **once, at the end**: running `loudnorm` per batch and summing the
results gives a level nobody can predict. Both are pinned, the second by an AST
test asserting `loudnorm` appears in `tron_cuoi` and **not** in `tron_lo`.

The bed is ducked by −6 dB under the voice. That is how real dubbing is mixed:
without it the Vietnamese voice must be raised to be heard, and raising it pushes
it into the clipping ceiling. ⚠️ The value is unmeasured — Phase 21.

## 4. 🔴 A guard that could never fire — the third one in five phases

`kiem()` had a check that "the output must not be longer than the source". It
sounds necessary — it is the V4 contract's promise. But the two checks above it
already prove it: the intervals do not overlap, and they all end inside `[0, T]`,
so their sum is always ≤ T. **No input could make it fire.**

⭐ A guard that never fires is worse than no guard: it looks like a layer of
protection, it protects nothing, and it misleads the next reader about what is
actually being watched. This is the third time in phases 12–16 — after "never cut
everything" (Phase 12, saved by the 50 % floor first) and the unreachable
`CO_GIAN` rung (Phase 15).

It was removed from the code, and the promise is now pinned **in the tests** as a
consequence, measured through the real construction path across five input
shapes — including deliberately malformed ones.

## 5. Both presets, and one of them must not even look

`localize_preserve_picture` returns the identity map without reading the edit
plan at all. Same shape as Phase 12's "preserve never reads the VLM's opinion",
and the same reason: reading it is not *wrong* here, but it creates a dependency
that is not needed — and an unnecessary dependency is an unnecessary failure
path. A preserve run should not fail because `EDIT_PLAN` is missing an artifact
it has no use for.

Pinned by a test that makes reading any other stage **raise**.

## 6. Tests and evidence

`tests/test_442_asv_v4_ban_do_va_phoi.py` — **26 tests**: conversion · what has
no image · plan on the output axis · FFmpeg expression · batching · loudness
placement · fingerprints · no-AI.

**Mutation testing — 19 mutations, 19 red** (after the two holes above).

Regression: ASV cluster **909 passed**, 3 skipped, 1 xfailed.
`lint_app_contract`: 20 apps, 0 ERROR, 0 WARN.

## 7. ⚠️ One deviation from the phase protocol, stated plainly

Phase 15's full gate run was **voided by the gate itself** —
`[CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]` — because I created this
phase's two new modules while that run was in progress. The gate's own safeguard
caught it; the run proves nothing about Phase 15.

Rather than spend a second ten-minute gate on a tree I was about to change again,
phases 15 and 16 are validated by **one clean full gate on a still tree**, and
committed as two commits from that validated state. Both phases' own evidence
(cluster tests, mutation runs) is independent and complete.

⭐ This is the same failure family as `chot-khong-duoc-ghi-vao-cay`, now recorded
with its third variant: two overlapping mutation runs leaving a **live mutation**
in the tree (Phase 15, §6 of that report).

## 8. Debt carried forward

⚠️ **`ra_gan_nhat` has no caller yet.** The bed is currently mixed whole; mapping
it through the cuts is where it will be used, and that belongs with the video
render (Phase 17) so the picture and the bed are cut by the same map.

⚠️ **`NEN_GIAM_DB = -6.0`, `DOAN_MOI_LO = 24` are unmeasured.** Phase 21.

⚠️ **The smart preset's output duration is not yet verified end to end against a
rendered video** — only against the audio master. Phase 17 renders the picture,
and only then can the two be compared.

## 9. Exit gate

**PASS.** A deterministic TimingPlan exists for both presets, carrying its own
time map so a later reader can tell what output second 74 corresponds to in the
source; the AudioMaster is produced from it by pure FFmpeg with a validated
duration and measured loudness; and no model is called anywhere in the phase.
