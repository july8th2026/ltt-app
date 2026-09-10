# Phase 13 — Audio separation quality and resource optimization

**Verdict: PASS.**
Source SHA at start `ea4c63f`. Branch `phien/asv-v4`.

Every number below was measured on **this machine**, on the **production venv**
(`C:\LTTPlatform\venv`, torch `2.11.0+cu128`, RTX 5060 Ti 16 GiB) — not the test
interpreter, which is a CPU-only build and therefore could never have run this
phase's central experiment.

---

## 1. 🔴 The first thing measured overturned the premise of the phase

`asv_gpu/manifest.py` declared `gpu_vram_mb = 4000` for `audio_prepare` with the
comment "CHUA DO" (not yet measured). So the obvious task was: measure VRAM.

Five durations, 60 s → 7 200 s:

| audio in | wall | **VRAM peak** | RSS peak |
|---|---|---|---|
| 60 s | 5,5 s | **1 089 MiB** | 1 557 MB |
| 180 s | 9,2 s | **1 089 MiB** | 1 829 MB |
| 600 s | 21,6 s | **1 089 MiB** | 3 152 MB |
| 1 800 s | 71,9 s | **1 089 MiB** | 7 323 MB |

⭐ **VRAM is flat across a 30× range.** `apply_model` splits internally and keeps
the result on the CPU side. The resource that scales with duration is **RAM**:

```
RSS ≈ 1 253 MB + 3,35 MB per second of audio      (linear fit, 4 points)
```

### And that is a contradiction with something else already declared

`nhap_media.THOI_LUONG_TOI_DA_S = 7200` — the product **accepts** 120-minute
video. By the law above, one separation of one *legal* file needs **≈ 24,8 GiB**.
This machine has **31,9 GiB total** and ~17,8 GiB free while serving customers.

⇒ A **legal job, running alone**, was enough to take the host down.
`tai_nguyen_suat=1` does not help: it only guarantees there is exactly one.

🔴 And the platform could not see it: `AppManifest` has `gpu_vram_mb` and **no
field for RAM**. The only resource that actually grows with the input is the one
resource admission control does not model.

⛔ I did **not** add a field to `AppManifest`. Phase 13's allowed changes are the
ASV audio engine, its resource settings and its tests; and CLAUDE.md is explicit
that a missing platform contract must be raised, not quietly worked around inside
one app — otherwise the next app falls into the same hole. It is recorded in
`apps/asv_gpu/manifest.py` and repeated in §8 below.

## 2. The fix bounds consumption instead of lowering the product ceiling

Lowering `THOI_LUONG_TOI_DA_S` would make the customer pay for an engineering
problem. Instead the separation now runs **block by block** — reading by block
and writing by block — so RSS is O(block), not O(duration).

Measured after the change, same machine, same venv:

| audio in | wall | VRAM peak | **RSS peak** |
|---|---|---|---|
| 600 s | 22,7 s | 1 555 MiB | **2 246 MB** |
| 1 800 s | 64,7 s | 1 555 MiB | **2 548 MB** |
| 3 600 s | 118,6 s | 1 673 MiB | **2 605 MB** |
| **7 200 s** (product ceiling) | 230,8 s | 1 673 MiB | **2 591 MB** |

**24,8 GiB → 2,59 GiB at the ceiling**, and flat. 1 800 s also got *faster*
(71,9 s → 64,7 s) despite ~3 % recomputation in the overlap: less allocation
pressure more than pays for it.

⭐ The 7 200 s row is a **measurement, not an extrapolation** — deliberately, because
this phase began with an extrapolation from a single point that turned out to be
wrong in the opposite direction.

## 3. 🔴 `shifts=1` — a third-party default that made the cache a lie

demucs 4.1.0 defaults `apply_model(..., shifts=1)`. Reading its source:

```python
if shifts:
    for shift_idx in range(shifts):
        offset = random.randint(0, max_shift)   # unseeded
    out /= shifts                               # divide by one
```

One pass at a **random** offset, then divided by 1. It takes the full randomness
of shift augmentation and gets **none of the averaging benefit** — averaging over
one sample is not averaging — and pays 0,5 s of padding on each side for it.

The consequence is not "slightly different output". `van_tay_tach` **promises**
the bed is a deterministic function of (source, model, stem policy, tool
versions). Measured: two runs of the same file down the same path differed
audibly in the stems (bass RMS diff 0,0072, correlation **−0,99** — sign
flipped). A cache that returns something recomputation cannot reproduce is not a
cache, and the app's whole artifact/lineage story rests on it.

`shifts=0` is now set **explicitly**, never inherited from the library. After the
change, two runs are **bit-identical**: difference 0,00000, correlation 1,0000000
on all four stems.

## 4. 🔴 Parity: the first measurement was measuring the wrong thing twice

Whole-file vs blocked, on pink noise, looked bad: `other` differed by 11,6 %.
But the **control was missing** — and once run, it showed the *same code* differed
from *itself* by nearly as much (§3). Almost all of that 11,6 % was the
nondeterminism, not the blocking.

