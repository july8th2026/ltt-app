# Phase 24 — CPU/GPU performance and load acceptance

**Verdict: PASS, with one blocker recorded and one earlier finding corrected.**
Branch `phien/asv-v4`. Evidence:
[`24_hieu_nang.json`](../evidence/24_hieu_nang.json) ·
[`24_suat_gpu.json`](../evidence/24_suat_gpu.json) ·
[`24_asr_cuda.json`](../evidence/24_asr_cuda.json).

This phase changed no product code. It measured, and two of the measurements
changed what the project believes.

---

## 1. Both presets, per stage, on a quiet machine

32.2 s source, four scenes, four spoken lines. Background load recorded with every
run because every number here is **whole-machine**, not per-process — the question
is "does a run saturate the host", and this host serves customers.

| stage | preserve | | smart | |
|---|---:|---:|---:|---:|
| | s | CPU mean/peak | s | CPU mean/peak |
| `tai_len` (form → run) | 0.11 | 0 / 0 | 0.09 | 0 / 0 |
| `media_prepare` | 0.18 | 0 / 0 | 0.19 | 0 / 0 |
| `audio_prepare` (demucs) | 21.8 | 28.8 / 40.3 | 23.0 | 30.4 / 44.0 |
| `transcribe` (large-v3) | 41.1 | 33.0 / 64.3 | 33.5 | 39.8 / 96.9 |
| `edit_plan` | 0.01 | – | 0.12 | – |
| `content_process` | 0.03 | – | 0.03 | – |
| `voice_synthesis` | 0.69 | 24.5 | 0.58 | 30.0 |
| `timing_align` (+ master) | 2.53 | 17.3 / 20.3 | 2.66 | 18.1 / 20.9 |
| `compose` | 0.09 | – | 0.11 | – |
| `render` | 1.16 | 18.2 / 26.1 | 1.17 | 36.8 / 48.5 |
| `qc` | 1.99 | 25.5 / 37.1 | 2.03 | 21.4 / 24.2 |
| **whole run** | | 30.4 / 64.3 | | 34.7 / 96.9 |
| background at start | | 8.3 | | 14.2 |

Two stages dominate and both scale with input length: separation and transcription
are ~68 s of the ~70 s. Everything after them is single-digit seconds.

⭐ **A 96.9% sample is not saturation, and the first version of this test said it
was.** The smart run touched 96.9% on exactly one 0.5 s sample while the stage
averaged 39.8%. Calling that "saturation" measures a spike, not a problem. The
instrument now reports three things — peak, sustained mean, and **seconds spent at
or above the ceiling** — and the gate asserts on the last two. Measured: **0.0 s
above 90% in every stage of both runs.**

⚠️ The ceiling (90% sustained, 3 s grace) is set by this phase, not approved as
policy. It is written in the report and in the code as self-set.

### Two corrections to my own instrument, before the numbers were read

🔴 **The baseline was sampled too late.** The first run recorded "background 83.2%"
because it measured *after* the form had already uploaded the video and probed it.
A measurement that samples background after it has started working is measuring
itself. Moving the sampler to open before the upload dropped the recorded baseline
to 8.3%/14.2% — which is what the machine actually looked like.

🔴 **The VRAM check was vacuous and now says so.** It compares measured peaks
against each app's declared `gpu_vram_mb`. On this tree torch is CPU-only
(V4-R05), so VRAM barely moves and *any* declaration passes. It now skips with
that reason rather than passing green — the same trap Phase 23 hit with two cache
tests that only ever exercised a function that always says no.

## 2. 🔴 BLOCKER B24-01 — the smart preset never uses the hardware encoder

Measured on this machine: `detect_gpu_encoder()` returns **`h264_nvenc`**. Measured
in the run: the smart preset's build manifest records **`bo_ma_hoa: "libx264"`**.

`giai_doan_ban_dung` decides with `co_gpu = bool(ctx.gpu_uuid)` — correct in
principle (I11/O6: never pick a card yourself, use the one the platform granted).
But `COMPOSE` runs on `asv_media`, whose manifest declares `requires=("ffmpeg",)`
and no `gpu_vram_mb`, so `_vram_can` returns 0, no lease is ever taken, `gpu_uuid`
is always empty, and `chon_bo_ma_hoa(cho_phep_gpu=False)` always returns the
fallback.

