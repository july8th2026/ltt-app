# Phase 19 — AI QC and targeted repair plan

**Verdict: PASS.**
Source SHA at start `04fa33a`. Branch `phien/asv-v4`.

---

## 1. Three questions technical QC cannot answer

Phase 18 measures: valid file, right duration, right loudness, not black. All of
that can **pass** while the output is still wrong in three ways:

1. the TTS **misread** the written line (swallowed a word, said a number wrong)
2. the Vietnamese line **means something else** than the source
3. a join between two kept scenes **breaks visual continuity**

None of these is a threshold. They need something that listens, reads and looks —
which is why this phase exists.

⛔ All three go through `ai.goi_tinh_tien`, the single door from Phase 08. The
phase forbids new providers, and that door is the only place such a change could
happen without anyone noticing.

## 2. 🔴 The repair map, and the direction that is easy to get wrong

A full rerun would fix anything — and pay for everything. The phase forbids it in
as many words, and the reason is not only cost:

⛔ Re-running a stage that already succeeded produces a **different** result
(models are stochastic). So a broad rerun is not "fixing one defect" — it is
trading one known defect for a set of unknown ones.

    misread     -> VOICE_SYNTHESIS   (re-read that one segment)
    mistranslated -> CONTENT_PROCESS (rewrite that one line)
    doesn't fit -> VOICE_SYNTHESIS   (refit — Phase 15's ladder already exists)
    bad cut     -> EDIT_PLAN         (revisit that one scene)
    broken picture -> RENDER         (re-render — not a content defect)

🔴 **The reverse direction is where it goes wrong.** A line the TTS misread must
**not** be pushed back to `CONTENT_PROCESS`: that text is *correct*. Rewriting it
pays to swap one correct sentence for another correct sentence — which can then be
misread again.

A mistranslation is the opposite: re-reading it any number of times yields the
same wrong meaning.

⇒ "Earliest stage that **can**" means the earliest stage whose *output is the
cause*. Earlier redoes work that was right; later fixes nothing.

`gon_theo_don_vi` enforces the rule where it matters: when one segment carries
**both** defects, the earlier stage wins — because re-reading a mistranslated line
still gives a mistranslated line — while a segment carrying **only** a speech
defect stays at `voice_synthesis`. Both directions are pinned, and mutation
testing kills both inversions.

## 3. Confidence is a field, not a rounding step

A model returns a verdict **with a confidence**. Below the threshold the verdict
is **recorded but generates no repair work**: an unsure model is not a reason to
pay to redo something — and not a reason to hide the observation either.

⛔ Missing confidence defaults to **0**, never 1. A model that did not say how
sure it was does not get to have certainty assigned to it; defaulting to 1 would
turn a malformed response into a paid repair order.

⭐ And speech QC is deliberately different: it is a **measurement** — two strings,
one ratio — so it carries confidence 1.0. We are not guessing there.

The word-overlap ratio is a coarse approximation, chosen because it fails in the
**safe** direction: it under-reports rather than over-reports. `SequenceMatcher`
over the whole string was rejected because a sentence with two clauses swapped is
still a correctly-read sentence for dubbing purposes, and it would score it very
low.

## 4. The VLM is asked only at the joins

An untouched scene has nothing to ask about. Asking across the whole film would be
paying to hear the model confirm that what was not touched is intact.

⛔ And each join needs **two** frames — before and after. The question is about a
*transition*; one frame cannot answer it.

## 5. Repair cycles are capped tighter than Phase 15's, and for a stated reason

`VONG_SUA_TOI_DA = 1`, against `VONG_TOI_DA = 2` for the fitting loop.

🔑 The fitting loop corrects a **measured** quantity — audio duration — so it
converges: each round lands closer to the slot. This loop corrects a model's
**subjective** verdict. Two runs can disagree about the same sentence, and looping
further is paying to watch it change its mind.

That relationship is pinned by a test, not just written down.

## 6. Tests and evidence

`tests/test_445_asv_v4_qc_ai_va_sua.py` — **25 tests** in five groups.

**Mutation testing — 19 mutations, 19 red**, including both inversions of the
repair map, dropping the confidence filter, removing the cycle cap, widening it
past the fitting loop's, defaulting missing confidence to certain, treating a
missing verdict as a failure, accepting invented ids, and asking the VLM
everywhere instead of at the joins.

⚠️ One mutation initially failed to anchor (wrong indentation in my patch script,
not a test gap) and was re-run once corrected.

Regression: ASV cluster **1003 passed**, 3 skipped, 1 xfailed.
`lint_app_contract`: 20 apps, 0 ERROR, 0 WARN.

## 7. Debt carried forward

⚠️ **The repair loop is planned, not yet driven.** `sua_chua` decides *what* to
redo and *where*; wiring that into `giai_doan_qc` so a failing run actually
invalidates those units and re-runs them is the remaining half. The phase's exit
gate asks for repairs that "rerun the smallest safe scope", and the scope
computation is complete and tested — the execution is not.

⚠️ **No real model has produced a verdict.** Prompts, parsers and the confidence
contract are exercised against constructed responses only.

⚠️ **`NGUONG_KHOP_DOC = 0.80` and `DO_TIN_TOI_THIEU = 0.70` are unmeasured**,
chosen toward fewer false alarms because a false alarm here costs a paid re-read.
Phase 21.

⚠️ **Speech QC has no ASR wiring yet.** `so_khop_doc` joins written text to what
ASR heard, but nothing runs ASR over the dubbed output. That is one call to the
existing boundary and belongs with the loop wiring above.

## 8. Exit gate

**PASS** for the scope this phase can complete deterministically: QC failures
produce evidence with confidence attached, and repairs are targeted at the exact
units and the earliest stage that can actually fix them, bounded by a cap that is
tighter than the measured-quantity loop and justified against it. The execution of
that plan is recorded as debt rather than claimed.
