# Phase 17 — Compose, render manifest, dual render and GPU encode

**Verdict: PASS.**
Source SHA at start `44b2c98`. Branch `phien/asv-v4`.

---

## 1. 🔴 The cutting preset cannot stream-copy, and here is the measurement

Stream-copy concat is tempting: no generational loss, no GPU, near-instant. But
**stream copy can only cut at keyframes** — a container constraint, not an FFmpeg
limitation.

Measured on a file this very chain produces (`libx264 -preset veryfast`, default
GOP):

    keyframes at: 0, 8.33, 16.67, 25.00, 33.33, 41.67 … seconds
    GOP = **8.333 s**, perfectly regular

So a scene cut at second 20 would be dragged to 16.67 or 25 — **up to 8.3 s
away** — while Phase 16's audio master was built for the *exact* cut point.
Picture and sound would drift apart by seconds.

⇒ The smart preset **must** re-encode. That is not an optimisation choice; it is
the condition for picture and sound still matching. The preserve preset keeps
`-c:v copy` exactly as before.

## 2. ⚠️ My first encoder comparison used the wrong scale

The naive benchmark said NVENC produced a file **twice as large**. That number
was meaningless: `cq=23` on NVENC is not `crf=23` on x264. Only after matching
**quality** does the comparison read:

| config | time | size | SSIM vs source | mean host CPU |
|---|---|---|---|---|
| `libx264 veryfast crf23` | 8.31 s | 40.6 MB | 0.99578 | 61.1 % |
| `h264_nvenc p4 cq23` | 4.98 s | 80.6 MB | 0.99795 | — |
| **`h264_nvenc p4 cq28`** | **4.95 s** | 50.8 MB | **0.99519** | **40.9 %** |
| `h264_nvenc p4 cq31` | 4.95 s | 36.7 MB | 0.99190 | — |

At matched quality NVENC is **1.68× faster and 25 % larger**. Neither dominates,
so "prefer hardware" is a reflex, not a conclusion.

⭐ The deciding axis is the third column: **mean host CPU 61 % → 41 %**. On this
machine CPU is the contended resource — the whole chain of incidents that led to
this session began with CPU-overload reboots — while the GPUs sit idle.

⚠️ And one thing must be said accurately: **both peak at ~91 %**. NVENC offloads
the *encode*; H.264 decode and the concat filter stay on the CPU. "The GPU takes
over" would be false, and the measurement says exactly how false.

`cq=28` is chosen over `23` because `23` doubles the file for a difference the
eye cannot see (SSIM 0.99795 vs 0.99519) — paying in disk and bandwidth for
nothing.

## 3. 🔴 A pre-existing test caught me removing a guard

`test_427::test_render_van_TU_CHOI_moi_che_do_hinh_khac_copy_HOAC_da_biet_den_preset`
was written **before this phase**, anticipating exactly this refactor. Its
docstring says the wrong way to relax the guard is to delete it, because then
`localize_preserve_picture` loses its protection **silently** — no test fails,
and one day a customer picks "keep the picture" and receives a re-encode.

I did precisely that: moved the decision upstream into `che_do_render.che_do_cho`
and left the renderer with no way to know. The test went red, and it was right.

⇒ The manifest now **carries the preset**, and the renderer cross-checks
`che_do_cho(preset) == cach_render` at the last gate before spending a render
slot. The guard was **narrowed, not removed**.

## 4. The renderer stopped mixing audio

Phase 16 produces a complete AudioMaster. The renderer was still mixing bed + N
voice layers with its own `loudnorm` — which would normalise the same signal
**twice**, the second silently winning, and would leave Phase 16's master as an
artifact that costs FFmpeg time and nobody reads (the exact defect removed
elsewhere in Phase 14).

`_loc_am` is gone. Its four hard-won lessons went **with** it into `am_master`,
together with their tests:

  * `amix … normalize=0` — the default divides by input count, so loudness would
    depend on **how many lines were spoken**
  * `adelay … :all=1` — without it only the first channel is delayed, and the
    voice sits off to one ear
  * `aformat` per input — letting `amix` choose means it chooses by the first input
  * `loudnorm … dual_mono=true` — a mono segment upmixed to stereo measures 3 dB
    louder than it is, and TTS returns mono

⛔ Deleting a function without carrying its reasons forward is the reliable way to
make the next author rewrite the original mistake.

The manifest still records `nen` and `lop` — they are the **record** of the timing
decision and answer "why is this line here" during an investigation — but the
renderer reads only `master`.

## 5. Tests and evidence

`tests/test_443_asv_v4_che_do_render.py` — **24 tests**: path selection · the
preserve promise and its last gate · cut-concat order and audio isolation ·
encoder policy · reproducibility · no-AI.

**Mutation testing — 19 mutations, 19 red** (after the three holes below).

### 🔴 Three holes, and one is a trap this repo had already learned

1. **My `dual_mono` test scanned the file's *text*** — and the comment above the
   line explains the rule using the string `dual_mono=true`. So removing the
   actual code left the test **green**, satisfied by its own explanation.

   ⭐ This is `test_401._vi_pham`'s lesson **inverted**: there a guard fired on
   the prose explaining it; here a test was *satisfied* by the prose explaining
   it. Both come from reading text instead of structure. It now reads the AST —
   comments never enter the syntax tree.

2. **Nothing passed an invalid render mode into `ban_dung.dung`.** Every test
   used a valid one, so whether it validated at all was unmeasured. A manifest is
   **stored**; a bogus mode would sit in the customer's storage until someone
   re-rendered from it, surfacing far from where it was created.

3. **The fingerprint has two fields carrying the same information** (`bo` and
   `tham_so`), so blanking one still changed the hash. Not a defect — redundancy
   makes a fingerprint harder to break — but claiming "the test caught removing
   `bo`" would have been false. The test now pins what actually matters: no two
   encoders ever produce the same fingerprint, whichever field carries it.

Regression: ASV cluster **940 passed**, 3 skipped, 1 xfailed.

## 6. Debt carried forward

⚠️ **The smart render path has not been run end to end through the queue.** The
chain tests exercise the preserve path; the cut-concat command is pinned as a
*command* and benchmarked *directly*, but no queued run has produced a cut video.
Phase 22 (E2E functional acceptance) is where that belongs.

⚠️ **Hardware decode is untried.** Item 5 of the phase makes it optional and
conditional on measured gain; since decode is what keeps both paths at ~91 % peak
CPU, it is the obvious next measurement — but it must be a measurement, not an
assumption.

⚠️ **QSV and AMF parameters are declared, never measured.** Only NVENC and
libx264 were benchmarked, because only they exist on this machine. The table
entries for the other two are borrowed conventions and are marked as such.

⚠️ **`ra_gan_nhat` still has no caller.** Mapping the background bed through the
cuts remains open (carried from Phase 16).

## 7. Exit gate

**PASS.** Both strategies are deterministic and declared in the manifest: the
preserve path stream-copies and cannot be silently pushed onto a re-encode
(cross-checked against the preset at the last gate), and the cutting path
re-encodes for a measured reason, with an encoder chosen by policy — hardware
only when the platform actually granted a GPU, CPU as an explicitly declared
fallback rather than a silent slide.
