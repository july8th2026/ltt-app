# PHASE 09 REPORT — Audio Prepare, Separation and Mix

**The first GPU-lane stage, and the first stage that runs a model.**

## Entry evidence
- starting SHA: `c31b1ae`, worktree `D:\LTTSTUDIOSAPP-asv`, branch `phien/asv`
- previous gate: Phase 08 **PASS**
- allowed change scope: audio capability extraction from Cut_only_ver2, runtime executor, tests

## Trace performed (item 1)

`Cut_only ver2/nerf_engine/stages/audio.py` — `_patch_torchaudio_save:8`,
`extract_audio:48` (`-vn -ac 2 -ar 48000`), `loudnorm:54` (−14 LUFS / −1.5 dBTP),
`demucs_separate:61` (subprocess `sys.executable -c` with an inline patch script),
`mix_stems:95` (ffmpeg `amix` + per-stem `volume`).

**Environment probe — this is what changed the design:**

| | |
|---|---|
| `demucs` | 4.0.1 installed; `demucs.api` absent, `demucs.pretrained`/`demucs.apply` present |
| `torch` / `torchaudio` | **2.11.0+cpu** — `torch.cuda.is_available() → False` |
| `torchaudio.save` | `ImportError: TorchCodec is required for save_with_torchcodec` |
| `soundfile` | **not installed** |
| htdemucs checkpoints | cached in torch hub |

## Decisions

**D-09-01 — no monkey-patch, no new dependency: WAV I/O via the stdlib.**
The legacy path patches `torchaudio.save` to route through `soundfile`, because
`torchaudio ≥ 2.10` needs torchcodec and its DLLs are broken on Windows. That patch is
correct about the problem and **cannot run here** — `soundfile` is not installed.

Rather than adding a dependency to keep a monkey-patch alive, `demucs_runner.py` reads and
writes WAV with the standard `wave` module and never calls `torchaudio.save`. That removes a
dependency, a global patch into another library's internals, and an entire failure class that
only appears on Windows.

**D-09-02 — separation runs in a subprocess**, for the two reasons `job_worker.py` already
documents: the leased card arrives through the environment (`ctx.gpu_env()`), and a
torch/CUDA crash must not take the worker down with a paying customer's other job.

**D-09-03 — this stage extracts its own audio; it does not reuse Phase 08's.**
Phase 08 produces 16 kHz **mono** for ASR. Feeding that to demucs is wrong twice over: it
discards everything above 8 kHz (Nyquist) — most of what separation relies on — and it
discards the stereo image htdemucs uses to tell sources apart. So this stage extracts
44.1 kHz stereo from the **original**. Two audio renditions for two purposes is correct, not
duplication.

**D-09-04 — stem policy, stated with its limits** (item 4).
Keep `drums + bass + other`; discard `vocals`. **The thing removed is the voice**, not the
music — calling it "background removal" names it backwards, and a backwards name leads to a
backwards policy.

Prompt 09 forbids implying perfect separation, so the known limits are written into
`tach_tieng.py`: residual voice survives in `other` when heavily mixed; mouth sounds
(laughter, breath) get classified as `vocals` and **vanish** from the bed — technically
correct, perceptually a scene going quiet; melodic instruments can be mistaken for voice.

Consequence carried to Phase 18: **QC measures "the bed is not silent", not "no original
voice remains."** The second cannot be reduced to a threshold, and promising it would be
promising something unverifiable.

**D-09-05 — no creative re-mix.** The legacy `mix_stems` gives each stem its own `volume`
gain because it is doing a creative edit. MVP keeps every gain at 1.0: the balance between
instruments is the author's, and Auto Scan is dubbing, not remixing. `loudnorm` is folded
into the same ffmpeg invocation — one less decode/encode round and one less temp file to
become garbage.