Phase 17 measured what this costs: NVENC **1.68× faster** at matched quality
(SSIM ≈ 0.995), with host CPU **61% → 41%** — on a machine whose scarcest resource
is CPU.

⛔ Not fixed here, and the reason is not caution: every obvious fix is a design
change. Declaring `gpu_vram_mb` for `asv_media.compose` would make the whole
ffmpeg lane wait for a GPU lease — on a host without a card, compose would never
run at all. Moving the choice to render time would break Phase 17's rule that a
saved manifest alone reproduces the output. Pinned with `xfail(strict=True)`.
**Owner: Phase 27.**

⭐ Third of the same shape in three phases: B22-01 (the VLM built and never
called), B23-01 (the cache built and never hitting), and now an encoder path
measured, proven, and unreachable. Each was finished as a *capability* and never
connected as a *path*.

## 3. 🔑 The shared GPU slot stays shared — and the measurement is why

`pipeline.CHUOI` keeps `audio_prepare` and `transcribe` on one resource name, and
its comment names the exact experiment that would release them:

> Run `asv_gpu.audio_prepare` and `asv_gpu.transcribe` concurrently on a machine
> serving customers, measure whole-host CPU + free RAM + VRAM per card. If peak
> CPU < 70% and free RAM > 8 GiB, split the resource name, and throughput rises
> ~1.3×.

Run:

| | wall | CPU peak | free RAM low |
|---|---:|---:|---:|
| demucs alone | 20.74 s | 49.0% | 11.2 GiB |
| ASR alone | 42.79 s | 46.5% | 9.6 GiB |
| **both together** | **42.43 s** | **78.6%** | **9.1 GiB** |

Sequential 63.53 s → concurrent 42.43 s = **throughput ×1.5**, better than the
×1.3 predicted. Free RAM 9.1 GiB clears the 8 GiB condition.

**And peak CPU 78.6% fails the 70% condition, so the slot stays shared.**

⭐ The threshold was written down by an earlier phase, before anyone knew the
answer. This run is the one that executes it — not the one that adjusts it to fit.
The tempting move was available and measurable: 1.5× throughput for one line of
config. The condition said no.

⛔ What this measurement **cannot** answer is recorded in the evidence file: this
tree is `torch+cpu` (V4-R05), so both engines ran on CPU. The VRAM question — two
models on one card — is still open, and the answer here does not transfer.

A test now pins that the two stages still share a resource name, and says in its
message that splitting them requires a *new measurement*, not a change of mind.

## 4. 🔴 ASR on CUDA is root-caused — and Phase 22's record was wrong

Phase 22 recorded: *"one call ran over seven minutes with no result and no error"*
and handed it here. Measured properly, in three separated steps:

| step | CPU | CUDA |
|---|---:|---:|
| ask ctranslate2 for devices | 2 cards | 2 cards |
| load `large-v3` | 7.64 s | 8.93 s — **succeeds** |
| run inference | 35.43 s, 4 segments, `en` | **0.23 s — `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`** |

The CUDA path does **not** hang. It fails in a fifth of a second with a precise,
actionable message: `ctranslate2` ships `cudnn64_9.dll` but the CUDA 12 cuBLAS
runtime is absent from this tree's site-packages.

⚠️ **And production is not affected.** `deploy/windows/install.ps1` writes
`LTT_WHISPERX_PYTHON` into `app.env`, and `C:\LTTPlatform\whisperx-venv` exists, so
`transcribe_file` takes the WhisperX sidecar branch there. The broken path is the
in-process fallback, which only runs where that variable is unset — i.e. in this
dev tree.

🔴 **A real defect stays open in the owner app**: `_get_faster_model` wraps only
the *constructor* in its CPU-fallback `try`. Construction succeeds on a broken
CUDA stack; the failure comes at `transcribe()`, outside the guard. So the fallback
can never fire for this failure mode — the one it most obviously exists for. Not
fixed here: `apps/autosubvideo` is another app's code, and Phase 07 set the rule
that its contract gets extended deliberately rather than reached into.