With `shifts=0` the measurement became clean, and then a second trap appeared:
a global RMS number **hides the shape**. Profiling the difference in 5-second
windows against a structured fixture:

```
  0–300 s : difference exactly zero  (bit-identical)
  300 s   : −51,9 dBFS   ← the joint itself is QUIETER than its neighbours
  305 s+  : −42,7 dBFS steady
```

So there was **no click at the seam** — the crossfade works — but every block
after the first was uniformly offset. Cause: `apply_model` splits internally at
`offsets = range(0, length, stride)`. Block 1 starts at 0 so its grid coincides
with the whole-file run's; block 2 starts at a point not divisible by `stride`,
so **every internal segment inside it is out of phase**.

⭐ Fix: round block boundaries **down** to a multiple of that stride
(`buoc_phan_doan`), so absolute offsets are `(m + j) · stride` — exactly the
offsets the whole-file run uses.

| bed (drums+bass+other — what the customer hears) | signal/difference | rel. error | correlation |
|---|---|---|---|
| before grid alignment | 27,1 dB | 4,39 % | 0,999035 |
| **after grid alignment** | **54,4 dB** | **0,190 %** | **0,9999982** |

**116 of 119** 5-second windows are now bit-identical; the three that are not sit
around the single block boundary.

And the reference that makes "quality-equivalent" a testable claim rather than a
hope: the **old shipping behaviour varied from itself** by 31,0 dB. The blocking
difference is now **23 dB smaller than the variation the product already had.**

⚠️ Before alignment it was *larger* (27,1 vs 31,0 dB), and I do not get to claim
the earlier version was equivalent. The claim holds for what ships.

## 5. No silent CPU fallback — and refusal that says something

The old line was `"cuda" if torch.cuda.is_available() else "cpu"`, which
`V4_RESOURCE_CPU_GPU_POLICY` forbids. The cost is not "a bit slower": measured,
CPU is **9,5× slower** (180 s of audio: 9,2 s on card, 86,5 s on CPU). At the
7 200 s ceiling that is ~37 minutes **holding the `tach_nguon_cuc_bo` slot** — so
every other customer's run stops behind it, with no error anywhere.

Two cases are now distinguished, which is the entire meaning of the flag:

* no card granted → CPU is the declared path, not a fallback;
* card granted (`ctx.gpu_uuid`) but torch sees no CUDA → **`ThieuCard`**.

⭐ And refusing loudly was not enough. Mutation testing found that the parent
flattened every non-zero exit into a generic `MediaError`, so `loi.phan_loai`
would **never be called with `ThieuCard`** — the classifier was correct and
unreachable. `tach_nguon` now reads the child's report first. `ThieuCard` is
`TAM_THOI` (retry — the platform may grant a *different* card); a corrupt audio
file stays a final failure.

**Device evidence** is now checkable rather than believable: the child reports the
card **it saw** (`torch.cuda.get_device_name(0)`), the parent adds the card **it
was granted** (`ctx.gpu_uuid`), and `tom_tat` carries both. One end reporting both
proves nothing.

⛔ My first version had the child read `CUDA_VISIBLE_DEVICES` "just as evidence",
and guard I11 rejected it. The guard was right: a file that knows that variable
name is one line away from pinning a card itself. The parent already knew.

## 6. 🔴 31 tests in 9 files were loading htdemucs for real, every gate run

`tests/rao_chan_nang.py` exists precisely to stop this. It was attached to the two
tests that call demucs **directly**. `test_406::test_cong_thoat_ban_nen_...`
reaches it **indirectly through the job queue**, so it was never barred — 16 s of
real model loading per gate run.

Then the new interlock showed the true scope: **31 tests across 9 files**
(QC, artifact lifecycle, downstream invalidation, fault injection, …). **None of
them is about demucs.** They touch it only because the chain passes through
`audio_prepare`.

⭐ The lesson, and the reason the interlock sits where it does: **a barrier placed
on the callers only stops the callers who know about it.** A new path to the same
dangerous place walks straight past. The interlock is now at the *model load*,
where there is exactly one path — it refuses when `PYTEST_CURRENT_TEST` is set and
`LTT_TEST_NANG` is not (a real worker never has the former, so it is invisible to
production).

The nine files each opt into a **file-scoped autouse** stub — one line, visible in
the file. Not a global `autouse` in `tests/conftest.py`: that file says plainly not
to add one unless it is right for *every* test, and points at exactly this pattern.
ffmpeg, storage, DB, queue and worker stay real; only the model is replaced.

Cluster runtime 219,8 s → **200,7 s**.

## 7. Measured and deliberately **not** changed

**Duplicate source decode** (media stage decodes 16 kHz mono; audio stage decodes
44,1 kHz stereo). One ffmpeg invocation with two outputs produces **byte-identical**
files and saves **0,34 s** on a 10-minute source (0,78 → 0,44 s). Next to demucs's
22 s that is noise, and merging them means MEDIA_PREPARE must emit a >1 GB WAV
artifact at the ceiling. Measured, and the measurement says no.

