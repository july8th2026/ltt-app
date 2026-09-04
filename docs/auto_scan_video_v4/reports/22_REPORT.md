# Phase 22 — E2E functional acceptance

**Verdict: PASS, with one named blocker handed to Phase 27.**
Branch `phien/asv-v4`. Machine evidence: [`evidence/22_nghiem_thu.json`](../evidence/22_nghiem_thu.json).

Both presets now produce a usable final video with every critical QC gate passing.
Three real defects were found by running the product end to end, and all three are
fixed here. A fourth finding — the visual-understanding half of the product is not
wired into the pipeline — is a feature gap, not a bug, and is recorded rather than
silently fixed.

---

## 1. What was actually run

One source video, both presets, from the customer's form to the file the customer
downloads. Real ffmpeg, real demucs (htdemucs on this machine's CPU), real ASR
(`faster-whisper large-v3` — the production constant, unchanged), real queue and
real worker claim/routing, real database, real storage, real credit hold and
settlement, real download route and real owner check.

| stage | preserve preset | cut preset |
|---|---:|---:|
| `media_prepare` | 0.17 s | 0.16 s |
| `audio_prepare` (demucs, CPU) | 19.4 s | 18.9 s |
| `transcribe` (large-v3, CPU) | 34.4 s | 23.8 s |
| `edit_plan` | 0.01 s | 0.10 s |
| `content_process` | 0.03 s | 0.03 s |
| `voice_synthesis` | 0.52 s | 0.52 s |
| `timing_align` (+ audio master) | 2.19 s | 2.11 s |
| `compose` | 0.08 s | 0.08 s |
| `render` | 1.15 s | 1.14 s |
| `qc` | 1.70 s | 1.67 s |
| **wall clock, form to download** | **63.0 s** | **51.5 s** |

Source: 32.2 s, four scenes, four spoken lines, two speakers.

### The source is real speech, and that is the point

Every chain test before this one ran on `asv_media.tiny_mp4` — a 440 Hz sine on a
static frame. Real ASR on it correctly returns **zero segments**, so every chain
test had to substitute the transcript, and nothing V4-specific (scene cuts, edit
plan, keep/cut) could ever fire.

The Phase 22 fixture uses Windows SAPI — five en-US voices already installed —
to read a four-line script into real speech, mixes it over a continuous
background bed, and cuts the picture between lines. No copyright, no PII, no
network, no key: the same three properties that made `asv_media` choose `lavfi`
in the first place. It just also speaks.

The proof that it is real speech is that the real engine reads it back:
`large-v3` returned **language `en` and four segments** matching the script.

⛔ What this fixture does **not** prove is stated in the report itself: SAPI is an
English voice. It stands in for the **source**, and it does not stand in for
`LTTStudioVoice` on the output. Vietnamese dubbing quality is still closed only by
a real run through the :8120 sidecar.

### What was substituted, and why

Two outbound doors. Both are declared in `tests/fixtures/asv_e2e.THAY_THE`, copied
verbatim into the report, and a test fails if the report and the declaration ever
disagree or if a named door stops existing.

| door | why not real here | what stayed real behind it |
|---|---|---|
| `platform_core.llm.dieu_phoi.goi` | provider keys live in `C:\LTTPlatform\secrets`, which is ACL-locked (`Test-Path` → *Access denied*) | `ai.goi` (provider order, model map, token ceiling, ambiguity classification) **and** `ai.goi_tinh_tien` (budget gate, usage ledger, `UNIQUE(run_id, ma_dispatch)`) both run |
| `giong_noi.doc_mot_doan` / `giai_giong` / `san_sang` | `LTTStudioVoice` :8120 answers `401` without `LTT_VOICE_SIDECAR_TOKEN`, same locked directory | the returned audio is a **real WAV** from SAPI, so the fit ladder, the file check, the mix, the loudness normalisation and the render all work on a real waveform |

⭐ The model door is substituted one level **below** `ai.goi_tinh_tien`, not at it.
That is deliberate: `goi_tinh_tien` is the paying path, and replacing it would mean
the acceptance says nothing about the invoice — one of the things Phase 22 has to
show. The ledger came back with 9 delivered rows per run and a clean two-way
reconciliation.

---

## 2. 🔴 The renderer delivered the wrong audio track

`giai_doan_ket_xuat.chay` loaded `ban["tieng"]["nen"]` — the **background bed** —
and handed it to ffmpeg as the output's only audio input.

So every delivered video carried the music and ambience separated out of the
customer's own source, and **not one line of the dubbing**. The entire chain from
Phase 14 to Phase 16 — adaptation, synthesis, fitting, timing, mixing, loudness —
was written to a file nobody read.

The build manifest says so on the line above the field it was reading:

> `nen` and `lop` stay here as the **record** of the timing decision […] but what
> the renderer actually reads is `master`.

### Why no test caught it

Both halves were correct and both were tested. Phase 16 proved the master is built
right. Phase 17 proved the render command is built right. Nobody checked that the
command reads the **right field** — the seam between two proven halves.

⭐ And the audio measurements are what exposed it, not a code reading: the delivered
file measured **-18.69 LUFS** against a -14 target and **+4.1 dBTP** against a -1.5
ceiling. That combination is not "a bad mix" — it is the signature of a signal that
never went through `loudnorm` at all.

Fixed: the renderer reads `tieng.master` and refuses the manifest without one;
`ban_dung.kiem` now requires the master key and includes it in the resource
cross-check; the parameter is named `duong_master`, because `duong_nen` was the
name that made the defect invisible. Pinned by an AST guard that fails if
`chay` ever reads `tieng.nen` again — comments never enter the syntax tree, so the
paragraph explaining this defect cannot satisfy the test that prevents it.

## 3. 🔴 One defect was hiding another: the picture was being truncated

With the master finally in use, `test_402`'s full-chain test went red on **T3** —
"output video stream is bit-identical to the source", the promise of the
preserve preset.

Cause: `loudnorm` shifts output timestamps by ~0.1 s, so `-t 3.000` cut the master
at 2.919 s; the render maps one video and one audio stream with `-shortest`, and a
short master **truncates the picture**.

That was invisible before, because the bed the renderer was wrongly using is always
exactly as long as the source. One defect masked the other.

Measured, step by step, on a 3.019 s source cut with `-t 3.000`:

```
anull                             -> 3.000
loudnorm                          -> 2.919   <- 0.1 s gone
loudnorm,apad                     -> 2.919   <- apad does not fix it
loudnorm,apad=pad_dur=0.5         -> 2.919
loudnorm,asetpts=N/SR/TB,apad     -> 3.000
```

⭐ The instinctive fix (`apad`) does nothing, because the problem is not missing
samples — it is displaced timestamps. `asetpts=N/SR/TB` resets them; `apad` then
covers the case where the mix genuinely is shorter. After the fix the master's
duration deviation is **0.000 s**, and the number of dubbed lines landing on their
source timing rose from 3/4 to **4/4**.

## 4. 🔴 QC measured the delivered file; nothing budgeted for the codec

With the audio correct, T5 (true peak) still failed — by **0.05 dB**. The master was
limited to -1.49 dBTP, exactly at the -1.5 ceiling, and AAC encoding pushed the
delivered file to -1.45.

The limit is enforced on the **PCM master**; the check measures the **AAC output**.
A lossy step sits between them and nothing left room for it.

Fixed by `am_master.BIEN_CHO_CODEC_DB = 1.0`: the mix targets one dB below the
delivery ceiling. Measured after: master -2.49 dBTP, delivered **-2.38 dBTP**, and
integrated loudness -14.62 → -14.66 LUFS, comfortably inside T4's ±1.0.

⛔ The wrong fix was available and rejected: widening QC's ceiling. That would stop
the check from describing what the customer actually receives.

### An earlier reading of T4 was wrong, and the fixture was the reason

Before the background bed was added, the same run measured -15.16 LUFS and T4
failed. It was tempting to call the -14 target unreachable — `loudnorm` itself
reported `target_offset: 1.20` and an LRA of **19.7 LU**.

⭐ But that LRA came from a source with **no background at all**: speech separated by
digital silence. Real video has a bed, `keep_background` is a contracted feature,
and with a bed the same chain lands at -14.62 LUFS. The defect was in the fixture.

🔴 That is the most dangerous way an acceptance suite can lie: reporting a defect
that does not exist, and inviting someone to "fix" a threshold to suit an input no
customer will ever submit.

## 5. 🔴 Both paid model calls would crash on a real model

`ai.goi` returns the model's **raw response text**; `ai.doc_json` is the function
that parses and schema-checks it. Two call sites skipped it:

* `giai_doan_noi_dung.py:165` passed the string straight to `long_tieng.doc_chuyen`
* `giai_doan_giong.py:268` passed the string straight to `nan_cho_vua.doc_nan`

Both immediately call `.get("doan")` on it. So **every call to a real model raised
`AttributeError`** — the translation stage had never once completed against a live
provider.

The whole suite stayed green because the shared double, `asv_media.cua_ai_gia`,
returned a **dict** in `noi_dung` — something the real door never returns. Two more
copies of the same lie lived in `test_440` and `test_441`.

⭐ A substitute must be faithful to **the contract of the thing it replaces**, not
to the expectations of its caller. All three doubles now return JSON text, so every
existing chain test exercises the real parse path, and an AST guard requires every
caller of `goi_tinh_tien` to read its response through `ai.doc_json`.

## 6. ⚠️ BLOCKER — `smart_localize` cannot cut anything

Not fixed here: fixing it is feature work, which this phase forbids.

`giai_doan_ban_bien_tap.chay` passes `hieu = ()` with the comment *"Phase 11 built
the domain; the caller is a later phase"*. `ban_bien_tap._quyet_dinh_mot_canh`
KEEPS every scene when there is no evidence — correctly, since cutting blind is
worse. Phases 12–21 never wrote that caller.

Measured, on a source whose **fourth scene contains no dialogue at all**:

```
preset smart_localize   so_canh 4   so_giu 4   so_cat 0   so_co_bang_chung 0
```

So today the "smart" preset differs from the preserve preset in exactly one way:
it **re-encodes the picture**. It pays the quality cost and delivers none of the
benefit, and Phase 21 shipped a customer-facing label promising the trade.

Pinned by `xfail(strict=True)`: the day the VLM is wired in, that test passes,
pytest reports XPASS, and the suite says the gap is closed — instead of a TODO
outliving another phase.

**Owner: Phase 27.** Related: `hieu_canh.doc_hieu_canh` asks `ai.doc_json` for a
required top-level `canh` key while `loi_nhac_canh` instructs the model to return
flat keys — a compliant response would be rejected. Latent today because nothing
calls it; it fires the moment the caller exists.

## 7. Tests and mutation results

`tests/test_448_asv_v4_e2e_nghiem_thu.py` — **19 tests + 1 xfail**, in three parts:

* **A** the heavy run (barrier `LTT_TEST_NANG`, default skipped), writing a
  machine-readable report to `LTT_ASV_E2E_RA`;
* **B** twelve checks that read the stored report and cross-check it against
  today's source — including `phien_ban_engine` for all ten stages, so **upgrading
  any engine turns the acceptance red** and the answer is to re-run it, not to edit
  the JSON;
* **C** four guards holding the defects above closed.

⛔ The heavy run never writes inside the working tree by default. A test that edits
a repo file mid-gate voids the gate that contains it (`gate.py`: *"CAY DA DOI GIUA
CHUNG"*) — a trap this repo has already paid for.

**Mutation testing: 11 mutations, 11 red** — after two holes were found and closed
(`ban_dung.kiem` could drop the master requirement, and the master could leave the
resource cross-check, both unnoticed because `test_411`'s fixture always supplied
one). Two regression tests were added there.

Regression: ASV cluster **1113 passed**, 4 skipped, 2 xfailed. V4 invariant round
`VONG_DU` 168 passed, 1 xfailed.

⚠️ And the evidence file went through the repo's own secret scanner, which flagged
**44** `bare_32_char_hex` findings — storage keys and fingerprints copied wholesale
into the report. They were removed rather than allow-listed: an acceptance report
needs numbers, not storage keys.

## 8. Debt carried forward

⚠️ **Vietnamese dubbing quality is still unmeasured.** Substituted TTS proves
placement, duration, level and mixing; it says nothing about how the product
sounds. Needs `LTT_VOICE_SIDECAR_TOKEN` and a run against :8120.

⚠️ **No live model call.** Prompt assembly, budget gating, ledger and schema
validation all ran; the network hop did not. Needs `LTT_LLM_TOKEN`.

⚠️ **`transcribe` on CUDA is unusable on this machine and not explained.** The
default device is `cuda`; with the tree's CPU-only torch and both cards serving
production, one call ran **over seven minutes with no result and no error**, versus
**7.5 s** on CPU. The acceptance therefore pins `LTT_AUTOSUB_WHISPER_DEVICE=cpu` —
an environment setting, not a substitution. **Owner: Phase 24.**

⚠️ **Dubbing sits only ~4 dB above the preserved bed** (bed -18/-19 dB, speech
-13/-15 dB in the delivered file). `am_master.NEN_GIAM_DB` attenuates the bed by a
flat -6 dB across the whole file, while its own comment describes ducking under
speech and says *"not measured on real material"*. This is that first measurement.
Whether 4 dB is enough is a mixing-policy decision, not a bug.

⚠️ **No real customer footage.** The fixture is representative in structure —
multi-scene, two speakers, continuous bed, a dialogue-free scene — but it is
synthetic, and G17 still names operator-supplied video as what closes it.

## 9. Exit gate

**PASS.** Both presets produce a usable final video: correct duration, both
streams, dubbing audible in the right places, every critical QC check green,
downloadable by the owner and 404 for anyone else, with a clean usage ledger.

⚠️ Recorded honestly alongside it: `smart_localize` produces **no cuts**, so what
passed for that preset is a re-encoded copy rather than a shortened edit. The
picture path, the render mode and the QC that governs them are all proven; the
decision that would use them is not yet connected.
