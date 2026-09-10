# Phase 21 — Product UI, API truth and durable upload workflow

**Verdict: PASS.**
Source SHA at start `9ddf7b0`. Branch `phien/asv-v4`.

---

## 1. 🔴 The headline feature had no way to be chosen

The string `preset` appeared **zero times** in `routes.py` and zero times in
`asv_trang_chinh.html`.

So the whole V4 product — *two* presets — offered the customer exactly one. Every
run fell back to `localize_preserve_picture`, and the entire `smart_localize`
path that phases 12 through 18 were built on was a road **nobody could reach**.

The form now offers both, with descriptions written for a customer rather than a
developer: they decide on what *they* care about — whether the picture gets cut —
not on how we do it. Pinned by a test that forbids `stream copy`, `re-encode`,
`keyframe`, `GOP`, `nvenc`, `libx264`, `ffmpeg`, `codec`, `concat` and `encode`
from appearing in the labels.

⚠️ And the cutting preset **states its cost**: the picture is re-encoded, so the
output is near-identical but no longer pixel-for-pixel the original. Hiding that
would be selling something other than what is delivered.

## 2. 🔴 The form offered a "default voice" the engine refuses to serve

Phase 09 removed the silent default: `rang_giong` raises when `USER_SELECTED`
arrives without a voice id, because "leave it blank and take the default" is
exactly what ADR-V4-001 D-V4-04 forbids.

The form never got the message. It still offered `<option value="">Giọng mặc
định</option>` — so a customer choosing it would pass four stages, have credits
held, and fail mid-chain.

`V4_MVP_PRODUCT_CONTRACT` has a name for that: a **false feature**. The fix is not
to make the engine more permissive — it is to stop offering something that does
not exist. The list now always includes sample voices, so a customer who has
cloned nothing still has a **real** choice rather than an empty box.

⭐ `AUTO_MATCH` is offered but **says plainly that it is not ready** — Phase 19
recorded that no stage produces a `HoSoNoiDung`, so auto-matching defers rather
than picking a voice at random. Exposing a control that cannot work, silently, is
the same false-feature defect in the other direction.

## 3. Failing at the door instead of mid-chain

`USER_SELECTED` with no voice is rejected at submission. The alternative is a
customer waiting through four stages with credits held, to receive a failure that
was knowable at the first keystroke.

Same for an invalid preset or voice mode: refused at the door, form returned with
the reason, rather than reaching a worker.

## 4. Tests and evidence

`tests/test_447_asv_v4_giao_dien_san_pham.py` — **20 tests**.

**Mutation testing — 11 mutations, 11 red** (after the holes below).

### 🔴 Eight holes at once, and they were all the same mistake

The first version of this file tested `gia.py`'s **tables** — and mutation testing
answered with eight consecutive green results: drop the preset check, drop the
voice-mode check, drop the voice requirement, stop saving `preset` into settings,
stop passing the table to the template, put the empty voice option back…

⭐ Every one of those lives in the **route and the template**, which is the entire
subject of Phase 21. I had tested the data behind the form instead of the form —
the easy thing rather than the thing that matters. The new group posts real
multipart requests over HTTP and reads the resulting run's settings.

### And one more the mutations found afterwards

Nothing checked the **error page**. Reverting only the error-path context to the
old voice list stayed green — meaning a customer who mistyped anything would get
the form back **with no voice to choose**, unable to fix the error they were just
told about.

⭐ The error page is viewed more than the normal page, at exactly the moments
people are least patient. It is not allowed to be a degraded copy of the main one.

### A boundary guard caught me too

`test_435::test_ASV_chi_cham_nhung_ten_da_khai` rejected my import of
`giong_mau.THEO_MA` — an internal dict — instead of the declared `loc()`. It was
right: an internal dict is something the other app may reshape at any time; a
declared function is a promise it keeps. Same family as the I11 guard that caught
the `CUDA_VISIBLE_DEVICES` read in Phase 13.

Regression: ASV cluster **1041 passed**, 3 skipped, 1 xfailed.

## 5. Debt carried forward

⚠️ **The durable upload path is unchanged and still untested end to end here.**
Phase 05 built it and it works; this phase did not touch it, and the bounded
90 MB multipart path remains the only one exercisable under `LocalStorage`.

⚠️ **No repair/retry-by-scope control in the UI.** Phase 19's plan is computed but
not driven, so there is nothing to expose yet; the existing whole-stage retry
remains.

⚠️ **QC status is not surfaced to the customer.** The report exists and the
timeline carries it for operators; the customer summary shows progress and cost
but not the QC verdict.

## 5b. ✅ Verified in a real browser, and it found one more thing

The repo's standing policy requires rendered-GUI changes to be checked in a real
browser, not asserted from returned HTML. The form was served from this worktree
on a spare port with a **throwaway database and data directory** — this machine is
production, so a UI check is not allowed to touch its files.

Confirmed on the rendered page: both presets present with their descriptions, the
cutting preset stating its cost, both voice modes with `AUTO_MATCH` saying plainly
that it is not finished, and **20 real sample voices with no empty option**.
Console: no errors. Network: every request 200.

⭐ And the browser found something the HTTP tests could not: the page was rendering
in English, and the **older** sections were translated while my **new** ones fell
back to Vietnamese — because the new strings had no EN entries yet. A mixed-language
form is the kind of defect that only shows up when you look at it. Fourteen
translations added, re-served, re-checked: consistent throughout.

## 6. Exit gate

**PASS.** A customer can now complete **both** presets — the second was
unreachable before this phase — choosing from voices that actually exist, with
labels that carry no implementation jargon and no feature that is not there. What
is not ready says so.