⚠️ The real cost is the duplicate **download**, not the decode — and it is zero
under `LocalStorage` and unmeasurable until R2 is deployed. Streaming hashes
(`assets.bam_tep`) were already done in an earlier phase.

**Separate resource slots for demucs and ASR.** The stated reason for sharing one
slot — "demucs eats every remaining core" — is **measurably obsolete**: with the
thread cap, one concurrent run peaks at 40 % host CPU and two peak at **57 %**,
RAM floor 14,4 GiB, throughput 1,33×. The host can clearly take two.

⛔ Still kept shared, and the comment now says why *honestly*: that measurement is
demucs + **demucs**. Nobody has measured demucs + **whisper**, which has a different
profile (6 000 MB VRAM declared, and whisperx is CPU-heavy in alignment). The exact
missing measurement is written down in `pipeline.py` with its acceptance threshold.

## 8. Tests and evidence

`tests/test_439_asv_v4_am_thanh_tai_nguyen.py` — **24 tests**, four groups.
The whole block-arithmetic group runs **without loading demucs** (the model call is
injected), in ~3 seconds.

**Mutation testing — 17 mutations, 17 red** (after the hole below was closed):

| Mutation | Caught by |
|---|---|
| drop segment-grid alignment | `test_ranh_khoi_la_BOI_cua_BUOC_PHAN_DOAN` |
| drop the crossfade | `test_KHONG_co_BUOC_NHAY_o_cho_noi_giua_hai_khoi` |
| swap the two crossfade weights | same |
| load the whole file instead of blocks | `test_KHONG_nap_ca_tep_vao_RAM` |
| silent CPU fallback | `test_DA_CAP_card_ma_khong_thay_CUDA_thi_NEM` |
| rely on demucs's `shifts` default | `test_apply_model_nhan_overlap_va_shifts_TUONG_MINH` |
| re-enable random shift | `test_dich_ngau_nhien_TAT` |
| remove the model-load interlock | `test_chot_chan_nap_model_that_trong_bo_test` |
| drop the sample-rate mismatch check | `test_tan_so_TEP_khac_tan_so_MODEL_thi_NEM` |
| raise the block ceiling back to danger | `test_KHOI_GIAY_giu_RSS_duoi_tran_da_do` |
| remove the torch thread cap | `test_tran_luong_torch_van_con` |
| don't tell the child a card was granted | `test_tach_nguon_them_co_BUOC_GPU_...` |
| parent doesn't pass the grant down | `test_giai_doan_bat_BUOC_GPU_theo_dung_card_da_cap` |
| don't record the granted card | same |
| **flatten `thieu_card` into `MediaError`** | `test_cha_NEM_dung_ThieuCard_...` |
| classify `ThieuCard` as final | same |
| revert VRAM to the unmeasured guess | `test_vram_khai_bang_con_so_DA_DO` |

🔴 **Two holes mutation testing found in my own tests:**

1. Every block test used an **identity** fake model — and with an identity model
   the previous block's tail and the next block's head are *equal*, so any convex
   combination returns the same thing. Removing the crossfade entirely, or
   swapping its weights, stayed **green**. A second fake model that returns a
   ramp *by position in the block* makes the two ends disagree maximally, so a
   bad joint shows up as a **step** — which is exactly what the ear hears as a click.
2. The parent-side `thieu_card` detection was untested (§5), leaving the
   classifier correct but unreachable.

⚠️ And one guard defect found while running the suite: `test_419` kept a **second
copy** of the `CUDA_VISIBLE_DEVICES` rule that scanned *every* string constant —
including docstrings. `test_401` had already hit that, learned it ("a guard that
fails on the text explaining the guard teaches the next author to delete the
explanation"), and been fixed to read the AST and exempt docstrings. The copy
never got the fix, and it flagged this phase's explanation of the rule. Resolved
by deleting the copy and calling the fixed one — one rule, one enforcement.

Regression: **827 passed, 3 skipped, 1 xfailed** across the ASV cluster.
`lint_app_contract`: 20 apps, 0 ERROR, 0 WARN.

## 9. Debt carried forward

⚠️ **`AppManifest` still cannot express RAM.** Consumption is bounded inside the
app, so nothing is at risk today, but the contract gap is open and the next
app with a memory-scaling stage will meet it.

⚠️ **`asv_gpu.transcribe` VRAM is still borrowed**, not measured.

⚠️ **Parity was measured on synthetic material.** Noise and a structured
bass/percussion/voice mix — not real programme audio. The grid-alignment result
(116/119 windows bit-identical) is largely content-independent, but the htdemucs
stem-quality limitations documented in `tach_tieng.py` remain untested against
real content and stay in QC's messaging unchanged.

⚠️ **The block/overlap constants (300 s / 10 s) are chosen, not optimised.** They
are inside no fingerprint — blocking does not change the declared separation
policy — but a future change to them should re-run §4.

## 10. Exit gate

**PASS.** The audio path is quality-equivalent by a measured margin (23 dB better
than the variation the product already shipped with), deterministic for the first
time, bounded in memory at the product's own input ceiling, and it cannot fall
back to CPU or load a model inside the test suite without saying so.