⛔ What I am **not** claiming: that this explains the long block observed twice
(Phase 22, and again during Phase 23's regression, where a process sat at ~0 % CPU
for 30 minutes with `ctranslate2.dll`, `cudnn64_9.dll` and `nvcuda.dll` loaded).
The bounded harness fails in 0.23 s and does not reproduce it. Phase 22's sentence
is corrected to what was actually measured; the long block remains unexplained.

## 5. Repeated work: audited, counted, and deliberately left alone

Counters were attached at four doors — the single command runner, `ffprobe`, the
file hasher, and storage `open` — rather than at call sites, so a new caller is
counted without anyone remembering to update the audit.

Per run: **ffmpeg 22–26 · ffprobe 21 · file hashes 3 · storage reads 67–68.**

| repetition | measured cost | scales with input? | action |
|---|---|---|---|
| source file hashed **twice** (`media_prepare` + `audio_prepare`) | hashing runs at **455 MB/s**; 0.20 s at today's 90 MB cap, 4–9 s for a 2-hour source | **yes** | none now — see below |
| source `ffprobe`d 3× | metadata only, ~30–60 ms each | no | none |
| same JSON artifact read up to 4× | kilobytes | no | none |
| ~21 process spawns per run | ~30 ms each on Windows | no | none |

⭐ **No change applied, and that is the finding.** The phase says apply only
evidence-backed improvements; the evidence says the largest of these saves 0.2 s
today and 1–2 % of a run at the contract's two-hour ceiling, against stages that
take tens of seconds. Removing the duplicate hash is three lines and risk-free — it
is simply not yet worth the churn, and the number that would change that is
written down: when a source can exceed ~1 GB, the duplicate read passes 2 s and
becomes worth removing.

## 6. Tests and mutation results

`tests/test_450_asv_v4_hieu_nang.py` — 3 heavy measurements (barrier-gated, never
writing into the working tree) and 9 light checks reading the stored evidence.
`tests/fixtures/do_tai.py` — the sampler and the four-door counter.

**Mutation testing: 6 mutations, 6 red.** One needed re-aiming first: mutating
`ram_trong_thap_nhat_mb` inside a *stage* row changed nothing, because the check
reads the *run total*. A mutation that edits a field no test reads proves nothing
about the test — it measures the mutation.

The mutations cover the decisions, not just the code: splitting the GPU slot,
flipping the recorded encoder, changing a conclusion without changing the numbers
it came from, hiding the CUDA error message, and both saturation ceilings.

## 7. The same trap, in the same shape, two phases apart

The gate came back red on the secret scanner: **75 `bare_32_char_hex` findings**,
all storage-key basenames copied into the new evidence file.

Phase 22 hit this exact rule with 44 findings and fixed it — inside its own test
file. So the sanitiser lived where only Phase 22 could see it, and Phase 24 wrote
a fresh evidence file and walked into the same wall.

⭐ The fix is not "sanitise this file too". It is that the function now lives in
`tests/fixtures/asv_e2e.sach_de_cong_bo`, where the next evidence writer will find
it, and both phases call it. A lesson that stays inside the file that learned it
is not a lesson the next file gets.

## 8. Debt carried forward

⚠️ **VRAM under real GPU load is still unmeasured** — the declared 2 200 MB for
`audio_prepare` (Phase 13, on the production venv) stands; `transcribe` still
borrows 6 000 MB from `autosubvideo` and has never been measured for ASV.

⚠️ **Concurrency under real GPU** — §3 answers the CPU/RAM question for a CPU-only
host. Two models on one card is a different question with a different binding
constraint.

⚠️ **`AppManifest` still cannot declare RAM.** Phase 13 recorded it: the only
resource that grows with input length is the one the platform cannot see. Phase 13
worked around it inside the app (block-wise separation); the contract gap is
untouched.

⚠️ **Load beyond a single run is unmeasured.** Every number here is one run at a
time. What two or three concurrent customer runs do to this host is not in this
report.

## 9. Exit gate

**PASS.** No stage puts the host into sustained saturation: zero seconds above 90 %
in any stage of either preset, free RAM never below 8.6 GiB against a 4 GiB floor,
and every number recorded next to the background load it was measured against.

⚠️ Recorded honestly alongside: the one accepted optimization the product has
evidence for — the hardware encoder — **is not reachable at runtime**, so the smart
preset pays CPU for encoding that a measured 1.68× faster path already exists for.