**D-09-06 — the customer's isolated voice is never persisted.** `vocals.wav` exists only
inside the subprocess temp directory and dies with it. Keeping a clean, separated copy of a
customer's voice is keeping something we do not need and never promised to hold.

## Changes

| Path | Change |
|---|---|
| `apps/auto_scan_video/demucs_runner.py` | **new** — subprocess entry; stdlib WAV I/O; never selects a card |
| `apps/auto_scan_video/tach_tieng.py` | **new** — full-band extraction, separation, bed mix + loudnorm, loudness measurement, fingerprint |
| `apps/auto_scan_video/giai_doan_am_thanh.py` | **new** — the stage body |
| `apps/auto_scan_video/thi_hanh.py` | dispatches AUDIO_PREPARE |
| `apps/asv_gpu/manifest.py` | `gpu_vram_mb` comment corrected — still an estimate, and now says why |
| `tests/test_406_asv_tach_tieng.py` | **new**, 16 tests |
| `locale/en/LC_MESSAGES/messages.po` | +13 entries |

## Tests

| Command | Result |
|---|---|
| `pytest tests/test_406…` | **16 passed** |
| `pytest tests/test_402… test_403…` (with real demucs in the chain) | **35 passed** |
| `python tools/check_i18n.py` | 774, at the mark |
| `python tools/lint_app_contract.py` | `ERROR: 0` |
| `python tools/gate.py --phien asv` | **`FAIL (4/26)`** — baseline |

### Required verification

| Required | Evidence |
|---|---|
| **real small audio smoke** | `test_tach_nguon_ra_du_BON_stem` runs actual demucs and gets all four stems. Measured: 3 s stereo → **4.3 s on CPU** |
| **assigned GPU env reaches the subprocess** | `test_moi_truong_GPU_duoc_truyen_XUONG_tien_trinh_con` sets a marker in `gpu_env` and reads it back **from inside** the child; `test_tach_nguon_truyen_gpu_env_cua_JobContext` intercepts the runner to confirm the env actually used |
| no legacy GPU claim on the new path | `test_KHONG_tep_nao_cua_auto_scan_tu_chon_card` runs the AST guard over all Auto Scan files |
| validate sample rate / channels / duration / loudness | asserted in the stage body and re-asserted at the exit gate |
| cancellation / progress | `_chay_kem_moi_truong` polls the cancel callback every 0.5 s and kills the child; progress at 10/30/75/95 |

### Legacy parity (item 2)

Same approach as Phase 08, for the same reason (no legacy test suite exists):
- the ffmpeg `amix` skeleton is preserved from `mix_stems`;
- the loudness targets (−14 LUFS / −1.5 dBTP) are inherited verbatim;
- deliberate divergences are named in code — per-stem gains dropped (D-09-05), and
  `torchaudio.save` replaced (D-09-01).

## Two real bugs this phase's tests caught

**1. `do_am_luong` never worked.** `loudnorm` prints its JSON to stderr *mid-stream*, and
ffmpeg then prints its own summary lines after it. The first version sliced from `{` to
**end of string**, so `json.loads` always failed — and the error message said "could not
measure loudness", pointing at ffmpeg while the fault was in my own function. Fixed by
slicing to the last `}`. This surfaced only because the end-to-end run exercised it.

**2. A test threshold I picked out of the air.** `test_doc_ghi_wav...` asserted peak
amplitude `> 0.1`; the real value is **0.088**, because ffmpeg's `sine` outputs around
−21 dBFS — consistent with the −21.75 LUFS the loudness probe reports. Lowered to `0.01`.
The test asks *"is there real signal?"*, not *"how loud is it?"*; a guessed threshold turns
it into a second, unintended assertion.

## Invariant regression

| Inv | Result | Evidence |
|---|---|---|
| I11 resource control | PASS | subprocess env test + AST guard; no `gpu_arbiter`, no self-selected card |
| I13 cancellation | PASS | child killed, `DaHuy` raised |
| I8 durable DONE | PASS | bed validated for rate/channels/duration **before** promotion |
| I10 cache correctness | PASS | fingerprint covers source checksum, model name, stem policy, loudness targets, ffmpeg version — each pinned by its own test |
| I6/I19 | PASS | owner in key and column; vocals never persisted |
| I1–I5, I7, I9, I12, I14, I18 | PASS | 35 chain tests green |

## Diff review
- changed paths: `apps/auto_scan_video/`, `apps/asv_gpu/manifest.py`, `tests/`, `locale/en/`
- three scratch scripts created and deleted
- `.po` appended only, LF preserved (0 CRLF)
- no model weights, media or generated artifact committed; secret scan PASS

## Risks / external evidence pending

- 🔴 **RISK-05-01 remains OPEN, and this phase could not close it.**
  `asv_gpu.gpu_vram_mb` is still an estimate: `torch` here is CPU-only, so demucs never
  touched a card. The repo's rule is *"CHUA DO THI KHONG CHAY"*.
  **`TestChoBangChungNgoai::test_torch_o_may_nay_la_ban_CPU` asserts CUDA is unavailable** —
  so the moment this runs on a CUDA machine the test **fails and names the task**, instead of
  the estimate quietly surviving to production. `PENDING_EXTERNAL_EVIDENCE`.
- **RISK-09-01 (P2, new)** — separation on CPU measured at ~1.4× realtime, so a 2-hour video
  would take ~3 hours. Acceptable only because this belongs to the GPU lane. If a deployment
  runs `asv_gpu` on a CPU-only host, `max_runtime_s` (3600) will kill long runs. Worth a
  startup check in Phase 22.
- **RISK-09-02 (P2, new)** — the bed inherits any residual voice demucs leaves behind. Not a
  defect to fix here; it is a stated quality limit that Phase 18 must not pretend to measure.
- **RISK-08-01, -02** unchanged. **RISK-06-01** closed in Phase 08.

## Exit gate

**PASS.**

Gate text: *"PASS when audio artifacts required by downstream transcript/compose are
canonical, validated and resource-safe."*

`test_cong_thoat_ban_nen_la_artifact_chinh_tac_da_kiem` runs the real queue through
MEDIA_PREPARE → AUDIO_PREPARE and asserts:
- exactly **one** durable artifact (the bed), integrity `ok` by checksum;
- 44.1 kHz stereo, duration within 0.5 s of the source — drift here would push the dub
  progressively out of sync with the picture;
- **no artifact anywhere has "vocal" in its key** — the customer's isolated voice is not kept;
- lineage: the bed's `parent_keys` include MEDIA_PREPARE's artifacts.

Resource-safe: separation runs in a subprocess with the platform-assigned environment, the
handler never selects a card, and the AST guard covers all Auto Scan files.

Downstream needs are met — TRANSCRIBE consumes Phase 08's 16 kHz mono, COMPOSE/RENDER consume
this bed. Neither reads the other's rendition.

**Explicitly forbidden and confirmed absent:** no transcript, translation or render
orchestration inside this stage.

## Next phase prerequisites

Phase 10 (Transcript Engine Extraction):
1. ADR-001 D5 says TRANSCRIBE **wraps `apps/autosubvideo`'s whisperx runner in code** rather
   than delegating a job to it, because that manifest declares `requires=("ffmpeg",)` while
   declaring GPU VRAM (RISK-00-11) — delegating would route GPU work onto an ffmpeg lane;
2. its input is Phase 08's 16 kHz mono WAV, already produced and validated;
3. `torch` is CPU-only here, so a real ASR smoke may be slow — budget for
   `PENDING_EXTERNAL_EVIDENCE` if the model is unavailable or too slow to run in CI;
4. the canonical transcript contract (segment ids preserved 1:1 downstream) is set by
   `MVP_CONTRACT.md` §8 — CONTENT_PROCESS depends on that identity for lineage.
